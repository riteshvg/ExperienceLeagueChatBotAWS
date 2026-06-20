"""Query preprocessing must not corrupt API doc queries."""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.core.query_processor import QueryProcessor


def test_segmentation_service_api_not_routed_to_analytics():
    qp = QueryProcessor()
    enhanced, meta = qp.preprocess_query(
        "How do I use the Segmentation Service API to create a segment?"
    )
    assert "Adobe Analytics report suite" not in enhanced
    assert not any(c.get("action") == "added_aa_keywords" for c in meta["changes"])
