"""Tests for numbered context / citation index alignment."""

from backend.core.evidence import build_context_index, build_numbered_context


def test_numbered_context_skips_unlinkable_chunks():
    docs = [
        {
            "content": "Linkable A",
            "metadata": {
                "url": "https://experienceleague.adobe.com/docs/a.html",
                "title": "Doc A",
                "product": "Adobe Target",
            },
        },
        {
            "content": "No URL chunk",
            "metadata": {"title": "Orphan", "product": "Adobe Target"},
        },
        {
            "content": "Linkable B",
            "metadata": {
                "url": "https://experienceleague.adobe.com/docs/b.html",
                "title": "Doc B",
                "product": "Adobe Target",
            },
        },
    ]
    context, index = build_numbered_context(docs)
    assert "[1] Linkable A" in context
    assert "No URL chunk" in context
    assert "[2]" not in context.split("No URL chunk")[0]  # unnumbered middle
    assert "[2] Linkable B" in context
    assert len(index) == 2
    assert all(entry["url"] for entry in index)
    assert build_context_index(docs) == index
