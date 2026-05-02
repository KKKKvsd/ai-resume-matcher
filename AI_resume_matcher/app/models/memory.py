"""
app/models/memory.py

记忆相关的 SQLAlchemy ORM 模型。
3 张表: agent_sessions, agent_session_turns, long_term_memory_items

【类型对齐说明】
本项目所有外键都用 BigInteger 风格(对照 match_result.py)。
主键 id 和所有 user_id / resume_id / job_id 必须是 BigInteger,
否则 MySQL 会因外键类型不一致拒绝建表(InnoDB 限制)。

非外键列(如 turn_id, summary_until_turn, token_estimate)仍可用普通 Integer。
"""

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AgentSession(Base):
    """一个完整的 Agent 会话(多轮对话的容器)。"""
    __tablename__ = "agent_sessions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # 关联简历 / 岗位(可选)
    resume_id = Column(BigInteger, ForeignKey("resumes.id"), nullable=True)
    job_id = Column(BigInteger, ForeignKey("job_descriptions.id"), nullable=True)

    summary = Column(Text, nullable=True)
    summary_until_turn = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    turns = relationship(
        "AgentSessionTurn",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AgentSessionTurn.turn_id",
    )


class AgentSessionTurn(Base):
    """一轮对话(user query 或 agent answer)。"""
    __tablename__ = "agent_session_turns"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(
        String(64),
        ForeignKey("agent_sessions.session_id"),
        nullable=False,
        index=True,
    )
    turn_id = Column(Integer, nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    token_estimate = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    session = relationship("AgentSession", back_populates="turns")

    __table_args__ = (
        # 同一 session 内 turn_id 唯一
        Index("idx_session_turn_unique", "session_id", "turn_id", unique=True),
    )


class LongTermMemoryItem(Base):
    """长期记忆条目(绑定到 user,跨 session)。"""
    __tablename__ = "long_term_memory_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    kind = Column(String(32), nullable=False, index=True)
    content = Column(Text, nullable=False)
    keywords = Column(Text, nullable=True)  # JSON-encoded list[str]

    importance = Column(Float, default=0.5, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    source_session_id = Column(String(64), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )