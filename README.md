# Company Skill Creator

交互式 Claude Code Skill 创建助手。通过 5 阶段访谈流程，引导用户将公司内部知识（API 文档、数据库 Schema、业务规范、脚本等）转化为可复用的 Claude Code Skill。

## 解决的问题

企业内部创建 Skill 时经常遇到这些痛点：

- **知识在脑子里，没写成文档** — 口头描述就够了，Agent 自动补全缺失内容
- **不确定从哪开始** — Agent 逐步访谈，每次只问一个问题
- **API / Schema 不公开** — Claude 训练数据里没有，需要用户提供，Agent 整理成 references/
- **自动生成的内容不放心** — 低置信度内容标记 `⚠️ 待确认`，用户 review 即可

## 架构

```
用户浏览器                    后端服务                       AI Agent
┌──────────┐    SSE 流式     ┌──────────┐    ADK Runner   ┌──────────────┐
│ React 前端 │ ◄────────────► │ FastAPI   │ ◄────────────► │ DeepSeek LLM │
│ (Vite)    │  POST /chat    │ server.py │                │ + Skill 提示词│
└──────────┘                └──────────┘                └──────────────┘
                                  │                             │
                                  │ 工具调用                      │ 工具定义
                                  ▼                             ▼
                           ┌──────────┐                ┌──────────────┐
                           │ run_command │              │ view_file    │
                           │ (shell)     │              │ (文件读取)    │
                           └──────────┘                └──────────────┘
                                  │                             │
                                  ▼                             ▼
                           ┌──────────────────────────────────────┐
                           │        skills/company-skill-creator/ │
                           │  SKILL.md │ scripts/ │ references/   │
                           └──────────────────────────────────────┘
```

- **前端**：React + Vite，SSE 流式消费，实时渲染 Agent 思考和回复
- **后端**：FastAPI + Google ADK，管理 Agent 生命周期和会话
- **Agent**：DeepSeek 模型，加载 company-skill-creator 自身作为 Skill，具备 `run_command` 和 `view_file` 工具
- **Skill 目录**：Agent 本身也是一个标准 Skill，包含 SKILL.md、scripts、references，可独立打包分发

## 交互流程（5 阶段）

| 阶段 | 做什么 | 产出 |
|------|--------|------|
| 1. 面试访谈 | 了解技能用途、触发场景、收集已有材料 | 需求文档 |
| 2. 搭建脚手架 | `init_skill.py` 生成标准目录结构 | `SKILL.md` + `scripts/` + `references/` + `assets/` |
| 3. 自动生成 | 补全用户缺少的脚本/参考文档/模板 | 生成文件，低置信度标记 `⚠️ 待确认` |
| 4. 撰写 SKILL.md | 渐进式披露，精炼主文件，细节放 references/ | 完整的 SKILL.md |
| 5. 校验打包 | `quick_validate.py` → `package_skill.py` | `.skill` 文件交付 |

## 项目结构

```
company-skill-creator/
├── start.sh                          # 一键启动前后端
├── backend/
│   ├── server.py                     # FastAPI 服务（SSE 流式、会话管理）
│   ├── client.py                     # CLI 测试客户端
│   ├── agent.md                      # Agent 系统提示词（5 阶段详细指令）
│   ├── env_example                   # 环境变量模板
│   └── skills/
│       └── company-skill-creator/    # Agent 自身对应的 Skill
│           ├── SKILL.md              # Skill 定义（触发条件、工作流、规范）
│           ├── agents/
│           │   └── interviewer.md    # 访谈问题模板
│           ├── references/
│           │   └── company-context.md # 公司上下文收集模板
│           └── scripts/
│               ├── init_skill.py     # 脚手架生成
│               ├── quick_validate.py # SKILL.md 格式校验
│               ├── package_skill.py  # 打包 .skill 文件
│               └── utils.py          # 通用工具函数
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx                   # 根组件
│       ├── App.css
│       ├── main.jsx
│       ├── hooks/
│       │   ├── useChat.js            # SSE 流式对话 + 会话管理
│       │   └── useAttachments.js     # 文件上传状态管理
│       └── components/
│           ├── ChatArea.jsx          # 消息列表（含折叠的思考过程）
│           ├── ChatInput.jsx         # 输入框 + 文件上传按钮
│           └── AttachmentBar.jsx     # 附件预览条
├── demo/
│   └── upload/                       # 示例：用户提交的材料
│       ├── requirements.md           # 统一的需求收集文档（公司信息+品牌规范+PPT结构+示例）
│       └── 模版.pptx                 # 公司 PPT 模版文件
└── doc/
    └── api.md                        # API 接口详细文档
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- DeepSeek API Key

### 1. 配置环境变量

```bash
cd backend
cp env_example .env
```

编辑 `.env`，填入 API 密钥：

```env
DEEPSEEK_API_KEY=sk-your-api-key
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 启动

```bash
./start.sh
```

启动后访问：

| 地址 | 说明 |
|------|------|
| http://localhost:5173 | 前端对话界面 |
| http://localhost:8046 | 后端 API |
| http://localhost:8046/docs | Swagger API 文档 |

按 `Ctrl+C` 停止所有服务。

### 手动启动

```bash
# 终端 1：后端
cd backend && python server.py

# 终端 2：前端
cd frontend && npm run dev
```

## 使用指南

### 创建一个企业 Skill

1. 打开前端界面 http://localhost:5173
2. 告诉 Agent 你想创建什么 Skill，例如：
   - "帮我创建一个代码审查 skill，基于我们团队的 review-checklist.md"
   - "我想做一个自动生成周报 PPT 的 skill，这是我们的模版和品牌规范"
3. Agent 会逐步访谈，每次只问一个问题
4. 在对话过程中上传你的材料（API 文档、Schema、脚本、模版等）
5. Agent 自动补全缺失内容，标记 `⚠️ 待确认` 的地方需要你 review
6. 最终生成 `.skill` 文件，可直接安装使用

### Demo 材料

`demo/upload/` 目录提供了一份完整的示例——一个「公司 PPT 自动生成 Skill」的需求材料：

- **`requirements.md`**：一站式需求收集文档，包含 Skill 目标、公司信息、品牌视觉规范（色值/字体/布局）、5 种 PPT 结构模板（周月报/技术分享/项目复盘/季度总结/产品介绍）、完整的填写示例
- **`模版.pptx`**：公司 PPT 模版文件

你可以参考这个示例来准备自己的 Skill 需求材料。

### 上传材料建议

| 材料类型 | 示例 | 作用 |
|----------|------|------|
| 需求描述 | 几句话说明要做什么 | Agent 理解目标 |
| API 文档 | Swagger/OpenAPI、curl 示例 | 生成 API 调用脚本 |
| 数据 Schema | 表结构、字段说明 | 生成数据查询参考 |
| 脚本/工具 | 现有 Python/Shell 脚本 | 直接集成到 Skill |
| 模版文件 | .pptx、代码脚手架 | 作为 assets/ 打包 |

没有正式文档也没关系，口头描述即可，Agent 会生成草稿供你 review。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/upload` | 文件上传（multipart/form-data） |
| POST | `/api/model/chat` | SSE 流式对话 |

详细文档见 [`doc/api.md`](doc/api.md)。

### 请求示例

```json
POST /api/model/chat
{
  "linkId": "fe-001",
  "sessionId": "sess-abc",
  "userId": 1,
  "messages": [{ "role": "user", "content": "帮我创建一个代码审查 skill" }],
  "attachment": {
    "files": [{ "name": "review-checklist.md", "size": 2048, "type": "text/markdown" }]
  }
}
```

SSE 响应格式：`data: { "message": "...", "reasoningMessage": "...", "type": 4 }`，以 `message: "[stop]"` 结束。

## 前端功能

- SSE 流式对话，实时渲染 Agent 回复
- 思考过程可折叠展示（思维链 + 工具调用）
- 文件上传（按钮 / 拖拽），支持常见文本格式
- 附件预览条，可移除或清空
- 会话管理，支持新建 / 终止
- 生产构建：`npm run build`，由 FastAPI 直接 serve

## CLI 客户端

```bash
python backend/client.py                      # 交互模式
python backend/client.py "帮我创建一个技能"      # 单次模式
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18 + Vite |
| 后端 | FastAPI + Uvicorn |
| Agent 框架 | Google ADK (Agent Development Kit) |
| LLM | DeepSeek (via LiteLLM) |
| Skill 脚本 | Python 3.10+ (python-pptx, PyYAML) |
