"""Seed a fake published Q&A pair locally so /q/<slug> can be previewed
without a real login + LLM round trip.

Usage:
    venv/bin/python scripts/seed_seo_landing.py "How do I set up tags in Adobe Launch?"
    venv/bin/python scripts/seed_seo_landing.py "How do I set up tags in Adobe Launch?" --answer "Custom answer text"
    venv/bin/python scripts/seed_seo_landing.py "..." --user-id github:12345
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=False)

from backend.core import google_db  # noqa: E402

DEFAULT_ANSWER = (
    "To set up tags in Adobe Experience Platform Launch, create a property, "
    "add the Tags extension you need, configure rules for your triggers, and "
    "publish the library to your target environment."
)
FAKE_CITATIONS = [
    {
        "url": "https://experienceleague.adobe.com/en/docs/experience-platform/tags/home",
        "title": "Tags Documentation",
        "product": "Adobe Experience Platform Launch",
    }
]
FAKE_EVIDENCE = {
    "source_count": 1,
    "citation_count": 1,
    "top_score": 0.91,
    "avg_score": 0.91,
    "evidence_level": "strong",
    "grounding_level": "documented",
    "match_label": "Strong match",
    "grounding_label": "Documented",
    "sources": [
        {
            "url": "https://experienceleague.adobe.com/en/docs/experience-platform/tags/home",
            "title": "Tags Documentation",
            "product": "Adobe Experience Platform Launch",
            "score": 0.91,
            "cited": True,
        }
    ],
}


def first_user_id() -> str:
    conn = google_db._connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM exl_users LIMIT 1")
            row = cur.fetchone()
            if not row:
                raise SystemExit("No rows in exl_users — log into the app locally once first.")
            return row["user_id"]
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--answer", default=DEFAULT_ANSWER)
    parser.add_argument("--user-id", default=None)
    args = parser.parse_args()

    user_id = args.user_id or first_user_id()

    conversation_id = google_db.create_conversation(user_id=user_id, session_id=None, title=args.query)
    google_db.append_conversation_message(conversation_id, "user", args.query)

    slug = google_db.make_slug(args.query)
    google_db.append_conversation_message(
        conversation_id, "assistant", args.answer,
        citations=FAKE_CITATIONS, slug=slug, is_published=True, evidence=FAKE_EVIDENCE,
    )

    print(f"conversation_id: {conversation_id}")
    print(f"slug:            {slug}")
    print(f"Frontend:        http://localhost:5173/q/{slug}")
    print(f"API:             http://localhost:8000/api/landing/{slug}")


if __name__ == "__main__":
    main()
