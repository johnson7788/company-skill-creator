# 如何测试 Demo：创建公司内部 PPT Skill

> 使用 `demo/upload/` 中的示例材料，测试 Company Skill Creator 的完整 skill 创建流程。

## 测试目标

验证 Agent 能否基于 `demo/upload/` 中的需求材料，完成 5 阶段流程（访谈 → 脚手架 → 自动生成 → 撰写 → 校验打包），最终产出一个可安装的「公司 PPT 自动生成」`.skill` 文件。

## 测试材料

| 文件 | 大小 | 说明 |
|------|------|------|
| `demo/upload/requirements.md` | 12.7 KB | 需求收集文档（Skill 目标、公司信息、品牌规范、PPT 结构模板、示例） |
| `demo/upload/模版.pptx` | 1.8 MB | 公司 PPT 模版文件（二进制，前端会自动跳过内容读取） |

## 第一步：启动服务

```bash
# 1. 确保已配置环境变量
cd backend
cp env_example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 2. 安装前端依赖（首次）
cd ../frontend
npm install

# 3. 回到项目根目录，一键启动
cd ..
./start.sh
```

确认服务正常：

```bash
curl http://localhost:8046/health
# 预期: {"status": "ok"}
```

## 第二步：选择测试方式

### 方式 A：Web UI 测试（推荐，可上传附件）

打开 http://localhost:5173

#### 第 1 轮对话：上传材料 + 发起请求

1. 点击 📎 按钮或拖拽，上传 `demo/upload/requirements.md`
   - 附件预览条会显示文件名和大小
   - `模版.pptx` 上传后前端会跳过内容读取（二进制文件），但可在对话中说明
2. 在输入框发送第一句话，例如：

> 我想创建一个公司内部 PPT 自动生成的 skill。我已经上传了 requirements.md，里面包含了所有需求、公司信息、品牌规范和 PPT 结构模板。另外模版.pptx 也在 demo/upload/ 目录下，请参考它。帮我开始创建这个 skill。

#### 第 2 轮及后续：按 Agent 引导逐步回答

Agent 会进入访谈模式，**每次只问一个问题**。预期的对话流程：

| 轮次 | Agent 大概会问 | 你可以回答 |
|------|---------------|-----------|
| 1 | （第一轮就开始分析你上传的材料） | — |
| 2 | 确认 skill 名称和用途 | "就叫 ppt-generator，用途是帮技术部自动生成符合公司品牌规范的汇报 PPT" |
| 3 | 确认触发短语 | "帮我生成一个关于 xxx 的 PPT"、"把以下内容转成 PPT"、"生成周报/月报 PPT" |
| 4 | 确认输出格式 | ".pptx 文件，基于模版.pptx 的母版和布局" |
| 5 | 确认目标用户 | "技术部全体，主要是团队负责人和技术分享讲师" |
| 6 | 询问是否有 API 文档/脚本 | "目前模版.pptx 就是最好的参考，requirements.md 里有品牌色和布局规范" |
| 7 | 总结确认范围 | 确认无误后回复"没问题，开始吧" |

#### 后续阶段（Agent 自动执行）

Agent 确认范围后会依次：

1. **脚手架** — 调用 `init_skill.py` 生成目录结构（你会在思考过程中看到 `[工具] 调用: run_command`）
2. **自动生成** — 生成 PPT 生成脚本（python-pptx）、品牌规范参考文档等
3. **撰写 SKILL.md** — 写出完整的 skill 定义
4. **校验打包** — 调用 `quick_validate.py` 校验，然后 `package_skill.py` 打包

#### 关键验证点

- [ ] Agent 正确读取了 `requirements.md` 的内容
- [ ] Agent 提到了品牌色（`#003D7A`）、字体规范等细节
- [ ] Agent 用到了 `ppt-structure-guide.md` 中的 5 种 PPT 结构
- [ ] 生成了 python-pptx 脚本
- [ ] `⚠️ 待确认` 标记只出现在确实不确定的地方
- [ ] 最终输出了 `.skill` 文件路径
- [ ] SKILL.md 的 frontmatter 包含了具体的触发短语
- [ ] 思考过程可折叠查看

### 方式 B：CLI 测试（无附件，手动粘贴内容）

使用 CLI 客户端，适合快速验证。但无法上传文件，需要手动粘贴 `requirements.md` 中的关键内容。

```bash
# 单次模式
python backend/client.py "我想创建一个公司内部 PPT 自动生成的 skill。需求如下：技术部每月需要做工作汇报 PPT，格式固定但排版耗时。我希望用户用文字描述内容后，skill 根据公司模版自动生成 PPT，自动填充封面、套用布局、保持品牌色。公司品牌主色是 #003D7A（深蓝），辅色是 #0066CC（科技蓝），字体用微软雅黑。封面规范：深蓝背景 + 36pt 白色标题 + 16pt 浅蓝底副标题 + 汇报人日期 + 右下角 Logo。核心价值观：危机 · 专业 · 专注 · 创新。请帮我创建这个 skill。"

# 交互模式（多轮对话）
python backend/client.py
```

CLI 会实时显示：
- `🧠 思考过程`：Agent 的推理内容
- `🤖 Agent 回复`：Agent 的正式回复

### 方式 C：直接调用 API

```bash
curl -X POST http://localhost:8046/api/model/chat \
  -H "Content-Type: application/json" \
  -d '{
    "linkId": "test-001",
    "sessionId": "test-session-ppt",
    "userId": 1,
    "messages": [{
      "role": "user",
      "content": "帮我创建一个公司内部 PPT 自动生成 skill。需求如下：..."
    }]
  }'
```

## 第三步：验证生成的 Skill

Agent 会在 `backend/skills/` 下生成 skill 目录，然后打包成 `.skill` 文件。

### 检查 skill 目录结构

```bash
# 找到生成的 skill 目录
ls backend/skills/
# 预期会看到 ppt-generator/（或类似名称）
```

标准结构应为：

```
ppt-generator/
├── SKILL.md              # skill 定义文件
├── scripts/
│   ├── generate_ppt.py   # PPT 生成脚本（python-pptx）
│   └── __init__.py
├── references/
│   ├── brand-guide.md    # 品牌视觉规范
│   └── ppt-structures.md # PPT 结构模板
└── assets/
    └── 模版.pptx          # 模版文件副本
```

### 手动校验

```bash
cd backend/skills/company-skill-creator
python scripts/quick_validate.py ../../ppt-generator
```

### 手动打包

```bash
python scripts/package_skill.py ../../ppt-generator
# 会生成 ppt-generator.skill 文件
```

## 测试检查清单

### 功能验证

- [ ] Agent 成功读取上传的 `requirements.md`
- [ ] Agent 正确提取了品牌色 `#003D7A`、`#0066CC` 等
- [ ] Agent 正确提取了字体规范（微软雅黑，各级字号）
- [ ] Agent 正确提取了 5 种 PPT 结构模板
- [ ] Agent 问了触发短语（至少 3 个）
- [ ] Agent 在阶段 1 结束时做了范围确认
- [ ] 脚手架创建了正确的目录结构
- [ ] 生成的 python-pptx 脚本可运行
- [ ] `⚠️ 待确认` 标记合理（不高不低）
- [ ] SKILL.md frontmatter 包含具体触发短语
- [ ] SKILL.md 正文符合渐进式披露原则

### 异常场景

- [ ] 上传 `.pptx` 二进制文件时前端不会崩溃（预期：静默跳过内容，但文件名出现在附件列表）
- [ ] 终止对话功能正常（点击终止按钮或 `Ctrl+C`）
- [ ] 新建会话后历史消息清空

### 前端 UI

- [ ] SSE 流式回复实时渲染
- [ ] 思考过程可折叠/展开
- [ ] 工具调用可折叠/展开（`[工具] 调用: xxx` / `[工具] 完成: xxx`）
- [ ] 文件拖拽上传和按钮上传均可使用
- [ ] 附件可单个移除和全部清空

## 常见问题

### Q: 前端看不到 agent 回复？
A: 检查后端日志 `[model-chat]` 是否有输出，确认 SSE 流正常。查看浏览器 Network 标签中 `/api/model/chat` 的 EventStream。

### Q: 模版.pptx 没有被 Agent 读取？
A: 前端 `useAttachments.js` 的 `file.text()` 对二进制文件会抛异常并被 catch 跳过。这是预期行为——你需要在对话文字中告知 Agent 模版文件的路径（如 `demo/upload/模版.pptx`），Agent 会通过 `view_file` 工具去读（但二进制文件读出来是乱码）。更好的做法是在 requirements.md 中已经描述了模版的所有视觉规范。

### Q: CLI 客户端连接失败？
A: 确认 `python server.py` 已启动且端口 8046 未被占用。

### Q: Agent 卡住不动？
A: 检查 DeepSeek API 余额是否充足；确认 `.env` 中的 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_BASE_URL` 配置正确。
