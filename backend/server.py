"""
FastAPI server for Company Skill Creator (Google ADK).
Interactive skill creation agent that guides users through 5 phases:
  1. Interview — gather requirements and existing materials
  2. Scaffold — init_skill.py to create directory structure
  3. Auto-generate — fill in missing scripts/references/templates, mark with ⚠️
  4. Write SKILL.md — progressive disclosure, pointers to references/
  5. Validate & package — quick_validate.py → package_skill.py → deliver

Streams agent events (thinking, tool calls, content) via SSE.
Interface compatible with model_chat.py SSE format:
  - type 4 = text stream delta (message for final text, reasoningMessage for thinking)
  - type -1 = abort

Usage:
    fastapi run server.py
    or
    python server.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset
from google.genai import types

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress verbose LiteLLM debug logs
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

AGENT_PROMPT = (Path(__file__).parent / "agent.md").read_text()

# ---------------------------------------------------------------------------
# Request model (compatible with model_chat.py)
# ---------------------------------------------------------------------------


class ModelChatMessage(BaseModel):
    role: str  # system | user | assistant | tool
    content: str


class ModelChatRequest(BaseModel):
    linkId: str
    sessionId: str
    userId: int = 1
    functionId: int = 1
    messages: list[ModelChatMessage] = []
    type: int = 0  # -1 = abort
    attachment: Any = {}
    callTools: bool = True
    XAPIVersion: Any = 1
    activeSkills: list[str] | None = None  # skill dir names to activate; defaults to ["company-skill-creator"]

    @field_validator("attachment", mode="before")
    @classmethod
    def _coerce_attachment(cls, v: Any) -> dict[str, Any]:
        if isinstance(v, dict):
            return v
        return {}

    @field_validator("XAPIVersion", mode="before")
    @classmethod
    def _coerce_xapi_version(cls, v: Any) -> int:
        try:
            return int(v) if v is not None else 1
        except (TypeError, ValueError):
            return 1


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
_DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "")
_DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "")
_APP_NAME = os.environ.get("APP_NAME", "company_skill_creator")

if not _DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY 未设置，请在 .env 文件或环境变量中配置")
if not _DEEPSEEK_MODEL:
    raise RuntimeError("DEEPSEEK_MODEL 未设置，请在 .env 文件或环境变量中配置")
if not _DEEPSEEK_BASE_URL:
    raise RuntimeError("DEEPSEEK_BASE_URL 未设置，请在 .env 文件或环境变量中配置")

# LiteLLM model string format: "provider/model-name"
# Allow user to provide full string (e.g. "deepseek/deepseek-chat") or short name
if "/" in _DEEPSEEK_MODEL:
    _LITELLM_MODEL = _DEEPSEEK_MODEL
else:
    _LITELLM_MODEL = f"deepseek/{_DEEPSEEK_MODEL}"

skills_dir = Path(__file__).parent / "skills"
uploads_dir = Path(__file__).parent / "uploads"

# ---------------------------------------------------------------------------
# Tools for skills (run_command, view_file)
# ---------------------------------------------------------------------------


def run_command(command: str) -> str:
    """Execute a shell command and return stdout + stderr.

    The working directory is set to the skills root.
    Available skill scripts:
      - scripts/init_skill.py — scaffold a new skill directory
      - scripts/quick_validate.py — validate SKILL.md frontmatter
      - scripts/package_skill.py — package skill into .skill file

    Args:
        command: The shell command to execute.
    """
    import subprocess

    logger.info("[tool] run_command: %s", command)
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=120, cwd=str(skills_dir / "company-skill-creator")
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr]\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[exit code: {result.returncode}]"
        logger.info("[tool] run_command output (first 500 chars): %s", output[:500])
        return output
    except subprocess.TimeoutExpired:
        return f"[错误] 命令执行超时 (120s): {command}"
    except Exception as exc:
        return f"[错误] 命令执行失败: {exc}"


def view_file(file_path: str) -> str:
    """Read and return the content of a file.

    Path resolution for relative paths:
      1. First try relative to the uploads directory (user-uploaded files)
      2. Then try relative to the skills root (built-in skill files)

    Handles both text and binary files. Text files are returned as-is
    (truncated at 20000 chars). Binary files return metadata.

    Common files:
      - SKILL.md — the company-skill-creator skill definition
      - agents/interviewer.md — interview question templates
      - references/company-context.md — company context capture template
      - Any user-uploaded file under uploads/<sessionId>/

    Args:
        file_path: Absolute or relative path to the file.
    """
    logger.info("[tool] view_file: %s", file_path)
    try:
        path = Path(file_path)
        if not path.is_absolute():
            # Try uploads dir first, then skills dir
            candidate = uploads_dir / file_path
            if candidate.exists():
                path = candidate
            else:
                path = skills_dir / "company-skill-creator" / file_path

        if not path.exists():
            return f"[错误] 文件不存在: {path}"

        # Try reading as text first
        try:
            content = path.read_text(encoding="utf-8")
            if len(content) > 20000:
                content = content[:20000] + "\n\n... [文件过长，已截断]"
            return content
        except UnicodeDecodeError:
            # Binary file — return metadata
            stat = path.stat()
            return (
                f"[二进制文件]\n"
                f"  文件名: {path.name}\n"
                f"  路径: {path}\n"
                f"  大小: {stat.st_size:,} bytes\n"
                f"  提示: 此文件无法以文本方式读取，请使用 run_command 调用对应工具处理"
                f"（如 python-pptx 读取 .pptx、PyPDF2 读取 .pdf、Pillow 读取图片）"
            )
    except Exception as exc:
        return f"[错误] 无法读取文件: {exc}"


# ---------------------------------------------------------------------------
# Agent setup (ADK)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Skill discovery and loading
# ---------------------------------------------------------------------------


def _parse_skill_md(skill_md_path: Path) -> dict[str, str]:
    """Parse YAML frontmatter from SKILL.md and return {name, description, dir_name}.

    Falls back to directory name if frontmatter is missing or malformed.
    """
    import re

    dir_name = skill_md_path.parent.name
    try:
        content = skill_md_path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if match:
            import yaml
            frontmatter = yaml.safe_load(match.group(1))
            if isinstance(frontmatter, dict):
                return {
                    "name": frontmatter.get("name", dir_name),
                    "description": frontmatter.get("description", "").strip(),
                    "dir_name": dir_name,
                }
    except Exception:
        pass
    return {"name": dir_name, "description": "", "dir_name": dir_name}


def _discover_skills() -> list[dict[str, str]]:
    """Scan skills directory and return list of available skills."""
    result = []
    if not skills_dir.is_dir():
        return result
    for d in sorted(skills_dir.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            result.append(_parse_skill_md(d / "SKILL.md"))
    return result


def _build_skill_toolset(skill_names: list[str]) -> skill_toolset.SkillToolset:
    """Build a SkillToolset from a list of skill directory names."""
    skills = []
    for name in skill_names:
        path = skills_dir / name
        if path.is_dir() and (path / "SKILL.md").exists():
            skills.append(load_skill_from_dir(path))
            logger.info("Loaded skill: %s", name)
        else:
            logger.warning("Skill not found: %s", name)
    return skill_toolset.SkillToolset(skills=skills)


# Default skill toolset for backward compatibility (used when no activeSkills specified)
_default_skill_toolset = _build_skill_toolset(["company-skill-creator"])

# ---------------------------------------------------------------------------
# Runner setup
# ---------------------------------------------------------------------------
session_service = InMemorySessionService()


def _build_runner(active_skills: list[str] | None = None) -> tuple[Runner, LlmAgent]:
    """Build a Runner and LlmAgent with the specified active skills.

    Returns (runner, agent) tuple so the agent can be used for abort tracking if needed.
    """
    skill_names = active_skills or ["company-skill-creator"]
    toolset = _build_skill_toolset(skill_names)
    agent = LlmAgent(
        name="company_skill_creator",
        model=LiteLlm(
            model=_LITELLM_MODEL,
            api_key=_DEEPSEEK_API_KEY,
            api_base=_DEEPSEEK_BASE_URL,
        ),
        instruction=AGENT_PROMPT,
        description="Interactive company skill creator. Guides users through interview, scaffold, auto-generate, write, validate, and package phases to create reusable Claude Code skills for internal company workflows.",
        tools=[run_command, view_file, toolset],
    )
    runner = Runner(
        agent=agent,
        app_name=_APP_NAME,
        session_service=session_service,
    )
    return runner, agent

# ---------------------------------------------------------------------------
# Abort tracking
# ---------------------------------------------------------------------------
_session_abort_events: dict[str, asyncio.Event] = {}
_active_invocations: dict[str, str] = {}  # session_id → invocation_id

# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _build_base(req: ModelChatRequest) -> dict[str, Any]:
    return {
        "linkId": req.linkId,
        "sessionId": req.sessionId,
        "userId": req.userId,
        "functionId": req.functionId,
        "attachment": req.attachment or {},
        "XAPIVersion": req.XAPIVersion,
    }


def _sse_line(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Company Skill Creator", version="1.0.0", lifespan=lifespan)

# Static file serving for frontend
# Production: serve built React app from frontend/dist/
# Development: use Vite dev server with proxy (see vite.config.js)
_frontend_dir = Path(__file__).parent.parent / "frontend"
_dist_dir = _frontend_dir / "dist"
if _dist_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_dist_dir / "assets")), name="assets")


@app.get("/")
async def index():
    """Serve the frontend chat interface."""
    # Production: serve built React app
    dist_index = _dist_dir / "index.html"
    if dist_index.exists():
        return FileResponse(dist_index)
    # Development: Vite dev server handles the frontend
    return {"message": "Company Skill Creator API", "docs": "/docs", "frontend": "Run `npm run dev` in frontend/ for the chat UI"}


@app.post("/api/model/chat")
async def model_chat(request: Request, body: ModelChatRequest):
    """Stream company skill creator agent events in model_chat SSE format."""

    # --- Abort ---
    if body.type == -1:
        abort_event = _session_abort_events.get(body.sessionId)
        if abort_event:
            abort_event.set()
            logger.info("[model-chat] abort session=%s", body.sessionId)
        return {"linkId": body.linkId, "sessionId": body.sessionId, "ok": True}

    # --- Validate ---
    if not body.linkId or not body.sessionId:
        raise HTTPException(status_code=400, detail="linkId and sessionId are required")
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages array is required and must not be empty")

    logger.info(
        "[model-chat] 请求开始: linkId=%s sessionId=%s userId=%s functionId=%s",
        body.linkId, body.sessionId, body.userId, body.functionId,
    )

    base = _build_base(body)
    user_id = str(body.userId)
    session_id = body.sessionId

    # Build runner and agent with the requested active skills
    runner, _agent = _build_runner(body.activeSkills)

    # Log user input
    for msg in body.messages:
        logger.info("[model-chat] [%s] %s", msg.role, msg.content)

    # Ensure session exists (ADK manages conversation history within sessions)
    await _ensure_session(user_id, session_id)

    # Build the new user message - only send the last user message
    # (ADK session automatically maintains conversation history)
    user_messages = [m for m in body.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="no user message found")
    last_user_msg = user_messages[-1].content

    # Append uploaded file paths to the user message so the agent knows
    # what files are available and can read them via view_file
    uploaded_paths = _extract_uploaded_paths(body.attachment)
    if uploaded_paths:
        paths_text = "\n".join(f"  - {p}" for p in uploaded_paths)
        last_user_msg += (
            f"\n\n[已上传文件 — 如需读取内容请使用 view_file 工具]\n{paths_text}"
        )

    new_message = types.Content(
        role="user",
        parts=[types.Part(text=last_user_msg)],
    )

    # Register abort event for this session
    abort_event = asyncio.Event()
    _session_abort_events[session_id] = abort_event

    async def _stream():
        full_text = ""
        trace_status = "not_started"

        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE),
            ):
                # Check abort signal
                if abort_event.is_set():
                    trace_status = "aborted"
                    break

                if await request.is_disconnected():
                    trace_status = "disconnected"
                    break

                # --- Tool calls → reasoningMessage ---
                for fc in event.get_function_calls():
                    yield _sse_line({
                        **base,
                        "message": "",
                        "reasoningMessage": f"[工具] 调用: {fc.name}",
                        "type": 4,
                    })

                # --- Tool responses → reasoningMessage ---
                for fr in event.get_function_responses():
                    yield _sse_line({
                        **base,
                        "message": "",
                        "reasoningMessage": f"[工具] 完成: {fr.name}",
                        "type": 4,
                    })

                # --- Partial text chunks ---
                if event.partial and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            full_text += part.text
                            if getattr(part, "thought", False):
                                # Model thinking/reasoning → reasoningMessage
                                yield _sse_line({
                                    **base,
                                    "message": "",
                                    "reasoningMessage": part.text,
                                    "type": 4,
                                })
                            else:
                                # Actual response → message
                                yield _sse_line({
                                    **base,
                                    "message": part.text,
                                    "reasoningMessage": "",
                                    "type": 4,
                                })

                # --- Final response check ---
                if event.is_final_response():
                    if not event.partial and event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text and part.text not in full_text:
                                full_text += part.text
                                if getattr(part, "thought", False):
                                    yield _sse_line({
                                        **base,
                                        "message": "",
                                        "reasoningMessage": part.text,
                                        "type": 4,
                                    })
                                else:
                                    yield _sse_line({
                                        **base,
                                        "message": part.text,
                                        "reasoningMessage": "",
                                        "type": 4,
                                    })

        except Exception as exc:
            logger.error("[model-chat] agent stream error: %s", exc)
            trace_status = "stream_error"
        finally:
            _session_abort_events.pop(session_id, None)

        # Log model output
        if full_text:
            logger.info("[model-chat] [assistant] %s", full_text)

        # Send stop signal
        yield _sse_line({**base, "message": "[stop]", "reasoningMessage": "", "type": 4})
        logger.info("[model-chat] 请求结束: sessionId=%s status=%s", body.sessionId, trace_status)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/upload")
async def upload_files(sessionId: str = Form(...), files: list[UploadFile] = File(...)):
    """Upload files for a session. Saves to backend/uploads/<sessionId>/.

    Returns file metadata including absolute paths that the agent can
    use with view_file to read the content.
    """
    # Sanitize sessionId to prevent path traversal
    safe_session = Path(sessionId).name
    if safe_session != sessionId or not safe_session:
        raise HTTPException(status_code=400, detail="invalid sessionId")

    session_upload_dir = uploads_dir / safe_session
    session_upload_dir.mkdir(parents=True, exist_ok=True)

    result_files = []
    for f in files:
        # Sanitize filename — keep only the basename
        safe_name = Path(f.filename).name
        if not safe_name:
            continue

        file_path = session_upload_dir / safe_name

        # Write file to disk
        content = await f.read()
        file_path.write_bytes(content)

        result_files.append({
            "name": safe_name,
            "path": str(file_path.resolve()),
            "size": len(content),
            "type": f.content_type or "application/octet-stream",
        })
        logger.info("[upload] saved: %s (%s bytes)", file_path, len(content))

    return {"files": result_files}


def _extract_uploaded_paths(attachment: Any) -> list[str]:
    """Extract uploaded file paths from the attachment metadata."""
    paths = []
    if isinstance(attachment, dict):
        for f in attachment.get("files", []):
            p = f.get("path", "")
            if p and Path(p).exists():
                paths.append(p)
    return paths


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/skills")
async def list_skills():
    """Return list of available skills with name and description from SKILL.md frontmatter."""
    discovered = _discover_skills()
    return {"skills": discovered}


async def _ensure_session(user_id: str, session_id: str) -> None:
    """Get or create an ADK session for the given user/session."""
    session = await session_service.get_session(
        app_name=_APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        await session_service.create_session(
            app_name=_APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        logger.info("[session] created session: user=%s session=%s", user_id, session_id)


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8036)
