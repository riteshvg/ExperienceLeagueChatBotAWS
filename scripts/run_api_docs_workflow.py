#!/usr/bin/env python3
"""
Run the Adobe API docs ingest pipeline (sync → ingest → enrich → verify).

Usage:
    python scripts/run_api_docs_workflow.py --list-steps
    python scripts/run_api_docs_workflow.py --step sync
    python scripts/run_api_docs_workflow.py --step ingest --repo adobe-docs/analytics-apis
    python scripts/run_api_docs_workflow.py --step all --dry-run

Requires: GITHUB_TOKEN, AWS credentials, Bedrock access for ingest.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from config.api_docs_repos import API_DOC_INGEST_ORDER, API_DOC_REPOS

STEPS = [
    ("1", "Branch", "Work on `enhancements`; merge to `main` after local verify"),
    ("2", "Sync GitHub → S3", "python scripts/sync_docs_to_s3.py --repo <repo-key> (or all API keys)"),
    ("3", "Verify S3", "Confirm markdown under adobe-docs/*-apis/ in S3 bucket"),
    ("4", "Ingest → Chroma", "python scripts/ingest_to_chroma.py --prefix <s3-prefix> --product '<Product>'"),
    ("5", "Enrich citations", "python scripts/enrich_citation_metadata.py --prefix <s3-prefix> --product '<Product>'"),
    ("6", "Smoke query", "Ask Rovr an API question; confirm developer.adobe.com citation"),
    ("7", "GHA incremental", "gh workflow run refresh-docs.yml --ref main (force=false)"),
    ("8", "GHA targeted (first run)", "gh workflow run refresh-docs.yml -f ingest_prefix=... -f ingest_product=..."),
    ("9", "Upload Chroma → S3", "GHA upload step or: python scripts/upload_chroma_to_s3.py (explicit only)"),
    ("10", "Railway reload", "Controlled FORCE_CHROMA_RESTORE during maintenance window"),
    ("11", "Prod verify", "curl /api/health chunk count; admin product breakdown includes API products"),
]


def _run(cmd: list[str], dry_run: bool) -> None:
    print(f"\n▶ {' '.join(cmd)}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=_ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Adobe API docs ingest workflow")
    parser.add_argument("--list-steps", action="store_true", help="Print the checklist and exit")
    parser.add_argument(
        "--step",
        choices=["sync", "ingest", "enrich", "all"],
        help="Run a pipeline step for one or all API repos",
    )
    parser.add_argument(
        "--repo",
        help="Repo key from sync_docs_to_s3.py (e.g. adobe-docs/analytics-apis). Default: all API repos",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list_steps:
        print("\nAdobe API docs workflow — tick in order:\n")
        for num, name, detail in STEPS:
            print(f"  [ ] {num}. {name}")
            print(f"      {detail}")
        print("\nAPI repos wired:\n")
        for key, _prefix, product in API_DOC_INGEST_ORDER:
            github = API_DOC_REPOS[key]["github"]
            print(f"  • {key}  ({github})  →  product={product!r}")
        return 0

    if not args.step:
        parser.error("Pass --list-steps or --step sync|ingest|enrich|all")

    targets = API_DOC_INGEST_ORDER
    if args.repo:
        match = [t for t in API_DOC_INGEST_ORDER if t[0] == args.repo]
        if not match:
            print(f"Unknown repo key: {args.repo}", file=sys.stderr)
            return 1
        targets = match

    for repo_key, prefix, product in targets:
        if args.step in ("sync", "all"):
            _run(["python", "scripts/sync_docs_to_s3.py", "--repo", repo_key], args.dry_run)
        if args.step in ("ingest", "all"):
            _run(
                ["python", "scripts/ingest_to_chroma.py", "--prefix", prefix, "--product", product],
                args.dry_run,
            )
        if args.step in ("enrich", "all"):
            _run(
                [
                    "python",
                    "scripts/enrich_citation_metadata.py",
                    "--prefix",
                    prefix,
                    "--product",
                    product,
                ],
                args.dry_run,
            )

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
