import re
import uuid

from backend.api.routes.chat import _valid_uuid
from backend.core.google_db import make_slug


def test_valid_uuid_passes_through_normalized():
    raw = str(uuid.uuid4())
    assert _valid_uuid(raw) == raw
    # Case/format differences (e.g. uppercase) normalize to the same canonical form.
    assert _valid_uuid(raw.upper()) == raw


def test_valid_uuid_rejects_legacy_client_ids():
    # Pre-migration frontend generated ids via Math.random().toString(36) — never a UUID.
    assert _valid_uuid("k3j9f8s71a2") is None
    assert _valid_uuid("") is None
    assert _valid_uuid(None) is None


def test_make_slug_is_url_safe_and_deterministic():
    slug = make_slug("How do I set up Tags in Adobe Launch?")
    assert slug == make_slug("How do I set up Tags in Adobe Launch?")
    assert re.fullmatch(r"[a-z0-9-]+", slug)
    assert slug.startswith("how-do-i-set-up-tags-in-adobe-launch-")


def test_make_slug_dedupes_similar_text_differently():
    a = make_slug("How do I set up Tags in Adobe Launch?")
    b = make_slug("How do I set up tags in adobe launch")
    assert a != b  # different punctuation/case -> different hash suffix, same base


def test_make_slug_handles_empty_base():
    slug = make_slug("???")  # no ascii alnum chars -> base collapses to empty
    assert "-" not in slug
    assert len(slug) == 6
