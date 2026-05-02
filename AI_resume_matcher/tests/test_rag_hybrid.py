import json
import math
import pytest

from langchain_core.documents import Document

from app.utils import rag_retriever
from app.schemas.retrieval import RetrievedChunk


class TestTokenize:
    def test_chinese_tokenized_per_char(self):
        tokens = rag_retriever._tokenize("智能体应用")
        assert tokens == ["智", "能", "体", "应", "用"]

    def test_english_lowercased_and_split(self):
        tokens = rag_retriever._tokenize("FastAPI vs Spring Boot")
        assert tokens == ["fastapi", "vs", "spring", "boot"]

    def test_mixed_language(self):
        tokens = rag_retriever._tokenize("Python 和 RAG 应用")
        assert "python" in tokens
        assert "rag" in tokens
        assert "和" in tokens
        assert "应" in tokens

    def test_special_tech_names_preserved(self):
        tokens = rag_retriever._tokenize("C++ and C# 开发")
        assert "c++" in tokens
        assert "c#" in tokens

    def test_empty_input(self):
        assert rag_retriever._tokenize("") == []
        assert rag_retriever._tokenize(None) == []


class TestRRFFusion:
    def test_single_source_only(self):
        """仅 BM25 召回时，融合结果应保留原始顺序。"""
        bm25 = [(0, 5.0), (3, 3.0), (1, 1.0)]
        fused = rag_retriever._rrf_fuse(bm25, [])

        assert len(fused) == 3
        # 排名 1 的 doc rrf 分数最高
        scores = [(idx, info["rrf_score"]) for idx, info in fused.items()]
        scores.sort(key=lambda x: -x[1])
        assert scores[0][0] == 0
        assert scores[2][0] == 1

    def test_double_hit_ranks_first(self):
        """两路都命中的 doc 应该 RRF 分数最高（hybrid 的核心价值）。"""
        bm25 = [(100, 5.0), (200, 1.0)]
        vector = [(100, 0.95), (300, 0.80)]
        fused = rag_retriever._rrf_fuse(bm25, vector)

        # doc 100 在两路都排第 1
        sorted_docs = sorted(fused.items(), key=lambda x: -x[1]["rrf_score"])
        assert sorted_docs[0][0] == 100
        assert "bm25" in fused[100]["matched_via"]
        assert "vector" in fused[100]["matched_via"]

    def test_rrf_math_correctness(self):
        """RRF 分数公式正确：1/(k+rank)。"""
        bm25 = [(0, 5.0)]
        fused = rag_retriever._rrf_fuse(bm25, [], k=60)
        # rank=1, k=60 → 1/61
        assert abs(fused[0]["rrf_score"] - 1.0 / 61) < 1e-9

    def test_double_hit_beats_single_top(self):
        """两路低排名命中应该胜过单路第 1 名。"""
        # doc 100 仅在 BM25 排第 1
        # doc 200 在 BM25 排第 10 + vector 排第 1
        bm25 = [(100, 5.0)] + [(i, 0.1) for i in range(400, 408)] + [(200, 0.05)]
        vector = [(200, 0.95)]
        fused = rag_retriever._rrf_fuse(bm25, vector)
        assert fused[200]["rrf_score"] > fused[100]["rrf_score"]


class TestRerank:
    def test_rerank_with_mock_llm(self, monkeypatch):
        """mock LLM 返回分数,验证 rerank 后顺序正确。"""

        def fake_call_llm(prompt, temperature=0):
            return json.dumps({
                "scores": [
                    {"chunk_id": 0, "score": 3.0},
                    {"chunk_id": 1, "score": 9.5},
                    {"chunk_id": 2, "score": 5.0},
                    {"chunk_id": 3, "score": 1.0},
                ]
            })

        # mock 掉 _llm_rerank 内部用到的 call_llm
        import app.utils.llm_client as llm_client
        monkeypatch.setattr(llm_client, "call_llm", fake_call_llm)

        candidates = [
            RetrievedChunk(content=f"content {i}", file_name="x.md", rrf_score=0.1)
            for i in range(4)
        ]
        result, used = rag_retriever._llm_rerank("test query", candidates, top_k=3)

        assert used is True
        assert len(result) == 3
        # rerank 后第一个应是原 chunk_id=1（分数 9.5 最高）
        assert result[0].content == "content 1"
        assert result[0].rerank_score == 9.5

    def test_rerank_falls_back_on_llm_failure(self, monkeypatch):
        """LLM 抛异常时,应该返回原 RRF 顺序的 top_k。"""

        def broken_llm(prompt, temperature=0):
            raise TimeoutError("LLM timeout")

        import app.utils.llm_client as llm_client
        monkeypatch.setattr(llm_client, "call_llm", broken_llm)

        candidates = [
            RetrievedChunk(content=f"c {i}", file_name="x.md", rrf_score=0.5 - 0.1 * i)
            for i in range(5)
        ]
        result, used = rag_retriever._llm_rerank("query", candidates, top_k=3)

        assert used is False
        assert len(result) == 3
        # 应保留 RRF 顺序
        assert result[0].content == "c 0"

    def test_rerank_skipped_when_candidates_few(self, monkeypatch):
        """候选数 ≤ top_k 时,rerank 被跳过。"""

        def should_not_be_called(prompt, temperature=0):
            raise AssertionError("LLM should not be called when candidates <= top_k")

        import app.utils.llm_client as llm_client
        monkeypatch.setattr(llm_client, "call_llm", should_not_be_called)

        candidates = [RetrievedChunk(content="c", file_name="x.md") for _ in range(2)]
        result, used = rag_retriever._llm_rerank("query", candidates, top_k=3)
        assert used is False
        assert len(result) == 2

    def test_rerank_handles_invalid_items(self, monkeypatch):
        """LLM 输出含非法条目时,跳过非法条目,有效条目仍能用。"""

        def fake_call_llm(prompt, temperature=0):
            return json.dumps({
                "scores": [
                    {"chunk_id": 0, "score": 7.0},
                    {"chunk_id": "invalid", "score": 5.0},  # 非法 chunk_id
                    {"chunk_id": 2},                         # 缺 score
                    {"chunk_id": 3, "score": None},          # score 为 null
                    {"chunk_id": 1, "score": 4.0},
                ]
            })

        import app.utils.llm_client as llm_client
        monkeypatch.setattr(llm_client, "call_llm", fake_call_llm)

        candidates = [
            RetrievedChunk(content=f"c {i}", file_name="x.md", rrf_score=0.1)
            for i in range(4)
        ]
        result, used = rag_retriever._llm_rerank("query", candidates, top_k=3)

        assert used is True
        # chunk 0 (7.0) 应在 chunk 1 (4.0) 前面
        c0 = next(c for c in result if c.content == "c 0")
        c1 = next(c for c in result if c.content == "c 1")
        assert (c0.rerank_score or 0) > (c1.rerank_score or 0)


class TestEndToEnd:
    def test_empty_query_returns_empty(self):
        result = rag_retriever.retrieve_knowledge_hybrid("", top_k=3)
        assert result.mode == "empty"
        assert result.final_count == 0

    def test_legacy_api_signature_preserved(self):
        """老接口 retrieve_knowledge(query, top_k) -> list[dict] 必须可用。"""
        # 即使索引未初始化或失败,这个调用也不能抛异常
        result = rag_retriever.retrieve_knowledge("test query", top_k=3)
        assert isinstance(result, list)


class TestRetrievedChunkSchema:
    def test_chunk_carries_all_score_dimensions(self):
        chunk = RetrievedChunk(
            content="hello",
            file_name="t.md",
            bm25_score=2.5,
            vector_score=0.8,
            rrf_score=0.03,
            rerank_score=8.5,
            matched_via=["bm25", "vector"],
        )
        assert chunk.bm25_score == 2.5
        assert chunk.vector_score == 0.8
        assert chunk.rrf_score == 0.03
        assert chunk.rerank_score == 8.5
        assert "bm25" in chunk.matched_via