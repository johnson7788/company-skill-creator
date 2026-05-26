# Company Skill Creator API 接口文档

## 概述

Company Skill Creator 是一个基于 Google ADK + DeepSeek 的交互式技能创建 Agent。后端提供 SSE（Server-Sent Events）流式接口，支持前端实时展示 Agent 的思考过程、工具调用和回复内容。

- **协议**: HTTP/1.1
- **数据格式**: JSON
- **流式协议**: SSE (text/event-stream)
- **默认端口**: `8036`
- **基础路径**: `http://<host>:8036`

---

## 1. 健康检查

### GET /health

检查服务是否正常运行。

**请求示例**:

```bash
curl http://localhost:8036/health
```

**成功响应** (200):

```json
{
  "status": "ok"
}
```

---

## 2. 文件上传

### POST /api/upload

上传文件到服务端。文件保存到 `backend/uploads/<sessionId>/` 目录，返回文件路径供 Agent 通过 `view_file` 工具读取。

- **Content-Type**: `multipart/form-data`

**请求参数**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sessionId` | string | **是** | 会话 ID，文件将存入对应的 session 子目录 |
| `files` | file[] | **是** | 一个或多个文件 |

**请求示例**:

```bash
curl -X POST http://localhost:8036/api/upload \
  -F "sessionId=sess-abc" \
  -F "files=@requirements.md" \
  -F "files=@模版.pptx"
```

**成功响应** (200):

```json
{
  "files": [
    {
      "name": "requirements.md",
      "path": "/path/to/backend/uploads/sess-abc/requirements.md",
      "size": 12696,
      "type": "text/markdown"
    },
    {
      "name": "模版.pptx",
      "path": "/path/to/backend/uploads/sess-abc/模版.pptx",
      "size": 1887778,
      "type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    }
  ]
}
```

> **说明**: 上传后的文件路径会通过 `attachment.files[].path` 传给 `/api/model/chat`，后端自动将路径追加到用户消息中告知 Agent。Agent 使用 `view_file` 工具按需读取文件内容。

---

## 3. 对话接口（SSE 流式）

### POST /api/model/chat

发送用户消息并接收 Agent 的流式响应。该接口兼容 `model_chat.py` 的 SSE 格式。

**请求头**:

| Header | 值 | 必填 |
|--------|------|------|
| Content-Type | application/json | 是 |

**请求体 (JSON)**:

```json
{
  "linkId": "string",
  "sessionId": "string",
  "userId": 1,
  "functionId": 1,
  "messages": [
    {
      "role": "user",
      "content": "string"
    }
  ],
  "type": 0,
  "attachment": {},
  "callTools": true,
  "XAPIVersion": 1
}
```

**请求参数说明**:

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `linkId` | string | **是** | - | 链路标识，用于日志追踪 |
| `sessionId` | string | **是** | - | 会话 ID，同一会话多次对话需保持一致 |
| `userId` | int | 否 | `1` | 用户 ID |
| `functionId` | int | 否 | `1` | 功能 ID |
| `messages` | array | **是** | - | 消息列表，格式为 `[{role, content}]` |
| `messages[].role` | string | **是** | - | 角色：`system` / `user` / `assistant` / `tool` |
| `messages[].content` | string | **是** | - | 消息内容（支持文本） |
| `type` | int | 否 | `0` | 消息类型：`0` = 正常对话，`-1` = 终止当前流 |
| `attachment` | object | 否 | `{}` | 附件元数据（含文件路径），详见 [附件字段说明](#4-附件字段说明) |
| `callTools` | bool | 否 | `true` | 是否允许 Agent 调用工具 |
| `XAPIVersion` | int | 否 | `1` | API 版本号 |

> **注意**: `messages` 数组中必须至少包含一条 `role` 为 `user` 的消息。Agent 通过 ADK session 自动管理对话历史，每次只需发送最新的用户消息即可。

### 终止流

设置 `type = -1` 可以终止当前正在进行的 SSE 流：

```json
{
  "linkId": "client-001",
  "sessionId": "session-abc",
  "userId": 1,
  "messages": [{"role": "user", "content": ""}],
  "type": -1
}
```

**非流式响应** (200):

```json
{
  "linkId": "client-001",
  "sessionId": "session-abc",
  "ok": true
}
```

---

## 3.1 SSE 流式响应格式

正常对话时（`type != -1`），后端返回 `text/event-stream` 格式的流式响应。

**响应头**:

```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
Connection: keep-alive
```

**SSE 事件格式**:

每行格式为 `data: <JSON>\n\n`，JSON 结构如下：

```json
{
  "linkId": "string",
  "sessionId": "string",
  "userId": 1,
  "functionId": 1,
  "message": "string",
  "reasoningMessage": "string",
  "type": 4,
  "attachment": {},
  "XAPIVersion": 1
}
```

**SSE 事件字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `linkId` | string | 链路标识（回传请求中的值） |
| `sessionId` | string | 会话 ID（回传请求中的值） |
| `userId` | int | 用户 ID（回传请求中的值） |
| `functionId` | int | 功能 ID（回传请求中的值） |
| `message` | string | Agent 的正式回复内容（增量文本块） |
| `reasoningMessage` | string | Agent 的思考过程 / 工具调用信息 |
| `type` | int | 始终为 `4`（文本流增量） |
| `attachment` | object | 附件数据（回传请求中的值） |
| `XAPIVersion` | int | API 版本号 |

**流结束信号**:

当 `message` 值为 `"[stop]"` 时，表示 SSE 流已结束：

```json
{
  "linkId": "...",
  "sessionId": "...",
  "message": "[stop]",
  "reasoningMessage": "",
  "type": 4
}
```

**事件类型说明**:

| `message` 值 | `reasoningMessage` 值 | 含义 |
|---------------|------------------------|------|
| 非空文本 | 空字符串 | Agent 正式回复的文本增量 |
| 空字符串 | `[工具] 调用: <name>` | Agent 正在调用工具 |
| 空字符串 | `[工具] 完成: <name>` | 工具调用完成 |
| 空字符串 | 非空文本 | Agent 的思考过程 |
| `"[stop]"` | 空字符串 | **流结束信号** |

---

## 3.2 完整 SSE 流示例

**请求**:

```bash
curl -X POST http://localhost:8036/api/model/chat \
  -H "Content-Type: application/json" \
  -d '{
    "linkId": "fe-001",
    "sessionId": "sess-20240524-001",
    "userId": 1,
    "messages": [
      {
        "role": "user",
        "content": "帮我创建一个检查代码质量的 skill"
      }
    ],
    "attachment": {
      "files": [
        {
          "name": "code-review-checklist.md",
          "size": 2048,
          "type": "text/markdown"
        }
      ]
    }
  }'
```

**SSE 流输出示例**:

```
data: {"linkId":"fe-001","sessionId":"sess-20240524-001","userId":1,"functionId":1,"message":"","reasoningMessage":"好的，让我来理解你的需求...","type":4,"attachment":{"files":[{"name":"code-review-checklist.md","size":2048,"type":"text/markdown"}]},"XAPIVersion":1}

data: {"linkId":"fe-001","sessionId":"sess-20240524-001","userId":1,"functionId":1,"message":"","reasoningMessage":"[工具] 调用: view_file","type":4,"attachment":{...},"XAPIVersion":1}

data: {"linkId":"fe-001","sessionId":"sess-20240524-001","userId":1,"functionId":1,"message":"","reasoningMessage":"[工具] 完成: view_file","type":4,"attachment":{...},"XAPIVersion":1}

data: {"linkId":"fe-001","sessionId":"sess-20240524-001","userId":1,"functionId":1,"message":"好的，我","reasoningMessage":"","type":4,"attachment":{...},"XAPIVersion":1}

data: {"linkId":"fe-001","sessionId":"sess-20240524-001","userId":1,"functionId":1,"message":"已经了解了你的需求。","reasoningMessage":"","type":4,"attachment":{...},"XAPIVersion":1}

data: {"linkId":"fe-001","sessionId":"sess-20240524-001","userId":1,"functionId":1,"message":"[stop]","reasoningMessage":"","type":4,"attachment":{...},"XAPIVersion":1}
```

---

## 4. 附件字段说明

文件先通过 `POST /api/upload` 上传到服务端，再将返回的路径信息填入 `attachment.files[]`。后端自动将路径追加到用户消息末尾，Agent 通过 `view_file` 工具按需读取。

**推荐结构**:

```json
{
  "attachment": {
    "files": [
      {
        "name": "requirements.md",
        "size": 12696,
        "type": "text/markdown",
        "path": "/absolute/path/to/uploads/sess-abc/requirements.md"
      }
    ]
  }
}
```

**文件内容传递策略**:

1. 前端调用 `POST /api/upload` 上传文件，获取文件路径
2. 将路径填入 `attachment.files[].path`，发送到 `POST /api/model/chat`
3. 后端从 `attachment.files` 提取路径，自动追加到用户消息：
   ```
   [已上传文件 — 如需读取内容请使用 view_file 工具]
     - /path/to/uploads/sess-abc/requirements.md
     - /path/to/uploads/sess-abc/模版.pptx
   ```
4. Agent 调用 `view_file` 工具读取文件内容（文本文件返回内容，二进制文件返回元信息）

**`files` 数组项字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 文件名 |
| `size` | number | 文件大小（字节） |
| `type` | string | MIME 类型 |
| `path` | string | 服务端文件绝对路径，供 Agent 通过 `view_file` 读取 |

---

## 5. 错误响应

### 4.1 参数校验失败 (400)

```json
{
  "detail": "linkId and sessionId are required"
}
```

```json
{
  "detail": "messages array is required and must not be empty"
}
```

```json
{
  "detail": "no user message found"
}
```

### 4.2 流中断（非标准 HTTP 错误）

SSE 流过程中可能因以下原因中断：

| 场景 | 表现 | 原因 |
|------|------|------|
| 用户主动终止 | 流正常结束（发送 `[stop]`） | `type = -1` 触发 |
| 客户端断开 | 流中断 | `request.is_disconnected()` 为 true |
| Agent 异常 | 流中断 | Agent 执行出错 |

---

## 6. 完整前端调用流程

```
┌──────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────┐
│  前端 UI  │      │ POST /api/   │      │ POST /api/   │      │  Agent   │
│          │      │   upload     │      │ model/chat   │      │  (ADK)   │
└────┬─────┘      └──────┬───────┘      └──────┬───────┘      └────┬─────┘
     │                   │                    │                    │
     │ 0. 用户选择文件     │                    │                    │
     │──────────────────>│                    │                    │
     │  FormData + files  │                    │                    │
     │                   │ 返回文件路径        │                    │
     │<──────────────────│                    │                    │
     │                   │                    │                    │
     │ 1. 用户输入+文件路径│                    │                    │
     │───────────────────────────────────────>│                    │
     │  POST + SSE 连接                        │                    │
     │                                          │ 2. 转发用户消息    │
     │                                          │──────────────────>│
     │                                          │ 文件路径已追加到    │
     │                                          │ 用户消息末尾        │
     │                                          │                    │
     │                                          │ 3. Agent 调用      │
     │                                          │  view_file 读附件   │
     │                                          │<──────────────────│
     │                                          │──────────────────>│
     │                                          │                    │
     │                                          │ 4. reasoningMessage│
     │  5. 思考/工具事件                         │<──────────────────│
     │<────────────────────────────────────────│                    │
     │  data: {reasoning...}                   │                    │
     │                                          │                    │
     │                                          │ 6. message 文本块   │
     │  7. 渲染回复文本                          │<──────────────────│
     │<────────────────────────────────────────│                    │
     │  data: {message...}                     │                    │
     │                                          │                    │
     │                                          │ 8. [stop] 信号      │
     │  9. 流结束                               │                    │
     │<────────────────────────────────────────│                    │
     │  data: {message: "[stop]"}              │                    │
```

---

## 7. 前端集成注意事项

### 7.1 Session 管理

- 每次新对话需要生成唯一的 `sessionId`（推荐使用 `crypto.randomUUID()`）
- 同一会话中的所有消息必须使用相同的 `sessionId`
- Agent 通过 ADK session 自动维护对话历史，前端**无需**回传历史消息

### 7.2 SSE 消费（JavaScript）

```javascript
async function sendMessage(sessionId, message, attachment) {
  const response = await fetch('/api/model/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      linkId: 'fe-' + Date.now(),
      sessionId: sessionId,
      userId: 1,
      messages: [{ role: 'user', content: message }],
      attachment: attachment || {}
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // 保留不完整的行

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const data = JSON.parse(line.slice(6));

      if (data.message === '[stop]') {
        console.log('流结束');
        return;
      }

      if (data.reasoningMessage) {
        console.log('思考:', data.reasoningMessage);
        // 渲染思考过程到 UI
      }

      if (data.message) {
        console.log('回复:', data.message);
        // 渲染回复内容到 UI（增量追加）
      }
    }
  }
}
```

### 7.3 文件上传处理

```javascript
async function uploadFiles(sessionId, files) {
  const formData = new FormData();
  formData.append('sessionId', sessionId);
  files.forEach(f => formData.append('files', f));

  const res = await fetch('/api/upload', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) throw new Error('上传失败');
  const data = await res.json();
  // data.files = [{ name, path, size, type }, ...]
  return data.files;
}
```

### 7.4 终止对话

```javascript
async function abortSession(sessionId) {
  await fetch('/api/model/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      linkId: 'fe-abort',
      sessionId: sessionId,
      messages: [{ role: 'user', content: '' }],
      type: -1
    })
  });
}
```

---

## 8. 环境配置

后端服务依赖以下环境变量（`.env` 文件）：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-xxx` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-v4-pro` |
| `DEEPSEEK_BASE_URL` | API 基础地址 | `https://api.deepseek.com/v1` |
| `PORT` | 服务端口 | `8036` |

---

## 9. 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-05-24 | 初始版本，包含健康检查和 SSE 流式对话接口 |
| 1.1.0 | 2026-05-25 | 新增 `POST /api/upload` 文件上传端点；`view_file` 支持二进制文件；附件改为路径传递方式 |
