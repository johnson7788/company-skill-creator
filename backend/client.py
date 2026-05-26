"""
Simple client for Company Skill Creator (Google ADK).
Sends user input to the SSE endpoint and prints thinking content +
agent reply content in real-time.

Usage:
    python client.py                    # interactive mode
    python client.py "帮我创建一个技能"   # single query mode
"""

import asyncio
import json
import sys
import time

import httpx

BASE_URL = "http://localhost:8036"
ENDPOINT = f"{BASE_URL}/api/model/chat"


def fmt_time() -> str:
    return time.strftime("%H:%M:%S", time.localtime()) + f".{int(time.time() * 1000) % 1000:03d}"


async def chat(prompt: str, session_id: str = "client-session"):
    """Send a single chat message and stream the response."""
    t_start = time.perf_counter()
    print(f"\n{'='*60}")
    print(f"[{fmt_time()}] 用户: {prompt}")
    print(f"{'='*60}")

    # Collect thinking and agent content separately
    thinking_lines: list[str] = []
    agent_lines: list[str] = []
    thinking_displayed = False
    agent_displayed = False

    request_body = {
        "linkId": "client",
        "sessionId": session_id,
        "userId": 1,
        "messages": [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                ENDPOINT,
                json=request_body,
                timeout=600.0,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue

                    msg = data.get("message", "")
                    reasoning = data.get("reasoningMessage", "")

                    # --- Thinking content (reasoningMessage) ---
                    if reasoning:
                        if not thinking_displayed:
                            print(f"\n[{fmt_time()}] 🧠 思考过程:")
                            print("-" * 40)
                            thinking_displayed = True
                        thinking_lines.append(reasoning)
                        print(reasoning, end="", flush=True)

                    # --- Agent reply content (message) ---
                    if msg:
                        if msg == "[stop]":
                            continue
                        if not agent_displayed:
                            if thinking_displayed:
                                print(f"\n{'-'*40}")
                            print(f"\n[{fmt_time()}] 🤖 Agent 回复:")
                            print("-" * 40)
                            agent_displayed = True
                        agent_lines.append(msg)
                        print(msg, end="", flush=True)

        except httpx.ConnectError:
            print(f"\n[{fmt_time()}] 连接失败: 无法连接到 {BASE_URL}")
            print("请确保 server.py 已启动 (python server.py)")
            return
        except Exception as e:
            print(f"\n[{fmt_time()}] 请求错误: {e}")
            return

    t_end = time.perf_counter()

    # Print summary
    print(f"\n\n[{fmt_time()}] 完成 — 耗时 {t_end - t_start:.2f}s")

    if thinking_lines:
        thinking_text = "".join(thinking_lines)
        print(f"  思考内容: {len(thinking_text)} 字符")
    if agent_lines:
        agent_text = "".join(agent_lines)
        print(f"  回复内容: {len(agent_text)} 字符")


async def interactive():
    """Interactive chat mode."""
    print(f"Company Skill Creator 交互客户端")
    print(f"服务端: {BASE_URL}")
    print(f"输入 'quit' 或 'exit' 退出")
    print(f"输入 'clear' 开始新的会话")

    session_id = f"interactive-{int(time.time())}"

    # Health check
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/health", timeout=5)
            r.raise_for_status()
            print(f"[{fmt_time()}] 服务健康检查通过")
    except Exception:
        print(f"[{fmt_time()}] 警告: 服务不可达 ({BASE_URL}/health)")
        print("请确保 server.py 已启动")
        return

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("再见！")
            break

        if user_input.lower() == "clear":
            session_id = f"interactive-{int(time.time())}"
            print(f"[{fmt_time()}] 已开始新会话: {session_id}")
            continue

        await chat(user_input, session_id)


async def main():
    if len(sys.argv) > 1:
        # Single query mode
        prompt = " ".join(sys.argv[1:])
        await chat(prompt)
    else:
        await interactive()


if __name__ == "__main__":
    asyncio.run(main())
