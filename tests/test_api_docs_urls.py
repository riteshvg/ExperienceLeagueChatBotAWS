"""URL derivation for developer.adobe.com API doc repos."""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.utils.exl_url_mapper import derive_exl_url, is_specific_url


def test_analytics_api_url():
    url = derive_exl_url(
        "adobe-docs/analytics-apis/src/pages/guides/oauth.md"
    )
    assert url == "https://developer.adobe.com/analytics-apis/docs/2.0/guides/oauth"


def test_cja_api_url():
    url = derive_exl_url(
        "adobe-docs/cja-apis/src/pages/endpoints/reporting/index.md"
    )
    assert url == "https://developer.adobe.com/cja-apis/docs/endpoints/reporting"


def test_aep_api_reference():
    url = derive_exl_url(
        "adobe-docs/experience-platform-apis/src/pages/references/segmentation.md"
    )
    assert url == "https://developer.adobe.com/experience-platform-apis/references/segmentation"


def test_data_collection_api_index():
    url = derive_exl_url(
        "adobe-docs/data-collection-apis/src/pages/api/index.md"
    )
    assert url == "https://developer.adobe.com/data-collection-apis/docs/api"


def test_ajo_api_url():
    url = derive_exl_url(
        "adobe-docs/journey-optimizer-apis/src/pages/references/authentication.md"
    )
    assert url == "https://developer.adobe.com/journey-optimizer-apis/references/authentication"


def test_is_specific_url_developer_adobe_short_paths():
    assert is_specific_url(
        "https://developer.adobe.com/journey-optimizer-apis/references/authentication"
    )
    assert is_specific_url(
        "https://developer.adobe.com/experience-platform-apis/references/segmentation"
    )
    assert not is_specific_url("https://developer.adobe.com/journey-optimizer-apis")
    assert not is_specific_url("https://developer.adobe.com/experience-platform-apis")
