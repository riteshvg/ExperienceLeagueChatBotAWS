#!/usr/bin/env python3
"""
Compare the local chroma_db against the deployed (Railway) backend to catch
drift before it surprises anyone — different total chunk counts, missing
products, or a per-product chunk delta usually means the local corpus was
rebuilt/re-ingested but never pushed through the S3 refresh pipeline (or
vice versa).

Usage:
    python3 check_chroma_sync.py                  # one-shot check
    python3 check_chroma_sync.py --watch           # re-check every --interval seconds
    python3 check_chroma_sync.py --watch --interval 1800
    python3 check_chroma_sync.py --remote-url https://chatbot.thelearningproject.in

Admin credentials (ADMIN_PASSWORD, optionally ADMIN_EMAIL) are read from the
environment or a local .env file — set them to get the full per-product
breakdown via /api/admin/status. Without them, the script falls back to the
public /api/health endpoint, which only reports the total chunk count.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

ROOT = Path(__file__).parent
DEFAULT_REMOTE_URL = "https://chatbot.thelearningproject.in"
DEFAULT_LOCAL_CHROMA_DIR = ROOT / "chroma_db"
DEFAULT_INTERVAL_SECONDS = 1800  # 30 min


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def get_local_stats(chroma_dir: Path) -> dict[str, Any]:
    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_dir))
    collections = client.list_collections()
    if not collections:
        return {"error": f"No collections found in {chroma_dir}"}
    col = client.get_collection(collections[0].name)
    total = col.count()

    metas: list[dict] = []
    batch = 1000
    offset = 0
    while offset < total:
        page = col.get(limit=batch, offset=offset, include=["metadatas"])
        batch_metas = page.get("metadatas", [])
        if not batch_metas:
            break
        metas.extend(batch_metas)
        offset += len(batch_metas)

    from collections import defaultdict

    chunks: dict[str, int] = defaultdict(int)
    pages: dict[str, set] = defaultdict(set)
    release_notes_chunks = 0
    release_notes_docs: set[str] = set()

    for m in metas:
        product = m.get("product") or "Unknown"
        url = m.get("url") or m.get("s3_key") or ""
        chunks[product] += 1
        if url:
            pages[product].add(url)
        s3_key = (m.get("s3_key") or "").lower()
        if "release-notes" in s3_key or "/rn/" in s3_key:
            release_notes_chunks += 1
            release_notes_docs.add(m.get("s3_key", ""))

    breakdown = {
        p: {"chunks": chunks[p], "pages": len(pages[p])} for p in chunks
    }

    return {
        "collection": collections[0].name,
        "total_chunks": total,
        "total_pages": sum(len(v) for v in pages.values()),
        "product_breakdown": breakdown,
        "release_notes_chunks": release_notes_chunks,
        "release_notes_docs": len(release_notes_docs),
    }


def get_remote_stats(base_url: str, timeout: float = 15.0) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    result: dict[str, Any] = {}

    try:
        resp = requests.get(f"{base_url}/api/health", timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        result["status"] = payload.get("status")
        result["total_chunks"] = (payload.get("chromadb") or {}).get("document_count")
    except Exception as exc:
        return {"error": f"/api/health failed: {exc}"}

    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not admin_password:
        result["admin_stats"] = None
        return result

    try:
        login_resp = requests.post(
            f"{base_url}/api/admin/login",
            json={"password": admin_password},
            timeout=timeout,
        )
        login_resp.raise_for_status()
        token = login_resp.json()["token"]

        status_resp = requests.get(
            f"{base_url}/api/admin/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        status_resp.raise_for_status()
        status_payload = status_resp.json()
        kb = status_payload.get("knowledge_base", {})
        breakdown = {
            row["product"]: {"chunks": row["chunks"], "pages": row["pages"]}
            for row in kb.get("product_breakdown", [])
        }
        result["admin_stats"] = {
            "last_refreshed": kb.get("last_refreshed"),
            "last_refreshed_source": kb.get("last_refreshed_source"),
            "total_pages": kb.get("total_pages"),
            "product_breakdown": breakdown,
        }
    except Exception as exc:
        result["admin_stats"] = {"error": f"admin/status failed: {exc}"}

    return result


def compare(local: dict[str, Any], remote: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (in_sync, human-readable lines)."""
    lines: list[str] = []
    in_sync = True

    if "error" in local:
        return False, [f"✗ Local error: {local['error']}"]
    if "error" in remote:
        return False, [f"✗ Remote error: {remote['error']}"]

    local_total = local["total_chunks"]
    remote_total = remote.get("total_chunks")
    if remote_total is None:
        lines.append("? Remote total chunk count unavailable")
        in_sync = False
    elif local_total == remote_total:
        lines.append(f"✓ Total chunks match: {local_total}")
    else:
        lines.append(f"✗ Total chunk mismatch — local={local_total} remote={remote_total}")
        in_sync = False

    admin_stats = remote.get("admin_stats")
    if not admin_stats:
        lines.append("  (set ADMIN_PASSWORD to compare per-product breakdown)")
        return in_sync, lines
    if "error" in admin_stats:
        lines.append(f"? Could not fetch remote product breakdown: {admin_stats['error']}")
        return in_sync, lines

    lines.append(f"  Remote last refreshed: {admin_stats.get('last_refreshed')} "
                 f"(source: {admin_stats.get('last_refreshed_source')})")

    local_bd = local["product_breakdown"]
    remote_bd = admin_stats["product_breakdown"]
    all_products = sorted(set(local_bd) | set(remote_bd))

    for product in all_products:
        l = local_bd.get(product, {"chunks": 0, "pages": 0})
        r = remote_bd.get(product, {"chunks": 0, "pages": 0})
        if l["chunks"] == r["chunks"] and l["pages"] == r["pages"]:
            lines.append(f"  ✓ {product:30s} chunks={l['chunks']:6d} pages={l['pages']:5d}")
        else:
            in_sync = False
            lines.append(
                f"  ✗ {product:30s} "
                f"local(chunks={l['chunks']},pages={l['pages']}) != "
                f"remote(chunks={r['chunks']},pages={r['pages']})"
            )

    return in_sync, lines


def run_once(chroma_dir: Path, remote_url: str) -> bool:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"\n{'=' * 70}")
    print(f"  Chroma sync check — {timestamp}")
    print(f"  local:  {chroma_dir}")
    print(f"  remote: {remote_url}")
    print("=" * 70)

    local = get_local_stats(chroma_dir)
    remote = get_remote_stats(remote_url)

    in_sync, lines = compare(local, remote)
    for line in lines:
        print(line)

    if "error" not in local:
        print(f"\n  Local release-notes: {local['release_notes_chunks']} chunks "
              f"across {local['release_notes_docs']} docs")

    print()
    print("✓ IN SYNC" if in_sync else "✗ OUT OF SYNC — see above")
    print("=" * 70)
    return in_sync


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL_CHROMA_DIR,
                         help="Path to local chroma_db persist directory")
    parser.add_argument("--remote-url", default=os.getenv("ROVR_REMOTE_URL", DEFAULT_REMOTE_URL),
                         help="Base URL of the deployed backend")
    parser.add_argument("--watch", action="store_true",
                         help="Keep checking on a fixed interval instead of exiting")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS,
                         help="Seconds between checks when --watch is set (default: 1800)")
    args = parser.parse_args()

    _load_dotenv(ROOT / ".env")

    if args.watch:
        while True:
            run_once(args.local_dir, args.remote_url)
            print(f"\nNext check in {args.interval}s… (Ctrl+C to stop)")
            try:
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\nStopped.")
                return 0
    else:
        in_sync = run_once(args.local_dir, args.remote_url)
        return 0 if in_sync else 1


if __name__ == "__main__":
    sys.exit(main())
