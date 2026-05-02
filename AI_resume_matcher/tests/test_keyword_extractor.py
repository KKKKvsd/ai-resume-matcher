"""
tests/test_keyword_extractor.py

验证 LLM + 规则混合关键词提取器的逻辑。

运行：pytest tests/test_keyword_extractor.py -v
"""

import json
import pytest

from app.schemas.keyword import KeywordExtractionResult, KeywordItem
from app.services import keyword_extractor


JD_KUAISHOU = """
负责 LLM 调用、参数调优、请求封装、结果解析等工作。
负责 prompt engineering 相关工作，设计高质量的提示词。
参与 Agent 相关功能的研发，协助实现智能体的任务规划、记忆管理、工具调用决策。
协助开展 deepsearch 技术调研与实践。

要求：
- 计算机科学相关专业优先
- 熟悉 Python 语言
- 了解 Agent 核心组件（如 Chains、Agents、Memory、Document Loaders 等）
- 了解 prompt engineering 的基本原理与方法
"""


class TestRuleLayer:
    def test_rule_extracts_basic_keywords(self):
        result = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=False)
        names = [k.name for k in result.keywords]
        for required in ["Python", "Agent", "Prompt Engineering", "LLM", "DeepSearch"]:
            assert required in names, f"规则层应该识别 {required}"
        assert result.mode == "rule_only"

    def test_rule_layer_handles_empty_input(self):
        assert keyword_extractor.extract_keywords_hybrid("", use_llm=False).total == 0
        assert keyword_extractor.extract_keywords_hybrid("   ", use_llm=False).total == 0

    def test_rule_layer_records_aliases(self):
        result = keyword_extractor.extract_keywords_hybrid("我熟悉 Python 和 智能体 开发", use_llm=False)
        agent_kw = next((k for k in result.keywords if k.name == "Agent"), None)
        assert agent_kw is not None
        assert "智能体" in agent_kw.aliases


class TestLLMLayerAndMerge:
    def test_llm_finds_out_of_dictionary_keywords(self, monkeypatch):
        mock_response = json.dumps({
            "keywords": [
                {"name": "Python", "aliases": ["Python"], "category": "language", "importance": "required"},
                {"name": "LangChain", "aliases": ["Chains"], "category": "framework", "importance": "preferred"},
                {"name": "Vector Database", "aliases": ["FAISS"], "category": "ai_capability", "importance": "preferred"},
            ]
        })
        monkeypatch.setattr(keyword_extractor, "call_llm", lambda *a, **kw: mock_response)

        result = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=True)
        names = [k.name for k in result.keywords]

        assert "LangChain" in names
        assert result.mode == "hybrid"

        langchain_kw = next(k for k in result.keywords if k.name == "LangChain")
        assert langchain_kw.source == "llm"

    def test_merge_combines_rule_and_llm_hits(self, monkeypatch):
        mock_response = json.dumps({
            "keywords": [
                {"name": "Python", "aliases": ["Python"], "category": "language", "importance": "required"},
            ]
        })
        monkeypatch.setattr(keyword_extractor, "call_llm", lambda *a, **kw: mock_response)

        result = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=True)
        python_kw = next(k for k in result.keywords if k.name == "Python")
        assert python_kw.source == "merged"
        assert python_kw.importance == "required"

    def test_synonym_normalization(self, monkeypatch):
        mock_response = json.dumps({
            "keywords": [
                {"name": "提示工程", "aliases": ["prompt"], "category": "ai_capability", "importance": "required"},
            ]
        })
        monkeypatch.setattr(keyword_extractor, "call_llm", lambda *a, **kw: mock_response)

        result = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=True)
        names = [k.name for k in result.keywords]
        assert "Prompt Engineering" in names
        assert "提示工程" not in names


class TestFallback:
    def test_llm_timeout_falls_back_to_rule_only(self, monkeypatch):
        def raise_timeout(*args, **kwargs):
            raise TimeoutError("LLM API timeout")

        monkeypatch.setattr(keyword_extractor, "call_llm", raise_timeout)
        result = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=True)

        assert result.mode == "rule_only"
        assert result.total > 0
        assert any("LLM" in w for w in result.warnings)

    def test_llm_returns_invalid_json_does_not_crash(self, monkeypatch):
        monkeypatch.setattr(
            keyword_extractor,
            "call_llm",
            lambda *a, **kw: "Sorry I cannot help. Just some text without JSON.",
        )
        result = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=True)

        assert result.mode == "rule_only"
        assert result.total > 0

    def test_llm_returns_partial_invalid_items(self, monkeypatch):
        mock_response = json.dumps({
            "keywords": [
                {"name": "Python", "category": "language", "importance": "required"},
                {"category": "framework"},
                {"name": "", "category": "framework"},
                {"name": "LangChain", "category": "framework", "importance": "preferred"},
            ]
        })
        monkeypatch.setattr(keyword_extractor, "call_llm", lambda *a, **kw: mock_response)

        result = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=True)
        names = [k.name for k in result.keywords]

        assert "Python" in names
        assert "LangChain" in names
        assert "" not in names


class TestBackwardCompat:
    def test_to_legacy_list_returns_strings_sorted_by_importance(self, monkeypatch):
        mock_response = json.dumps({
            "keywords": [
                {"name": "Python", "category": "language", "importance": "required"},
                {"name": "Docker", "category": "devops", "importance": "nice_to_have"},
                {"name": "FastAPI", "category": "framework", "importance": "preferred"},
            ]
        })
        monkeypatch.setattr(keyword_extractor, "call_llm", lambda *a, **kw: mock_response)

        result = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=True)
        legacy = result.to_legacy_list()

        assert isinstance(legacy, list)
        assert all(isinstance(s, str) for s in legacy)
        if "Python" in legacy and "Docker" in legacy:
            assert legacy.index("Python") < legacy.index("Docker")

    def test_extract_keywords_tool_still_returns_list_str(self):
        from app.services import tools_service
        result = tools_service.extract_keywords_tool(JD_KUAISHOU)
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)
        assert len(result) > 0


class TestRecallImprovement:
    def test_hybrid_recalls_more_than_rule_only(self, monkeypatch):
        mock_response = json.dumps({
            "keywords": [
                {"name": "LangChain", "category": "framework", "importance": "preferred"},
                {"name": "Vector Database", "category": "ai_capability", "importance": "preferred"},
            ]
        })
        monkeypatch.setattr(keyword_extractor, "call_llm", lambda *a, **kw: mock_response)

        rule_only = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=False)
        hybrid = keyword_extractor.extract_keywords_hybrid(JD_KUAISHOU, use_llm=True)

        assert hybrid.total >= rule_only.total