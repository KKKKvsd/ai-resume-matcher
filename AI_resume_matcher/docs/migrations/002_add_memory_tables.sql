-- 记忆系统数据库迁移
-- 应用方式: 在 Postgres / MySQL 上执行此脚本（或者用 Alembic 写迁移）

CREATE TABLE IF NOT EXISTS agent_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    resume_id INTEGER REFERENCES resumes(id),
    job_id INTEGER REFERENCES job_descriptions(id),
    summary TEXT,
    summary_until_turn INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_user ON agent_sessions(user_id);

CREATE TABLE IF NOT EXISTS agent_session_turns (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL REFERENCES agent_sessions(session_id),
    turn_id INTEGER NOT NULL,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    intent VARCHAR(64),
    confidence FLOAT,
    token_estimate INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_turn_unique
    ON agent_session_turns(session_id, turn_id);

CREATE TABLE IF NOT EXISTS long_term_memory_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    kind VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,
    importance FLOAT NOT NULL DEFAULT 0.5,
    last_used_at TIMESTAMP,
    source_session_id VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_longterm_user ON long_term_memory_items(user_id);
CREATE INDEX IF NOT EXISTS idx_longterm_kind ON long_term_memory_items(kind);