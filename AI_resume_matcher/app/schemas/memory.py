"""
app/schemas/memory.py

Memory 子系统的结构化 schema。

设计目标：
1. 区分三种 memory 类型（working / session / longterm），每种有不同的生命周期。
2. 暴露出"用了多少 token / 命中了几条记忆 / 摘要了几轮"等可观测指标，便于评测。
3. 接口面向 Agent layer，DB ORM model 在 app/models/memory.py 单独写。
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


MemoryRole = Literal["user", "agent", "system"]
MemoryKind = Literal["fact", "preference", "goal", "event"]


class SessionTurn(BaseModel):
    """一轮 Agent 对话的最简记录。"""
    turn_id: int = Field(..., description="同一 session 内自增。")
    role: MemoryRole
    content: str = Field(..., description="user 的 query 或 agent 的 final_answer。")
    intent: Optional[str] = Field(default=None, description="本轮的 Agent intent。")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: Optional[float] = None
    token_estimate: Optional[int] = None


class SessionMemory(BaseModel):
    """单个 session 的完整对话上下文。"""
    session_id: str
    user_id: int
    turns: list[SessionTurn] = Field(default_factory=list)
    summary: Optional[str] = Field(
        default=None,
        description="超过窗口长度时，由 LLM 生成的早期对话摘要。",
    )
    summary_until_turn: int = Field(default=0, description="摘要覆盖到第几个 turn（含）。")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LongTermMemoryItem(BaseModel):
    """长期记忆中的单条事实条目。"""
    item_id: Optional[int] = None
    user_id: int
    kind: MemoryKind = Field(..., description="事实类型。")
    content: str = Field(..., description="自然语言描述。")
    keywords: list[str] = Field(default_factory=list, description="关键词，用于召回。")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    last_used_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_session_id: Optional[str] = Field(default=None)


class MemoryBundle(BaseModel):
    """Agent 启动时拉取的记忆包。"""
    session_id: Optional[str] = None
    recent_turns: list[SessionTurn] = Field(default_factory=list)
    session_summary: Optional[str] = None
    longterm_items: list[LongTermMemoryItem] = Field(default_factory=list)

    used_session_memory: bool = False
    used_longterm_memory: bool = False
    summary_compressed: bool = False
    total_tokens_estimate: int = 0