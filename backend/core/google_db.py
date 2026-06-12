"""
PostgreSQL-backed Google OAuth tables.

Tables created on first startup:
  exl_users      — one row per Google account (user_id = Google sub)
  exl_sessions   — active sessions with 30-day TTL
  exl_ratelimits — per-IP rate limiting for the auth endpoint
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

_ADMIN_EMAIL_ENV = "ADMIN_EMAIL"

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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS exl_users (
                    user_id            TEXT PRIMARY KEY,
                    email              TEXT NOT NULL UNIQUE,
                    name               TEXT NOT NULL DEFAULT '',
                    picture            TEXT NOT NULL DEFAULT '',
                    first_seen         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_seen          TIMESTAMPTZ,
                    total_queries      INTEGER NOT NULL DEFAULT 0,
                    is_admin           BOOLEAN NOT NULL DEFAULT FALSE,
                    is_disabled        BOOLEAN NOT NULL DEFAULT FALSE,
                    daily_query_limit  INTEGER NOT NULL DEFAULT 20,
                    daily_query_count  INTEGER NOT NULL DEFAULT 0,
                    daily_reset_at     TIMESTAMPTZ
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
            """)
            # Safe migrations for existing deployments
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS is_disabled BOOLEAN NOT NULL DEFAULT FALSE"
            )
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS daily_query_limit INTEGER NOT NULL DEFAULT 20"
            )
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS daily_query_count INTEGER NOT NULL DEFAULT 0"
            )
            cur.execute(
                "ALTER TABLE exl_users ADD COLUMN IF NOT EXISTS daily_reset_at TIMESTAMPTZ"
            )
            cur.execute(
                "INSERT INTO system_config (key, value) VALUES ('default_daily_limit', '20') ON CONFLICT (key) DO NOTHING"
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
            # Seed kill switch default
            cur.execute(
                "INSERT INTO system_config (key, value) VALUES ('api_enabled', 'true') ON CONFLICT (key) DO NOTHING"
            )
        conn.commit()
    finally:
        conn.close()


def upsert_user(user_id: str, email: str, name: str, picture: str) -> dict:
    """Insert or update a Google user. Updates last_seen on every login."""
    admin_email = os.getenv(_ADMIN_EMAIL_ENV, "").strip().lower()
    is_admin_value = email.strip().lower() == admin_email if admin_email else False

    # Read default limit for new users
    default_limit = 20
    try:
        raw = get_system_config("default_daily_limit")
        if raw and raw.isdigit():
            default_limit = int(raw)
    except Exception:
        pass

    conn = _connect()
    try:
        with conn.cursor() as cur:
            if is_admin_value:
                # Ensure the admin email always has is_admin=true
                cur.execute(
                    """
                    INSERT INTO exl_users (user_id, email, name, picture, first_seen, last_seen, is_admin, daily_query_limit)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), TRUE, %s)
                    ON CONFLICT (user_id) DO UPDATE
                        SET email     = EXCLUDED.email,
                            name      = EXCLUDED.name,
                            picture   = EXCLUDED.picture,
                            last_seen = NOW(),
                            is_admin  = TRUE
                    RETURNING *
                    """,
                    (user_id, email, name, picture, default_limit),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO exl_users (user_id, email, name, picture, first_seen, last_seen, daily_query_limit)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), %s)
                    ON CONFLICT (user_id) DO UPDATE
                        SET email     = EXCLUDED.email,
                            name      = EXCLUDED.name,
                            picture   = EXCLUDED.picture,
                            last_seen = NOW()
                    RETURNING *
                    """,
                    (user_id, email, name, picture, default_limit),
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
                return {"allowed": True, "count": 0, "limit": 20}

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
            return {"count": 0, "limit": 20}
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
    default_limit = 20
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


def get_rate_limit_analytics() -> dict:
    """Return analytics about daily query usage across all users."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
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


def list_query_logs(limit: int = 100) -> list[dict]:
    """Return recent query logs with feedback rating joined from exl_feedback."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT q.id, q.message_id, q.user_id, q.email, q.query_text,
                       q.llm_model, q.input_tokens, q.output_tokens, q.cost_usd, q.created_at,
                       f.rating AS feedback_rating
                FROM exl_query_logs q
                LEFT JOIN exl_feedback f ON f.message_id = q.message_id AND q.message_id <> ''
                ORDER BY q.created_at DESC LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
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
    finally:
        conn.close()


def log_feedback(message_id: str, user_id: str, email: str, query_text: str, rating: int) -> None:
    """Insert or replace a feedback row for a given message_id."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO exl_feedback (message_id, user_id, email, query_text, rating)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (message_id, user_id, email, query_text, rating),
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
                "SELECT id, message_id, user_id, email, query_text, rating, created_at "
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
