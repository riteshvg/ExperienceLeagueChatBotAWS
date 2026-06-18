"""
Unit tests for Experience League URL derivation and citation metadata.

Run: pytest tests/test_exl_url_mapper.py tests/test_citation_metadata.py -v
"""

import importlib
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(autouse=True)
def fresh_redirect_cache():
    import src.utils.exl_redirects as redirects
    importlib.reload(redirects)
    redirects._load_redirects.cache_clear()
    yield
    redirects._load_redirects.cache_clear()


from src.utils.citation_metadata import (
    URL_SOURCE_VALIDATED,
    apply_url_validation,
    build_index_metadata,
)
from src.utils.exl_url_mapper import (
    derive_exl_url,
    get_canonical_exl_url,
    resolve_doc_url,
)

SAMPLES = [
    (
        "AdobeDocs/analytics.en",
        "adobe-docs/adobe-analytics/help/analyze/analysis-workspace/attribution/algorithmic.md",
        "https://experienceleague.adobe.com/en/docs/analytics/analyze/analysis-workspace/attribution/algorithmic",
    ),
    (
        "AdobeDocs/experience-platform.en",
        "adobe-docs/experience-platform/help/datastreams/configure.md",
        "https://experienceleague.adobe.com/en/docs/experience-platform/datastreams/configure",
    ),
    (
        "AdobeDocs/journey-optimizer.en",
        "adobe-docs/adobe-journey-optimizer/help/using/campaigns/api-triggered-campaigns.md",
        "https://experienceleague.adobe.com/en/docs/journey-optimizer/using/campaigns/api-triggered-campaigns",
    ),
    (
        "AdobeDocs/journey-optimizer.en",
        "adobe-docs/adobe-journey-optimizer/help/using/administration/high-low-permissions.md",
        "https://experienceleague.adobe.com/en/docs/journey-optimizer/using/access-control/high-low-permissions",
    ),
    (
        "AdobeDocs/target.en",
        "adobe-docs/adobe-target/help/main/c-activities/activities.md",
        "https://experienceleague.adobe.com/en/docs/target/using/activities/activities",
    ),
    (
        "AdobeDocs/analytics-platform.en",
        "adobe-docs/customer-journey-analytics/help/cja-main/analysis-workspace/templates/use-templates.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/templates/use-templates",
    ),
    (
        "AdobeDocs/data-collection.en",
        "adobe-docs/data-collection/help/tags/release-notes/current.md",
        "https://experienceleague.adobe.com/en/docs/data-collection/tags/release-notes/current",
    ),
]


@pytest.mark.parametrize("repo,s3_key,expected", SAMPLES)
def test_derive_exl_url(repo, s3_key, expected):
    assert derive_exl_url(s3_key) == expected
    repo_path = s3_key.split("/", 2)[-1]
    assert get_canonical_exl_url(repo_path, repo) == expected


def test_resolve_doc_url_reads_stored_metadata_only():
    meta = {
        "s3_key": "adobe-docs/customer-journey-analytics/help/cja-main/analysis-workspace/templates/use-templates.md",
        "exl_url": "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/templates/use-templates",
        "url": "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/templates/use-templates",
        "url_source": URL_SOURCE_VALIDATED,
    }
    assert resolve_doc_url(meta) == meta["url"]


def test_resolve_doc_url_ignores_s3_key_without_stored_url():
    meta = {
        "s3_key": "adobe-docs/adobe-journey-optimizer/help/using/campaigns/api-triggered-campaigns.md",
        "url": "",
        "exl_url": "",
    }
    assert resolve_doc_url(meta) is None


def test_build_index_metadata_sets_repo_path():
    s3_key = "adobe-docs/adobe-analytics/help/admin/home.md"
    meta = build_index_metadata(s3_key)
    assert meta.repo_path == "help/admin/home.md"
    assert meta.exl_url.endswith("/analytics/admin/home")


def test_apply_url_validation_stores_live_url_only():
    base = build_index_metadata(
        "adobe-docs/adobe-journey-optimizer/help/using/campaigns/api-triggered-campaigns.md"
    )
    live = apply_url_validation(base, True)
    assert live.url == live.exl_url
    assert live.url_source == URL_SOURCE_VALIDATED

    dead = apply_url_validation(base, False)
    assert dead.url == ""
    assert dead.exl_url == ""
