# Company Skill Creator

交互式 Claude Code 技能创建助手。通过 5 阶段访谈流程，引导用户将公司内部知识转化为可复用的 Claude Code Skill。

## 交互流程

1. **面试** — 了解技能用途、触发场景、向用户索要已有材料（API 文档、脚本、Schema 等）
2. **搭建脚手架** — `init_skill.py` 生成目录结构
3. **自动生成** — 用户缺少的内容根据描述自动生成，低置信度标记 `⚠️ 待确认`
4. **撰写 SKILL.md** — 渐进式披露，放入脚本/参考文档的指针
5. **校验打包** — `quick_validate.py` → `package_skill.py` → 交付 `.skill` 文件

## 项目结构

```
├── start.sh                  # 一键启动前后端
├── backend/
│   ├── server.py             # FastAPI 服务（SSE 流式对话）
│   ├── client.py             # CLI 测试客户端
│   ├── agent.md              # Agent 系统提示词
│   └── skills/
│       └── company-skill-creator/
│           ├── SKILL.md
│           ├── agents/
│           ├── references/
│           └── scripts/
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # 根组件
│   │   ├── hooks/
│   │   │   ├── useChat.js    # SSE 流式对话 + 会话管理
│   │   │   └── useAttachments.js
│   │   └── components/
│   │       ├── ChatArea.jsx  # 消息列表
│   │       ├── ChatInput.jsx # 输入框 + 文件上传
│   │       └── AttachmentBar.jsx
│   └── package.json
└── doc/
    └── api.md                # API 接口文档
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- DeepSeek API Key

### 1. 配置环境

```bash
cd backend
cp env_example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
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
# 终端 1: 后端
cd backend && python server.py

# 终端 2: 前端
cd frontend && npm run dev
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
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
