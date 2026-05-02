import json
from typing import Any

from pydantic import ValidationError

from app.core.logger import logger
from app.schemas.keyword import KeywordExtractionResult, KeywordItem
from app.utils.llm_client import call_llm, clean_llm_json_text

KEYWORD_REGISTRY: dict[str, dict[str, Any]] = {
    "Python": {
        "aliases": ["python", "py"],
        "category": "language",
        "default_importance": "required",
    },
    "Java": {
        "aliases": ["java"],
        "category": "language",
        "default_importance": "preferred",
    },
    "FastAPI": {
        "aliases": ["fastapi", "fast api"],
        "category": "framework",
        "default_importance": "preferred",
    },
    "Spring Boot": {
        "aliases": ["spring boot", "springboot"],
        "category": "framework",
        "default_importance": "preferred",
    },
    "MySQL": {
        "aliases": ["mysql"],
        "category": "database",
        "default_importance": "preferred",
    },
    "PostgreSQL": {
        "aliases": ["postgresql", "postgres"],
        "category": "database",
        "default_importance": "preferred",
    },
    "Redis": {
        "aliases": ["redis"],
        "category": "database",
        "default_importance": "preferred",
    },
    "Docker": {
        "aliases": ["docker", "容器化"],
        "category": "devops",
        "default_importance": "preferred",
    },
    "Linux": {
        "aliases": ["linux"],
        "category": "devops",
        "default_importance": "preferred",
    },
    "RAG": {
        "aliases": ["rag", "检索增强", "retrieval augmented"],
        "category": "ai_capability",
        "default_importance": "required",
    },
    "Agent": {
        "aliases": ["agent", "agents", "智能体"],
        "category": "ai_capability",
        "default_importance": "required",
    },
    "Tool Calling": {
        "aliases": ["tool calling", "function calling", "工具调用"],
        "category": "ai_capability",
        "default_importance": "preferred",
    },
    "Memory": {
        "aliases": ["记忆管理", "长期记忆", "短期记忆"],
        "category": "ai_capability",
        "default_importance": "preferred",
    },
    "Prompt Engineering": {
        "aliases": ["prompt engineering", "提示词工程", "提示词"],
        "category": "ai_capability",
        "default_importance": "required",
    },
    "LLM": {
        "aliases": ["llm", "大模型", "大语言模型"],
        "category": "ai_capability",
        "default_importance": "preferred",
    },
    "Document Loader": {
        "aliases": ["document loader", "文档加载", "文档解析"],
        "category": "ai_capability",
        "default_importance": "preferred",
    },
    "DeepSearch": {
        "aliases": ["langchain"],
        "category": "framework",
        "default_importance": "preferred",
    },
    "Vector Database": {
        "aliases": ["向量数据库", "向量检索", "faiss", "milvus", "chroma", "pinecone"],
        "default_importance": "preferred",
    },
    "Pydantic": {
        "aliases": ["pydantic"],
        "category": "framework",
        "default_importance": "nice_to_have",
    },
}

# ---------------------------------------------------------------------------
# Layer 1: Rule-based extraction
# ---------------------------------------------------------------------------
def _rule_extract(job_text: str) -> dict[str, KeywordItem]:
    """基于字典做精确匹配。"""
    if not job_text:
        return {}

    text_lower = job_text.lower()
    hits: dict[str, KeywordItem] = {}

    for canonical, meta in KEYWORD_REGISTRY.items():
        matched_aliases = [
            alias for alias in meta["aliases"] if alias.lower() in text_lower
        ]
        if not matched_aliases:
            continue

        hits[canonical] = KeywordItem(
            name=canonical,
            aliases=matched_aliases,
            category=meta.get("category", "general"),
            importance=meta.get("default_importance", "preferred"),
            source="rule",
        )

    return hits


# ---------------------------------------------------------------------------
# Layer 2: LLM-based structured extraction
# ---------------------------------------------------------------------------
def _build_llm_extraction_prompt(job_text: str) -> str:
    """构造 LLM 抽取 prompt。"""
    return f"""
你是一个专业的招聘 JD 技能抽取助手。请从下面的岗位描述中抽取技术与业务相关的技能关键词。

要求：
1. 只抽取 JD 中明确出现的技能或概念，不要编造。
2. 把"Python 编程"、"熟悉 Python"等都规范化为同一个关键词 "Python"。
3. category 必须是以下之一：
   language / framework / database / devops / ai_capability / tool / soft_skill / general
4. importance 必须是以下之一：
   - required: JD 用"必须"、"熟练"、"精通"等词，或在硬性要求段落
   - preferred: JD 用"熟悉"、"了解"、"优先"等词
   - nice_to_have: JD 用"加分项"、"有兴趣"等词
5. 不要输出 markdown，不要输出 ```json 包裹，只输出一个合法 JSON。

返回 JSON 格式：
{{
  "keywords": [
    {{
      "name": "Python",
      "aliases": ["python", "py"],
      "category": "language",
      "importance": "required"
    }}
  ]
}}

岗位 JD：
{job_text}
""".strip()


def _llm_extract(job_text: str) -> tuple[dict[str, KeywordItem], str | None]:
    """调用 LLM 做结构化抽取。失败时返回空 hits。"""
    if not job_text:
        return {}, None

    prompt = _build_llm_extraction_prompt(job_text)

    try:
        raw = call_llm(prompt, temperature=0)
        cleaned = clean_llm_json_text(raw)
        data = json.loads(cleaned)

        hits: dict[str, KeywordItem] = {}
        for item in data.get("keywords", []):
            try:
                kw = KeywordItem(
                    name=item.get("name", "").strip(),
                    aliases=item.get("aliases", []) or [],
                    category=item.get("category", "general"),
                    importance=item.get("importance", "preferred"),
                    source="llm",
                )
                if not kw.name:
                    continue
                hits[kw.name] = kw
            except ValidationError as ve:
                logger.warning(f"LLM keyword item validation failed: {repr(ve)}")
                continue

        logger.info(f"LLM extracted keywords count: {len(hits)}")
        return hits, None

    except (json.JSONDecodeError, Exception) as exc:
        logger.warning(f"LLM keyword extraction failed: {repr(exc)}")
        return {}, repr(exc)


# ---------------------------------------------------------------------------
# Layer 3: Normalization & merge
# ---------------------------------------------------------------------------
SYNONYM_MAP: dict[str, str] = {
    "python 编程": "Python",
    "python3": "Python",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "向量搜索": "Vector Database",
    "向量库": "Vector Database",
    "faiss": "Vector Database",
    "milvus": "Vector Database",
    "function calling": "Tool Calling",
    "function-calling": "Tool Calling",
    "提示工程": "Prompt Engineering",
    "提示词": "Prompt Engineering",
    "大语言模型": "LLM",
    "大模型": "LLM",
    "agents": "Agent",
    "智能体": "Agent",
    "检索增强生成": "RAG",
}


def _canonicalize_name(name: str) -> str:
    """把 LLM 输出的非标准名称收敛到字典 canonical name。"""
    lower = name.strip().lower()
    if lower in SYNONYM_MAP:
        return SYNONYM_MAP[lower]
    for canonical in KEYWORD_REGISTRY:
        if canonical.lower() == lower:
            return canonical
    return name.strip()


def _merge(
    rule_hits: dict[str, KeywordItem],
    llm_hits: dict[str, KeywordItem],
) -> list[KeywordItem]:
    """
    合并规则层和 LLM 层的结果。

    合并规则：
    - 两层都命中: source=merged, importance 取 LLM 的判断（看了上下文更准）
    - 只有规则命中: source=rule
    - 只有 LLM 命中: source=llm
    - aliases 取并集
    """
    normalized_llm: dict[str, KeywordItem] = {}
    for raw_name, item in llm_hits.items():
        canonical = _canonicalize_name(raw_name)
        if canonical in normalized_llm:
            existing = normalized_llm[canonical]
            existing.aliases = list(set(existing.aliases + item.aliases))
        else:
            item.name = canonical
            normalized_llm[canonical] = item

    all_names = set(rule_hits.keys()) | set(normalized_llm.keys())
    merged: list[KeywordItem] = []

    for name in all_names:
        rule_item = rule_hits.get(name)
        llm_item = normalized_llm.get(name)

        if rule_item and llm_item:
            merged.append(
                KeywordItem(
                    name=name,
                    aliases=list(set(rule_item.aliases + llm_item.aliases)),
                    category=rule_item.category,
                    importance=llm_item.importance,
                    source="merged",
                )
            )
        elif rule_item:
            merged.append(rule_item)
        else:
            merged.append(llm_item)  # type: ignore[arg-type]

    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract_keywords_hybrid(
    job_text: str,
    use_llm: bool = True,
) -> KeywordExtractionResult:
    """
    混合关键词提取的对外入口。

    Args:
        job_text: 岗位 JD 全文。
        use_llm: 是否启用 LLM 层。设为 False 时退化为纯规则模式（用于测试或省钱）。

    Returns:
        KeywordExtractionResult。即使 LLM 失败也会返回规则层结果，永远不抛异常。
    """
    if not job_text or not job_text.strip():
        return KeywordExtractionResult(mode="rule_only")

    warnings: list[str] = []

    # Layer 1
    rule_hits = _rule_extract(job_text)
    logger.info(f"Rule layer extracted: {len(rule_hits)} keywords")

    # Layer 2
    llm_hits: dict[str, KeywordItem] = {}
    if use_llm:
        llm_hits, llm_error = _llm_extract(job_text)
        if llm_error:
            warnings.append(f"LLM extraction failed, using rule-only mode: {llm_error}")
    else:
        warnings.append("LLM extraction disabled by caller.")

    # Layer 3
    if not llm_hits:
        merged_keywords = list(rule_hits.values())
        mode = "rule_only"
    else:
        merged_keywords = _merge(rule_hits, llm_hits)
        mode = "hybrid"

    rule_only = sum(1 for k in merged_keywords if k.source == "rule")
    llm_only = sum(1 for k in merged_keywords if k.source == "llm")
    merged_count = sum(1 for k in merged_keywords if k.source == "merged")

    return KeywordExtractionResult(
        keywords=merged_keywords,
        total=len(merged_keywords),
        rule_only=rule_only,
        llm_only=llm_only,
        merged=merged_count,
        mode=mode,  # type: ignore[arg-type]
        warnings=warnings,
    )