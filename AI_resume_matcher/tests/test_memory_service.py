"""
tests/test_memory_service.py

验证 memory service 的核心逻辑。
使用 SQLite in-memory 跑真实 SQLAlchemy,但 mock 掉 LLM。

运行: pytest tests/test_memory_service.py -v
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user import User
from app.models.memory import (
    AgentSession,
    AgentSessionTurn,
    LongTermMemoryItem as LongTermMemoryItemORM,
)
from app.services import memory_service


@pytest.fixture
def db_session():
    """每个测试用一个独立的 in-memory SQLite。"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    user = User(
        username="testuser",
        email="t@example.com",
        hashed_password="x",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    yield session, user.id

    session.close()


class TestSessionMemory:
    def test_create_and_append_turns(self, db_session):
        db, user_id = db_session
        sid = memory_service.generate_session_id()

        memory_service.get_or_create_session(db, sid, user_id)
        memory_service.append_turn(db, sid, role="user", content="你好", intent="follow_up_qa")
        memory_service.append_turn(db, sid, role="agent", content="你好,有什么可以帮你的?")

        recent = memory_service.fetch_recent_turns(db, sid, limit=10)
        assert len(recent) == 2
        assert recent[0].turn_id == 1
        assert recent[0].role == "user"
        assert recent[1].turn_id == 2
        assert recent[1].role == "agent"

    def test_recent_window_returns_only_latest_n(self, db_session):
        db, user_id = db_session
        sid = memory_service.generate_session_id()
        memory_service.get_or_create_session(db, sid, user_id)

        for i in range(10):
            memory_service.append_turn(db, sid, role="user", content=f"msg-{i}")

        recent = memory_service.fetch_recent_turns(db, sid, limit=3)
        assert len(recent) == 3
        # 应该是最近 3 个: turn 8, 9, 10
        assert [t.turn_id for t in recent] == [8, 9, 10]

    def test_compress_not_triggered_below_threshold(self, db_session):
        db, user_id = db_session
        sid = memory_service.generate_session_id()
        memory_service.get_or_create_session(db, sid, user_id)

        # 6 轮,远低于 SUMMARY_TRIGGER_TURNS=12
        for i in range(6):
            memory_service.append_turn(db, sid, role="user", content=f"msg-{i}")

        triggered = memory_service.maybe_compress_session(db, sid)
        assert triggered is False

    def test_compress_triggered_when_exceed(self, db_session, monkeypatch):
        """超过阈值时,触发摘要压缩。mock LLM 返回固定摘要。"""
        db, user_id = db_session
        sid = memory_service.generate_session_id()
        memory_service.get_or_create_session(db, sid, user_id)

        # mock LLM
        def fake_call_llm(prompt, temperature=0.2):
            return "用户与 Agent 讨论了简历优化和岗位匹配。"
        from app.utils import llm_client
        monkeypatch.setattr(llm_client, "call_llm", fake_call_llm)

        # 写 15 轮
        for i in range(15):
            memory_service.append_turn(db, sid, role="user", content=f"msg-{i}")

        triggered = memory_service.maybe_compress_session(db, sid)
        assert triggered is True

        session = db.query(AgentSession).filter(AgentSession.session_id == sid).first()
        assert session.summary is not None
        # 保留最近 4 轮原文,所以 summary_until_turn = 15 - 4 = 11
        assert session.summary_until_turn == 11


class TestLongTermMemory:
    def test_add_and_retrieve(self, db_session):
        db, user_id = db_session

        memory_service.add_longterm_item(
            db, user_id, kind="goal",
            content="目标岗位是快手 AI 应用开发实习",
            keywords=["快手", "ai", "实习"],
            importance=0.9,
        )

        items = memory_service.search_longterm_items(db, user_id, query="快手")
        assert len(items) == 1
        assert items[0].kind == "goal"
        assert "快手" in items[0].content

    def test_dedup_on_same_content(self, db_session):
        db, user_id = db_session
        memory_service.add_longterm_item(db, user_id, "fact", "用户简历包含 RAG 项目", importance=0.5)
        memory_service.add_longterm_item(db, user_id, "fact", "用户简历包含 RAG 项目", importance=0.8)

        all_items = db.query(LongTermMemoryItemORM).filter(
            LongTermMemoryItemORM.user_id == user_id
        ).all()
        assert len(all_items) == 1
        # importance 取较大值
        assert all_items[0].importance == 0.8

    def test_search_ranks_by_match_and_importance(self, db_session):
        db, user_id = db_session

        memory_service.add_longterm_item(
            db, user_id, "goal", "目标快手 AI 实习",
            keywords=["快手"], importance=0.9,
        )
        memory_service.add_longterm_item(
            db, user_id, "preference", "喜欢 bullet 输出",
            keywords=["bullet"], importance=0.6,
        )
        memory_service.add_longterm_item(
            db, user_id, "fact", "用户简历包含 RAG 项目",
            keywords=["rag"], importance=0.7,
        )

        # query 命中 RAG 那条
        items = memory_service.search_longterm_items(db, user_id, query="rag 怎么写")
        assert len(items) == 1
        assert "RAG" in items[0].content

    def test_empty_query_returns_top_by_importance(self, db_session):
        db, user_id = db_session
        memory_service.add_longterm_item(db, user_id, "fact", "fact-A", importance=0.3)
        memory_service.add_longterm_item(db, user_id, "fact", "fact-B", importance=0.9)

        items = memory_service.search_longterm_items(db, user_id, query="", top_k=2)
        assert len(items) == 2
        assert items[0].content == "fact-B"


class TestMemoryBundle:
    def test_empty_bundle_for_no_session(self, db_session):
        db, user_id = db_session
        bundle = memory_service.build_memory_bundle(db, session_id=None, user_id=None)
        assert bundle.used_session_memory is False
        assert bundle.used_longterm_memory is False
        assert len(bundle.recent_turns) == 0

    def test_bundle_includes_session_and_longterm(self, db_session):
        db, user_id = db_session
        sid = memory_service.generate_session_id()

        memory_service.get_or_create_session(db, sid, user_id)
        memory_service.append_turn(db, sid, "user", "之前的问题")
        memory_service.add_longterm_item(db, user_id, "goal", "目标快手 AI", importance=0.9)

        bundle = memory_service.build_memory_bundle(db, sid, user_id, query="新问题")
        assert bundle.used_session_memory is True
        assert bundle.used_longterm_memory is True
        assert len(bundle.recent_turns) == 1


class TestRender:
    def test_render_empty(self):
        from app.schemas.memory import MemoryBundle
        bundle = MemoryBundle()
        assert memory_service.render_memory_for_prompt(bundle) == ""

    def test_render_includes_all_sections(self):
        from app.schemas.memory import MemoryBundle, SessionTurn, LongTermMemoryItem
        bundle = MemoryBundle(
            longterm_items=[
                LongTermMemoryItem(user_id=1, kind="goal", content="目标快手"),
            ],
            session_summary="之前讨论了简历优化。",
            recent_turns=[
                SessionTurn(turn_id=1, role="user", content="怎么补 RAG"),
            ],
        )
        rendered = memory_service.render_memory_for_prompt(bundle)
        assert "已知信息" in rendered
        assert "早期对话摘要" in rendered
        assert "最近对话" in rendered
        assert "目标快手" in rendered