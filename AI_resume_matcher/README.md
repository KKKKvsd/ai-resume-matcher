# AI Resume Matcher V1.0

AI Resume Matcher 是一个基于 **FastAPI + React + LLM / Agent** 的全栈 AI 求职辅助系统。系统支持用户注册登录、PDF 简历上传解析、岗位 JD 管理、AI 简历岗位匹配分析、历史结果查看、结果详情展示以及 Agent 问答追问，帮助用户快速判断简历与目标岗位的匹配度，并生成可执行的优化建议。

## 在线体验

前端地址：

```text
https://ai-resume-matcher-ruddy.vercel.app
```

后端 API 文档：

```text
https://ai-resume-matcher-qccv.onrender.com/docs
```

> 国内访问 Vercel / Render 可能不稳定，如无法打开，可能需要使用稳定网络环境。

---

## 功能特性

### 用户模块

- 用户注册 / 登录
- JWT 鉴权
- 当前用户信息展示
- Token 失效自动退出

### 简历管理

- 上传 PDF 简历
- 解析简历文本
- 查看简历列表
- 查看解析状态

### 岗位管理

- 创建岗位 JD
- 查看岗位列表
- 管理公司名称、岗位来源和岗位内容

### 匹配分析

- 选择简历与岗位
- 生成匹配分
- 分析优势、不足和优化建议
- 展示 matched keywords / missing keywords
- 支持 RAG Evidence 展示
- LLM 调用失败时支持 fallback，保证主流程可用

### 历史结果与详情

- 查看历史匹配记录
- 查看匹配分和摘要
- 跳转结果详情页
- 展示 AI 总结、关键词差距、RAG Evidence 和原始 JSON 调试数据

### Agent 问答

- 独立 Agent 问答页面
- 结果详情页内置 Follow-up 追问区
- 支持简历改写、面试题生成、关键词缺口分析和学习计划生成
- 返回 Agent 执行步骤，方便展示工具调用链路

---

## 技术栈

### 前端

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Axios
- Lucide React
- Vercel

### 后端

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT / python-jose / passlib
- Uvicorn
- PDF 文本解析
- LLM / RAG / Agent Workflow
- Render

### 数据库

- PostgreSQL / MySQL
- SQLAlchemy ORM

---

## 系统流程

```text
注册 / 登录
   ↓
上传 PDF 简历
   ↓
创建岗位 JD
   ↓
选择简历和岗位
   ↓
AI 匹配分析
   ↓
查看历史结果与详情
   ↓
Agent 继续追问
```

---

## 项目结构

```text
AI_resume_matcher/
├── app/                         # FastAPI 后端
│   ├── api/                     # 路由层
│   ├── core/                    # 配置、数据库连接、安全相关
│   ├── models/                  # ORM 模型
│   ├── schemas/                 # 请求 / 响应结构
│   ├── services/                # 业务逻辑
│   └── utils/                   # PDF 解析、LLM 调用、RAG 检索等工具
│
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── components/          # 页面组件
│   │   │   ├── common/          # 通用组件
│   │   │   ├── layout/          # 布局组件
│   │   │   ├── match/           # 匹配分析与 Agent 组件
│   │   │   └── results/         # 结果详情组件
│   │   ├── pages/               # 页面路由
│   │   ├── lib/                 # API 封装与工具函数
│   │   ├── types/               # TypeScript 类型
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── docs/knowledge/              # RAG 本地知识库
├── uploads/                     # 本地上传文件目录
├── tests/                       # 测试用例
├── requirements.txt             # 后端依赖
├── runtime.txt                  # Render Python 版本
├── docker-compose.yml
├── Dockerfile
├── .gitignore
└── README.md
```

---

## 本地运行

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/ai-resume-matcher.git
cd ai-resume-matcher
```

### 2. 启动后端

推荐使用独立 Python 环境：

```bash
conda create -n resume-matcher python=3.10 -y
conda activate resume-matcher
pip install -r requirements.txt
```

在项目根目录创建 `.env`：

```env
APP_NAME=AI Resume Matcher
DEBUG=True
DATABASE_URL=你的数据库连接
SECRET_KEY=你的随机密钥
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=uploads

LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT=30
EMBEDDING_MODEL=text-embedding-3-small

FRONTEND_ORIGIN=http://localhost:5173
```

生成随机密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

启动后端：

```bash
uvicorn app.main:app --reload
```

后端地址：

```text
http://127.0.0.1:8000
```

API 文档：

```text
http://127.0.0.1:8000/docs
```

### 3. 启动前端

```bash
cd frontend
npm install
```

创建 `frontend/.env`：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

启动前端：

```bash
npm run dev
```

前端地址：

```text
http://localhost:5173
```

---

## 主要页面

```text
/login          登录 / 注册
/dashboard      工作台
/resumes        简历管理
/jobs           岗位管理
/match          匹配分析
/results        历史结果
/results/:id    结果详情
/agent          Agent 问答
```

---

## 核心接口

### 用户模块

```text
POST /api/v1/users/register
POST /api/v1/users/login
GET  /api/v1/users/me
```

### 简历模块

```text
POST /api/v1/resumes/upload
GET  /api/v1/resumes
GET  /api/v1/resumes/{resume_id}
```

### 岗位模块

```text
POST /api/v1/jobs
GET  /api/v1/jobs
GET  /api/v1/jobs/{job_id}
```

### 匹配与 Agent 模块

```text
POST /api/v1/match/analyze
GET  /api/v1/match/results
GET  /api/v1/match/results/{result_id}
POST /api/v1/match/follow-up
POST /api/v1/match/agent
```

---

## Agent Workflow

当前版本使用轻量生产化的 **Planner-Executor Agent**：

- **LLM Planner**：根据用户问题生成结构化执行计划
- **Plan Sanitizer**：校验工具名、最大步骤数和必需步骤
- **Tool Registry**：集中管理关键词提取、RAG 检索、匹配分析、简历改写、面试题生成、学习计划生成等工具
- **Working Memory**：每一步工具结果写入运行时状态，供后续步骤复用
- **Execution Trace**：接口返回完整 `steps`，可观察工具输入、输出、状态和错误
- **Final Synthesizer**：汇总工具结果生成最终答复，LLM 不可用时使用 deterministic fallback
- **Confidence & Warnings**：返回置信度和运行警告，便于前端展示和调试

示例调用：

```http
POST /api/v1/match/agent
Content-Type: application/json

{
  "query": "帮我根据这个 AI 开发岗位生成面试题，并指出我简历里最缺什么"
}
```

返回核心字段：

```json
{
  "intent": "interview_questions",
  "final_answer": "...",
  "plan": {
    "intent": "interview_questions",
    "steps": []
  },
  "steps": [
    {
      "step_id": 1,
      "tool_name": "extract_job_keywords",
      "status": "success"
    }
  ],
  "result": {},
  "confidence": 0.88,
  "mode": "llm_planner",
  "warnings": []
}
```

---

## 部署说明

### 前端部署

前端部署在 Vercel。

```text
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
```

环境变量：

```env
VITE_API_BASE_URL=https://你的后端服务名.onrender.com
```

注意：

- 必须使用 `https://`
- 不要填写 `localhost` 或 `127.0.0.1`
- 不要在末尾添加 `/api/v1`
- 修改环境变量后需要重新部署前端

### 后端部署

后端部署在 Render。

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

环境变量：

```env
DATABASE_URL=你的云数据库连接
SECRET_KEY=你的随机密钥
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
FRONTEND_ORIGIN=https://你的前端.vercel.app
```

---

## 数据库说明

核心表：

- `users`
- `job_descriptions`
- `resumes`
- `match_results`

`match_results` 会保存：

- `score`
- `summary`
- `strengths`
- `weaknesses`
- `suggestions`
- `matched_keywords`
- `missing_keywords`
- `evidence`
- `model_name`
- `analysis_mode`
- `status`
- `error_message`

生产环境建议引入 Alembic 管理数据库迁移。

---

## 常见问题

### 前端请求后端时报 Network Error

检查：

- `VITE_API_BASE_URL` 是否使用 `https://`
- Vercel 修改环境变量后是否重新部署
- Render 后端是否正常启动
- `FRONTEND_ORIGIN` 是否配置为 Vercel 前端地址
- 后端 CORS 是否允许本地和线上前端域名

### Render 部署找不到 requirements.txt

检查：

- `requirements.txt` 是否在 GitHub 仓库根目录
- Render Root Directory 是否留空
- 是否已经 `git add` / `commit` / `push`

### PostgreSQL 报 `database() does not exist`

`SELECT DATABASE()` 是 MySQL 专用 SQL。PostgreSQL 应使用：

```sql
SELECT current_database()
```

如果只是调试日志，可以直接删除该数据库名称检查代码。

### NumPy / scikit-learn 版本不兼容

如果出现：

```text
ValueError: numpy.dtype size changed
```

建议固定：

```text
numpy==1.26.4
```

---

## 项目状态

当前版本：`v1.0`

已完成：

- 前后端开发
- 登录注册
- 简历管理
- 岗位管理
- AI 匹配分析
- 历史结果
- 结果详情页
- Agent 问答
- 本地运行
- 云端部署

---

## 后续优化方向

- 简历删除 / 编辑
- 岗位编辑 / 删除
- 匹配报告导出 PDF
- Agent 多轮对话历史
- 文件上传接入对象存储
- 引入 Alembic 管理数据库迁移
- 完善单元测试与接口测试
- 优化移动端体验
