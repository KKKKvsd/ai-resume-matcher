from typing import Literal, Optional

from pydantic import BaseModel, Field


RetrievalSource = Literal["bm25", "vector", "fused", "reranked"]


class RetrievedChunk(BaseModel):
    """单个被检索到的知识 chunk。"""

    content: str = Field(..., description="chunk 的文本内容。")
    source: str = Field(default="unknown", description="文件路径。")
    file_name: str = Field(default="unknown", description="文件名。")
    rank: int = Field(default=0, description="最终排名（从 1 开始）。")

    # 各阶段分数；缺失时为 None
    bm25_score: Optional[float] = Field(default=None, description="BM25 原始分数。")
    vector_score: Optional[float] = Field(default=None, description="向量相似度分数。")
    rrf_score: Optional[float] = Field(default=None, description="RRF 融合后分数。")
    rerank_score: Optional[float] = Field(default=None, description="reranker 给的最终分数。")

    matched_via: list[RetrievalSource] = Field(
        default_factory=list,
        description="此 chunk 通过哪些路径被找到（bm25 / vector / 都有）。",
    )


class RetrievalResult(BaseModel):
    """一次检索的完整结果。"""

    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)

    # 各阶段统计
    bm25_candidates: int = 0
    vector_candidates: int = 0
    fused_candidates: int = 0
    final_count: int = 0

    mode: Literal["hybrid", "vector_only", "bm25_only", "empty"] = "hybrid"
    rerank_used: bool = False
    warnings: list[str] = Field(default_factory=list)

    def to_legacy_list(self) -> list[dict]:
        """向后兼容：老的 retrieve_knowledge() 返回 list[dict]。"""
        return [
            {
                "content": chunk.content,
                "source": chunk.source,
                "file_name": chunk.file_name,
                "rank": chunk.rank,
            }
            for chunk in self.chunks
        ]