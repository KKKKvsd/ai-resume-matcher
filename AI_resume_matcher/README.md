# AI Resume Matcher Agent

一个基于 LLM + RAG + Agent 架构的生产级简历岗位匹配系统。支持简历解析、岗位匹配、关键词差距分析、简历改写、面试题生成,以及多轮记忆的 Agent 问答。

[在线演示](https://你的-vercel-地址.vercel.app)|[API 文档](https://你的-render-地址.onrender.com/docs)

---

## 核心特性

### Agent 架构
- **Planner-Executor 流水线**:LLM Planner → Plan Sanitizer → 工具白名单校验 → 工具调用 → Final Synthesizer
- **9 个可调用工具**:关键词抽取、关键词差距、RAG 检索、DeepSearch、匹配分析、简历改写、面试题生成、学习计划、最终回答合成
- **Plan Sanitizer 容错**:LLM Planner 不可用时自动 fallback 到规则 Planner,保证主流程零中断

### LLM 工程化
- **生产级 LLM 客户端**:指数退避重试(±25% 抖动)、超时三档(fast/default/heavy)、异常分级(致命错误立即终止)
- **完整可观测性**:每次调用 call_id 追踪、`/metrics` 端点暴露成功率/延迟/Token 消耗
- **三级容错**:Pydantic schema 校验 → JSON Repair → 规则兜底,LLM 输出可用率 > 98%

### RAG 混合检索
- **三阶段管道**:BM25 + 向量并行召回 → RRF (Reciprocal Rank Fusion) 融合 → LLM Rerank 精排
- **支持中英文混合分词**(无 jieba 依赖,部署友好)
- **任一路失败自动降级**:BM25 挂了纯向量,向量挂了纯 BM25

### Agent 三层记忆
- **Working Memory**:单次任务内的工具中间结果
- **Session Memory**:多轮对话上下文,滑窗 + LLM 摘要压缩控制 token 预算
- **Long-Term Memory**:跨会话用户画像(目标岗位、偏好、简历版本演化),LLM Fact Extractor 自动提炼

### Streaming(SSE)
- **9 类事件流**:status / plan / tool_start / tool_done / token / memory / warning / error / done
- **首字节延迟 < 1s**:用户立刻看到 Agent 进度,vs 一次性返回的 8-15s

### 评测框架
- **11 例评测样本**,覆盖关键词抽取、匹配分析、RAG 检索三类核心组件
- **4 类 metrics**:P/R/F1、区间 MAE、Hit Rate、MRR@K
- **CLI 工具**:`python -m tests.eval.run_eval --kind all --label baseline`

---

## 技术栈

**后端**: Python 3.12, FastAPI, SQLAlchemy, Pydantic v2, OpenAI SDK, LangChain, FAISS, rank-bm25, MySQL

**前端**: React 18, TypeScript, Tailwind, Vite, Lucide

**部署**: Vercel (前端) + Render (后端) + 自托管 MySQL

---

## 架构图

```
┌──────────────────────────────────────────────┐
│            React + TypeScript                │
│  Login / Resume / Job / Match / Agent Chat   │
└────────────────────┬─────────────────────────┘
                     │ HTTP + SSE
┌────────────────────▼─────────────────────────┐
│              FastAPI                         │
│  Auth │ Resume │ Job │ Match │ Agent Stream  │
└──┬─────────────────┬───────────────────┬─────┘
   │                 │                   │
┌──▼──┐    ┌─────────▼─────────┐    ┌────▼────┐
│MySQL│    │  Agent Pipeline   │    │  LLM    │
│     │    │ Plan→Tools→Synth  │◄──►│ Client  │
└─────┘    └───┬──────────┬────┘    │ Retry   │
               │          │         │ Metrics │
        ┌──────▼───┐  ┌───▼─────┐   └─────────┘
        │  RAG     │  │ Memory  │
        │ BM25+Vec │  │ 3-tier  │
        │  Rerank  │  └─────────┘
        └──────────┘
```

---

## 本地启动

```bash
# 后端
git clone https://github.com/你的用户名/AI_resume_matcher.git
cd AI_resume_matcher
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # Mac/Linux
pip install -r requirements.txt
cp .env.example .env          # 填入你的 API key 和 DB 配置
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
cp .env.example .env.development
npm run dev
```

---

## 开发指南

### 跑评测

```bash
# 跑所有评测
python -m tests.eval.run_eval --kind all --label baseline

# 对比两次运行
python -m tests.eval.run_eval compare \
    tests/eval/reports/keyword_extraction_baseline_*.json \
    tests/eval/reports/keyword_extraction_v2_*.json
```

### 看 LLM 监控指标

```bash
curl http://127.0.0.1:8000/api/v1/metrics/llm
```

### 跑单元测试

```bash
pytest tests/test_keyword_extractor.py -v
pytest tests/test_memory_service.py -v
```

---

## 项目里我做的关键技术决策(给面试官看)

### 为什么 RAG 用 BM25 + 向量混合而不是纯向量?
向量擅长语义但对**专有名词和短查询**(如 "FastAPI")召回不准;BM25 反过来。两路 + RRF 融合后,召回率明显高于单路。RRF 不需要 normalize 不同量纲的分数,稳健性高,这是 Elasticsearch 8.x 的默认融合策略。

### 为什么 Agent 记忆分三层?
三种记忆生命周期完全不同:working 是单次任务内中间结果,session 是一次会话内对话历史,long-term 是跨会话用户画像。混在一起会有生命周期错乱(本该清理的中间数据被永久存了)和 token 预算难控两个问题。这是 LangChain Memory / Letta / MemGPT 共有的设计。

### 为什么 Streaming 流的不是 token,是事件?
普通 LLM streaming 流 token 就够了,但 Agent 是个复合任务——plan 生成、工具执行、最终 LLM,每一步都值得让用户看到。所以设计成 9 类事件,前端按 type 分发到不同 UI 组件。这是 OpenAI Assistant API 和 LangGraph 的官方设计模式。

### 为什么自己写 retry 不用 tenacity?
tenacity 是好库,但对这场景太重。我的需求很具体:指数退避 + 抖动 + 异常分类 + 调用上下文记录。这套加起来 30 行代码,比 tenacity 装饰器嵌套更可读、零依赖。

---

## License

MIT