"""Tests for admin refresh status enrichment."""

from backend.core.refresh_pipeline import enrich_status_for_admin


def test_enrich_fills_last_run_chunks_files_and_log():
    status = {
        "state": "idle",
        "last_run": None,
        "last_run_duration_s": None,
        "files_updated": 0,
        "chunks_indexed": 0,
        "error": None,
        "log": [],
    }
    enriched = enrich_status_for_admin(
        status,
        chroma_count=41017,
        kb_last_refreshed="2026-06-22T10:00:00+00:00",
        kb_source="s3:chroma_last_refreshed.json",
        kb_source_label="GitHub Actions",
        manifest_files_updated=12,
    )
    assert enriched["last_run"] == "2026-06-22T10:00:00+00:00"
    assert enriched["last_run_source"] == "s3:chroma_last_refreshed.json"
    assert enriched["last_run_source_label"] == "GitHub Actions"
    assert enriched["chunks_indexed"] == 41017
    assert enriched["files_updated"] == 12
    assert len(enriched["log"]) >= 4
    assert "GitHub Actions" in enriched["log"][1]


def test_enrich_does_not_override_local_pipeline_values():
    status = {
        "state": "success",
        "last_run": "2026-06-21T08:00:00+00:00",
        "last_run_duration_s": 180,
        "chunks_indexed": 123,
        "files_updated": 5,
        "log": ["done"],
    }
    enriched = enrich_status_for_admin(
        status,
        chroma_count=99999,
        kb_last_refreshed="2026-06-22T10:00:00+00:00",
        kb_source_label="GitHub Actions",
        manifest_files_updated=99,
    )
    assert enriched["last_run"] == "2026-06-21T08:00:00+00:00"
    assert enriched["chunks_indexed"] == 123
    assert enriched["files_updated"] == 5
    assert enriched["log"] == ["done"]
