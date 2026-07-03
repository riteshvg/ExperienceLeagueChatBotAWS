# CJA corpus fix — runbook

## Background

Broad/onboarding CJA questions ("I'm new to CJA, how do I set it up end-to-end")
were returning no answer. Root cause: `scripts/sync_docs_to_s3.py` has a repo
entry for CJA's tutorial/walkthrough content —

```python
"adobe-docs/customer-journey-analytics-learn": {
    "github": "AdobeDocs/customer-journey-analytics-learn.en",
    "doc_type": "tutorial",
    "level": "beginner",
    ...
},
```

— and `data/sync_manifest.json` showed its 161 file SHAs had been tracked by an
earlier sync run, but `data/metadata_registry.json` (the file `ingest_to_chroma.py`
actually reads to know what to embed) had **zero** entries for that repo. The
162 tutorial/walkthrough files were pulled from GitHub at some point but never
made it past the registry step into Chroma.

Separately, even once this content exists, the topical-relevance gate
(`backend/core/topical_relevance.py`) penalizes broad multi-part questions —
that's a follow-up fix, not covered by this runbook.

## Done (2026-07-03)

1. **Dry-run check** — confirmed the repo is reachable and healthy before
   touching anything:
   ```bash
   venv/bin/python scripts/sync_docs_to_s3.py --repo adobe-docs/customer-journey-analytics-learn --dry-run
   ```
   Result: `162 markdown files found`, `checked=162 updated=25 skipped=137 errors=0`.

2. **Real sync** — pulled the 25 changed files from GitHub, pushed them to S3,
   and backfilled the registry for all 162 files (the `sync_repo()` backfill
   loop in `sync_docs_to_s3.py:318-325` fills in registry entries for
   previously-synced-but-unregistered files, not just newly-changed ones):
   ```bash
   venv/bin/python scripts/sync_docs_to_s3.py --repo adobe-docs/customer-journey-analytics-learn
   ```
   Result: `Registry saved — 5400 total entries` (up from 5238 — exactly +162).

   Verified:
   ```bash
   python3 -c "
   import json
   data = json.load(open('data/metadata_registry.json'))
   learn = [k for k in data if 'customer-journey-analytics-learn' in k]
   print(len(learn))  # -> 162
   "
   ```

   Changed files (freshly downloaded from GitHub + pushed to S3 this run) are
   listed in `data/changed_s3_keys.txt` (25 entries). The other 137 already had
   their content in S3 from the earlier (never-registered) sync run — only
   their registry entry was missing, and that's now backfilled.

   **Known minor gap:** the 137 backfilled-but-unchanged entries were written
   with placeholder empty content (`_generate_registry_entry(..., b"", config)`),
   so their `title` field in the registry is a filename-derived fallback, not
   the real H1 from the markdown. This doesn't block ingestion — `ingest_to_chroma.py`
   re-downloads real content from S3 for chunking/embedding regardless of what's
   in the registry's `title` field — it just means citation titles for those
   pages may look a bit rough (e.g. "Add Bar Visualizations" derived from the
   filename instead of a hand-written page title) until the next time those
   files' SHAs actually change upstream and get a real `_extract_title()` pass.

## Left to do — run this yourself when ready

This step costs real Bedrock Titan embedding calls (modest for 162 files, but
not free), which is why it wasn't run automatically:

```bash
venv/bin/python scripts/ingest_to_chroma.py --product "Customer Journey Analytics"
```

This reads `data/metadata_registry.json`, downloads each CJA file from S3,
splits into ≤500-token chunks, embeds via Titan, and upserts into the
`experience_league` Chroma collection. It'll process the *entire* CJA product
(both the existing 373-chunk product-guide repo and the newly-registered
162-file tutorial repo), not just the new files — pass `--limit N` first if
you want to sanity-check a small batch before running the full thing.

## Verify afterward

```bash
source .env && export ADMIN_PASSWORD
venv/bin/python scripts/run_cja_readiness.py --base-url http://127.0.0.1:8000
```

Before this fix: `373 chunks / 287 pages` (readiness bar: `min_chunks: 4000,
min_pages: 700`, `ok: false`). Expect both numbers to jump meaningfully after
ingest — 162 more pages of tutorial content, likely several chunks each given
the ~500-token chunk size. It may still land under the 4000-chunk bar; worth
re-checking whether that bar is realistic for CJA's actual doc size, or should
be recalibrated, once the real post-ingest numbers are in.

You can also directly test the retrieval gate against the real onboarding
question afterward, e.g. via `assess_retrieval()` in
`backend/core/topical_relevance.py`, to see whether the new tutorial content
gets picked up as `relevant_docs` for a broad "I'm new to CJA" style query —
that's the multi-part-query gating issue flagged separately above, and may
still need its own fix even after ingestion.

## Related follow-up (not done, separate work)

- Fix the topical-relevance gate for broad/multi-part queries (query
  decomposition or a loosened gate for "getting started" intent).
- Add onboarding-style questions to `CJA_READINESS_QUESTIONS` in
  `backend/core/cja_readiness.py` so this regressions gets caught automatically.
- Audit the other `REPOS` entries in `sync_docs_to_s3.py` against
  `metadata_registry.json` for the same silent backfill gap — only confirmed
  for CJA-learn so far.
- `scripts/extract_metadata_from_github.py` has its own stale 4-product
  `REPOS` dict (missing Target/Data Collection/CJA-learn) — check if it's
  dead code, and delete it if so, to avoid confusion later.
