"""Unit tests for Experience League URL derivation."""

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


from src.utils.exl_url_mapper import derive_exl_url, get_canonical_exl_url
from src.utils.exl_redirects import resolve_canonical_url

CJA_SAMPLES = [
    (
        "AdobeDocs/analytics-platform.en",
        "adobe-docs/customer-journey-analytics/help/cja-main/analysis-workspace/templates/use-templates.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/templates/use-templates",
    ),
    (
        "AdobeDocs/analytics-platform.en",
        "adobe-docs/customer-journey-analytics/help/cja-main/connections/overview.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-connections/overview",
    ),
    (
        "AdobeDocs/analytics-platform.en",
        "adobe-docs/customer-journey-analytics/help/cja-main/data-views/derived-fields/derived-fields.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-dataviews/derived-fields",
    ),
    (
        "AdobeDocs/analytics-platform.en",
        "adobe-docs/customer-journey-analytics/help/cja-main/use-cases/complex-data/object-arrays-in-cja.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-usecases/complex-data/object-arrays",
    ),
    (
        "AdobeDocs/analytics-platform.en",
        "adobe-docs/customer-journey-analytics/help/cja-main/guided-analysis/guided-analysis-in-workspace.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/guided-analysis/overview",
    ),
    (
        "AdobeDocs/analytics-platform.en",
        "adobe-docs/customer-journey-analytics/help/cja-main/overview.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/home",
    ),
    (
        "AdobeDocs/analytics-platform.en",
        "adobe-docs/customer-journey-analytics/help/cja-main/analysis-workspace/curate-and-share/download-send.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/export/download-send",
    ),
    (
        "AdobeDocs/customer-journey-analytics-learn.en",
        "adobe-docs/customer-journey-analytics-learn/help/cja-main/analysis-workspace/panels/build-the-attribution-panel.md",
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-workspace/panels/build-the-attribution-panel",
    ),
]


@pytest.mark.parametrize("repo,s3_key,expected", CJA_SAMPLES)
def test_cja_derive_exl_url(repo, s3_key, expected):
    assert derive_exl_url(s3_key) == expected
    repo_path = s3_key.split("/", 2)[-1]
    assert get_canonical_exl_url(repo_path, repo) == expected


def test_cja_unpublished_paths_return_none():
    assert derive_exl_url("adobe-docs/customer-journey-analytics/code-of-conduct.md") is None
    assert (
        derive_exl_url(
            "adobe-docs/customer-journey-analytics/help/video-clips/summit/2025/example.md"
        )
        is None
    )


def test_redirect_chain_resolves_cca_to_stitching():
    url = (
        "https://experienceleague.adobe.com/en/docs/analytics-platform/using/"
        "cja-connections/cca/overview"
    )
    resolved = resolve_canonical_url(url)
    assert resolved.endswith("/stitching/overview")
