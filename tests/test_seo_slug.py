import re

from backend.core.google_db import make_slug


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
