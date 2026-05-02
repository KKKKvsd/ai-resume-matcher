"""
app/utils/llm_client.py

【升级说明】
本次升级把 call_llm 从"能用"升级到"生产级":
1. 指数退避重试(默认 3 次,可配置)
2. 超时分级(fast / default / heavy 三档)
3. 异常分级(可重试 vs 致命错误)
4. 调用上下文(call_id + 完整指标:latency / tokens / attempts / model)
5. 调用统计聚合(可被 /metrics endpoint 暴露)

向后兼容:
- 原签名 call_llm(prompt, temperature=0.2) 完全保留,所有老代码零改动
- 新功能通过可选参数 profile / max_attempts 启用

不引入新依赖:重试逻辑自己写(30 行,不用 tenacity)。
"""

import json
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Literal, Optional, Iterator

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.config import settings
from app.core.logger import logger
from app.schemas.analysis import MatchAnalysisResult


client = OpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL,
)


# ===========================================================================
# 配置:profile / 重试策略
# ===========================================================================
TimeoutProfile = Literal["fast", "default", "heavy"]

# 三档 timeout(秒):
# - fast: 短 prompt、低 token 输出(关键词抽取、rerank scoring)
# - default: 一般任务(匹配分析、follow-up)
# - heavy: 大 context + 长输出(简历改写、deepsearch synthesis)
TIMEOUT_BY_PROFILE: dict[TimeoutProfile, float] = {
    "fast": 15.0,
    "default": 45.0,
    "heavy": 90.0,
}

# 重试配置
MAX_RETRY_ATTEMPTS = 3
INITIAL_BACKOFF_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0
MAX_BACKOFF_SECONDS = 16.0
JITTER_RATIO = 0.25


# ===========================================================================
# 异常分类
# ===========================================================================
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)

FATAL_EXCEPTIONS: tuple[type[BaseException], ...] = (
    AuthenticationError,
    BadRequestError,
)


class LLMCallError(Exception):
    """所有重试都失败后抛出。包含完整调用上下文便于定位。"""

    def __init__(
        self,
        message: str,
        *,
        call_id: str,
        attempts: int,
        last_exception: Optional[BaseException] = None,
    ):
        super().__init__(message)
        self.call_id = call_id
        self.attempts = attempts
        self.last_exception = last_exception


# ===========================================================================
# 调用上下文 + 指标
# ===========================================================================
@dataclass
class LLMCallMetrics:
    call_id: str
    profile: str
    model: str
    attempts: int = 0
    success: bool = False
    total_latency_ms: float = 0.0
    last_attempt_latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error_type: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class _AggregateStats:
    total_calls: int = 0
    total_success: int = 0
    total_failures: int = 0
    total_retries: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    sum_latency_ms: float = 0.0
    by_profile: dict[str, int] = field(default_factory=dict)
    by_error_type: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record(self, metrics: LLMCallMetrics) -> None:
        with self._lock:
            self.total_calls += 1
            self.by_profile[metrics.profile] = (
                self.by_profile.get(metrics.profile, 0) + 1
            )
            self.total_retries += max(0, metrics.attempts - 1)
            self.sum_latency_ms += metrics.total_latency_ms
            self.total_prompt_tokens += metrics.prompt_tokens
            self.total_completion_tokens += metrics.completion_tokens
            if metrics.success:
                self.total_success += 1
            else:
                self.total_failures += 1
                if metrics.error_type:
                    self.by_error_type[metrics.error_type] = (
                        self.by_error_type.get(metrics.error_type, 0) + 1
                    )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg_latency = (
                self.sum_latency_ms / self.total_calls
                if self.total_calls > 0
                else 0.0
            )
            return {
                "total_calls": self.total_calls,
                "total_success": self.total_success,
                "total_failures": self.total_failures,
                "total_retries": self.total_retries,
                "success_rate": (
                    self.total_success / self.total_calls
                    if self.total_calls > 0
                    else 0.0
                ),
                "avg_latency_ms": round(avg_latency, 1),
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "by_profile": dict(self.by_profile),
                "by_error_type": dict(self.by_error_type),
            }


LLM_STATS = _AggregateStats()


# ===========================================================================
# 重试 + 退避算法
# ===========================================================================
def _compute_backoff(attempt: int) -> float:
    base = INITIAL_BACKOFF_SECONDS * (BACKOFF_MULTIPLIER ** (attempt - 1))
    base = min(base, MAX_BACKOFF_SECONDS)
    jitter = random.uniform(-JITTER_RATIO, JITTER_RATIO) * base
    return max(0.0, base + jitter)


def _categorize_error(exc: BaseException) -> str:
    return type(exc).__name__


# ===========================================================================
# 核心调用
# ===========================================================================
def _do_single_call(
    prompt: str,
    temperature: float,
    timeout: float,
    metrics: LLMCallMetrics,
) -> str:
    response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是一个严谨、稳定、擅长结构化输出的 AI 应用分析助手。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        timeout=timeout,
    )

    content = response.choices[0].message.content or ""

    usage = getattr(response, "usage", None)
    if usage is not None:
        metrics.prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        metrics.completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        metrics.total_tokens = getattr(usage, "total_tokens", 0) or 0

    return content.strip()


def call_llm(
    prompt: str,
    temperature: float = 0.2,
    profile: TimeoutProfile = "default",
    max_attempts: int = MAX_RETRY_ATTEMPTS,
) -> str:
    """
    生产级 LLM 调用。

    Args:
        prompt: 用户消息
        temperature: 采样温度
        profile: timeout 档位 (fast / default / heavy)
        max_attempts: 总尝试次数(含首次)

    Returns:
        模型输出文本

    Raises:
        LLMCallError: 所有尝试都失败时抛出
    """
    call_id = uuid.uuid4().hex[:8]
    timeout = TIMEOUT_BY_PROFILE.get(profile, TIMEOUT_BY_PROFILE["default"])
    metrics = LLMCallMetrics(
        call_id=call_id,
        profile=profile,
        model=settings.LLM_MODEL,
    )

    overall_start = time.perf_counter()
    last_exception: Optional[BaseException] = None

    for attempt in range(1, max_attempts + 1):
        metrics.attempts = attempt
        attempt_start = time.perf_counter()

        try:
            content = _do_single_call(prompt, temperature, timeout, metrics)
            metrics.success = True
            metrics.last_attempt_latency_ms = (time.perf_counter() - attempt_start) * 1000
            metrics.total_latency_ms = (time.perf_counter() - overall_start) * 1000

            logger.info(
                f"[LLM call_id={call_id}] success "
                f"profile={profile} attempts={attempt} "
                f"latency={metrics.total_latency_ms:.0f}ms "
                f"tokens={metrics.total_tokens}"
            )
            LLM_STATS.record(metrics)
            return content

        except FATAL_EXCEPTIONS as fatal:
            metrics.last_attempt_latency_ms = (time.perf_counter() - attempt_start) * 1000
            metrics.total_latency_ms = (time.perf_counter() - overall_start) * 1000
            metrics.error_type = _categorize_error(fatal)
            metrics.error_message = repr(fatal)

            logger.error(
                f"[LLM call_id={call_id}] FATAL {metrics.error_type}: {fatal}. "
                f"Not retrying."
            )
            LLM_STATS.record(metrics)
            raise LLMCallError(
                f"Fatal LLM error: {metrics.error_type}",
                call_id=call_id,
                attempts=attempt,
                last_exception=fatal,
            ) from fatal

        except RETRYABLE_EXCEPTIONS as retryable:
            last_exception = retryable
            metrics.last_attempt_latency_ms = (time.perf_counter() - attempt_start) * 1000
            metrics.error_type = _categorize_error(retryable)
            metrics.error_message = repr(retryable)

            if attempt >= max_attempts:
                logger.error(
                    f"[LLM call_id={call_id}] retryable error on final attempt "
                    f"{attempt}/{max_attempts}: {metrics.error_type}: {retryable}"
                )
                break

            backoff = _compute_backoff(attempt)
            logger.warning(
                f"[LLM call_id={call_id}] {metrics.error_type} on attempt "
                f"{attempt}/{max_attempts}, retrying in {backoff:.2f}s"
            )
            time.sleep(backoff)

        except APIStatusError as api_status:
            last_exception = api_status
            metrics.last_attempt_latency_ms = (time.perf_counter() - attempt_start) * 1000
            metrics.error_type = _categorize_error(api_status)
            metrics.error_message = repr(api_status)

            status_code = getattr(api_status, "status_code", 0)
            if 500 <= status_code < 600 and attempt < max_attempts:
                backoff = _compute_backoff(attempt)
                logger.warning(
                    f"[LLM call_id={call_id}] APIStatusError {status_code} on "
                    f"attempt {attempt}/{max_attempts}, retrying in {backoff:.2f}s"
                )
                time.sleep(backoff)
                continue

            logger.error(
                f"[LLM call_id={call_id}] APIStatusError {status_code} not retryable: {api_status}"
            )
            break

        except Exception as unknown:
            last_exception = unknown
            metrics.last_attempt_latency_ms = (time.perf_counter() - attempt_start) * 1000
            metrics.error_type = _categorize_error(unknown)
            metrics.error_message = repr(unknown)
            logger.error(f"[LLM call_id={call_id}] unknown exception: {repr(unknown)}")
            break

    metrics.total_latency_ms = (time.perf_counter() - overall_start) * 1000
    metrics.success = False
    LLM_STATS.record(metrics)

    raise LLMCallError(
        f"LLM call failed after {metrics.attempts} attempts: "
        f"{metrics.error_type or 'unknown'}",
        call_id=call_id,
        attempts=metrics.attempts,
        last_exception=last_exception,
    )


# ===========================================================================
# 以下为原有辅助函数,完全不变
# ===========================================================================

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


def build_resume_analysis_prompt(
    resume_text: str,
    job_text: str,
    retrieved_context: str = "",
) -> str:
    context_block = ""
    if retrieved_context and retrieved_context.strip():
        context_block = f"\n【参考知识库内容】\n{retrieved_context}\n"

    return f"""
你是一个严谨的 AI 简历岗位匹配分析助手。

你的任务是分析候选人简历和岗位 JD 的匹配度。

要求:
1. 只能基于【简历内容】、【岗位 JD】和【参考知识库内容】进行分析。
2. 不要编造简历中不存在的经历。
3. 不要输出 Markdown。
4. 不要输出 ```json 代码块。
5. 不要添加解释文字。
6. 只返回一个合法 JSON 对象。
7. score 必须是 0 到 100 之间的数字。
8. suggestions 必须具体、可执行,不能只写"继续学习"这类空泛建议。
9. evidence 中要给出支撑判断的简短依据。

返回 JSON 格式必须如下:

{{
  "score": 78,
  "summary": "该简历与岗位匹配度较高,但仍需要补充 RAG 和 Agent 项目表达。",
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
    cleaned = clean_llm_json_text(raw_text)
    logger.info(f"LLM cleaned content length: {len(cleaned)}")

    if not cleaned:
        raise ValueError("LLM returned empty content after cleaning.")

    data: dict[str, Any] = json.loads(cleaned)
    return MatchAnalysisResult.model_validate(data)


def repair_analysis_json(raw_text: str, error_message: str) -> MatchAnalysisResult:
    repair_prompt = f"""
下面是一段模型输出,但它不是合法 JSON,或者字段不符合要求。

请你把它修复成合法 JSON。

要求:
1. 不要解释。
2. 不要输出 Markdown。
3. 不要输出 ```json 代码块。
4. 只返回 JSON。
5. 必须包含以下字段:
score, summary, strengths, weaknesses, suggestions, matched_keywords, missing_keywords, evidence

字段要求:
- score: 0 到 100 的数字
- summary: 字符串
- strengths: 字符串数组
- weaknesses: 字符串数组
- suggestions: 字符串数组
- matched_keywords: 字符串数组
- missing_keywords: 字符串数组
- evidence: 数组,每一项包含 source、content、score

错误信息:
{error_message}

原始输出:
{raw_text}
""".strip()

    logger.info("Start LLM JSON repair request")
    repaired_text = call_llm(repair_prompt, temperature=0, profile="fast")
    result = parse_analysis_result(repaired_text)
    result.analysis_mode = "repair"
    logger.info("LLM JSON repair finished")
    return result


def find_keywords_in_text(text: str) -> list[str]:
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
            "简历中已体现部分岗位相关能力:" + "、".join(matched_keywords[:6]) + "。"
        )
    else:
        strengths.append("简历具备一定项目和技术基础,但与岗位关键词的直接匹配表达不足。")

    if missing_keywords:
        weaknesses.append(
            "简历中对以下岗位关键词体现不足:" + "、".join(missing_keywords[:6]) + "。"
        )
        suggestions.append(
            "建议在项目经历中补充这些能力的真实实践表达:"
            + "、".join(missing_keywords[:6]) + "。"
        )
    else:
        weaknesses.append("当前未发现明显关键词缺口,但仍可增强项目结果和技术细节表达。")

    suggestions.append('建议将项目经历按照"业务场景 + 技术方案 + 工程实现 + 结果指标"的结构重写。')
    suggestions.append("建议突出 FastAPI 接口封装、Prompt Engineering、结构化输出、RAG/Agent 等 AI 应用开发能力。")

    fallback_result = MatchAnalysisResult(
        score=score,
        summary="LLM 分析暂不可用,系统已基于关键词匹配生成兜底分析结果。",
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
    prompt = build_resume_analysis_prompt(
        resume_text=resume_text,
        job_text=job_text,
        retrieved_context=retrieved_context,
    )

    logger.info("Start LLM resume-job match analysis request")

    try:
        # 大 prompt + 长 JSON 输出 → heavy profile
        raw_content = call_llm(prompt, temperature=0.2, profile="heavy")
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
            except (LLMCallError, json.JSONDecodeError, ValidationError, ValueError) as repair_error:
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

    except LLMCallError as llm_error:
        logger.error(f"LLM call failed: {repr(llm_error)}")
        return build_fallback_analysis(
            resume_text=resume_text,
            job_text=job_text,
            error_message=(
                f"call_id={llm_error.call_id}; attempts={llm_error.attempts}; "
                f"last_error={repr(llm_error.last_exception)}"
            ),
        )
    except Exception as unknown_error:
        logger.error(f"Unexpected error in analyze_resume_with_llm: {repr(unknown_error)}")
        return build_fallback_analysis(
            resume_text=resume_text,
            job_text=job_text,
            error_message=repr(unknown_error),
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
    prompt = f"""
你是一个简历优化助手。下面是某次简历分析的上下文,请基于这些内容回答用户追问。

要求:
1. 回答要简洁、明确、可执行。
2. 优先结合已有分析结果回答。
3. 不要编造未提供的信息。
4. 如果用户要求改写简历,请给出可以直接放进简历的 bullet point。
5. 如果用户询问面试准备,请按照"知识点 + 高频问题 + 准备建议"的结构回答。

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
        content = call_llm(prompt, temperature=0.3, profile="default")
        logger.info("Follow-up LLM response received")
        return content.strip()
    except LLMCallError as error:
        logger.error(f"Follow-up LLM request failed: {repr(error)}")
        return (
            "当前大模型追问服务暂时不可用。"
            "建议你先根据已有分析结果优化简历:突出与岗位 JD 相关的技术关键词,"
            '并按照"项目背景 + 技术方案 + 个人职责 + 量化结果"的结构重写项目经历。'
        )

def call_llm_stream(
        prompt: str,
        temperature: float = 0.2,
        profile: TimeoutProfile = "default",
) -> Iterator[str]:
    """
    流式LLM调用。每次yield一个token chunk。

    与call_llm的差异:
    -返回值从str改为Iterator[str]
    -不做重试(streaming重试会让用户看到两遍token，体验糟糕;
    用户感知到错误时手动重试更合适)
    -仍然记录metrics到LLM_STATS

    用法:
        for chunk in call_llm_stream("你好"):
            print(chunk, end="", flush=True)
    
    Raises:
        LLMCallError: 调用失败
    """
    call_id = uuid.uuid4().hex[:8]
    timeout = TIMEOUT_BY_PROFILE.get(profile, TIMEOUT_BY_PROFILE["default"])
    metrics = LLMCallMetrics(
        call_id=call_id,
        profile=profile,
        model=settings.LLM_MODEL,
        attempts=1,
    )

    overall_start = time.perf_counter()
    accumulated_text_parts: list[str] = []

    try:
        stream = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个严谨、稳定、擅长结构化输出的AI应用分析助手。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            timeout=timeout,
            stream=True,
            stream_options={"include_usage": True},
        )

        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if choices:
                delta = getattr(choices[0], "delta", None)
                if delta is not None:
                    content = getattr(delta, "content", None)
                    if content:
                        accumulated_text_parts.append(content)
                        yield content

            usage = getattr(chunk, "usage", None)
            if usage is not None:
                metrics.prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                metrics.completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                metrics.total_tokens = getattr(usage, "total_tokens", 0) or 0

        metrics.success = True
        metrics.total_latency_ms = (time.perf_counter() - overall_start) * 1000
        metrics.last_attempt_latency_ms = metrics.total_latency_ms

        if metrics.completion_tokens == 0:
            full_text = "".join(accumulated_text_parts)
            metrics.completion_tokens = max(1, int(len(full_text) * 0.5))

        logger.info(
            f"[LLM stream call_id={call_id}] success"
            f"profile={profile} latency={metrics.total_latency_ms:.0f}ms "
            f"tokens={metrics.total_tokens or metrics.completion_tokens}"
        )
        LLM_STATS.record(metrics)
    
    except FATAL_EXCEPTIONS as fatal:
        metrics.total_latency_ms = (time.perf_counter() - overall_start) * 1000
        metrics.success = False
        metrics.error_type = _categorize_error(fatal)
        metrics.error_message = repr(fatal)
        logger.error(f"[LLM stream call_id={call_id}] FATAL {metrics.error_type}: {fatal}")
        LLM_STATS.record(metrics)
        raise LLMCallError(
            f"Fatal LLM sstreaming error: {metrics.error_type}",
            call_id=call_id, attempts=1, last_exception=fatal,
        ) from fatal
    
    except (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError, APIStatusError) as exc:
        metrics.total_latency_ms = (time.perf_counter() - overall_start) * 1000
        metrics.success = False
        metrics.error_type = _categorize_error(exc)
        metrics.error_message = repr(exc)
        logger.error(f"[LLM stream call_id={call_id}] error: {repr(exc)}")
        LLM_STATS.record(metrics)
        raise LLMCallError(
            f"LLM streaming error: {metrics.error_type}",
            call_id=call_id, attempts=1, last_exception=exc,
        ) from exc
    
    except Exception as unknown:
        metrics.total_latency_ms = {time.perf_counter() - overall_start} * 1000
        metrics.success = False
        metrics.error_message = repr(unknown)
        logger.error(f"[LLM stream call_id={call_id}] unknown: {repr(unknown)}")
        LLM_STATS.record(metrics)
        raise LLMCallError(
            f"LLM streaming unknown error",
            call_id-call_id, attempts=1, last_exception=unknown,
        ) from unknown
