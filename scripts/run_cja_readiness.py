#!/usr/bin/env python3
"""
Run CJA readiness checks against a deployed Rovr API (retrieval-only, no LLM).

Usage:
    python scripts/run_cja_readiness.py
    python scripts/run_cja_readiness.py --base-url https://experienceleaguechatbotaws-production.up.railway.app
    ADMIN_PASSWORD=... python scripts/run_cja_readiness.py --base-url http://127.0.0.1:8000

Exit code 0 when all checks pass, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _login(base_url: str, password: str) -> str:
    resp = requests.post(
        f"{base_url.rstrip('/')}/api/admin/login",
        json={"password": password},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def main() -> int:
    parser = argparse.ArgumentParser(description="CJA readiness API smoke test")
    parser.add_argument(
        "--base-url",
        default=os.getenv("ROVR_API_URL", "http://127.0.0.1:8000"),
        help="Backend base URL",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ADMIN_PASSWORD", ""),
        help="Admin password (or set ADMIN_PASSWORD)",
    )
    args = parser.parse_args()

    if not args.password:
        print("ERROR: Set ADMIN_PASSWORD or pass --password", file=sys.stderr)
        return 1

    base = args.base_url.rstrip("/")
    token = _login(base, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    health = requests.get(f"{base}/api/health", timeout=30)
    health.raise_for_status()
    print(f"Health: {health.json().get('status')} — {health.json().get('chromadb', {}).get('document_count')} chunks")

    resp = requests.get(f"{base}/api/admin/readiness/cja", headers=headers, timeout=120)
    try:
        payload = resp.json()
    except Exception:
        print(resp.text)
        resp.raise_for_status()
        return 1

    print(json.dumps(payload, indent=2))

    corpus = payload.get("corpus", {})
    questions = payload.get("questions", {})
    print(
        f"\nCJA corpus: {corpus.get('chunks')} chunks / {corpus.get('pages')} pages "
        f"(ok={corpus.get('ok')})"
    )
    print(f"Questions: {questions.get('passed')}/{questions.get('total')} passed")

    if payload.get("passed"):
        print("\n✅ CJA readiness PASSED")
        return 0

    print("\n❌ CJA readiness FAILED")
    for item in questions.get("items", []):
        if not item.get("passed"):
            print(f"  - {item.get('id')}: {item.get('details')} ({item.get('outcome')})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
