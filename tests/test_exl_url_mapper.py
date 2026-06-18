"""
Unit tests for Experience League URL derivation.

Run: pytest tests/test_exl_url_mapper.py -v
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
    """Bust redirect CSV cache between tests."""
    import src.utils.exl_redirects as redirects
    importlib.reload(redirects)
    redirects._load_redirects.cache_clear()
    yield
    redirects._load_redirects.cache_clear()


from src.utils.exl_url_mapper import derive_exl_url, resolve_doc_url


# Validated samples from ChromaDB → EXL mapping audit
SAMPLES = [
    (
        "adobe-docs/adobe-analytics/help/analyze/analysis-workspace/attribution/algorithmic.md",
        "https://experienceleague.adobe.com/en/docs/analytics/analyze/analysis-workspace/attribution/algorithmic",
    ),
    (
        "adobe-docs/experience-platform/help/datastreams/configure.md",
        "https://experienceleague.adobe.com/en/docs/experience-platform/datastreams/configure",
    ),
    (
        "adobe-docs/experience-platform/help/administrative-tags/api/folders.md",
        "https://experienceleague.adobe.com/en/docs/experience-platform/administrative-tags/api/folders",
    ),
    (
        "adobe-docs/adobe-journey-optimizer/help/using/campaigns/api-triggered-campaigns.md",
        "https://experienceleague.adobe.com/en/docs/journey-optimizer/using/campaigns/api-triggered-campaigns",
    ),
    (
        "adobe-docs/adobe-journey-optimizer/help/using/administration/high-low-permissions.md",
        "https://experienceleague.adobe.com/en/docs/journey-optimizer/using/access-control/high-low-permissions",
    ),
    (
        "adobe-docs/adobe-target/help/main/c-activities/activities.md",
        "https://experienceleague.adobe.com/en/docs/target/using/activities/activities",
    ),
    (
        "adobe-docs/adobe-target/help/main/c-recommendations/recommendations.md",
        "https://experienceleague.adobe.com/en/docs/target/using/recommendations/recommendations",
    ),
    (
        "adobe-docs/customer-journey-analytics/help/cja-main/analysis-workspace/templates/use-templates.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/templates/use-templates",
    ),
    (
        "adobe-docs/customer-journey-analytics/help/cja-main/connections/overview.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-connections/overview",
    ),
    (
        "adobe-docs/customer-journey-analytics/help/cja-main/data-views/data-views.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-dataviews/data-views",
    ),
]


@pytest.mark.parametrize("s3_key,expected", SAMPLES)
def test_derive_exl_url(s3_key, expected):
    assert derive_exl_url(s3_key) == expected


def test_resolve_doc_url_prefers_s3_key_over_stale_stored():
    meta = {
        "s3_key": (
            "adobe-docs/customer-journey-analytics/help/cja-main/"
            "analysis-workspace/templates/use-templates.md"
        ),
        "url": (
            "https://experienceleague.adobe.com/en/docs/customer-journey-analytics/"
            "analysis-workspace/templates/use-templates"
        ),
    }
    url = resolve_doc_url(meta)
    assert url == (
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/"
        "cja-workspace/templates/use-templates"
    )


def test_resolve_doc_url_falls_back_to_stored_with_redirect():
    meta = {
        "s3_key": "",
        "url": (
            "https://experienceleague.adobe.com/en/docs/journey-optimizer/using/"
            "administration/high-low-permissions"
        ),
    }
    url = resolve_doc_url(meta)
    assert url == (
        "https://experienceleague.adobe.com/en/docs/journey-optimizer/using/"
        "access-control/high-low-permissions"
    )
