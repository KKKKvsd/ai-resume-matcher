"""
app/services/tools_service.py

【改动说明】
本次升级把 extract_keywords_tool 内部从纯字典匹配升级为 LLM + 规则混合提取。
对外签名仍返回 list[str]，所有调用方（match_service / agent_service）零改动。
新增 extract_keywords_structured() 供未来按 importance / category 处理使用。
"""

from typing import Any

from app.core.logger import logger
from app.schemas.keyword import KeywordExtractionResult
from app.services.keyword_extractor import (
    KEYWORD_REGISTRY,
    extract_keywords_hybrid,
)
from app.utils.llm_client import analyze_resume_with_llm, answer_followup_with_llm
from app.utils.rag_retriever import retrieve_knowledge


# ---------------------------------------------------------------------------
# 向后兼容：保留 KEYWORD_ALIASES 变量名
# ---------------------------------------------------------------------------
KEYWORD_ALIASES: dict[str, list[str]] = {
    canonical: meta["aliases"] for canonical, meta in KEYWORD_REGISTRY.items()
}


# ---------------------------------------------------------------------------
# 核心改动
# ---------------------------------------------------------------------------
def extract_keywords_tool(job_text: str) -> list[str]:
    """
    从岗位描述中提取标准化关键词（list[str]，按 importance 排序）。

    【行为变化】
    - 老版本：纯规则匹配，覆盖 ~20 个固定词。
    - 新版本：LLM + 规则混合，可识别字典外的新词（如 LangChain、向量数据库），
      并返回按 importance（required/preferred/nice_to_have）排序的列表。
    - LLM 不可用时自动降级为纯规则模式，外部调用方无感。
    """
    if not job_text:
        return []

    result: KeywordExtractionResult = extract_keywords_hybrid(job_text)
    legacy = result.to_legacy_list()

    logger.info(
        f"extract_keywords_tool mode={result.mode} "
        f"total={result.total} (rule={result.rule_only}, "
        f"llm={result.llm_only}, merged={result.merged})"
    )

    return legacy


def extract_keywords_structured(job_text: str) -> KeywordExtractionResult:
    """
    返回完整结构化结果。供新功能使用：
    - 前端按 category 分组展示（语言/框架/AI 能力）
    - 评分时按 importance 加权
    - 简历改写时优先针对 required 关键词
    """
    return extract_keywords_hybrid(job_text)


# ---------------------------------------------------------------------------
# 以下函数保持完全不变（_keyword_hit 仅微调以兼容新字典）
# ---------------------------------------------------------------------------
def _keyword_hit(text: str, keyword: str) -> bool:
    text_lower = (text or "").lower()
    meta = KEYWORD_REGISTRY.get(keyword)
    aliases = meta["aliases"] if meta else [keyword.lower()]
    aliases = list(set(aliases + [keyword.lower()]))
    return any(alias.lower() in text_lower for alias in aliases)


def retrieve_knowledge_tool(job_text: str, keywords: list[str], top_k: int = 3) -> dict[str, Any]:
    """基于岗位描述和关键词做知识检索，返回可注入 Prompt 的上下文。"""
    query_parts: list[str] = []

    if keywords:
        query_parts.append("岗位关键词：" + "、".join(keywords))

    if job_text:
        query_parts.append("岗位描述：" + job_text)

    query = "\n".join(query_parts).strip()
    chunks = retrieve_knowledge(query, top_k=top_k)

    context = "\n\n".join(
        f"[来源: {item.get('file_name', 'unknown')}] {item.get('content', '')}"
        for item in chunks
    )

    logger.info(f"retrieve_knowledge_tool retrieved chunks count: {len(chunks)}")

    return {
        "query": query,
        "chunks": chunks,
        "context": context,
    }


def deepsearch_tool(job_text: str, resume_text: str, keywords: list[str], top_k: int = 3) -> dict[str, Any]:
    """轻量 DeepSearch：拆子查询 + 多轮检索 + 证据聚合。"""
    focus_keywords = keywords[:6] if keywords else extract_keywords_tool(job_text)[:6]

    subqueries = [
        "AI 开发实习岗位核心技能要求",
        "AI 应用开发项目简历表达方式",
        "FastAPI LLM RAG Agent 项目面试准备",
    ]

    for keyword in focus_keywords[:4]:
        subqueries.append(f"{keyword} 在 AI 应用开发岗位中的要求和项目表达")

    evidence: list[dict[str, Any]] = []
    seen = set()

    for subquery in subqueries:
        chunks = retrieve_knowledge(subquery + "\n" + job_text, top_k=top_k)
        for chunk in chunks:
            key = (chunk.get("file_name"), chunk.get("content", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "subquery": subquery,
                    "source": chunk.get("file_name", "unknown"),
                    "content": chunk.get("content", ""),
                    "rank": chunk.get("rank"),
                }
            )

    return {
        "subqueries": subqueries,
        "evidence": evidence[:12],
        "evidence_count": len(evidence[:12]),
    }


def analyze_match_tool(resume_text: str, job_text: str, retrieved_context: str = "") -> dict[str, Any]:
    """调用 LLM 做简历-岗位匹配分析。"""
    logger.info("analyze_match_tool started")
    result = analyze_resume_with_llm(
        resume_text=resume_text,
        job_text=job_text,
        retrieved_context=retrieved_context,
    )
    logger.info("analyze_match_tool finished")
    return result


def rewrite_suggestions_tool(
    suggestions: list[str],
    matched_keywords: list[str],
    missing_keywords: list[str],
) -> list[str]:
    """基于关键词缺口增强简历优化建议。"""
    final_suggestions = list(suggestions or [])

    if missing_keywords:
        final_suggestions.append(
            "建议在项目经历中补充这些岗位缺失关键词的真实实践表达："
            + "、".join(missing_keywords[:6])
            + "。"
        )

    if matched_keywords:
        final_suggestions.append(
            '建议将已匹配能力写成"业务场景 + 技术动作 + 结果指标"的形式，例如：'
            + "、".join(matched_keywords[:5])
            + "。"
        )

    deduped: list[str] = []
    for item in final_suggestions:
        item = str(item).strip()
        if item and item not in deduped:
            deduped.append(item)

    logger.info(f"rewrite_suggestions_tool final suggestions count: {len(deduped)}")
    return deduped[:8]


def keyword_gap_analysis_tool(resume_text: str, matched_keywords: list[str]) -> dict[str, list[str]]:
    """识别简历中已经覆盖和仍然缺失的关键词。"""
    hit_keywords: list[str] = []
    missing_keywords: list[str] = []

    for keyword in matched_keywords:
        if _keyword_hit(resume_text, keyword):
            hit_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    return {
        "matched_keywords": hit_keywords,
        "missing_keywords": missing_keywords,
    }


def resume_rewrite_tool(
    resume_text: str,
    job_text: str,
    suggestions: list[str],
    missing_keywords: list[str] | None = None,
) -> str:
    """生成简历改写建议。"""
    missing_keywords = missing_keywords or []

    prompt_question = f"""
请基于当前简历、岗位要求和已有建议，输出更适合该岗位的简历项目经历改写建议。

要求：
1. 按"原问题 → 改写方向 → 示例 bullet"输出。
2. 重点突出 AI 应用开发、FastAPI、Prompt Engineering、RAG、Agent、结果解析。
3. 不要编造未提供的公司、实习或指标。
4. 如果需要补充能力，请优先补充这些缺失关键词：{"、".join(missing_keywords[:6]) if missing_keywords else "无明显缺失关键词"}。
""".strip()

    return answer_followup_with_llm(
        question=prompt_question,
        resume_text=resume_text,
        job_text=job_text,
        summary="请重点输出简历项目经历改写建议。",
        strengths=[],
        weaknesses=[],
        suggestions=suggestions,
    )


def generate_interview_questions_tool(
    missing_keywords: list[str], matched_keywords: list[str] | None = None
) -> dict[str, Any]:
    """基于缺失关键词和已匹配关键词生成面试题。"""
    matched_keywords = matched_keywords or []
    questions: list[dict[str, str]] = []

    focus_keywords = (
        missing_keywords[:6]
        or matched_keywords[:6]
        or ["FastAPI", "Prompt Engineering", "RAG", "Agent"]
    )

    for keyword in focus_keywords:
        questions.append(
            {
                "keyword": keyword,
                "question": f"请解释你对 {keyword} 的理解，并结合你的项目说明你如何使用或计划使用它。",
                "answer_hint": '建议按"概念 → 项目场景 → 实现细节 → 遇到的问题 → 优化方案"回答。',
            }
        )

    questions.extend(
        [
            {
                "keyword": "系统架构",
                "question": "请介绍 AI 简历匹配与求职 Agent 系统的整体架构。",
                "answer_hint": "从 FastAPI 接口、MySQL 数据、LLM 调用、RAG 检索、Agent 工具调用链路展开。",
            },
            {
                "keyword": "LLM 稳定性",
                "question": "你如何保证大模型输出结果稳定可用？",
                "answer_hint": "回答 Prompt 约束、Pydantic 校验、JSON Repair、fallback、日志记录。",
            },
        ]
    )

    return {
        "questions": questions[:10],
        "focus_keywords": focus_keywords,
    }


def generate_learning_plan_tool(missing_keywords: list[str]) -> dict[str, Any]:
    """生成学习计划。"""
    if not missing_keywords:
        return {
            "learning_plan": [
                {
                    "topic": "项目工程化",
                    "tasks": [
                        "补充 README 架构图和接口示例。",
                        "补充测试用例和 Docker 启动说明。",
                        "准备 3 分钟项目讲解稿。",
                    ],
                }
            ]
        }

    plan = []
    for keyword in missing_keywords[:6]:
        plan.append(
            {
                "topic": keyword,
                "tasks": [
                    f"学习 {keyword} 的核心概念和常见面试问题。",
                    f"在 AI 简历匹配系统中补充一个体现 {keyword} 的小功能或文档说明。",
                    f'准备一个"我如何在项目中使用 {keyword}"的 60 秒回答。',
                ],
            }
        )

    return {"learning_plan": plan}