import os
import pathlib

import pytest
from dotenv import load_dotenv

_ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=False)


@pytest.fixture(scope="session", autouse=True)
def _interview_db():
    """Real local Postgres (DATABASE_URL from .env) — tables created and question
    bank seeded once per test run, matching how the app initializes on startup."""
    from backend.core import google_db
    from config.interview_profiles import seed_all_questions

    google_db.init_tables()
    seed_all_questions()
