"""Tests for knowledge base last-refreshed resolution."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.core.knowledge_base_refresh import get_knowledge_base_last_refreshed


def test_prefers_s3_chroma_metadata():
    with patch("backend.core.knowledge_base_refresh._s3_chroma_metadata") as meta:
        meta.return_value = ("2026-06-19T12:00:00+00:00", "s3:chroma_last_refreshed.json")
        result = get_knowledge_base_last_refreshed()
    assert result["last_refreshed"] == "2026-06-19T12:00:00+00:00"
    assert result["source"] == "s3:chroma_last_refreshed.json"


def test_falls_back_to_chroma_archive_mtime():
    with patch("backend.core.knowledge_base_refresh._s3_chroma_metadata", return_value=(None, "")):
        with patch("backend.core.knowledge_base_refresh._local_refresh_status", return_value=(None, "")):
            with patch("backend.core.knowledge_base_refresh._s3_head_last_modified") as head:
                head.side_effect = [
                    ("2026-06-18T08:30:00+00:00", "s3:chroma_db/chroma_db.tar.gz"),
                    (None, ""),
                ]
                result = get_knowledge_base_last_refreshed()
    assert "2026-06-18" in result["last_refreshed"]
    assert "chroma_db.tar.gz" in result["source"]


def test_local_chroma_mtime_last_resort():
    with patch("backend.core.knowledge_base_refresh._s3_chroma_metadata", return_value=(None, "")):
        with patch("backend.core.knowledge_base_refresh._local_refresh_status", return_value=(None, "")):
            with patch("backend.core.knowledge_base_refresh._s3_head_last_modified", return_value=(None, "")):
                with patch("backend.core.knowledge_base_refresh._chroma_dir_mtime") as mtime:
                    mtime.return_value = (
                        datetime(2026, 6, 17, 9, 0, tzinfo=timezone.utc).isoformat(),
                        "local:chroma_db_mtime",
                    )
                    result = get_knowledge_base_last_refreshed()
    assert result["source"] == "local:chroma_db_mtime"
