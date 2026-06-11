"""
User management — SQLite-backed users and usage_logs tables.

DB file: data/users.db
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).parent.parent.parent
_DB_PATH = _ROOT / "data" / "users.db"

# Cost per 1 000 tokens (USD)
_COST = {
    "haiku":  {"input": 0.00025, "output": 0.00125},
    "sonnet": {"input": 0.003,   "output": 0.015},
}


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                username        TEXT    NOT NULL UNIQUE,
                password_hash   TEXT    NOT NULL,
                role            TEXT    NOT NULL DEFAULT 'user',
                is_active       INTEGER NOT NULL DEFAULT 1,
                question_limit  INTEGER,
                question_count  INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT    NOT NULL,
                last_seen_at    TEXT
            );

            CREATE TABLE IF NOT EXISTS usage_logs (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id           INTEGER NOT NULL,
                session_id        TEXT,
                question_text     TEXT,
                answer_text       TEXT,
                prompt_tokens     INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                total_cost_usd    REAL    NOT NULL DEFAULT 0.0,
                model             TEXT,
                created_at        TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)
        # Migrate existing DBs that predate answer_text column
        try:
            conn.execute("ALTER TABLE usage_logs ADD COLUMN answer_text TEXT")
        except Exception:
            pass  # column already exists


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, h = password_hash.split(":", 1)
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_user(
    username: str,
    password: str,
    role: str = "user",
    question_limit: Optional[int] = None,
    is_active: bool = True,
) -> dict:
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO users (username, password_hash, role, is_active, question_limit, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, hash_password(password), role, int(is_active), question_limit, _now()),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)


def get_user_by_username(username: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def list_users() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_user(user_id: int, **fields) -> Optional[dict]:
    """Update any subset of user fields. Pass question_limit=None to remove the limit."""
    updates, params = [], []
    if "password" in fields:
        updates.append("password_hash = ?")
        params.append(hash_password(fields["password"]))
    if "role" in fields:
        updates.append("role = ?")
        params.append(fields["role"])
    if "question_limit" in fields:
        updates.append("question_limit = ?")
        params.append(fields["question_limit"])  # None → NULL (unlimited)
    if "is_active" in fields:
        updates.append("is_active = ?")
        params.append(int(fields["is_active"]))
    if "question_count" in fields:
        updates.append("question_count = ?")
        params.append(fields["question_count"])
    if not updates:
        return get_user_by_id(user_id)
    params.append(user_id)
    with _connect() as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    return get_user_by_id(user_id)


def delete_user(user_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return cur.rowcount > 0


def touch_last_seen(user_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE users SET last_seen_at = ? WHERE id = ?", (_now(), user_id))


def try_increment_if_under_limit(user_id: int) -> bool:
    """Atomically check question limit and increment if allowed.

    Returns True if the request is permitted (and count was incremented),
    False if the user has reached their limit.
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT question_count, question_limit FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            return True  # unknown user — allow and skip tracking
        count = row["question_count"]
        limit = row["question_limit"]
        if limit is not None and count >= limit:
            return False
        conn.execute(
            "UPDATE users SET question_count = question_count + 1 WHERE id = ?", (user_id,)
        )
        return True


def increment_question_count(user_id: int) -> int:
    """Unconditional increment. Returns new count."""
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET question_count = question_count + 1 WHERE id = ?", (user_id,)
        )
        row = conn.execute(
            "SELECT question_count FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return row["question_count"] if row else 0


# ── Usage logging ─────────────────────────────────────────────────────────────

def log_usage(
    user_id: int,
    session_id: str,
    question_text: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    answer_text: str = "",
) -> None:
    costs = _COST.get(model, _COST["haiku"])
    cost = (prompt_tokens / 1000 * costs["input"]) + (completion_tokens / 1000 * costs["output"])
    with _connect() as conn:
        conn.execute(
            """INSERT INTO usage_logs
               (user_id, session_id, question_text, answer_text, prompt_tokens, completion_tokens,
                total_cost_usd, model, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, session_id, question_text[:500], answer_text[:4000] if answer_text else "",
             prompt_tokens, completion_tokens, cost, model, _now()),
        )


def get_user_usage(user_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM usage_logs WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_user_total_cost(user_id: int) -> float:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(total_cost_usd), 0) AS total FROM usage_logs WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return float(row["total"]) if row else 0.0


# ── Seeding ───────────────────────────────────────────────────────────────────

def _user_count() -> int:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        return row["c"]


def seed_defaults(site_username: Optional[str], site_password: Optional[str]) -> None:
    """Seed default users on first startup. No-op if any users already exist."""
    if _user_count() > 0:
        return
    # Always seed the shared demo account
    create_user("demo", "demo", role="demo", question_limit=5)
    # Seed site user from env if provided
    if site_username and site_password:
        create_user(site_username, site_password, role="user")
