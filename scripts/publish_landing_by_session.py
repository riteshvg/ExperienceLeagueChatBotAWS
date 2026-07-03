"""Publish a real, already-persisted local chat turn as an SEO landing page,
keyed off the browser's session_id — no fake data, no re-running the LLM.

The frontend sends its client-generated session_id (chatStore's activeSessionId,
a base36 string) on every /api/chat call; chat.py stores it on `conversations.session_id`
when the conversation is first created. This just finds that conversation, picks a
turn, and mints + sets the slug on the existing assistant message row.

Get your session_id from the browser: it's in-memory only (not persisted to
localStorage), so grab it from DevTools -> Network tab -> a POST /api/chat
request -> Payload -> "session_id".

Usage:
    venv/bin/python scripts/publish_landing_by_session.py <session_id>
    venv/bin/python scripts/publish_landing_by_session.py <session_id> --turn 2
    venv/bin/python scripts/publish_landing_by_session.py <session_id> --conversation-index 1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=False)

from backend.core import google_db  # noqa: E402
from backend.core.landing_questions import classify_solution  # noqa: E402


def find_conversations(session_id: str) -> list[dict]:
    conn = google_db._connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at FROM conversations WHERE session_id = %s ORDER BY created_at DESC",
                (session_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_messages(conversation_id) -> list[dict]:
    conn = google_db._connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, role, content, slug, is_published FROM messages "
                "WHERE conversation_id = %s ORDER BY created_at ASC",
                (conversation_id,),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def publish(message_id, slug: str) -> None:
    conn = google_db._connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE messages SET slug = %s, is_published = TRUE WHERE id = %s",
                (slug, message_id),
            )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("session_id")
    parser.add_argument("--conversation-index", type=int, default=1, help="1-indexed, most recent first")
    parser.add_argument("--turn", type=int, default=None, help="1-indexed answered turn; default: last")
    args = parser.parse_args()

    conversations = find_conversations(args.session_id)
    if not conversations:
        raise SystemExit(
            f"No conversation found with session_id={args.session_id!r}. "
            "This must be a session_id from a real /api/chat turn (not the seed_seo_landing.py script)."
        )
    if len(conversations) > 1:
        print(f"{len(conversations)} conversations share this session_id:")
        for i, c in enumerate(conversations, 1):
            print(f"  [{i}] {c['id']}  {c['created_at']}  {c['title']!r}")

    conversation = conversations[args.conversation_index - 1]
    messages = get_messages(conversation["id"])

    turns = []  # (user_msg, assistant_msg) pairs
    pending_user = None
    for m in messages:
        if m["role"] == "user":
            pending_user = m
        elif m["role"] == "assistant" and pending_user is not None and m["content"].strip():
            turns.append((pending_user, m))
            pending_user = None

    if not turns:
        raise SystemExit(f"No answered turns found in conversation {conversation['id']}.")

    turn_index = args.turn if args.turn is not None else len(turns)
    user_msg, assistant_msg = turns[turn_index - 1]

    query = user_msg["content"]
    solution = classify_solution(query)
    if not solution:
        print(f"Note: classify_solution() returned None for this query — "
              f"the live pipeline would NOT have auto-published it. Publishing anyway.")

    slug = assistant_msg["slug"] or google_db.make_slug(query)
    publish(assistant_msg["id"], slug)

    print(f"query:  {query!r}")
    print(f"slug:   {slug}")
    print(f"Frontend: http://localhost:5173/q/{slug}")
    print(f"API:      http://localhost:8000/api/landing/{slug}")


if __name__ == "__main__":
    main()
