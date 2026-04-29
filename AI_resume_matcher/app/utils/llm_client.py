import json
import re
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.core.config import settings
from app.core.logger import logger
from app.schemas.analysis import MatchAnalysisResult


client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
)


KEYWORD_ALIASES = {
    "Python": ["python", "py"],
    "FastAPI": ["fastapi", "fast api"],
    "MySQL": ["mysql", "sql", "数据库"],
    "Docker": ["docker", "容器化", "容器"],
    "RAG": ["rag", "检索增强", "向量检索", "知识库问答"],
    "Agent": ["agent", "agents", "智能体"],
    "Tool Calling": ["tool calling", "function calling", "工具调用"],
    "Memory": ["memory", "记忆管理", "长期记忆", "短期记忆"],
    "Prompt Engineering": ["prompt", "提示词", "prompt engineering"],
    "LLM API": ["llm", "大模型", "模型调用", "openai"],
    "Document Loader": ["document loader", "文档加载", "pdf解析", "文档解析"],
    "Result Parsing": ["结果解析", "json", "结构化输出", "pydantic"],
    "DeepSearch": ["deepsearch", "deep research", "深度检索", "深度调研"],
}


def clean_llm_json_text(text: str) -> str:
    """
    清洗 LLM 返回内容：
    1. 去掉 ```json 代码块
    2. 截取第一个 { 到最后一个 }
    3. 返回可能合法的 JSON 字符串
    """
    text = (text or "").strip()

    if text.startswith("```"):
        text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return text.strip()


def call_llm(prompt: str, temperature: float = 0.2) -> str:
    """
    统一封装 LLM 调用。
    后续 timeout、retry、日志追踪都可以集中加在这里。
    """
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是一个严谨、稳定、擅长结构化输出的 AI 应用分析助手。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=temperature,
        timeout=getattr(settings, "LLM_TIMEOUT", 30),
    )

    content = response.choices[0].message.content or ""
    return content.strip()

def build_resume_analysis_prompt(
    resume_text: str,
    job_text: str,
    retrieved_context: str = "",
) -> str:
    """
    构建简历与岗位匹配分析 Prompt。
    retrieved_context 会被注入 prompt，用于 RAG 检索增强。
    """
    context_block = ""
    if retrieved_context and retrieved_context.strip():
        context_block = f"""
【参考知识库内容】
{retrieved_context}
"""

    return f"""
你是一个严谨的 AI 简历岗位匹配分析助手。

你的任务是分析候选人简历和岗位 JD 的匹配度。

要求：
1. 只能基于【简历内容】、【岗位 JD】和【参考知识库内容】进行分析。
2. 不要编造简历中不存在的经历。
3. 不要输出 Markdown。
4. 不要输出 ```json 代码块。
5. 不要添加解释文字。
6. 只返回一个合法 JSON 对象。
7. score 必须是 0 到 100 之间的数字。
8. suggestions 必须具体、可执行，不能只写“继续学习”这类空泛建议。
9. evidence 中要给出支撑判断的简短依据。

返回 JSON 格式必须如下：

{{
  "score": 78,
  "summary": "该简历与岗位匹配度较高，但仍需要补充 RAG 和 Agent 项目表达。",
  "strengths": ["优势1", "优势2"],
  "weaknesses": ["不足1", "不足2"],
  "suggestions": ["建议1", "建议2", "建议3"],
  "matched_keywords": ["Python", "FastAPI"],
  "missing_keywords": ["RAG", "Agent"],
  "evidence": [
    {{
      "source": "resume",
      "content": "支撑判断的简短依据",
      "score": null
    }}
  ]
}}

{context_block}

【简历内容】
{resume_text}

【岗位 JD】
{job_text}
""".strip()


def parse_analysis_result(raw_text: str) -> MatchAnalysisResult:
    """
    将 LLM 原始输出解析为 MatchAnalysisResult。
    这里会同时完成：
    1. JSON 清洗
    2. json.loads
    3. Pydantic 字段校验
    """
    cleaned = clean_llm_json_text(raw_text)
    logger.info(f"LLM cleaned content: {cleaned}")

    if not cleaned:
        raise ValueError("LLM returned empty content after cleaning.")

    data: dict[str, Any] = json.loads(cleaned)

    result = MatchAnalysisResult.model_validate(data)
    return result


def repair_analysis_json(
    raw_text: str,
    error_message: str,
) -> MatchAnalysisResult:
    """
    当 LLM 输出不是合法 JSON，或字段不符合 analysis.py schema 时，
    再让模型修复一次。
    """
    repair_prompt = f"""
下面是一段模型输出，但它不是合法 JSON，或者字段不符合要求。

请你把它修复成合法 JSON。

要求：
1. 不要解释。
2. 不要输出 Markdown。
3. 不要输出 ```json 代码块。
4. 只返回 JSON。
5. 必须包含以下字段：
score, summary, strengths, weaknesses, suggestions, matched_keywords, missing_keywords, evidence

字段要求：
- score: 0 到 100 的数字
- summary: 字符串
- strengths: 字符串数组
- weaknesses: 字符串数组
- suggestions: 字符串数组
- matched_keywords: 字符串数组
- missing_keywords: 字符串数组
- evidence: 数组，每一项包含 source、content、score

错误信息：
{error_message}

原始输出：
{raw_text}
""".strip()

    logger.info("Start LLM JSON repair request")

    repaired_text = call_llm(repair_prompt, temperature=0)
    result = parse_analysis_result(repaired_text)
    result.analysis_mode = "repair"

    logger.info("LLM JSON repair finished")

    return result

def find_keywords_in_text(text: str) -> list[str]:
    """
    基于 KEYWORD_ALIASES 做轻量关键词匹配。
    用于 fallback，避免 LLM 不可用时完全没有分析结果。
    """
    text_lower = (text or "").lower()
    matched: list[str] = []

    for canonical, aliases in KEYWORD_ALIASES.items():
        if any(alias.lower() in text_lower for alias in aliases):
            matched.append(canonical)

    return matched


def build_fallback_analysis(
    resume_text: str,
    job_text: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    """
    当 LLM 调用失败、JSON 解析失败、repair 也失败时，
    返回一个符合 MatchAnalysisResult schema 的 fallback 结果。
    """
    resume_keywords = find_keywords_in_text(resume_text)
    job_keywords = find_keywords_in_text(job_text)

    matched_keywords = [kw for kw in job_keywords if kw in resume_keywords]
    missing_keywords = [kw for kw in job_keywords if kw not in resume_keywords]

    score = 55.0 + len(matched_keywords) * 5 - len(missing_keywords) * 2
    score = max(35.0, min(85.0, score))

    strengths: list[str] = []
    weaknesses: list[str] = []
    suggestions: list[str] = []

    if matched_keywords:
        strengths.append(
            "简历中已体现部分岗位相关能力："
            + "、".join(matched_keywords[:6])
            + "。"
        )
    else:
        strengths.append("简历具备一定项目和技术基础，但与岗位关键词的直接匹配表达不足。")

    if missing_keywords:
        weaknesses.append(
            "简历中对以下岗位关键词体现不足："
            + "、".join(missing_keywords[:6])
            + "。"
        )
        suggestions.append(
            "建议在项目经历中补充这些能力的真实实践表达："
            + "、".join(missing_keywords[:6])
            + "。"
        )
    else:
        weaknesses.append("当前未发现明显关键词缺口，但仍可增强项目结果和技术细节表达。")

    suggestions.append(
        "建议将项目经历按照“业务场景 + 技术方案 + 工程实现 + 结果指标”的结构重写。"
    )
    suggestions.append(
        "建议突出 FastAPI 接口封装、Prompt Engineering、结构化输出、RAG/Agent 等 AI 应用开发能力。"
    )

    fallback_result = MatchAnalysisResult(
        score=score,
        summary="LLM 分析暂不可用，系统已基于关键词匹配生成兜底分析结果。",
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        evidence=[],
        model_name="fallback-keyword-analyzer",
        status="fallback",
        analysis_mode="mock",
        error_message=error_message,
    )

    return fallback_result.model_dump()


def analyze_resume_with_llm(
    resume_text: str,
    job_text: str,
    retrieved_context: str = "",
) -> dict[str, Any]:
    """
    简历与岗位匹配分析主函数。

    注意：
    - 函数名保留不变，兼容 tools_service.py / match_service.py 调用。
    - 使用 analysis.py 中的 MatchAnalysisResult 做结构化校验。
    - 包含 JSON repair 和 fallback。
    """
    prompt = build_resume_analysis_prompt(
        resume_text=resume_text,
        job_text=job_text,
        retrieved_context=retrieved_context,
    )

    logger.info("Start LLM resume-job match analysis request")

    try:
        raw_content = call_llm(prompt, temperature=0.2)
        logger.info("LLM raw content received")

        try:
            result = parse_analysis_result(raw_content)

        except (json.JSONDecodeError, ValidationError, ValueError) as parse_error:
            logger.warning(f"LLM JSON parse failed, trying repair: {repr(parse_error)}")

            try:
                result = repair_analysis_json(
                    raw_text=raw_content,
                    error_message=repr(parse_error),
                )

            except Exception as repair_error:
                logger.error(f"LLM JSON repair failed: {repr(repair_error)}")

                return build_fallback_analysis(
                    resume_text=resume_text,
                    job_text=job_text,
                    error_message=(
                        f"parse_error={repr(parse_error)}; "
                        f"repair_error={repr(repair_error)}"
                    ),
                )

        result.model_name = settings.LLM_MODEL
        result.status = "success"

        if result.analysis_mode not in ["repair", "mock"]:
            result.analysis_mode = "llm"

        logger.info("LLM resume-job match analysis finished successfully")

        return result.model_dump()

    except Exception as llm_error:
        logger.error(f"LLM analysis request failed: {repr(llm_error)}")

        return build_fallback_analysis(
            resume_text=resume_text,
            job_text=job_text,
            error_message=repr(llm_error),
        )
    
def answer_followup_with_llm(
    question: str,
    resume_text: str,
    job_text: str,
    summary: str,
    strengths: list[str],
    weaknesses: list[str],
    suggestions: list[str],
) -> str:
    """
    用户追问回答函数。

    注意：
    - 函数名保留不变，兼容原有 follow-up / Agent 调用。
    - 增加异常兜底，避免 LLM 调用失败导致接口报错。
    """
    prompt = f"""
你是一个简历优化助手。下面是某次简历分析的上下文，请基于这些内容回答用户追问。

要求：
1. 回答要简洁、明确、可执行。
2. 优先结合已有分析结果回答。
3. 不要编造未提供的信息。
4. 如果用户要求改写简历，请给出可以直接放进简历的 bullet point。
5. 如果用户询问面试准备，请按照“知识点 + 高频问题 + 准备建议”的结构回答。

【简历内容】
{resume_text}

【岗位描述】
{job_text}

【历史分析总结】
{summary}

【历史优势】
{json.dumps(strengths or [], ensure_ascii=False, indent=2)}

【历史不足】
{json.dumps(weaknesses or [], ensure_ascii=False, indent=2)}

【历史建议】
{json.dumps(suggestions or [], ensure_ascii=False, indent=2)}

【用户追问】
{question}
""".strip()

    logger.info("Start follow-up LLM request")

    try:
        content = call_llm(prompt, temperature=0.3)
        logger.info("Follow-up LLM response received")
        return content.strip()

    except Exception as error:
        logger.error(f"Follow-up LLM request failed: {repr(error)}")

        return (
            "当前大模型追问服务暂时不可用。"
            "建议你先根据已有分析结果优化简历：突出与岗位 JD 相关的技术关键词，"
            "并按照“项目背景 + 技术方案 + 个人职责 + 量化结果”的结构重写项目经历。"
        )