"""
app/services/memory_service.py

Agent 三层记忆的统一服务层。
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.models.memory import (
    AgentSession,
    AgentSessionTurn,
    LongTermMemoryItem as LongTermMemoryItemORM,
)
from app.schemas.memory import (
    LongTermMemoryItem,
    MemoryBundle,
    SessionTurn,
)


# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------
RECENT_WINDOW_SIZE = 6
SUMMARY_TRIGGER_TURNS = 12
SUMMARY_KEEP_TURNS = 4
LONGTERM_TOP_K = 5
TOKEN_PER_CHAR_ESTIMATE = 0.5


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return int(len(text) * TOKEN_PER_CHAR_ESTIMATE)


# ===========================================================================
# Session ID
# ===========================================================================
def generate_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:16]}"


# ===========================================================================
# Session memory: 写入
# ===========================================================================
def get_or_create_session(
    db: Session,
    session_id: str,
    user_id: int,
    resume_id: Optional[int] = None,
    job_id: Optional[int] = None,
) -> Optional[AgentSession]:
    try:
        session = db.query(AgentSession).filter(AgentSession.session_id == session_id).first()
        if session:
            return session

        session = AgentSession(
            session_id=session_id,
            user_id=user_id,
            resume_id=resume_id,
            job_id=job_id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    except SQLAlchemyError as exc:
        logger.warning(f"get_or_create_session failed: {repr(exc)}")
        db.rollback()
        return None


def append_turn(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    intent: Optional[str] = None,
    confidence: Optional[float] = None,
) -> Optional[AgentSessionTurn]:
    try:
        last_turn = (
            db.query(AgentSessionTurn)
            .filter(AgentSessionTurn.session_id == session_id)
            .order_by(AgentSessionTurn.turn_id.desc())
            .first()
        )
        next_turn_id = (last_turn.turn_id + 1) if last_turn else 1

        turn = AgentSessionTurn(
            session_id=session_id,
            turn_id=next_turn_id,
            role=role,
            content=content,
            intent=intent,
            confidence=confidence,
            token_estimate=_estimate_tokens(content),
        )
        db.add(turn)
        db.query(AgentSession).filter(
            AgentSession.session_id == session_id
        ).update({"updated_at": datetime.utcnow()})
        db.commit()
        db.refresh(turn)
        return turn
    except SQLAlchemyError as exc:
        logger.warning(f"append_turn failed: {repr(exc)}")
        db.rollback()
        return None


# ===========================================================================
# Session memory: 读取与窗口管理
# ===========================================================================
def fetch_recent_turns(
    db: Session,
    session_id: str,
    limit: int = RECENT_WINDOW_SIZE,
) -> list[SessionTurn]:
    try:
        rows = (
            db.query(AgentSessionTurn)
            .filter(AgentSessionTurn.session_id == session_id)
            .order_by(AgentSessionTurn.turn_id.desc())
            .limit(limit)
            .all()
        )
        rows = list(reversed(rows))
        return [
            SessionTurn(
                turn_id=r.turn_id,
                role=r.role,
                content=r.content,
                intent=r.intent,
                confidence=r.confidence,
                token_estimate=r.token_estimate,
                created_at=r.created_at,
            )
            for r in rows
        ]
    except SQLAlchemyError as exc:
        logger.warning(f"fetch_recent_turns failed: {repr(exc)}")
        return []


def maybe_compress_session(db: Session, session_id: str) -> bool:
    """超过阈值时，触发 LLM 摘要压缩。"""
    try:
        session = db.query(AgentSession).filter(AgentSession.session_id == session_id).first()
        if session is None:
            return False

        total = (
            db.query(AgentSessionTurn)
            .filter(AgentSessionTurn.session_id == session_id)
            .count()
        )
        if total <= SUMMARY_TRIGGER_TURNS:
            return False

        new_summary_until = total - SUMMARY_KEEP_TURNS
        if new_summary_until <= session.summary_until_turn:
            return False

        rows = (
            db.query(AgentSessionTurn)
            .filter(
                AgentSessionTurn.session_id == session_id,
                AgentSessionTurn.turn_id > session.summary_until_turn,
                AgentSessionTurn.turn_id <= new_summary_until,
            )
            .order_by(AgentSessionTurn.turn_id)
            .all()
        )

        if not rows:
            return False

        new_summary = _summarize_turns(
            previous_summary=session.summary,
            turns=rows,
        )
        if new_summary is None:
            return False

        session.summary = new_summary
        session.summary_until_turn = new_summary_until
        db.commit()
        logger.info(
            f"Session {session_id} compressed: summary now covers up to turn {new_summary_until}"
        )
        return True
    except SQLAlchemyError as exc:
        logger.warning(f"maybe_compress_session failed: {repr(exc)}")
        db.rollback()
        return False


def _summarize_turns(
    previous_summary: Optional[str],
    turns: list[AgentSessionTurn],
) -> Optional[str]:
    """LLM 失败时返回 None。"""
    try:
        from app.utils.llm_client import call_llm
    except ImportError:
        return None

    transcript = "\n".join(
        f"[turn {t.turn_id}][{t.role}] {t.content}" for t in turns
    )
    prev = previous_summary or "（暂无早期摘要）"

    prompt = f"""
你是一个对话摘要助手。请把下面的早期对话压缩成不超过 200 字的中文摘要。

要求：
1. 保留用户的核心问题、Agent 的关键结论、明确提到的简历或岗位信息。
2. 不要包含寒暄、确认语、重复内容。
3. 用客观语气，不要"用户问..."这种叙述视角，直接陈述事实。
4. 如果已有早期摘要，请把新内容整合进去，不要重复。

早期摘要：
{prev}

新增对话：
{transcript}

输出（仅摘要正文，无任何解释或前缀）：
""".strip()

    try:
        result = call_llm(prompt, temperature=0.2)
        return result.strip() if result else None
    except Exception as exc:
        logger.warning(f"_summarize_turns LLM call failed: {repr(exc)}")
        return None


# ===========================================================================
# Long-term memory
# ===========================================================================
def add_longterm_item(
    db: Session,
    user_id: int,
    kind: str,
    content: str,
    keywords: Optional[list[str]] = None,
    importance: float = 0.5,
    source_session_id: Optional[str] = None,
) -> Optional[LongTermMemoryItemORM]:
    try:
        existing = (
            db.query(LongTermMemoryItemORM)
            .filter(
                LongTermMemoryItemORM.user_id == user_id,
                LongTermMemoryItemORM.content == content,
            )
            .first()
        )
        if existing:
            existing.importance = max(existing.importance, importance)
            existing.last_used_at = datetime.utcnow()
            db.commit()
            return existing

        item = LongTermMemoryItemORM(
            user_id=user_id,
            kind=kind,
            content=content,
            keywords=json.dumps(keywords or [], ensure_ascii=False),
            importance=importance,
            source_session_id=source_session_id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    except SQLAlchemyError as exc:
        logger.warning(f"add_longterm_item failed: {repr(exc)}")
        db.rollback()
        return None


def search_longterm_items(
    db: Session,
    user_id: int,
    query: str = "",
    top_k: int = LONGTERM_TOP_K,
) -> list[LongTermMemoryItem]:
    """轻量字符串匹配 + importance 加权打分。"""
    try:
        all_items = (
            db.query(LongTermMemoryItemORM)
            .filter(LongTermMemoryItemORM.user_id == user_id)
            .all()
        )
        if not all_items:
            return []

        if not query.strip():
            ranked = sorted(
                all_items,
                key=lambda x: (x.importance, x.last_used_at or x.created_at),
                reverse=True,
            )[:top_k]
        else:
            query_lower = query.lower()
            scored = []
            for item in all_items:
                score = 0.0
                if query_lower in item.content.lower():
                    score += 1.0
                try:
                    kws = json.loads(item.keywords or "[]")
                except (json.JSONDecodeError, TypeError):
                    kws = []
                for kw in kws:
                    if kw and kw.lower() in query_lower:
                        score += 0.5
                final_score = score * (0.5 + item.importance)
                if final_score > 0:
                    scored.append((item, final_score))

            scored.sort(key=lambda x: x[1], reverse=True)
            ranked = [item for item, _ in scored[:top_k]]

        now = datetime.utcnow()
        for item in ranked:
            item.last_used_at = now
        db.commit()

        return [_orm_to_pydantic_longterm(item) for item in ranked]
    except SQLAlchemyError as exc:
        logger.warning(f"search_longterm_items failed: {repr(exc)}")
        db.rollback()
        return []


def _orm_to_pydantic_longterm(orm_item: LongTermMemoryItemORM) -> LongTermMemoryItem:
    try:
        kws = json.loads(orm_item.keywords or "[]")
    except (json.JSONDecodeError, TypeError):
        kws = []
    return LongTermMemoryItem(
        item_id=orm_item.id,
        user_id=orm_item.user_id,
        kind=orm_item.kind,
        content=orm_item.content,
        keywords=kws,
        importance=orm_item.importance,
        last_used_at=orm_item.last_used_at,
        created_at=orm_item.created_at,
        source_session_id=orm_item.source_session_id,
    )


# ===========================================================================
# Fact extraction
# ===========================================================================
def extract_facts_from_session(
    db: Session,
    session_id: str,
    user_id: int,
) -> int:
    try:
        from app.utils.llm_client import call_llm, clean_llm_json_text
    except ImportError:
        return 0

    recent = fetch_recent_turns(db, session_id, limit=4)
    if not recent:
        return 0

    transcript = "\n".join(
        f"[{t.role}] {t.content[:300]}" for t in recent
    )

    prompt = f"""
你是一个用户长期记忆提炼器。从下面的最近对话中识别出"值得长期记住"的事实。

只识别这四类：
- preference: 用户偏好（如"喜欢中文输出"、"偏好 bullet 格式"）
- goal: 用户目标（如"目标岗位是快手 AI 应用开发"）
- fact: 客观信息（如"用户简历中已包含 RAG 项目"）
- event: 重要事件（如"用户在 2025-12 更新了简历到 v3"）

要求：
1. 只输出真正"长期有用"的条目，寒暄、临时性问题不要。
2. 没有可提炼的也要返回空数组，不要硬凑。
3. importance 0-1 之间，越重要越接近 1。
4. 不要 markdown，只输出 JSON。

返回格式：
{{
  "items": [
    {{
      "kind": "goal",
      "content": "用户的目标岗位是快手 AI 应用开发实习",
      "keywords": ["快手", "AI 应用开发", "实习"],
      "importance": 0.9
    }}
  ]
}}

对话：
{transcript}
""".strip()

    try:
        raw = call_llm(prompt, temperature=0)
        cleaned = clean_llm_json_text(raw)
        data = json.loads(cleaned)
    except Exception as exc:
        logger.warning(f"extract_facts LLM/parse failed: {repr(exc)}")
        return 0

    items = data.get("items", []) or []
    added = 0
    for item in items:
        kind = item.get("kind", "").strip()
        content = (item.get("content") or "").strip()
        if kind not in {"preference", "goal", "fact", "event"}:
            continue
        if not content:
            continue
        try:
            importance = float(item.get("importance", 0.5))
            importance = max(0.0, min(1.0, importance))
        except (TypeError, ValueError):
            importance = 0.5

        result = add_longterm_item(
            db=db,
            user_id=user_id,
            kind=kind,
            content=content,
            keywords=item.get("keywords") or [],
            importance=importance,
            source_session_id=session_id,
        )
        if result:
            added += 1

    if added > 0:
        logger.info(f"Extracted {added} facts from session {session_id}")
    return added


# ===========================================================================
# 顶层 API：组装 MemoryBundle
# ===========================================================================
def build_memory_bundle(
    db: Session,
    session_id: Optional[str],
    user_id: Optional[int],
    query: str = "",
) -> MemoryBundle:
    bundle = MemoryBundle(session_id=session_id)

    if not session_id or not user_id:
        return bundle

    try:
        maybe_compress_session(db, session_id)
        session = db.query(AgentSession).filter(AgentSession.session_id == session_id).first()
        if session is not None:
            bundle.session_summary = session.summary
            if bundle.session_summary:
                bundle.summary_compressed = True

        recent = fetch_recent_turns(db, session_id, limit=RECENT_WINDOW_SIZE)
        bundle.recent_turns = recent
        if recent:
            bundle.used_session_memory = True
    except Exception as exc:
        logger.warning(f"build_memory_bundle session part failed: {repr(exc)}")

    try:
        lt_items = search_longterm_items(db, user_id, query=query, top_k=LONGTERM_TOP_K)
        bundle.longterm_items = lt_items
        if lt_items:
            bundle.used_longterm_memory = True
    except Exception as exc:
        logger.warning(f"build_memory_bundle longterm part failed: {repr(exc)}")

    estimate = 0
    if bundle.session_summary:
        estimate += _estimate_tokens(bundle.session_summary)
    for t in bundle.recent_turns:
        estimate += t.token_estimate or _estimate_tokens(t.content)
    for it in bundle.longterm_items:
        estimate += _estimate_tokens(it.content)
    bundle.total_tokens_estimate = estimate

    return bundle


def render_memory_for_prompt(bundle: MemoryBundle) -> str:
    parts: list[str] = []

    if bundle.longterm_items:
        items_text = "\n".join(
            f"- [{item.kind}] {item.content}" for item in bundle.longterm_items
        )
        parts.append(f"【关于该用户的已知信息】\n{items_text}")

    if bundle.session_summary:
        parts.append(f"【早期对话摘要】\n{bundle.session_summary}")

    if bundle.recent_turns:
        turns_text = "\n".join(
            f"[{t.role}] {t.content}" for t in bundle.recent_turns
        )
        parts.append(f"【最近对话】\n{turns_text}")

    return "\n\n".join(parts)