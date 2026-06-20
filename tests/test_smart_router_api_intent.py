"""API product intent must win over guide product names."""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.core.smart_router import detect_product_intent


def test_ajo_api_beats_ajo_guide():
    assert detect_product_intent("Journey Optimizer API messaging endpoints") == "AJO APIs"


def test_aep_api_beats_aep_guide():
    assert detect_product_intent("Experience Platform API segmentation") == "AEP APIs"


def test_analytics_api_beats_analytics_guide():
    assert detect_product_intent("Adobe Analytics Reporting API OAuth") == "Analytics APIs"
