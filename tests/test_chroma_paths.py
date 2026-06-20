"""Chroma persist path resolution."""

import sys
from pathlib import Path
from unittest.mock import patch

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.core import chroma_paths


def test_local_default():
    with patch.dict("os.environ", {}, clear=True):
        assert chroma_paths.chroma_persist_dir() == _ROOT / "chroma_db"


def test_railway_defaults_to_tmp():
    with patch.dict("os.environ", {"RAILWAY_ENVIRONMENT": "production"}, clear=True):
        assert chroma_paths.chroma_persist_dir() == Path("/tmp/chroma_db")


def test_chroma_persist_dir_override():
    with patch.dict("os.environ", {"CHROMA_PERSIST_DIR": "/data/chroma"}, clear=True):
        assert chroma_paths.chroma_persist_dir() == Path("/data/chroma")
