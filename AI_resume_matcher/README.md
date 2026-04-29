# AI Resume Matcher & Job Application Agent

一个基于 **FastAPI + MySQL + LLM + RAG + Agent Workflow** 构建的 AI 求职辅助后端系统。

系统支持用户注册登录、岗位 JD 管理、PDF 简历上传解析、简历与岗位匹配分析、关键词差距分析、RAG 知识库检索增强、Agent 多意图任务处理、历史结果查询，并在大模型调用失败时自动 fallback，保证主流程可用。

---

## 1. Project Highlights

- 基于 FastAPI 构建 AI 应用后端，采用 `api / service / schema / model / utils` 分层结构。
- 使用 Pydantic 对接口请求、响应和 LLM 输出进行结构化校验。
- 设计 Prompt + JSON 清洗 + Pydantic 校验 + JSON Repair + Fallback 机制，提升 LLM 输出稳定性。
- 引入 RAG 检索增强模块，基于岗位技能知识库进行 top-k 语义检索，并将相关知识片段注入 Prompt。
- 构建轻量 Agent Pipeline，支持岗位匹配、关键词缺口分析、简历改写、面试题生成和学习计划生成。
- 使用 MySQL 持久化用户、岗位、简历、匹配分数、关键词缺口、分析模式、模型名称、错误信息和证据片段。

---

## 2. 已实现功能

### 用户模块

- 用户注册
- 用户登录
- JWT 鉴权
- 获取当前登录用户信息

### 岗位模块

- 新建岗位描述
- 获取岗位列表
- 获取岗位详情

### 简历模块

- 上传 PDF 简历
- 本地保存文件
- 提取 PDF 文本内容
- 获取简历列表
- 获取简历详情

### 分析模块

- 根据简历和岗位生成匹配分析结果
- 返回匹配分数、总结、优势、不足、优化建议
- 返回已匹配关键词、缺失关键词和 evidence 证据片段
- 分析结果持久化存储
- 支持历史结果查询和详情查询
- 大模型调用失败时自动 fallback

### Agent 模块

- `/api/v1/match/agent`
- 支持意图识别：岗位匹配、关键词差距、简历改写、面试题、学习计划
- 返回 Agent 执行步骤 `steps`，方便展示工具调用链路

---

## 3. 技术栈

- Python
- FastAPI
- SQLAlchemy
- MySQL
- Pydantic
- JWT / python-jose / passlib
- PyPDF
- OpenAI-compatible LLM API
- LangChain Text Splitter
- FAISS
- OpenAI Embeddings
- Docker / Docker Compose

---

## 4. 系统流程

```text
用户注册 / 登录
        ↓
获取 JWT Token
        ↓
保存岗位 JD
        ↓
上传 PDF 简历
        ↓
解析简历文本并存库
        ↓
提取岗位关键词
        ↓
RAG 检索岗位技能知识库
        ↓
调用 LLM 生成结构化匹配分析
        ↓
Pydantic 校验 / JSON Repair / Fallback
        ↓
保存分析结果到数据库
        ↓
查询历史结果 / Follow-up / Agent 任务
```

---

## 5. 项目结构

```text
AI_resume_matcher/
├── app/
│   ├── api/              # 路由层
│   ├── core/             # 配置、数据库连接、安全相关
│   ├── models/           # ORM 模型
│   ├── schemas/          # 请求 / 响应结构
│   ├── services/         # 业务逻辑
│   └── utils/            # PDF解析、LLM调用、RAG检索等工具
├── docs/knowledge/       # RAG 本地知识库
├── uploads/              # 上传文件保存目录
├── tests/                # 测试用例
├── .env.example          # 环境变量示例
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 6. 核心接口

### 用户模块

- `POST /api/v1/users/register`
- `POST /api/v1/users/login`
- `GET /api/v1/users/me`

### 岗位模块

- `POST /api/v1/jobs`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`

### 简历模块

- `POST /api/v1/resumes/upload`
- `GET /api/v1/resumes`
- `GET /api/v1/resumes/{resume_id}`

### 分析模块

- `POST /api/v1/match/analyze`
- `GET /api/v1/match/results`
- `GET /api/v1/match/results/{result_id}`
- `POST /api/v1/match/follow-up`
- `POST /api/v1/match/agent`

---

## 7. 环境变量

复制 `.env.example` 为 `.env`，并填写自己的配置。

```env
APP_NAME=AI Resume Matcher
DEBUG=True
DATABASE_URL=mysql+pymysql://appuser:AppPass123%21@host.docker.internal:3306/ai_resume_matcher
SECRET_KEY=change_me_to_a_long_random_secret
ALGORITHM=HS256
UPLOAD_DIR=uploads

LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT=30
EMBEDDING_MODEL=text-embedding-3-small
```

> 不要提交真实 `.env` 或真实 API Key。

---

## 8. 本地启动

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

打开 Swagger：

```text
http://127.0.0.1:8000/docs
```

---

## 9. Docker Compose 启动

```bash
docker compose up --build
```

---

## 10. 数据库说明

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

如果已有旧表，需要手动新增字段或删除旧表后让 SQLAlchemy 重新创建。生产环境建议引入 Alembic 做迁移。

---

## 11. 后续优化方向

- 引入 Alembic 管理数据库迁移
- 增加 Docx / Markdown / TXT 简历解析
- 增加 Rerank、Hybrid Search 和 Query Rewrite
- 增加前端页面或 Streamlit Demo
- 增加在线部署和 CI/CD
- 增加更多单元测试与接口测试

## Production-style Agent Upgrade

当前版本已从轻量规则式 Agent 升级为更接近生产级的 **Planner-Executor Agent**：

- **LLM Planner**：根据用户问题生成结构化执行计划，自动选择工具。
- **Plan Sanitizer**：校验工具名、最大步骤数和必需步骤，避免模型生成不可执行计划。
- **Tool Registry**：集中管理可调用工具，包括关键词抽取、RAG 检索、DeepSearch、匹配分析、简历改写、面试题生成、学习计划生成。
- **Working Memory**：每一步工具结果都会写入运行时状态，供后续步骤复用。
- **Execution Trace**：接口返回完整 `steps`，可观察每个工具的输入、输出、状态和错误。
- **Final Synthesizer**：使用 LLM 汇总工具结果生成最终答复；LLM 不可用时使用 deterministic fallback。
- **Confidence & Warnings**：返回置信度和运行警告，便于前端展示和调试。
- **DeepSearch Mode**：将复杂问题拆分为多个子查询，多轮检索知识库并聚合证据。

典型 Agent 调用：

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
  "result": {
    "keyword_gap": {},
    "interview_questions": {}
  },
  "confidence": 0.88,
  "mode": "llm_planner",
  "warnings": []
}
```
