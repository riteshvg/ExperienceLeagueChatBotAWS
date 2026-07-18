"""
PostgreSQL-backed Google OAuth tables.

Tables created on first startup:
  exl_users      — one row per Google account (user_id = Google sub)
  exl_sessions   — active sessions with 30-day TTL
  exl_ratelimits — per-IP rate limiting for the auth endpoint
  conversations  — one row per chat conversation, keyed to exl_users.user_id
  messages       — full turn-by-turn transcript for a conversation
"""

import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

_ADMIN_EMAIL_ENV = "ADMIN_EMAIL"

# Single source of truth for new-user query allowances. Only takes effect for
# users created after a change (system_config 'default_daily_limit' /
# 'default_monthly_limit' are the live, admin-editable values — see
# backend/api/routes/admin.py's /settings/default-limit and
# /settings/default-monthly-limit endpoints); these constants are just the
# seed value for those system_config rows and the fallback if a read fails.
DEFAULT_DAILY_QUERY_LIMIT = 50
DEFAULT_MONTHLY_QUERY_LIMIT = 50

_TTL_DAYS = 30
_RATE_WINDOW_MINUTES = 1
_RATE_MAX_REQUESTS = 20  # per minute per IP


def _connect():
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        raise RuntimeError("psycopg2-binary is required for Google OAuth. Install it: pip install psycopg2-binary")

    url = os.getenv("DATABASE_URL", "")
    if not url or not url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError(
            "DATABASE_URL must be a PostgreSQL connection string for Google OAuth "
            "(e.g. postgresql://user:pass@host:port/dbname)"
        )
    conn = psycopg2.connect(dsn=url, cursor_factory=psycopg2.extras.RealDictCursor,
                            connect_timeout=10)
    conn.autocommit = False
    return conn


_COST_PER_MTK = {
    "haiku":  {"input": 0.80,  "output": 4.0},
    "sonnet": {"input": 3.0,   "output": 15.0},
}


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = _COST_PER_MTK.get(model.lower(), _COST_PER_MTK["sonnet"])
    return round(
        (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000, 8
    )


def init_tables() -> None:
    """Create tables if they don't exist. Called once at startup."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS exl_users (
                    user_id               TEXT PRIMARY KEY,
                    email                 TEXT NOT NULL UNIQUE,
                    name                  TEXT NOT NULL DEFAULT '',
                    picture               TEXT NOT NULL DEFAULT '',
                    first_seen            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_seen             TIMESTAMPTZ,
                    total_queries         INTEGER NOT NULL DEFAULT 0,
                    is_admin              BOOLEAN NOT NULL DEFAULT FALSE,
                    is_disabled           BOOLEAN NOT NULL DEFAULT FALSE,
                    daily_query_limit     INTEGER NOT NULL DEFAULT {DEFAULT_DAILY_QUERY_LIMIT},
                    daily_query_count     INTEGER NOT NULL DEFAULT 0,
                    daily_reset_at        TIMESTAMPTZ,
                    monthly_query_limit   INTEGER NOT NULL DEFAULT {DEFAULT_MONTHLY_QUERY_LIMIT},
                    monthly_queries_used  INTEGER NOT NULL DEFAULT 0,
                    quota_reset_date      DATE NOT NULL DEFAULT DATE_TRUNC('month', NOW())::DATE
                );

                CREATE TABLE IF NOT EXISTS exl_sessions (
                    session_token TEXT PRIMARY KEY,
                    user_id       TEXT NOT NULL,
                    email         TEXT NOT NULL,
                    name          TEXT NOT NULL DEFAULT '',
                    picture       TEXT NOT NULL DEFAULT '',
                    expires_at    TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS exl_ratelimits (
                    ip            TEXT NOT NULL,
                    window_start  TIMESTAMPTZ NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (ip, window_start)
                );

                CREATE TABLE IF NOT EXISTS exl_query_logs (
                    id            BIGSERIAL PRIMARY KEY,
                    message_id    TEXT NOT NULL DEFAULT '',
                    user_id       TEXT NOT NULL,
                    email         TEXT NOT NULL DEFAULT '',
                    query_text    TEXT NOT NULL,
                    llm_model     TEXT NOT NULL DEFAULT '',
                    input_tokens  INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost_usd      NUMERIC(10,6) NOT NULL DEFAULT 0,
                    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS exl_feedback (
                    id          BIGSERIAL PRIMARY KEY,
                    message_id  TEXT NOT NULL,
                    user_id     TEXT NOT NULL DEFAULT '',
                    email       TEXT NOT NULL DEFAULT '',
                    query_text  TEXT NOT NULL DEFAULT '',
                    rating      SMALLINT NOT NULL,
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS system_config (
                    key        TEXT PRIMARY KEY,
                    value      TEXT NOT NULL DEFAULT '',
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id          UUID PRIMARY KEY,
                    user_id     TEXT NOT NULL REFERENCES exl_users(user_id) ON DELETE CASCADE,
                    session_id  TEXT,
                    title       TEXT NOT NULL DEFAULT '',
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id              UUID PRIMARY KEY,
                    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content         TEXT NOT NULL,
                    citations       JSONB,
                    slug            TEXT,
                    is_published    BOOLEAN NOT NULL DEFAULT FALSE,
                    evidence        JSONB,
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS interview_questions (
                    question_id      TEXT NOT NULL,
                    version          INTEGER NOT NULL DEFAULT 1,
                    level            TEXT NOT NULL,
                    profile_id       TEXT NOT NULL,
                    topic            TEXT NOT NULL,
                    difficulty       SMALLINT NOT NULL,
                    prompt_text      TEXT NOT NULL,
                    expected_themes  JSONB NOT NULL,
                    retrieval_hint   TEXT NOT NULL,
                    question_type    TEXT NOT NULL DEFAULT 'standard',
                    grading_rubric   JSONB,
                    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    deprecated_at    TIMESTAMPTZ,
                    PRIMARY KEY (question_id, version)
                );

                CREATE TABLE IF NOT EXISTS interview_sessions (
                    session_id       UUID PRIMARY KEY,
                    user_id          TEXT NOT NULL DEFAULT '',
                    level            TEXT NOT NULL,
                    profile_id       TEXT NOT NULL,
                    current_index    INTEGER NOT NULL DEFAULT 0,
                    phase            TEXT NOT NULL DEFAULT 'questioning'
                                       CHECK (phase IN ('questioning', 'review', 'complete')),
                    awaiting_advance BOOLEAN NOT NULL DEFAULT FALSE,
                    evaluated        BOOLEAN NOT NULL DEFAULT FALSE,
                    evaluation_started_at TIMESTAMPTZ,
                    session_report   JSONB,
                    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS interview_answers (
                    session_id            UUID NOT NULL REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
                    question_id           TEXT NOT NULL,
                    question_version      INTEGER NOT NULL DEFAULT 1,
                    question_index        INTEGER NOT NULL,
                    answer                TEXT NOT NULL DEFAULT '',
                    score                 SMALLINT,
                    score_pct             SMALLINT,
                    strengths             JSONB,
                    gaps                  JSONB,
                    model_answer_outline  TEXT,
                    feedback              TEXT,
                    citations             JSONB,
                    is_followup           BOOLEAN NOT NULL DEFAULT FALSE,
                    parent_question_id    TEXT,
                    followup_prompt_text  TEXT,
                    is_voice_input        BOOLEAN NOT NULL DEFAULT FALSE,
                    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (session_id, question_id)
                );

                CREATE TABLE IF NOT EXISTS exl_transcription_ratelimits (
                    user_id       TEXT NOT NULL,
                    window_start  TIMESTAMPTZ NOT NULL,
                    request_count INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (user_id, window_start)
                );

                CREATE TABLE IF NOT EXISTS interview_feedback (
                    session_id            UUID PRIMARY KEY REFERENCES interview_sessions(session_id) ON DELETE CASCADE,
                    user_id               TEXT NOT NULL DEFAULT '',
                    status                TEXT NOT NULL DEFAULT 'submitted'
                                            CHECK (status IN ('submitted', 'dismissed')),
                    questions_match_level SMALLINT,
                    feedback_quality      SMALLINT,
                    suggestions           TEXT,
                    would_recommend       BOOLEAN,
                    submitted_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute(
                "ALTER TABLE interview_answers ADD COLUMN IF NOT EXISTS "
                "is_voice_input BOOLEAN NOT NULL DEFAULT FALSE"
            )
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_interview_questions_active "
                "ON interview_questions (question_id) WHERE deprecated_at IS NULL"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_interview_questions_level_profile "
                "ON interview_questions (level, profile_id) WHERE deprecated_at IS NULL"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_interview_sessions_user_id ON interview_sessions (user_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_interview_feedback_user_id ON interview_feedback (user_id)"
            )
            cur.execute(
                "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS evaluation_started_at TIMESTAMPTZ"
            )
            cur.execute(
                "ALTER TABLE interview_answers ADD COLUMN IF NOT EXISTS is_followup BOOLEAN NOT NULL DEFAULT FALSE"
            )
            cur.execute(
                "ALTER TABLE interview_answers ADD COLUMN IF NOT EXISTS parent_question_id TEXT"
            )
            cur.execute(
                "ALTER TABLE interview_answers ADD COLUMN IF NOT EXISTS followup_prompt_text TEXT"
            )
            cur.execute(
                "ALTER TABLE interview_questions ADD COLUMN IF NOT EXISTS "
                "question_type TEXT NOT NULL DEFAULT 'standard'"
            )
            cur.execute(
                "ALTER TABLE interview_questions ADD COLUMN IF NOT EXISTS grading_rubric JSONB"
            )
            # Safe migrations for existing deployments
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS is_disabled BOOLEAN NOT NULL DEFAULT FALSE"
            )
            cur.execute(
                f"ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS daily_query_limit "
                f"INTEGER NOT NULL DEFAULT {DEFAULT_DAILY_QUERY_LIMIT}"
            )
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS daily_query_count INTEGER NOT NULL DEFAULT 0"
            )
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS daily_reset_at TIMESTAMPTZ"
            )
            cur.execute(
                "INSERT INTO system_config (key, value) VALUES ('default_daily_limit', %s) ON CONFLICT (key) DO NOTHING",
                (str(DEFAULT_DAILY_QUERY_LIMIT),),
            )
            cur.execute(
                "ALTER TABLE exl_query_logs ADD COLUMN IF NOT EXISTS message_id TEXT NOT NULL DEFAULT ''"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_exl_query_logs_created_at ON exl_query_logs (created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_exl_query_logs_message_id ON exl_query_logs (message_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_exl_feedback_message_id ON exl_feedback (message_id)"
            )
            cur.execute(
                "ALTER TABLE exl_feedback ADD COLUMN IF NOT EXISTS comment TEXT"
            )
            # Seed kill switch default
            cur.execute(
                "INSERT INTO system_config (key, value) VALUES ('api_enabled', 'true') ON CONFLICT (key) DO NOTHING"
            )
            cur.execute(
                f"ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS monthly_query_limit "
                f"INTEGER NOT NULL DEFAULT {DEFAULT_MONTHLY_QUERY_LIMIT}"
            )
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS monthly_queries_used INTEGER NOT NULL DEFAULT 0"
            )
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS quota_reset_date DATE NOT NULL DEFAULT DATE_TRUNC('month', NOW())::DATE"
            )
            cur.execute(
                "INSERT INTO system_config (key, value) VALUES ('default_monthly_limit', %s) ON CONFLICT (key) DO NOTHING",
                (str(DEFAULT_MONTHLY_QUERY_LIMIT),),
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_created ON conversations (user_id, created_at DESC)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages (conversation_id, created_at ASC)"
            )
            # session_id is a free-form client-generated id (not guaranteed to be a
            # UUID) kept only for analytics correlation — TEXT, not UUID.
            cur.execute(
                "ALTER TABLE conversations ALTER COLUMN session_id TYPE TEXT"
            )
            cur.execute(
                "ALTER TABLE messages ADD COLUMN IF NOT EXISTS slug TEXT"
            )
            cur.execute(
                "ALTER TABLE messages ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT FALSE"
            )
            cur.execute(
                "ALTER TABLE messages ADD COLUMN IF NOT EXISTS evidence JSONB"
            )
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_slug ON messages (slug) WHERE slug IS NOT NULL"
            )
        conn.commit()
    finally:
        conn.close()


def upsert_user(user_id: str, email: str, name: str, picture: str) -> dict:
    """Insert or update an OAuth user. Updates last_seen on every login.

    Email is the account identity in Rovr. If the same person signs in with a
    second OAuth provider, keep the original row so quotas/admin flags/history
    remain attached to one account.
    """
    admin_email = os.getenv(_ADMIN_EMAIL_ENV, "").strip().lower()
    is_admin_value = email.strip().lower() == admin_email if admin_email else False

    # Read default limits for new users
    default_limit = DEFAULT_DAILY_QUERY_LIMIT
    try:
        raw = get_system_config("default_daily_limit")
        if raw and raw.isdigit():
            default_limit = int(raw)
    except Exception:
        pass

    default_monthly_limit = DEFAULT_MONTHLY_QUERY_LIMIT
    try:
        raw_monthly = get_system_config("default_monthly_limit")
        if raw_monthly and raw_monthly.isdigit():
            default_monthly_limit = int(raw_monthly)
    except Exception:
        pass

    conn = _connect()
    try:
        with conn.cursor() as cur:
            if is_admin_value:
                # Ensure the admin email always has is_admin=true
                cur.execute(
                    """
                    INSERT INTO exl_users (user_id, email, name, picture, first_seen, last_seen, is_admin, daily_query_limit, monthly_query_limit)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), TRUE, %s, %s)
                    ON CONFLICT (email) DO UPDATE
                        SET name      = EXCLUDED.name,
                            picture   = EXCLUDED.picture,
                            last_seen = NOW(),
                            is_admin  = TRUE
                    RETURNING *
                    """,
                    (user_id, email, name, picture, default_limit, default_monthly_limit),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO exl_users (user_id, email, name, picture, first_seen, last_seen, daily_query_limit, monthly_query_limit)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), %s, %s)
                    ON CONFLICT (email) DO UPDATE
                        SET name      = EXCLUDED.name,
                            picture   = EXCLUDED.picture,
                            last_seen = NOW()
                    RETURNING *
                    """,
                    (user_id, email, name, picture, default_limit, default_monthly_limit),
                )
            row = cur.fetchone()
        conn.commit()
        return dict(row)
    finally:
        conn.close()


def create_session(user_id: str, email: str, name: str, picture: str) -> tuple[str, int]:
    """Create a session. Returns (session_token, expires_at_unix_timestamp)."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(days=_TTL_DAYS)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exl_sessions (session_token, user_id, email, name, picture, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (token, user_id, email, name, picture, expires_at),
            )
        conn.commit()
    finally:
        conn.close()
    return token, int(expires_at.timestamp())


def get_session(session_token: str) -> Optional[dict]:
    """Return session + user flags if the token exists and hasn't expired."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.session_token, s.user_id, s.email, s.name, s.picture, s.expires_at,
                       COALESCE(u.is_admin, FALSE) AS is_admin,
                       COALESCE(u.is_disabled, FALSE) AS is_disabled
                FROM exl_sessions s
                LEFT JOIN exl_users u ON u.user_id = s.user_id
                WHERE s.session_token = %s AND s.expires_at > NOW()
                """,
                (session_token,),
            )
            row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_session(session_token: str) -> None:
    """Invalidate a session (logout)."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM exl_sessions WHERE session_token = %s", (session_token,))
        conn.commit()
    finally:
        conn.close()


def touch_last_seen(user_id: str) -> None:
    """Update last_seen to now."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE exl_users SET last_seen = NOW() WHERE user_id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()


def increment_total_queries(user_id: str) -> None:
    """Increment the total_queries counter for a user."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE exl_users SET total_queries = total_queries + 1 WHERE user_id = %s",
                (user_id,),
            )
        conn.commit()
    finally:
        conn.close()


def list_users() -> list[dict]:
    """Return all users ordered by last_seen desc."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM exl_users ORDER BY last_seen DESC NULLS LAST")
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


_USER_SORT_ALLOWLIST = {"last_seen", "first_seen", "total_queries", "name", "email"}


def _user_search_clause(search: str) -> tuple[str, list]:
    """Build WHERE clause and params for name/email search."""
    term = (search or "").strip().lower()
    if not term:
        return "", []
    pattern = f"%{term}%"
    return "WHERE (LOWER(name) LIKE %s OR LOWER(email) LIKE %s)", [pattern, pattern]


def list_users_paginated(
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "last_seen",
    sort_order: str = "desc",
    search: str = "",
) -> dict:
    """Return paginated users with total count metadata."""
    if sort_by not in _USER_SORT_ALLOWLIST:
        sort_by = "last_seen"
    direction = "ASC" if sort_order.lower() == "asc" else "DESC"
    offset = (page - 1) * page_size
    where, params = _user_search_clause(search)

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM exl_users {where}", params or None)
            total = cur.fetchone()["count"]
            cur.execute(
                f"""
                SELECT * FROM exl_users
                {where}
                ORDER BY {sort_by} {direction} NULLS LAST
                LIMIT %s OFFSET %s
                """,
                (*params, page_size, offset) if params else (page_size, offset),
            )
            rows = cur.fetchall()
        total_pages = max(1, -(-total // page_size))
        return {
            "data": [dict(r) for r in rows],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
    finally:
        conn.close()


def export_all_users(search: str = "") -> list[dict]:
    """Return all users for Excel export, optionally filtered by name/email search."""
    where, params = _user_search_clause(search)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT user_id, email, name, first_seen, last_seen, total_queries,
                       is_admin, is_disabled, daily_query_limit, daily_query_count,
                       daily_reset_at, monthly_query_limit, monthly_queries_used,
                       quota_reset_date
                FROM exl_users
                {where}
                ORDER BY last_seen DESC NULLS LAST
                """,
                params or None,
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for key in ("first_seen", "last_seen", "daily_reset_at", "quota_reset_date"):
                if hasattr(d.get(key), "isoformat"):
                    d[key] = d[key].isoformat()
            result.append(d)
        return result
    finally:
        conn.close()


def set_admin(user_id: str, is_admin: bool) -> Optional[dict]:
    """Set is_admin flag on a user. Returns updated row or None if not found."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE exl_users SET is_admin = %s WHERE user_id = %s RETURNING *",
                (is_admin, user_id),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    finally:
        conn.close()


def get_summary() -> dict:
    """Return aggregate stats: total users, total queries all time."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS total_users, COALESCE(SUM(total_queries), 0) AS total_queries_all_time "
                "FROM exl_users"
            )
            row = dict(cur.fetchone())
        return {
            "total_users": int(row["total_users"]),
            "total_queries_all_time": int(row["total_queries_all_time"]),
        }
    finally:
        conn.close()


def set_disabled(user_id: str, is_disabled: bool) -> Optional[dict]:
    """Set is_disabled flag on a user. Returns updated row or None if not found."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE exl_users SET is_disabled = %s WHERE user_id = %s RETURNING *",
                (is_disabled, user_id),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    finally:
        conn.close()


def check_rate_limit(user_id: str) -> dict:
    """Check if user is within their daily query limit.

    Resets the counter if a new UTC day has started.
    Does NOT increment the counter.
    Returns {"allowed": bool, "count": int, "limit": int}.
    """
    today = datetime.now(tz=timezone.utc).date()
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT daily_query_count, daily_query_limit, daily_reset_at FROM exl_users WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return {"allowed": True, "count": 0, "limit": DEFAULT_DAILY_QUERY_LIMIT}

            count = row["daily_query_count"]
            limit = row["daily_query_limit"]
            reset_at = row["daily_reset_at"]

            # Reset if this is a new UTC day or never been reset
            needs_reset = (reset_at is None) or (reset_at.date() < today)
            if needs_reset:
                cur.execute(
                    "UPDATE exl_users SET daily_query_count = 0, daily_reset_at = NOW() WHERE user_id = %s",
                    (user_id,),
                )
                conn.commit()
                count = 0

            if count >= limit:
                return {"allowed": False, "count": count, "limit": limit}
            return {"allowed": True, "count": count, "limit": limit}
    finally:
        conn.close()


def increment_daily_count(user_id: str) -> dict:
    """Increment the daily_query_count for a user.
    Returns {"count": int, "limit": int}.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE exl_users SET daily_query_count = daily_query_count + 1 WHERE user_id = %s "
                "RETURNING daily_query_count, daily_query_limit",
                (user_id,),
            )
            row = cur.fetchone()
        conn.commit()
        if row is None:
            return {"count": 0, "limit": DEFAULT_DAILY_QUERY_LIMIT}
        return {"count": row["daily_query_count"], "limit": row["daily_query_limit"]}
    finally:
        conn.close()


def get_usage_info(user_id: str) -> dict:
    """Return current daily usage info for a user (read-only, applies reset logic).
    Returns {"queries_used": int, "queries_limit": int, "queries_remaining": int}.
    """
    today = datetime.now(tz=timezone.utc).date()
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT daily_query_count, daily_query_limit, daily_reset_at FROM exl_users WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
        if row is None:
            return {"queries_used": 0, "queries_limit": 20, "queries_remaining": 20}

        count = row["daily_query_count"]
        limit = row["daily_query_limit"]
        reset_at = row["daily_reset_at"]

        # If new UTC day, report 0 used (without writing)
        if (reset_at is None) or (reset_at.date() < today):
            count = 0

        remaining = max(0, limit - count)
        return {"queries_used": count, "queries_limit": limit, "queries_remaining": remaining}
    finally:
        conn.close()


def set_user_daily_limit(user_id: str, limit: int) -> Optional[dict]:
    """Set the daily_query_limit for a specific user. Returns updated row or None."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE exl_users SET daily_query_limit = %s WHERE user_id = %s RETURNING *",
                (limit, user_id),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    finally:
        conn.close()


def apply_default_limit_to_all() -> int:
    """Apply the default_daily_limit from system_config to all users. Returns rows updated."""
    default_limit = DEFAULT_DAILY_QUERY_LIMIT
    try:
        raw = get_system_config("default_daily_limit")
        if raw and raw.isdigit():
            default_limit = int(raw)
    except Exception:
        pass

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE exl_users SET daily_query_limit = %s", (default_limit,))
            count = cur.rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def apply_default_monthly_limit_to_all() -> int:
    """Apply the default_monthly_limit from system_config to all users. Returns rows updated."""
    default_limit = DEFAULT_MONTHLY_QUERY_LIMIT
    try:
        raw = get_system_config("default_monthly_limit")
        if raw and raw.isdigit():
            default_limit = int(raw)
    except Exception:
        pass

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE exl_users SET monthly_query_limit = %s", (default_limit,))
            count = cur.rowcount
        conn.commit()
        return count
    finally:
        conn.close()


def get_rate_limit_analytics() -> dict:
    """Return analytics about daily query usage across all users."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_users,
                    COUNT(*) FILTER (WHERE daily_query_count > 0) AS active_users_today,
                    COALESCE(SUM(daily_query_count), 0) AS queries_today,
                    COUNT(*) FILTER (WHERE daily_query_count >= daily_query_limit) AS users_at_limit,
                    COUNT(*) FILTER (WHERE daily_query_count >= daily_query_limit * 0.75
                                     AND daily_query_count < daily_query_limit) AS users_above_75pct,
                    COALESCE(AVG(daily_query_count) FILTER (WHERE daily_query_count > 0), 0) AS avg_queries_active
                FROM exl_users
                """
            )
            row = dict(cur.fetchone())

            cur.execute(
                "SELECT email, daily_query_count FROM exl_users ORDER BY daily_query_count DESC LIMIT 1"
            )
            top = cur.fetchone()

        return {
            "total_users": int(row["total_users"]),
            "active_users_today": int(row["active_users_today"]),
            "queries_today": int(row["queries_today"]),
            "users_at_limit": int(row["users_at_limit"]),
            "users_above_75pct": int(row["users_above_75pct"]),
            "avg_queries_active_users": float(row["avg_queries_active"]),
            "highest_usage_email": top["email"] if top else None,
            "highest_usage_count": int(top["daily_query_count"]) if top else 0,
        }
    finally:
        conn.close()


def log_query(
    user_id: str,
    email: str,
    query_text: str,
    llm_model: str,
    input_tokens: int,
    output_tokens: int,
    message_id: str = "",
) -> None:
    """Append a query log row."""
    cost = _compute_cost(llm_model, input_tokens, output_tokens)
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exl_query_logs (message_id, user_id, email, query_text, llm_model, input_tokens, output_tokens, cost_usd)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (message_id, user_id, email, query_text, llm_model, input_tokens, output_tokens, cost),
            )
        conn.commit()
    finally:
        conn.close()


_QUERY_SORT_ALLOWLIST = {"created_at", "email", "llm_model", "input_tokens", "output_tokens", "cost_usd"}


def _rows_to_query_log_dicts(rows) -> list[dict]:
    result = []
    for r in rows:
        d = dict(r)
        if hasattr(d.get("created_at"), "isoformat"):
            d["created_at"] = d["created_at"].isoformat()
        if d.get("cost_usd") is not None:
            d["cost_usd"] = float(d["cost_usd"])
        if d.get("feedback_rating") is not None:
            d["feedback_rating"] = int(d["feedback_rating"])
        result.append(d)
    return result


def get_popular_query_logs(limit: int = 200) -> list[dict]:
    """Return deduplicated user queries ranked by frequency and recency."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH normalized AS (
                    SELECT
                        TRIM(query_text) AS query_text,
                        LOWER(TRIM(query_text)) AS norm,
                        created_at,
                        llm_model
                    FROM exl_query_logs
                    WHERE llm_model NOT LIKE 'blocked%%'
                      -- Mirrors MIN/MAX_QUERY_LENGTH in backend/core/landing_questions.py
                      AND LENGTH(TRIM(query_text)) BETWEEN 15 AND 100
                ),
                counts AS (
                    SELECT norm, COUNT(*) AS times_asked, MAX(created_at) AS last_asked
                    FROM normalized
                    GROUP BY norm
                ),
                latest AS (
                    SELECT DISTINCT ON (norm)
                        query_text,
                        norm,
                        created_at
                    FROM normalized
                    ORDER BY norm, created_at DESC
                )
                SELECT l.query_text, c.times_asked, c.last_asked
                FROM latest l
                JOIN counts c ON c.norm = l.norm
                ORDER BY c.times_asked DESC, c.last_asked DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if hasattr(d.get("last_asked"), "isoformat"):
                d["last_asked"] = d["last_asked"].isoformat()
            result.append(d)
        return result
    finally:
        conn.close()


def list_query_logs(limit: int = 100) -> list[dict]:
    """Return recent query logs with feedback rating joined from exl_feedback."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT q.id, q.message_id, q.user_id, q.email, q.query_text,
                       q.llm_model, q.input_tokens, q.output_tokens, q.cost_usd, q.created_at,
                       f.rating AS feedback_rating, f.comment AS feedback_comment
                FROM exl_query_logs q
                LEFT JOIN exl_feedback f ON f.message_id = q.message_id AND q.message_id <> ''
                ORDER BY q.created_at DESC LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return _rows_to_query_log_dicts(rows)
    finally:
        conn.close()


def _attach_seo_slugs(conn, rows: list[dict]) -> None:
    """Mutate rows in place, adding `seo_slug` for any query that got a published landing page.

    exl_query_logs.message_id is a client-generated id and isn't the messages.id
    the slug lives on, so the only reliable link back is the deterministic
    make_slug() hash of the question text itself.
    """
    slug_by_query_text = {r["query_text"]: make_slug(r["query_text"]) for r in rows if r.get("query_text")}
    if not slug_by_query_text:
        return
    candidate_slugs = list(set(slug_by_query_text.values()))
    with conn.cursor() as cur:
        cur.execute(
            "SELECT slug FROM messages WHERE slug = ANY(%s) AND is_published = TRUE",
            (candidate_slugs,),
        )
        published = {r["slug"] for r in cur.fetchall()}
    for r in rows:
        slug = slug_by_query_text.get(r.get("query_text"))
        r["seo_slug"] = slug if slug in published else None


def list_query_logs_paginated(
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """Return paginated query logs with total count metadata."""
    if sort_by not in _QUERY_SORT_ALLOWLIST:
        sort_by = "created_at"
    direction = "ASC" if sort_order.lower() == "asc" else "DESC"
    offset = (page - 1) * page_size

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM exl_query_logs")
            total = cur.fetchone()["count"]
            cur.execute(
                f"""
                SELECT q.id, q.message_id, q.user_id, q.email, q.query_text,
                       q.llm_model, q.input_tokens, q.output_tokens, q.cost_usd, q.created_at,
                       f.rating AS feedback_rating, f.comment AS feedback_comment
                FROM exl_query_logs q
                LEFT JOIN exl_feedback f ON f.message_id = q.message_id AND q.message_id <> ''
                ORDER BY q.{sort_by} {direction}
                LIMIT %s OFFSET %s
                """,
                (page_size, offset),
            )
            rows = cur.fetchall()
        data = _rows_to_query_log_dicts(rows)
        _attach_seo_slugs(conn, data)
        total_pages = max(1, -(-total // page_size))  # ceiling division
        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }
    finally:
        conn.close()


def export_all_query_logs(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict]:
    """Return all query logs for Excel export, optionally filtered by date range."""
    conditions: list[str] = []
    params: list = []
    if date_from:
        conditions.append("q.created_at >= %s")
        params.append(date_from)
    if date_to:
        conditions.append("q.created_at <= %s")
        params.append(date_to)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    conn = _connect()
    try:
        with conn.cursor() as cur:
            query = f"""
                SELECT q.email, q.query_text, q.llm_model,
                       q.input_tokens, q.output_tokens, q.cost_usd, q.created_at,
                       f.rating AS feedback_rating, f.comment AS feedback_comment
                FROM exl_query_logs q
                LEFT JOIN exl_feedback f ON f.message_id = q.message_id AND q.message_id <> ''
                {where}
                ORDER BY q.created_at DESC
            """
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if hasattr(d.get("created_at"), "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            if d.get("cost_usd") is not None:
                d["cost_usd"] = float(d["cost_usd"])
            result.append(d)
        return result
    finally:
        conn.close()


def log_feedback(message_id: str, user_id: str, email: str, query_text: str, rating: int, comment: str = "") -> None:
    """Insert or replace a feedback row for a given message_id."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exl_feedback (message_id, user_id, email, query_text, rating, comment)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (message_id, user_id, email, query_text, rating, comment or ""),
            )
        conn.commit()
    finally:
        conn.close()


def list_feedback(limit: int = 100) -> list[dict]:
    """Return recent feedback rows ordered by created_at desc."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, message_id, user_id, email, query_text, rating, comment, created_at "
                "FROM exl_feedback ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if hasattr(d.get("created_at"), "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            if d.get("rating") is not None:
                d["rating"] = int(d["rating"])
            result.append(d)
        return result
    finally:
        conn.close()


def save_interview_feedback(
    session_id: str,
    user_id: str,
    status: str = "submitted",
    questions_match_level: Optional[int] = None,
    feedback_quality: Optional[int] = None,
    suggestions: Optional[str] = None,
    would_recommend: Optional[bool] = None,
) -> None:
    """Upsert the one feedback row for a session — one row per session_id,
    covering both an actual submission (status='submitted') and a dismiss
    with no ratings (status='dismissed'). Re-submitting overwrites the prior
    row and refreshes submitted_at."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO interview_feedback
                    (session_id, user_id, status, questions_match_level,
                     feedback_quality, suggestions, would_recommend, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (session_id) DO UPDATE SET
                    status                 = EXCLUDED.status,
                    questions_match_level  = EXCLUDED.questions_match_level,
                    feedback_quality       = EXCLUDED.feedback_quality,
                    suggestions            = EXCLUDED.suggestions,
                    would_recommend        = EXCLUDED.would_recommend,
                    submitted_at           = NOW()
                """,
                (session_id, user_id, status, questions_match_level,
                 feedback_quality, suggestions, would_recommend),
            )
        conn.commit()
    finally:
        conn.close()


def get_interview_feedback(session_id: str) -> Optional[dict]:
    """Return the feedback row for a session, or None if not yet seen."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT session_id, user_id, status, questions_match_level, feedback_quality, "
                "suggestions, would_recommend, submitted_at "
                "FROM interview_feedback WHERE session_id = %s",
                (session_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        if hasattr(d.get("submitted_at"), "isoformat"):
            d["submitted_at"] = d["submitted_at"].isoformat()
        return d
    finally:
        conn.close()


def list_interview_feedback(limit: int = 200) -> list[dict]:
    """Return recent interview feedback rows (submitted and dismissed) for
    manual review — e.g. `python -c "from backend.core.google_db import
    list_interview_feedback as f; import json; print(json.dumps(f(), indent=2))"`."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT session_id, user_id, status, questions_match_level, feedback_quality, "
                "suggestions, would_recommend, submitted_at "
                "FROM interview_feedback ORDER BY submitted_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if hasattr(d.get("submitted_at"), "isoformat"):
                d["submitted_at"] = d["submitted_at"].isoformat()
            result.append(d)
        return result
    finally:
        conn.close()


def get_system_config(key: str) -> Optional[str]:
    """Read a value from system_config table."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = %s", (key,))
            row = cur.fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_system_config(key: str, value: str) -> None:
    """Upsert a value in system_config table."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_config (key, value, updated_at) VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()


def check_monthly_quota(user_id: str) -> dict:
    """Check if user is within their monthly query quota.

    Resets counter if quota_reset_date is before the first of the current month.
    Does NOT increment the counter.
    Returns {"allowed": bool, "used": int, "limit": int, "reset_date": date}.
    """
    from datetime import date as _date
    today = datetime.now(tz=timezone.utc).date()
    first_of_this_month = today.replace(day=1)
    yr, mo = today.year, today.month
    first_of_next_month = _date(yr + 1, 1, 1) if mo == 12 else _date(yr, mo + 1, 1)

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT monthly_queries_used, monthly_query_limit, quota_reset_date FROM exl_users WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return {"allowed": True, "used": 0, "limit": 999999, "reset_date": first_of_next_month}

            used = row["monthly_queries_used"]
            limit = row["monthly_query_limit"]
            reset_date = row["quota_reset_date"]

            # Reset if the stored reset date is before the first of this month
            needs_reset = (reset_date is None) or (reset_date < first_of_this_month)
            if needs_reset:
                cur.execute(
                    "UPDATE exl_users SET monthly_queries_used = 0, quota_reset_date = %s WHERE user_id = %s",
                    (first_of_this_month, user_id),
                )
                conn.commit()
                used = 0

            if used >= limit:
                return {"allowed": False, "used": used, "limit": limit, "reset_date": first_of_next_month}
            return {"allowed": True, "used": used, "limit": limit, "reset_date": first_of_next_month}
    finally:
        conn.close()


def increment_monthly_count(user_id: str) -> dict:
    """Increment monthly_queries_used for a user.
    Returns {"used": int, "limit": int}.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE exl_users SET monthly_queries_used = monthly_queries_used + 1 WHERE user_id = %s "
                "RETURNING monthly_queries_used, monthly_query_limit",
                (user_id,),
            )
            row = cur.fetchone()
        conn.commit()
        if row is None:
            return {"used": 0, "limit": 999999}
        return {"used": row["monthly_queries_used"], "limit": row["monthly_query_limit"]}
    finally:
        conn.close()


def get_monthly_quota_info(user_id: str) -> dict:
    """Return full monthly quota state for the /api/auth/quota endpoint.
    Returns {"monthly_limit", "monthly_used", "monthly_remaining", "reset_date", "is_new_user"}.
    """
    from datetime import date as _date
    today = datetime.now(tz=timezone.utc).date()
    first_of_this_month = today.replace(day=1)
    yr, mo = today.year, today.month
    first_of_next_month = _date(yr + 1, 1, 1) if mo == 12 else _date(yr, mo + 1, 1)

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT monthly_queries_used, monthly_query_limit, quota_reset_date, first_seen FROM exl_users WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
        if row is None:
            return {
                "monthly_limit": 999999,
                "monthly_used": 0,
                "monthly_remaining": 999999,
                "reset_date": first_of_next_month.isoformat(),
                "is_new_user": True,
            }

        used = row["monthly_queries_used"]
        limit = row["monthly_query_limit"]
        reset_date = row["quota_reset_date"]
        first_seen = row["first_seen"]

        # Read-only reset logic (don't write here — check_monthly_quota writes on actual requests)
        if (reset_date is None) or (reset_date < first_of_this_month):
            used = 0

        is_new_user = False
        if first_seen:
            seen_date = first_seen.date() if hasattr(first_seen, "date") else first_seen
            is_new_user = seen_date >= first_of_this_month

        remaining = max(0, limit - used)
        return {
            "monthly_limit": limit,
            "monthly_used": used,
            "monthly_remaining": remaining,
            "reset_date": first_of_next_month.isoformat(),
            "is_new_user": is_new_user,
        }
    finally:
        conn.close()


def set_user_monthly_limit(user_id: str, limit: int) -> Optional[dict]:
    """Set the monthly_query_limit for a specific user. Returns updated row or None."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE exl_users SET monthly_query_limit = %s WHERE user_id = %s RETURNING *",
                (limit, user_id),
            )
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    finally:
        conn.close()


def check_and_update_ratelimit(ip: str) -> bool:
    """Return True if request is allowed, False if rate-limited (20 req/min per IP)."""
    now = datetime.now(tz=timezone.utc)
    # Truncate to the current minute as the window key
    window_start = now.replace(second=0, microsecond=0)

    conn = _connect()
    try:
        with conn.cursor() as cur:
            # Purge stale windows (older than 2 minutes)
            cur.execute(
                "DELETE FROM exl_ratelimits WHERE window_start < NOW() - INTERVAL '2 minutes'"
            )
            cur.execute(
                "SELECT request_count FROM exl_ratelimits WHERE ip = %s AND window_start = %s",
                (ip, window_start),
            )
            row = cur.fetchone()

            if row is None:
                cur.execute(
                    "INSERT INTO exl_ratelimits (ip, window_start, request_count) VALUES (%s, %s, 1)",
                    (ip, window_start),
                )
                conn.commit()
                return True

            count = row["request_count"]
            if count >= _RATE_MAX_REQUESTS:
                conn.commit()
                return False

            cur.execute(
                "UPDATE exl_ratelimits SET request_count = request_count + 1 "
                "WHERE ip = %s AND window_start = %s",
                (ip, window_start),
            )
        conn.commit()
        return True
    finally:
        conn.close()


# ── Conversation history (persistent, keyed to the authenticated user) ────────
#
# This is a pure storage layer: creating/appending rows here never calls the
# RAG pipeline, embeddings, or the LLM. session_id is carried along only for
# analytics correlation with exl_query_logs — history lookups always go
# through conversation_id + user_id, never session_id.

_TITLE_MAX_LEN = 60


def create_conversation(user_id: str, session_id: Optional[str], title: str) -> str:
    """Create a new conversation row. Returns the new conversation id."""
    conversation_id = str(uuid.uuid4())
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (id, user_id, session_id, title)
                VALUES (%s, %s, %s, %s)
                """,
                (conversation_id, user_id, session_id, title.strip()[:_TITLE_MAX_LEN]),
            )
        conn.commit()
    finally:
        conn.close()
    return conversation_id


def conversation_belongs_to_user(conversation_id: str, user_id: str) -> bool:
    """True if conversation_id exists and is owned by user_id. False on any mismatch or bad id."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT 1 FROM conversations WHERE id = %s AND user_id = %s",
                    (conversation_id, user_id),
                )
            except Exception:
                return False
            return cur.fetchone() is not None
    finally:
        conn.close()


def append_conversation_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: Optional[list] = None,
    slug: Optional[str] = None,
    is_published: bool = False,
    evidence: Optional[dict] = None,
) -> None:
    """Append one message row (user or assistant turn) to a conversation.

    make_slug() hashes the question text, so a repeated (popular) question produces
    the same slug every time — by design, only one published FAQ page per unique
    question. idx_messages_slug enforces that with a partial unique index. If this
    exact question was already published, retry without claiming the slug rather
    than losing the message (and the whole turn's conversation persistence) to a
    duplicate-key error.
    """
    from psycopg2.errors import UniqueViolation
    from psycopg2.extras import Json

    conn = _connect()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, citations, slug, is_published, evidence)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()), conversation_id, role, content,
                        Json(citations) if citations is not None else None,
                        slug, is_published,
                        Json(evidence) if evidence is not None else None,
                    ),
                )
            except UniqueViolation:
                if slug is None:
                    raise
                conn.rollback()
                with conn.cursor() as retry_cur:
                    retry_cur.execute(
                        """
                        INSERT INTO messages (id, conversation_id, role, content, citations, slug, is_published, evidence)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()), conversation_id, role, content,
                            Json(citations) if citations is not None else None,
                            None, False,
                            Json(evidence) if evidence is not None else None,
                        ),
                    )
        conn.commit()
    finally:
        conn.close()


def make_slug(text: str) -> str:
    """URL-safe, human-legible slug for a query, deduplicated via a content hash suffix."""
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].rstrip("-")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:6]
    return f"{base}-{digest}" if base else digest


def list_published_slugs() -> list[dict]:
    """Return every published landing-page slug with its last-updated timestamp, for sitemap generation."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT slug, created_at FROM messages
                WHERE is_published = TRUE AND slug IS NOT NULL AND role = 'assistant'
                ORDER BY created_at DESC
                """
            )
            rows = cur.fetchall()
        return [
            {
                "slug": r["slug"],
                "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else r["created_at"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_landing_by_slug(slug: str) -> Optional[dict]:
    """Return a published query+answer pair for a public SEO landing page, or None."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT conversation_id, content AS answer, citations, evidence, created_at
                FROM messages
                WHERE slug = %s AND is_published = TRUE AND role = 'assistant'
                """,
                (slug,),
            )
            row = cur.fetchone()
            if not row:
                return None
            cur.execute(
                """
                SELECT content FROM messages
                WHERE conversation_id = %s AND role = 'user' AND created_at <= %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (row["conversation_id"], row["created_at"]),
            )
            q = cur.fetchone()
        created_at = row["created_at"]
        return {
            "slug": slug,
            "query": q["content"] if q else "",
            "answer": row["answer"],
            "citations": row["citations"] or [],
            "evidence": row["evidence"],
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
        }
    finally:
        conn.close()


def list_conversations(user_id: str) -> list[dict]:
    """Return id/title/created_at only for a user's conversations, most recent first."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at FROM conversations WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["id"] = str(d["id"])
            if hasattr(d.get("created_at"), "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            result.append(d)
        return result
    finally:
        conn.close()


def get_conversation_messages(conversation_id: str, user_id: str) -> Optional[list[dict]]:
    """Return ordered messages for a conversation, or None if it doesn't exist or
    isn't owned by user_id — callers must treat None as "not found", never leak
    which case it was.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "SELECT 1 FROM conversations WHERE id = %s AND user_id = %s",
                    (conversation_id, user_id),
                )
            except Exception:
                return None
            if cur.fetchone() is None:
                return None
            cur.execute(
                """
                SELECT id, role, content, citations, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                """,
                (conversation_id,),
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["id"] = str(d["id"])
            if hasattr(d.get("created_at"), "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            result.append(d)
        return result
    finally:
        conn.close()


def seed_interview_question(
    question_id: str,
    level: str,
    profile_id: str,
    topic: str,
    difficulty: int,
    prompt_text: str,
    expected_themes: list[str],
    retrieval_hint: str,
    question_type: str = "standard",
    grading_rubric: dict | None = None,
) -> None:
    """Insert version 1 of a question if it doesn't already exist. Idempotent — safe to
    call on every startup with the same seed data."""
    from psycopg2.extras import Json

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO interview_questions
                    (question_id, version, level, profile_id, topic, difficulty,
                     prompt_text, expected_themes, retrieval_hint, question_type, grading_rubric)
                VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (question_id, version) DO NOTHING
                """,
                (question_id, level, profile_id, topic, difficulty, prompt_text,
                 Json(expected_themes), retrieval_hint, question_type,
                 Json(grading_rubric) if grading_rubric is not None else None),
            )
        conn.commit()
    finally:
        conn.close()


def get_active_question_bank(level: str, profile_id: str) -> list[dict]:
    """Active (non-deprecated) questions for a level × profile_id, in insertion order.
    Rows stored with level='multi' (e.g. scenario_troubleshooting) are visible at every
    level for that profile_id, since they aren't tied to one specific level."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT question_id, version, level, profile_id, topic, difficulty,
                       prompt_text, expected_themes, retrieval_hint, question_type, grading_rubric
                FROM interview_questions
                WHERE (level = %s OR level = 'multi') AND profile_id = %s AND deprecated_at IS NULL
                ORDER BY question_id
                """,
                (level, profile_id),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_question_ids(user_id: str, level: str, profile_id: str, *, limit_sessions: int = 3) -> set[str]:
    """Question IDs asked to this user in their most recent sessions for this
    level × profile_id, used to avoid repeating the same questions on the next
    attempt. Empty user_id (anonymous) returns an empty set."""
    if not user_id:
        return set()
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ia.question_id
                FROM interview_answers ia
                JOIN interview_sessions s ON s.session_id = ia.session_id
                WHERE s.session_id IN (
                    SELECT session_id FROM interview_sessions
                    WHERE user_id = %s AND level = %s AND profile_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                )
                """,
                (user_id, level, profile_id, limit_sessions),
            )
            rows = cur.fetchall()
        return {r["question_id"] for r in rows}
    finally:
        conn.close()


def list_active_question_combinations() -> list[tuple[str, str]]:
    """Distinct (level, profile_id) pairs with at least one active question."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT level, profile_id
                FROM interview_questions
                WHERE deprecated_at IS NULL
                """
            )
            rows = cur.fetchall()
        return [(r["level"], r["profile_id"]) for r in rows]
    finally:
        conn.close()


def get_active_question_version(question_id: str) -> Optional[int]:
    """Current active version number for a question_id, or None if deprecated/missing."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version FROM interview_questions WHERE question_id = %s AND deprecated_at IS NULL",
                (question_id,),
            )
            row = cur.fetchone()
        return row["version"] if row else None
    finally:
        conn.close()


def create_interview_session(
    session_id: str,
    user_id: str,
    level: str,
    profile_id: str,
    questions: list[tuple[str, int]],
) -> str:
    """Insert the session row plus one stub answer row per question (question_id,
    question_version), in the order the candidate will see them. One transaction —
    either the whole session is persisted or none of it is. Returns created_at
    (ISO string) so the frontend can render an elapsed-time indicator without a
    second round trip."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO interview_sessions (session_id, user_id, level, profile_id)
                VALUES (%s, %s, %s, %s)
                RETURNING created_at
                """,
                (session_id, user_id, level, profile_id),
            )
            created_at = cur.fetchone()["created_at"]
            for index, (question_id, question_version) in enumerate(questions):
                cur.execute(
                    """
                    INSERT INTO interview_answers (session_id, question_id, question_version, question_index)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session_id, question_id, question_version, index),
                )
        conn.commit()
        return created_at.isoformat()
    finally:
        conn.close()


def get_interview_session_row(session_id: str) -> Optional[dict]:
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, user_id, level, profile_id, current_index, phase,
                       awaiting_advance, evaluated, session_report, created_at
                FROM interview_sessions WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        d = dict(row)
        d["session_id"] = str(d["session_id"])
        if d.get("created_at") is not None:
            d["created_at"] = d["created_at"].isoformat()
        return d
    finally:
        conn.close()


def get_interview_session_answers(session_id: str) -> list[dict]:
    """Answers joined with their question content, ordered by question_index —
    resolves each answer to the exact question text/version the candidate saw,
    even if that question has since been edited or deprecated.

    A follow-up row (is_followup=TRUE) has no interview_questions row of its own
    — it inherits topic/difficulty/expected_themes/retrieval_hint from its parent
    (COALESCE(parent_question_id, question_id) below), since a follow-up probes
    the same scope more deeply rather than a new domain, and its own generated
    wording (followup_prompt_text) overrides prompt_text.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.question_id, a.question_version, a.question_index, a.answer,
                       a.score, a.score_pct, a.strengths, a.gaps, a.model_answer_outline,
                       a.feedback, a.citations, a.is_followup, a.parent_question_id,
                       COALESCE(a.followup_prompt_text, q.prompt_text) AS prompt_text,
                       q.topic, q.difficulty, q.expected_themes, q.retrieval_hint
                FROM interview_answers a
                JOIN interview_questions q
                  ON q.question_id = COALESCE(a.parent_question_id, a.question_id)
                 AND q.version = a.question_version
                WHERE a.session_id = %s
                ORDER BY a.question_index ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_followup_for_parent(session_id: str, parent_question_id: str) -> Optional[dict]:
    """Existing follow-up for a parent question, if one was already generated —
    used to skip re-running the Haiku detection/generation call on a retried
    /answer, and as the pre-check that makes insert_followup_if_absent's shift
    step safe to skip on retry."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT question_id, question_index, followup_prompt_text
                FROM interview_answers
                WHERE session_id = %s AND parent_question_id = %s
                """,
                (session_id, parent_question_id),
            )
            row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def insert_followup_if_absent(
    session_id: str,
    parent_question_id: str,
    parent_question_version: int,
    followup_prompt_text: str,
) -> dict:
    """Insert a follow-up question row immediately after its parent, shifting
    every later question_index by one to make room. Idempotent: locks the
    parent's own answer row (SELECT ... FOR UPDATE) to serialize concurrent
    /answer calls for the same question, then checks for an existing follow-up
    before touching anything — the index shift is NOT itself safe to re-run, so
    the pre-check (not just the INSERT's ON CONFLICT) is what makes retries safe.
    ON CONFLICT (session_id, question_id) DO NOTHING on the INSERT is kept as a
    defense-in-depth backstop; the row lock above should make it unreachable in
    practice. Either way, the returned dict always reflects what's actually
    persisted, never the just-generated (possibly discarded) text.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT question_index FROM interview_answers WHERE session_id = %s AND question_id = %s FOR UPDATE",
                (session_id, parent_question_id),
            )
            parent_row = cur.fetchone()
            if parent_row is None:
                raise ValueError(f"Unknown parent question {parent_question_id} for session {session_id}")
            parent_index = parent_row["question_index"]

            cur.execute(
                "SELECT question_id, question_index, followup_prompt_text "
                "FROM interview_answers WHERE session_id = %s AND parent_question_id = %s",
                (session_id, parent_question_id),
            )
            existing = cur.fetchone()
            if existing is not None:
                conn.commit()
                return dict(existing)

            followup_question_id = f"{parent_question_id}-fu"
            cur.execute(
                "UPDATE interview_answers SET question_index = question_index + 1 "
                "WHERE session_id = %s AND question_index > %s",
                (session_id, parent_index),
            )
            cur.execute(
                """
                INSERT INTO interview_answers
                    (session_id, question_id, question_version, question_index,
                     is_followup, parent_question_id, followup_prompt_text)
                VALUES (%s, %s, %s, %s, TRUE, %s, %s)
                ON CONFLICT (session_id, question_id) DO NOTHING
                RETURNING question_id, question_index, followup_prompt_text
                """,
                (session_id, followup_question_id, parent_question_version,
                 parent_index + 1, parent_question_id, followup_prompt_text),
            )
            row = cur.fetchone()
        conn.commit()
        if row is None:
            # Should be unreachable given the row lock above; stay defensive.
            existing = get_followup_for_parent(session_id, parent_question_id)
            if existing is None:
                raise RuntimeError(f"Follow-up insert for {parent_question_id} vanished unexpectedly")
            return existing
        return dict(row)
    finally:
        conn.close()


def save_interview_answer(
    session_id: str, question_id: str, answer: str, awaiting_advance: bool, is_voice_input: bool = False,
) -> None:
    """Persist a draft answer edit and the session's awaiting_advance flag together."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE interview_answers SET answer = %s, is_voice_input = %s, updated_at = NOW() "
                "WHERE session_id = %s AND question_id = %s",
                (answer, is_voice_input, session_id, question_id),
            )
            cur.execute(
                "UPDATE interview_sessions SET awaiting_advance = %s, updated_at = NOW() WHERE session_id = %s",
                (awaiting_advance, session_id),
            )
        conn.commit()
    finally:
        conn.close()


def update_interview_answer_text(
    session_id: str, question_id: str, answer: str, is_voice_input: bool = False,
) -> None:
    """Edit an already-saved draft answer (PATCH /answer) without touching awaiting_advance."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE interview_answers SET answer = %s, is_voice_input = %s, updated_at = NOW() "
                "WHERE session_id = %s AND question_id = %s",
                (answer, is_voice_input, session_id, question_id),
            )
        conn.commit()
    finally:
        conn.close()


_TRANSCRIPTION_RATE_MAX_PER_HOUR = 10


def check_transcription_rate_limit(user_id: str) -> bool:
    """Return True if a voice-transcription call is allowed, False if the per-user
    hourly cap is exceeded. Separate from the IP-based ratelimit table since this
    route triggers billed external API usage and is keyed to the authenticated user."""
    now = datetime.now(tz=timezone.utc)
    window_start = now.replace(minute=0, second=0, microsecond=0)

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM exl_transcription_ratelimits WHERE window_start < NOW() - INTERVAL '2 hours'"
            )
            cur.execute(
                "SELECT request_count FROM exl_transcription_ratelimits WHERE user_id = %s AND window_start = %s",
                (user_id, window_start),
            )
            row = cur.fetchone()

            if row is None:
                cur.execute(
                    "INSERT INTO exl_transcription_ratelimits (user_id, window_start, request_count) "
                    "VALUES (%s, %s, 1)",
                    (user_id, window_start),
                )
                conn.commit()
                return True

            count = row["request_count"]
            if count >= _TRANSCRIPTION_RATE_MAX_PER_HOUR:
                conn.commit()
                return False

            cur.execute(
                "UPDATE exl_transcription_ratelimits SET request_count = request_count + 1 "
                "WHERE user_id = %s AND window_start = %s",
                (user_id, window_start),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def try_advance_interview_session(session_id: str, new_index: int, new_phase: str) -> bool:
    """Atomically move the session forward. Only succeeds if the session is still
    'questioning' and awaiting_advance — guards against a duplicate concurrent
    /advance request re-applying the same transition twice."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE interview_sessions
                SET current_index = %s, phase = %s, awaiting_advance = FALSE, updated_at = NOW()
                WHERE session_id = %s AND phase = 'questioning' AND awaiting_advance = TRUE
                RETURNING session_id
                """,
                (new_index, new_phase, session_id),
            )
            row = cur.fetchone()
        conn.commit()
        return row is not None
    finally:
        conn.close()


def try_end_interview_session(session_id: str) -> bool:
    """Atomically move a session straight from 'questioning' to 'review',
    regardless of awaiting_advance — the candidate-initiated "End interview"
    action, which can fire at any point mid-question, not just right after
    saving an answer. Returns False if the session already left 'questioning'
    (already ended, already complete, or a concurrent duplicate end/advance)."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE interview_sessions
                SET phase = 'review', awaiting_advance = FALSE, updated_at = NOW()
                WHERE session_id = %s AND phase = 'questioning'
                RETURNING session_id
                """,
                (session_id,),
            )
            row = cur.fetchone()
        conn.commit()
        return row is not None
    finally:
        conn.close()


def record_question_evaluation(
    session_id: str,
    question_id: str,
    score: int,
    score_pct: int,
    strengths: list,
    gaps: list,
    model_answer_outline: str,
    feedback: str,
    citations: list,
    claim_token,
) -> bool:
    """Write a per-question evaluation result, but only if `claim_token` still
    matches interview_sessions.evaluation_started_at for this session — i.e. only
    if this call's own /submit run is still the one holding the claim. If a stale
    reclaim has since taken over (evaluation_started_at moved on), this becomes a
    no-op and returns False: an old, merely-slow run must not keep mutating state
    out from under whichever run now owns the session's evaluation.
    """
    from psycopg2.extras import Json

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE interview_answers a
                SET score = %s, score_pct = %s, strengths = %s, gaps = %s,
                    model_answer_outline = %s, feedback = %s, citations = %s, updated_at = NOW()
                FROM interview_sessions s
                WHERE a.session_id = %s AND a.question_id = %s
                  AND s.session_id = a.session_id
                  AND s.evaluation_started_at = %s
                RETURNING a.session_id
                """,
                (score, score_pct, Json(strengths), Json(gaps),
                 model_answer_outline, feedback, Json(citations), session_id, question_id, claim_token),
            )
            row = cur.fetchone()
        conn.commit()
        return row is not None
    finally:
        conn.close()


def try_claim_interview_session_for_evaluation(session_id: str, stale_after_seconds: int = 120):
    """Atomically flip evaluated -> TRUE, but only from ('review', not-yet-evaluated) —
    or from a claim that's gone stale (evaluation_started_at older than
    stale_after_seconds). The staleness path is what lets a retry recover a session
    whose evaluation was interrupted mid-stream (client disconnect, server restart):
    without it, a claimed-but-never-completed session would be stuck in 'review'
    with evaluated=TRUE forever, since nothing else ever clears the flag.
    Whichever concurrent /submit request wins this update is the only one that goes
    on to run LLM evaluation; the loser sees None and must not proceed.

    Returns the newly-set evaluation_started_at timestamp on success (None on
    failure) — this is the CAS token callers must pass to
    record_question_evaluation/complete_interview_session, so that if a stale
    reclaim later takes the claim away from this run, this run's writes stop
    landing instead of racing the reclaiming run's writes.

    stale_after_seconds default (120s): the per-question LLM eval loop in
    InterviewerPipeline.stream_submit runs sequentially (not in parallel) — for
    the largest question banks (8 questions, ~5-10s each for retrieval + a
    1200-token Sonnet call) plus a final ~2000-token synthesis call, worst-case
    total is ~90-100s. 120s leaves ~25% margin above that worst case, so a
    reclaim should only ever fire once an evaluation has genuinely stalled
    (client gone, server crashed), not because it was merely a large bank still
    working. Too short (e.g. 30s) would risk reclaiming and double-running a
    still-in-flight evaluation; too long (e.g. 10+ minutes) leaves a genuinely
    interrupted session unrecoverable for an unnecessarily long time.
    """
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE interview_sessions
                SET evaluated = TRUE, evaluation_started_at = NOW(), updated_at = NOW()
                WHERE session_id = %s AND phase = 'review'
                  AND (evaluated = FALSE OR evaluation_started_at < NOW() - (%s || ' seconds')::interval)
                RETURNING evaluation_started_at
                """,
                (session_id, stale_after_seconds),
            )
            row = cur.fetchone()
        conn.commit()
        return row["evaluation_started_at"] if row else None
    finally:
        conn.close()


def complete_interview_session(session_id: str, session_report: dict, claim_token) -> bool:
    """Finalize the session, but only if `claim_token` still matches
    evaluation_started_at (see record_question_evaluation) — the same CAS guard,
    applied to the final write. Returns False (session_report NOT written) if a
    stale reclaim has since taken over this session's evaluation."""
    from psycopg2.extras import Json

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE interview_sessions
                SET phase = 'complete', session_report = %s, updated_at = NOW()
                WHERE session_id = %s AND evaluation_started_at = %s
                RETURNING session_id
                """,
                (Json(session_report), session_id, claim_token),
            )
            row = cur.fetchone()
        conn.commit()
        return row is not None
    finally:
        conn.close()
