# 解忧小铺 · AI 智能助手 (Chat-Assistant v2.0)

一个生产级的全栈多模型 AI 对话平台，基于 **FastAPI + SQLAlchemy (SQLite) + LangChain + 模块化原生 ES 前端** 构建。支持真实 SSE 流式输出、多会话持久化管理、游客即用 + JWT 账号体系、联网搜索引用、多模态视觉理解与 AI 绘图/改图、自定义角色工坊，以及完整的自动化测试与 Docker 一键部署。

---

## 核心特性

- **多模型懒加载引擎**：支持 DeepSeek、通义千问（Qwen + Qwen-VL）、腾讯混元、智谱 GLM、字节豆包（Doubao + Seedream），按需配置即可启动，不会因某个 Key 缺失导致服务崩溃。
- **真实 SSE 流式对话**：基于 `POST /api/v1/chat/stream` 逐 token 推送，支持实时状态反馈（联网检索 / 图片分析 / 绘图 / 思考）、真正中断生成（AbortController + 服务端断连检测）。
- **多会话持久化管理**：SQLite + SQLAlchemy 持久化，侧边栏支持按时间分组（置顶 / 今天 / 昨天 / 更早）、全文搜索、置顶、重命名、单条消息删除、重试生成、编辑重发、以及 Markdown / JSON 导出。
- **游客即用 + 可选账号同步**：打开即用（通过 `X-Guest-ID` 自动持久化历史），注册或登录（PBKDF2 密码哈希 + JWT 鉴权）时自动将游客历史对话与自定义角色无缝迁移到个人账号。
- **角色工坊 (Persona Studio)**：内置 5 位个性鲜明的专属角色（Zoe / Luna / Ethan / Felix / 小Y），并支持自由创建、编辑和删除自定义角色（含系统提示词、默认模型、图标和主题配色）。
- **精准意图路由 + 手动控制**：支持联网搜索（自动 / 开启 / 关闭，带可折叠参考来源卡片）和 AI 绘图（自动 / 强制生图 / 关闭），修复了“生成代码”误触发画图、“怎么看”误触发搜索等问题。
- **富文本与专业渲染**：完整 Markdown、代码高亮与一键复制代码栏、KaTeX 数学公式渲染（`$...$` / `$$...$$`）、图片拖拽/粘贴上传、全屏灯箱预览与原图下载、亮色/暗色主题切换。
- **工程化与可观测性**：分层目录架构、Pydantic Settings 配置管理、请求级 `X-Request-ID` 结构化日志、滑动窗口 API 限流、健康检查端点（`/api/health`）、`pytest` 单元测试、Docker & Vercel 部署支持。

---

## 项目结构

```text
Chat-Assistant/
├── main.py                      # ASGI 入口（兼容 uvicorn main:app、Docker、Vercel）
├── app/
│   ├── main.py                  # FastAPI 应用工厂、中间件、异常与路由注册
│   ├── core/                    # 配置、结构化日志、PBKDF2/JWT 安全、滑动窗口限流
│   ├── db/                      # SQLAlchemy 引擎与 ORM 模型（User/Persona/Conversation/Message）
│   ├── schemas/                 # Pydantic 请求与响应数据校验模型
│   ├── services/                # 模型注册表、角色服务、意图识别、联网搜索、绘图、流式编排
│   └── api/                     # 依赖注入与 REST/SSE 路由模块
├── static/
│   ├── index.html               # 响应式双栏聊天界面与弹窗结构
│   ├── css/app.css              # Markdown/KaTeX/代码块/动画样式
│   └── js/                      # 模块化前端（api.js / store.js / markdown.js / ui.js / app.js）
├── tests/                       # pytest 自动化测试套件
├── .env.example                 # 环境变量配置模板
├── Dockerfile                   # 生产环境镜像构建文件
├── docker-compose.yml           # 一键编排与持久化卷配置
├── requirements.txt             # 精简核心依赖清单
└── vercel.json                  # Vercel Serverless 部署配置
```

---

## 快速开始

### 1. 本地运行

```bash
# 1. 创建并激活虚拟环境（推荐 Python 3.10 - 3.12）
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量（至少配置一个模型的 API Key 即可体验）
cp .env.example .env
# 编辑 .env 填入你的 DEEPSEEK_API_KEY / DASHSCOPE_API_KEY 等

# 4. 启动服务
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

打开浏览器访问 `http://127.0.0.1:8000`，接口文档位于 `http://127.0.0.1:8000/docs`。

### 2. Docker 一键部署

```bash
cp .env.example .env
# 编辑 .env 填入 API Key 与随机 JWT_SECRET_KEY

docker compose up -d --build
```

SQLite 数据文件会自动持久化在名为 `chat_data` 的 Docker Volume 中，容器自带 `/api/health` 健康检查。

### 3. 部署到 Vercel

1. 将仓库导入 Vercel，框架预设选择 **Other**（已内置 `vercel.json`）。
2. 在 Vercel Project Settings -> Environment Variables 中配置所需的 API Key（及 `JWT_SECRET_KEY`）。
3. 如需跨 Serverless 实例长期保存会话，建议配置外部云数据库 `DATABASE_URL`（如 Neon / Supabase PostgreSQL）；未配置时会自动回退到 `/tmp/chat_assistant.db`。

---

## 主要 API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/health` | 健康检查与数据库/模型配置诊断 |
| `GET` | `/api/v1/models` | 获取全部模型列表及可用状态 |
| `POST` | `/api/v1/auth/register` | 用户注册（自动迁移当前 `X-Guest-ID` 数据） |
| `POST` | `/api/v1/auth/login` | 用户登录获取 JWT |
| `GET` | `/api/v1/auth/me` | 获取当前用户或游客身份 |
| `GET/POST/PUT/DELETE` | `/api/v1/personas` | 获取内置角色与自定义角色 CRUD |
| `GET/POST/PATCH/DELETE` | `/api/v1/conversations` | 会话列表（支持 `?q=` 搜索）、创建、置顶/重命名、删除 |
| `GET` | `/api/v1/conversations/{id}/export` | 导出会话（`?format=markdown` 或 `json`） |
| `POST` | `/api/v1/chat/stream` | SSE 真流式对话接口（支持搜索/多模态/生图/重试/编辑） |
| `POST` | `/api/v1/chat` | 非流式对话接口（同步返回完整 JSON） |
| `POST` | `/api/v1/images/generate` | 独立文生图接口 |

> 保留了旧版 `/chat`、`/models`、`/generate_image` 兼容路由，方便老客户端平滑过渡。

---

## 运行测试

```bash
pytest
```

测试套件使用隔离的临时 SQLite 数据库与 Mock LLM，无需消耗真实 API 额度即可验证健康检查、鉴权与游客数据迁移、会话 CRUD/搜索/导出、自定义角色、意图识别与 SSE 流式响应。
