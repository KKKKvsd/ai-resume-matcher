import json
import math
import re
from pathlib import Path
from typing import Any, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logger import logger
from app.schemas.retrieval import RetrievalResult, RetrievedChunk


KNOWLEDGE_DIR = Path("docs/knowledge")

# 模块级单例,保留你原来的设计
_vector_store = None
_bm25_index = None
_chunk_corpus: list[Document] = []


# ---------------------------------------------------------------------------
# BM25 实现
# ---------------------------------------------------------------------------
# 用 rank_bm25 库（纯 Python，无 C 扩展，部署友好）。
# 装好 rank_bm25 后这个 import 才会成功；否则会自动降级为纯向量模式。
try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False
    BM25Okapi = None  # type: ignore[assignment, misc]
    logger.warning("rank_bm25 not installed; BM25 retrieval disabled. "
                   "Install via: pip install rank-bm25")


def _tokenize(text: str) -> list[str]:
    """
    简单的中英文混合分词。
    设计选择：
    - 中文按字切（细粒度，BM25 上下文中召回率更高）。
    - 英文按 \\W 分割并小写化。
    - 不引入 jieba 等重型分词器，部署更简单；如需精度可后续升级。
    """
    if not text:
        return []
    # 把 ASCII 单词切出来
    en_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_+\-#]*", text.lower())
    # 把中文字符按单字切（BM25 召回率友好）
    zh_tokens = re.findall(r"[\u4e00-\u9fff]", text)
    return en_tokens + zh_tokens


def _build_bm25_index(documents: list[Document]) -> Optional[Any]:
    """构建 BM25 索引。"""
    if not _BM25_AVAILABLE or not documents:
        return None

    try:
        tokenized_corpus = [_tokenize(doc.page_content) for doc in documents]
        # 防御：corpus 全空时 BM25Okapi 会抛异常
        if not any(tokenized_corpus):
            logger.warning("All documents tokenized to empty; skip BM25 index.")
            return None
        return BM25Okapi(tokenized_corpus)
    except Exception as exc:
        logger.warning(f"Failed to build BM25 index: {repr(exc)}")
        return None


def _bm25_search(query: str, top_k: int = 10) -> list[tuple[int, float]]:
    """
    BM25 检索。

    Returns:
        [(doc_index, score), ...]
        按 score 降序，最多 top_k 个。
    """
    global _bm25_index, _chunk_corpus
    if _bm25_index is None or not _chunk_corpus:
        return []

    try:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        scores = _bm25_index.get_scores(query_tokens)
        # 取 top_k
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        # 过滤分数为 0 的（完全没命中）
        ranked = [(i, s) for i, s in ranked if s > 0][:top_k]
        return ranked
    except Exception as exc:
        logger.warning(f"BM25 search failed: {repr(exc)}")
        return []


# ---------------------------------------------------------------------------
# 文档加载与索引初始化
# ---------------------------------------------------------------------------
def load_knowledge_documents() -> list[Document]:
    """加载 docs/knowledge/*.md。保留你原来的实现。"""
    documents: list[Document] = []

    if not KNOWLEDGE_DIR.exists():
        logger.warning(f"Knowledge directory not found: {KNOWLEDGE_DIR}")
        return documents

    for file_path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        try:
            content = file_path.read_text(encoding="utf-8")
            if content.strip():
                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": str(file_path),
                            "file_name": file_path.name,
                        },
                    )
                )
        except Exception as exc:
            logger.warning(f"Failed to read knowledge file {file_path}: {repr(exc)}")

    logger.info(f"Loaded knowledge documents: {len(documents)}")
    return documents


def _build_indices() -> tuple[Optional[FAISS], Optional[Any], list[Document]]:
    """同时构建向量索引和 BM25 索引,共享同一份 chunk corpus。"""
    documents = load_knowledge_documents()
    if not documents:
        return None, None, []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )
    chunks = splitter.split_documents(documents)

    # 给每个 chunk 写入稳定 index，避免后续 vector 检索结果回查时
    # 用内容比对（chunk 内容可能撞重复）。
    for i, c in enumerate(chunks):
        c.metadata["chunk_idx"] = i

    logger.info(f"Knowledge chunks created: {len(chunks)}")

    # 向量索引
    vector_store: Optional[FAISS] = None
    if settings.LLM_API_KEY:
        try:
            embeddings = OpenAIEmbeddings(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                model=settings.EMBEDDING_MODEL,
            )
            vector_store = FAISS.from_documents(chunks, embedding=embeddings)
            logger.info("FAISS vector store built successfully")
        except Exception as exc:
            logger.warning(f"Failed to build vector store: {repr(exc)}")
    else:
        logger.warning("LLM_API_KEY is empty; vector store will not be initialized.")

    # BM25 索引
    bm25_index = _build_bm25_index(chunks)
    if bm25_index is not None:
        logger.info("BM25 index built successfully")

    return vector_store, bm25_index, chunks


def _ensure_indices_initialized() -> None:
    """懒加载初始化。第一次 retrieve 调用时构建索引。"""
    global _vector_store, _bm25_index, _chunk_corpus

    if _vector_store is not None or _bm25_index is not None:
        return  # 已初始化

    logger.info("Initializing RAG indices (vector + BM25)")
    try:
        _vector_store, _bm25_index, _chunk_corpus = _build_indices()
    except Exception as exc:
        logger.warning(f"Failed to initialize RAG indices: {repr(exc)}")


def get_vector_store():
    """保留向后兼容的 getter。"""
    _ensure_indices_initialized()
    return _vector_store


# ---------------------------------------------------------------------------
# RRF 融合
# ---------------------------------------------------------------------------
# RRF 是工业界（Elasticsearch、Vespa、Weaviate）的标准融合策略。
# 公式: score(d) = sum over each retriever of 1/(k + rank_d)
# 优点: 不需要 normalize 不同检索器的分数（向量 cosine 和 BM25 不在同一量纲）。
# 经验值 k=60 来自原论文 (Cormack et al., 2009)。
def _rrf_fuse(
    bm25_results: list[tuple[int, float]],
    vector_results: list[tuple[int, float]],
    k: int = 60,
) -> dict[int, dict[str, Any]]:
    """
    Reciprocal Rank Fusion。

    Returns:
        {doc_index: {"rrf_score": float, "bm25_score": float|None,
                     "vector_score": float|None, "matched_via": [...]}}
    """
    fused: dict[int, dict[str, Any]] = {}

    for rank, (doc_idx, score) in enumerate(bm25_results, start=1):
        fused.setdefault(
            doc_idx,
            {"rrf_score": 0.0, "bm25_score": None, "vector_score": None, "matched_via": []},
        )
        fused[doc_idx]["rrf_score"] += 1.0 / (k + rank)
        fused[doc_idx]["bm25_score"] = float(score)
        fused[doc_idx]["matched_via"].append("bm25")

    for rank, (doc_idx, score) in enumerate(vector_results, start=1):
        fused.setdefault(
            doc_idx,
            {"rrf_score": 0.0, "bm25_score": None, "vector_score": None, "matched_via": []},
        )
        fused[doc_idx]["rrf_score"] += 1.0 / (k + rank)
        fused[doc_idx]["vector_score"] = float(score)
        fused[doc_idx]["matched_via"].append("vector")

    return fused


# ---------------------------------------------------------------------------
# LLM Reranker（cross-encoder 风格）
# ---------------------------------------------------------------------------
def _build_rerank_prompt(query: str, candidates: list[RetrievedChunk]) -> str:
    """
    LLM rerank prompt。

    设计原则：
    - 让 LLM 对每个候选给 0-10 的相关度打分，而不是直接排序（打分更稳定）。
    - 强制 JSON 输出便于解析。
    - 使用 chunk_id 而不是序号，避免顺序错乱。
    """
    candidates_text = "\n\n".join(
        f"[chunk_id={i}]\n{chunk.content[:400]}"  # 截断防止 prompt 太长
        for i, chunk in enumerate(candidates)
    )

    return f"""
你是一个 RAG 检索结果的相关性评分器。请对每个候选 chunk 与 query 的相关程度打分。

评分标准：
- 10: 完全回答了 query 或包含 query 询问的关键信息
- 7-9: 高度相关，包含部分关键信息
- 4-6: 中度相关，涉及相关主题但不直接回答
- 1-3: 弱相关，仅有少量背景信息
- 0: 完全无关

要求：
1. 对每个 chunk_id 都打分，不要遗漏。
2. 只返回 JSON，不要 markdown，不要解释。

返回格式：
{{
  "scores": [
    {{"chunk_id": 0, "score": 8.5}},
    {{"chunk_id": 1, "score": 3.0}}
  ]
}}

Query: {query}

候选 chunks:
{candidates_text}
""".strip()


def _llm_rerank(
    query: str,
    candidates: list[RetrievedChunk],
    top_k: int,
) -> tuple[list[RetrievedChunk], bool]:
    """
    用 LLM 对候选 chunk 重排。

    Returns:
        (重排后的 top_k chunks, 是否成功使用 rerank)
        失败时返回 (按 RRF 排序的 top_k, False)。
    """
    if not candidates:
        return [], False

    # 候选太少没必要 rerank
    if len(candidates) <= top_k:
        return candidates[:top_k], False

    # 延迟 import 避免循环依赖
    try:
        from app.utils.llm_client import call_llm, clean_llm_json_text
    except ImportError as exc:
        logger.warning(f"Cannot import LLM client for rerank: {repr(exc)}")
        return candidates[:top_k], False

    prompt = _build_rerank_prompt(query, candidates)

    try:
        raw = call_llm(prompt, temperature=0)
        cleaned = clean_llm_json_text(raw)
        data = json.loads(cleaned)

        # 把 LLM 给的分数贴回到 chunk 上
        score_map: dict[int, float] = {}
        for item in data.get("scores", []):
            cid = item.get("chunk_id")
            score = item.get("score")
            if isinstance(cid, int) and isinstance(score, (int, float)):
                score_map[cid] = float(score)

        if not score_map:
            logger.warning("LLM rerank returned empty scores; fallback to RRF order.")
            return candidates[:top_k], False

        for i, chunk in enumerate(candidates):
            chunk.rerank_score = score_map.get(i, 0.0)

        # 按 rerank_score 降序
        reranked = sorted(
            candidates,
            key=lambda c: c.rerank_score if c.rerank_score is not None else -math.inf,
            reverse=True,
        )
        return reranked[:top_k], True

    except (json.JSONDecodeError, Exception) as exc:
        logger.warning(f"LLM rerank failed, fallback to RRF order: {repr(exc)}")
        return candidates[:top_k], False


# ---------------------------------------------------------------------------
# Public API: 三阶段混合检索
# ---------------------------------------------------------------------------
def retrieve_knowledge_hybrid(
    query: str,
    top_k: int = 3,
    candidate_pool_size: int = 10,
    use_rerank: bool = True,
) -> RetrievalResult:
    """
    BM25 + 向量混合召回 + LLM rerank。

    Args:
        query: 查询文本
        top_k: 最终返回的 chunk 数量
        candidate_pool_size: 每路检索召回的候选数（rerank 池大小 = 2 * 这个值）
        use_rerank: 是否启用 LLM rerank

    Returns:
        RetrievalResult。任何阶段失败都不会抛异常，返回最佳可获得的结果。
    """
    if not query or not query.strip():
        return RetrievalResult(query=query, mode="empty")

    _ensure_indices_initialized()

    warnings: list[str] = []

    # === 阶段 1: 双路召回 ===
    bm25_results: list[tuple[int, float]] = []
    vector_results_with_score: list[tuple[int, float]] = []

    # BM25
    if _bm25_index is not None and _chunk_corpus:
        bm25_results = _bm25_search(query, top_k=candidate_pool_size)
        logger.info(f"BM25 candidates: {len(bm25_results)}")
    else:
        warnings.append("BM25 unavailable; using vector-only retrieval.")

    # Vector
    if _vector_store is not None:
        try:
            # similarity_search_with_score 返回 (Document, distance)
            # 注意：FAISS 默认是 L2 距离，越小越相关；我们转成"相似度"（越大越相关）
            docs_with_scores = _vector_store.similarity_search_with_score(
                query, k=candidate_pool_size
            )
            # 转成 (chunk_index, similarity_score) 列表
            for doc, distance in docs_with_scores:
                # 在 _chunk_corpus 里找这个 doc 的 index
                idx = _find_chunk_index(doc)
                if idx is not None:
                    similarity = 1.0 / (1.0 + float(distance))  # 把 distance 转成 0-1 的相似度
                    vector_results_with_score.append((idx, similarity))
            logger.info(f"Vector candidates: {len(vector_results_with_score)}")
        except Exception as exc:
            logger.warning(f"Vector search failed: {repr(exc)}")
            warnings.append(f"Vector search failed: {repr(exc)}")
    else:
        warnings.append("Vector store unavailable; using BM25-only retrieval.")

    # 都失败的情况
    if not bm25_results and not vector_results_with_score:
        return RetrievalResult(
            query=query,
            mode="empty",
            warnings=warnings + ["Both BM25 and vector retrieval failed."],
        )

    # 决定 mode
    if not bm25_results:
        mode = "vector_only"
    elif not vector_results_with_score:
        mode = "bm25_only"
    else:
        mode = "hybrid"

    # === 阶段 2: RRF 融合 ===
    fused = _rrf_fuse(bm25_results, vector_results_with_score)

    candidates: list[RetrievedChunk] = []
    for doc_idx, info in fused.items():
        if doc_idx >= len(_chunk_corpus):
            continue
        doc = _chunk_corpus[doc_idx]
        candidates.append(
            RetrievedChunk(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                file_name=doc.metadata.get("file_name", "unknown"),
                rank=0,  # 临时占位,rerank 后再赋值
                bm25_score=info["bm25_score"],
                vector_score=info["vector_score"],
                rrf_score=info["rrf_score"],
                matched_via=info["matched_via"],
            )
        )

    # 按 RRF 分数降序排
    candidates.sort(key=lambda c: c.rrf_score or 0.0, reverse=True)
    logger.info(f"Fused candidates: {len(candidates)}")

    # === 阶段 3: LLM rerank ===
    rerank_used = False
    if use_rerank:
        # 只对 top 2*top_k 做 rerank,省钱
        rerank_pool = candidates[: max(top_k * 2, 6)]
        final_chunks, rerank_used = _llm_rerank(query, rerank_pool, top_k=top_k)
    else:
        final_chunks = candidates[:top_k]

    # 赋最终 rank
    for i, chunk in enumerate(final_chunks, start=1):
        chunk.rank = i

    logger.info(
        f"Retrieval done: mode={mode}, fused={len(candidates)}, "
        f"final={len(final_chunks)}, rerank={rerank_used}"
    )

    return RetrievalResult(
        query=query,
        chunks=final_chunks,
        bm25_candidates=len(bm25_results),
        vector_candidates=len(vector_results_with_score),
        fused_candidates=len(candidates),
        final_count=len(final_chunks),
        mode=mode,
        rerank_used=rerank_used,
        warnings=warnings,
    )


def _find_chunk_index(doc: Document) -> Optional[int]:
    """
    在 _chunk_corpus 里找到 doc 的索引。

    优先用 metadata['chunk_idx']（稳定且唯一，在 _build_indices 里写入）；
    metadata 缺失时回退到内容匹配（兼容外部传入的 Document）。
    """
    idx = doc.metadata.get("chunk_idx")
    if isinstance(idx, int) and 0 <= idx < len(_chunk_corpus):
        return idx

    # fallback: 内容匹配
    target_content = doc.page_content
    target_source = doc.metadata.get("source")
    for i, c in enumerate(_chunk_corpus):
        if c.page_content == target_content and c.metadata.get("source") == target_source:
            return i
    return None


# ---------------------------------------------------------------------------
# 向后兼容：保留老接口 retrieve_knowledge
# ---------------------------------------------------------------------------
def retrieve_knowledge(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """
    向后兼容接口。
    内部走 hybrid retrieval；外部签名保持原样，所有调用方零改动。
    """
    if not query or not query.strip():
        return []

    result = retrieve_knowledge_hybrid(query=query, top_k=top_k, use_rerank=True)

    if result.mode == "empty":
        logger.warning(f"No retrieval result; warnings: {result.warnings}")
        return []

    return result.to_legacy_list()