# Keeping the Knowledge Base Fresh — Building the Data Refresh Pipeline

*thelearningproject.in*

---

The chatbot I'd been building for the past few months had a silent flaw baked into it from day one. The ChromaDB instance powering every retrieval query had a hard cutoff: **March 14, 2026**. That's the date the most recent markdown file was uploaded to S3. Everything since then — new CJA features, AEP schema updates, Journey Optimizer UI redesigns, new API versions across a dozen Adobe products — was invisible to the system.

Claude's training cutoff is August 2025. The whole point of RAG is to cover the gap between that cutoff and now with actual documentation. But RAG only covers the gap as far as the last sync. After that, I'd built a chatbot that gave confident, well-formatted, cited answers based on increasingly stale data. That's arguably worse than a hallucination — at least a hallucination is obviously wrong. Stale documentation looks right.

For a documentation chatbot to remain trustworthy, the data has to refresh automatically. This post covers how I built that pipeline.

---

## The Architecture: Four Scripts, One Flow

The pipeline has four stages. Two of the scripts (`ingest_to_chroma.py` and `ingest_with_media.py`) already existed from the original build. The new work was building the delta sync at the front of the pipeline and the S3 backup at the end.

```
AdobeDocs GitHub repos
  ↓ (sync_docs_to_s3.py — delta sync, only changed files)
S3 bucket (experienceleaguechatbot)
  ↓ (ingest_to_chroma.py — text chunking + Titan Embed v2)
ChromaDB (local)
  ↓ (ingest_with_media.py — video URLs, screenshots)
ChromaDB (enriched with media)
  ↓ (upload_chroma_to_s3.py — 66MB archive)
S3 bucket (chroma_db/chroma_db.tar.gz)
  ↓ (Railway cold start)
Production ChromaDB (Railway)
```

The full pipeline runs weekly via GitHub Actions (Monday at 2am UTC). It can also be triggered manually from the admin panel. I'll go through each piece.

---

## The Delta Sync Script

This is the most consequential piece of the pipeline, and the one that makes weekly automation practical rather than theoretical.

Adobe's three main documentation repos — `analytics.en`, `analytics-platform.en`, and `experience-platform.en` — contain roughly 1,260 markdown files in total. A naive sync would download all 1,260 on every run. That would take hours and generate unnecessary Bedrock Titan embedding calls on every unchanged file. Not acceptable.

The key insight: GitHub's Git Trees API returns a SHA for every file in a repo. The SHA changes when the file content changes. If I store the SHA for every file after each sync, I can compare on the next run and only download files where the SHA differs. That's the delta.

Here's the repo manifest and sync logic:

```python
REPOS = {
    "adobe-docs/adobe-analytics": {
        "github": "AdobeDocs/analytics.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/adobe-analytics/",
        "path_filter": "help/",
    },
    "adobe-docs/customer-journey-analytics": {
        "github": "AdobeDocs/analytics-platform.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/customer-journey-analytics/",
        "path_filter": "help/",
    },
    "adobe-docs/experience-platform": {
        "github": "AdobeDocs/experience-platform.en",
        "branch": "main",
        "s3_prefix": "adobe-docs/experience-platform/",
        "path_filter": "help/",
    },
}

def get_repo_tree(repo: str, branch: str) -> list[dict]:
    """Fetch full recursive file tree — returns list of {path, sha, type}."""
    url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
    resp = requests.get(url, headers=_gh_headers(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("truncated"):
        logger.warning(f"Tree truncated for {repo} — some files may be missed")
    return [f for f in data.get("tree", []) if f["type"] == "blob"]
```

The truncation warning is worth noting. GitHub's tree API will truncate results for very large repos. `experience-platform.en` is borderline. If it truncates, some changed files might be missed on that run — they'll be caught on the next weekly run, so it's not catastrophic, but it's worth logging so you know it happened.

The sync logic itself:

```python
def sync_repo(repo_key: str, config: dict, s3, manifest: dict,
              dry_run: bool = False, force: bool = False) -> dict:
    tree = get_repo_tree(config["github"], config["branch"])

    # Only markdown files under help/
    md_files = [
        f for f in tree
        if f["path"].endswith(".md") and f["path"].startswith(config["path_filter"])
    ]

    repo_manifest = manifest.get(repo_key, {})
    stats = {"checked": len(md_files), "updated": 0, "skipped": 0, "errors": 0}

    for file in md_files:
        path, sha = file["path"], file["sha"]

        # Skip unchanged files — this is the key efficiency win
        if not force and repo_manifest.get(path) == sha:
            stats["skipped"] += 1
            continue

        content = download_file(config["github"], path, config["branch"])
        s3.put_object(Bucket=S3_BUCKET, Key=config["s3_prefix"] + path, Body=content)
        repo_manifest[path] = sha   # update manifest with new SHA
        stats["updated"] += 1
        time.sleep(0.05)            # gentle rate limiting

    manifest[repo_key] = repo_manifest
    return stats
```

The manifest is stored at `data/sync_manifest.json` and committed to the repo between runs. Its structure is a nested dict: `{repo_key: {file_path: sha}}`. After a typical Monday run, you'll see entries like:

```json
{
  "adobe-docs/customer-journey-analytics": {
    "help/components/calc-metrics/cm-adv-function-ref.md": "a3f8d12...",
    "help/connections/cca/overview.md": "b7c4e91...",
    ...
  },
  "_last_sync": "2026-06-02T02:14:37+00:00",
  "_last_updated_count": 34
}
```

One practical note: the `GITHUB_TOKEN` environment variable is optional but important. Without it, GitHub's API rate limit is 60 requests per hour. The tree fetch is one request per repo, and each file download is another. On a full re-sync with `--force`, you can easily exceed 60 requests. With a token, the rate limit is 5,000 per hour — effectively unlimited for this use case.

---

## The Pipeline Orchestrator

With the sync script in place, I needed something to run the four-step pipeline in sequence and report status back to the admin panel. That's `backend/core/refresh_pipeline.py`.

The design requirement: the pipeline runs in a background thread (so the API call that triggers it returns immediately), writes status to `data/refresh_status.json` on every step, and the admin panel polls that file to show live progress.

```python
def _run_refresh(force: bool = False):
    global _running
    status = get_status()
    log: list[str] = []
    started = datetime.now(timezone.utc)

    status.update({
        "state": "running",
        "started_at": started.isoformat(),
        "log": log,
        "error": None,
    })
    _write_status(status)

    try:
        # Step 1: Sync from GitHub → S3
        log.append("=== Step 1: Sync GitHub → S3 ===")
        sync_args = ["--force"] if force else []
        if not _run_script("sync_docs_to_s3.py", sync_args, status, log):
            raise RuntimeError("Sync failed")

        # Check if anything actually changed
        manifest = _load_manifest()
        files_updated = manifest.get("_last_updated_count", 0)
        status["files_updated"] = files_updated

        if files_updated == 0 and not force:
            log.append("✓ No files changed — skipping ingest")
        else:
            # Step 2: Re-ingest into ChromaDB
            log.append("=== Step 2: Ingest into ChromaDB ===")
            if not _run_script("ingest_to_chroma.py", [], status, log):
                raise RuntimeError("Ingest failed")

            # Step 3: Media enrichment
            log.append("=== Step 3: Media enrichment ===")
            if not _run_script("ingest_with_media.py", [], status, log):
                log.append("⚠ Media enrichment failed — continuing")

            # Step 4: Upload ChromaDB to S3 for Railway cold starts
            log.append("=== Step 4: Upload ChromaDB → S3 ===")
            if not _run_script("upload_chroma_to_s3.py", [], status, log):
                log.append("⚠ ChromaDB upload failed — local DB updated but S3 backup failed")

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        status.update({
            "state": "success",
            "last_run": started.isoformat(),
            "last_run_duration_s": round(duration),
        })
    except Exception as e:
        status.update({"state": "failed", "error": str(e)})
    finally:
        _write_status(status)
        with _lock:
            _running = False
```

The `_run_script` helper calls each script as a subprocess, captures stdout and stderr, and appends the last 20 lines to the log list after each step. This gives the admin panel something meaningful to show without overwhelming it with 1,000 lines of ingest progress.

One subtle logic in Step 2: if the sync found zero changed files and this isn't a forced run, we skip ingest entirely. No point running Titan embeddings on a database that hasn't changed. This also means a Monday run where Adobe's docs team didn't publish anything takes about 2 minutes total rather than 20.

The trigger endpoint:

```python
def trigger_refresh(force: bool = False) -> dict:
    global _running
    with _lock:
        if _running:
            return {"started": False, "reason": "Refresh already running"}
        _running = True

    thread = threading.Thread(target=_run_refresh, args=(force,), daemon=True)
    thread.start()
    return {"started": True}
```

The lock prevents two simultaneous refresh runs — if someone double-clicks the admin button, the second call returns `{"started": False}` and the first run continues uninterrupted.

---

## The Admin Panel Integration

The Data Refresh tab in the admin panel surfaces three actions:

- **Run on Server** — triggers `trigger_refresh(force=False)` directly on the Railway container
- **Force Full Sync** — same but passes `force=True`, which adds `--force` to the sync script, re-downloading all files regardless of SHA
- **Run via GitHub Actions** — dispatches the `workflow_dispatch` event to the GitHub Actions workflow

The third option is the interesting one. Because GitHub Actions gives you free compute for the weekly job, I didn't want to burn Railway CPU on a 20-minute pipeline when I could use GitHub's CI runners instead. The dispatch endpoint:

```python
@router.post("/refresh/trigger-actions")
async def trigger_github_actions(
    _: Annotated[str, Depends(get_admin_user)],
    force: bool = False,
):
    """Trigger the GitHub Actions weekly refresh workflow via API."""
    import httpx
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="GITHUB_TOKEN not configured")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.github.com/repos/riteshvg/ExperienceLeagueChatBotAWS/actions/workflows/refresh-docs.yml/dispatches",
            json={"ref": "main", "inputs": {"force": "true" if force else "false"}},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=15,
        )

    if resp.status_code == 204:
        return {"triggered": True, "message": "GitHub Actions workflow dispatched"}
    raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text}")
```

A 204 response from GitHub means the workflow was dispatched. There's no job ID returned — if you want to track progress, you'd poll the GitHub Actions API for recent workflow runs. For this project, clicking the button and checking the GitHub Actions tab a minute later is sufficient.

The admin panel polls `GET /api/admin/refresh/status` every few seconds when a run is in progress, showing the live log entries from `refresh_status.json`. Watching the log scroll while ingest runs is genuinely useful for debugging — you can see exactly which step is taking time and whether any errors surface mid-run.

---

## The GitHub Actions Workflow

The weekly automation runs entirely outside of Railway, which was an intentional design choice. Railway containers have a limited CPU allocation, and running a 20-minute pipeline on them would compete with live traffic. GitHub Actions gives you a free `ubuntu-latest` runner with no such constraints.

```yaml
name: Weekly docs refresh

on:
  schedule:
    - cron: '0 2 * * 1'   # Every Monday at 2am UTC
  workflow_dispatch:
    inputs:
      force:
        description: 'Force full re-sync (ignore manifest)'
        required: false
        default: 'false'

jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 90

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install boto3 requests python-dotenv chromadb

      - name: Sync GitHub → S3
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
          AWS_S3_BUCKET: experienceleaguechatbot
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          ARGS=""
          if [ "${{ github.event.inputs.force }}" = "true" ]; then
            ARGS="--force"
          fi
          python scripts/sync_docs_to_s3.py $ARGS

      - name: Ingest into ChromaDB
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
          AWS_S3_BUCKET: experienceleaguechatbot
          BEDROCK_REGION: us-east-1
        run: python scripts/ingest_to_chroma.py

      - name: Media enrichment
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
          AWS_S3_BUCKET: experienceleaguechatbot
        run: python scripts/ingest_with_media.py

      - name: Upload ChromaDB → S3
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
          AWS_S3_BUCKET: experienceleaguechatbot
        run: python scripts/upload_chroma_to_s3.py
```

A few things worth noting about this workflow:

The `timeout-minutes: 90` is a safety valve. On a week where a lot of documentation changed and the ingest step is running Titan embeddings on hundreds of files, 90 minutes should be enough with margin. Without this, a hung subprocess could run indefinitely on GitHub's bill.

The `pip cache: 'pip'` on the Python setup step saves 30-60 seconds on repeat runs. Small but worth having.

`${{ secrets.GITHUB_TOKEN }}` in the Sync step is the automatically-injected token from GitHub Actions, not a manually configured secret. This means the sync script gets 5,000 API requests per hour without any additional configuration — the Actions environment handles it.

---

## The Cold Start Problem — Why the S3 Backup Matters

Railway's filesystem is ephemeral. Every time the container restarts — whether from a redeployment, a crash recovery, or Railway's own infrastructure maintenance — the local disk is wiped. The ChromaDB database lives at `chroma_db/` on that disk. Without an external backup and restore mechanism, every Railway restart would start with an empty database, and every query would return no results.

The restore logic runs in `backend/main.py` during the FastAPI lifespan startup:

```python
def _restore_chroma_from_s3() -> bool:
    """Download and extract chroma_db.tar.gz from S3 if local DB is empty."""
    import tarfile, tempfile
    import boto3

    # Check if already populated — warm restart skips the download
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        client = chromadb.PersistentClient(
            path=str(_CHROMA_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        col = client.get_or_create_collection("experience_league")
        if col.count() > 0:
            logger.info(f"ChromaDB already populated ({col.count()} chunks) — skipping S3 restore")
            return True
    except Exception:
        pass

    bucket = os.getenv("AWS_S3_BUCKET", "")
    if not bucket:
        logger.warning("AWS_S3_BUCKET not set — skipping S3 restore")
        return False

    logger.info(f"ChromaDB empty — downloading from s3://{bucket}/{_CHROMA_S3_KEY} ...")
    try:
        s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
            tmp_path = tmp.name
        s3.download_file(bucket, _CHROMA_S3_KEY, tmp_path)
        size_mb = Path(tmp_path).stat().st_size / 1024 / 1024
        logger.info(f"Downloaded {size_mb:.1f} MB — extracting ...")
        _CHROMA_DIR.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tmp_path, "r:gz") as tar:
            tar.extractall(_CHROMA_DIR.parent)
        Path(tmp_path).unlink()
        logger.info("ChromaDB restored from S3 ✓")
        return True
    except Exception as e:
        logger.warning(f"S3 restore failed: {e} — continuing with empty DB")
        return False
```

The `col.count() > 0` check on startup is the key guard. When Railway restarts a container that's been running for a while (a warm restart, not a fresh deployment), the filesystem persists across that restart. The ChromaDB data is already on disk. Without this check, the startup logic would download a 66MB archive from S3 on every restart — unnecessary and slow.

The upload script (`upload_chroma_to_s3.py`) runs as the last step of the refresh pipeline. It compresses the entire `chroma_db/` directory to a `.tar.gz` archive and uploads it:

```python
with tarfile.open(tmp_path, "w:gz") as tar:
    tar.add(CHROMA_DIR, arcname="chroma_db")

s3.upload_file(
    tmp_path,
    S3_BUCKET,
    "chroma_db/chroma_db.tar.gz",
    ExtraArgs={"ContentType": "application/gzip"},
)
```

The compressed archive is about 66MB for 5,685 chunks. Uncompressed ChromaDB storage for the same data is around 180MB. The compression is worth it — that's about 10 seconds shaved off every cold start download.

---

## What a Refresh Run Actually Looks Like

After running the pipeline for a few weeks, here's what a typical Monday run looks like:

| Stage | Duration | Notes |
|---|---|---|
| GitHub → S3 sync | 2–5 minutes | Depends on changed file count |
| ChromaDB ingest | 5–15 minutes | Titan embedding calls via Bedrock |
| Media enrichment | 1–2 minutes | Parsing frontmatter and markdown bodies |
| S3 upload | 1–2 minutes | 66MB archive upload |
| **Total** | **~20–30 minutes** | On a week with 20–80 changed files |

The delta sync makes the variance in that "2–5 minutes for sync" very tight. On a slow week for Adobe's docs team, maybe 20 files changed out of 1,260. The sync step takes 90 seconds. On a busy week (new product release, CJA feature update, AEP schema documentation), maybe 80 files changed. The sync takes 4 minutes.

Without the delta sync — downloading all 1,260 files unconditionally — the sync step alone would take 30–40 minutes. With Bedrock rate limits on Titan embeddings, the full ingest would then take hours. Weekly automation stops being practical at that point.

One more detail: the early-exit logic when `files_updated == 0`. On weeks where nothing changed, the pipeline completes in about 2 minutes total (just the sync check), writes `"state": "success"` with a note that no files changed, and exits. No unnecessary embedding calls, no upload, no CPU burned.

---

## The Full Refresh Flow, End to End

Putting it together: every Monday at 2am UTC, the GitHub Actions workflow runs. It checks the three AdobeDocs repos against the manifest, downloads any changed files to S3, re-ingests them into ChromaDB with Titan embeddings, enriches with media metadata, and uploads the updated ChromaDB archive back to S3.

When Railway's container restarts (next deployment or maintenance), `backend/main.py` checks if ChromaDB is empty. If it is, it downloads the 66MB archive from S3 and extracts it. The chatbot is now serving queries against the freshly updated database within about 45 seconds of container start.

The result: the knowledge base cutoff moves forward by a week every Monday. The gap between "what Adobe documented" and "what the chatbot knows" is bounded at one week, not open-ended.

---

## Key Takeaways

- **SHA-based delta sync is the foundation.** Without it, a weekly automation becomes impractical. GitHub's tree API returns file SHAs — store them, compare on the next run, skip unchanged files. This is the entire efficiency story.

- **Store the manifest between runs.** If you lose `sync_manifest.json`, you lose the delta benefit and trigger a full re-sync. Commit the manifest to the repo or store it in S3 alongside the docs.

- **Railway's ephemeral filesystem requires an external backup.** ChromaDB data lives on disk. Every cold start wipes it. S3 is the right place for the archive — cheap, durable, and accessible from both GitHub Actions and Railway.

- **The `count > 0` guard prevents redundant downloads.** Warm restarts should not re-download 66MB from S3. Check if the collection already has data before making the network call.

- **GitHub Actions gives you free compute for the weekly job.** There's no reason to run a 20-minute pipeline on Railway when GitHub's CI runners are free. Use `workflow_dispatch` for manual triggers and `schedule` for automation.

- **The admin panel trigger via GitHub API removes GitHub UI dependency.** You can fire the Actions workflow from the admin panel without opening a browser tab to GitHub. Small but useful when you're responding to a support question and need to trigger a refresh immediately.

- **Skip ingest when nothing changed.** If the sync finds zero updated files and it's not a force run, there's nothing to embed. Exit early and save the Bedrock API calls.

- **Log verbosely during each pipeline step.** When the ingest step fails on week 6 because a markdown file has malformed frontmatter, you want to know exactly which file and which line. Capturing stderr per script and streaming it to the status file is worth the extra plumbing.

---

## Where This Leaves Things

The pipeline is running. The knowledge base is no longer frozen at March 14, 2026. Every Monday it catches up to whatever Adobe published the prior week.

What's still missing: a more granular ingest that only re-embeds the *changed* files rather than running `ingest_to_chroma.py` on the entire S3 bucket every time. Right now the ingest script does a full reset and re-index on every run. That's correct but not optimal — for weeks with 20 changed files out of 1,260, you're re-generating embeddings for 1,240 files that didn't change. The sync script knows exactly which files changed; the ingest script should be taught to receive that list.

That incremental ingest is the next improvement. It won't change the external behavior of the system — the chatbot will still answer correctly either way — but it would cut the ingest step from 5–15 minutes to under a minute for a typical weekly run.

For now, though: the gap is bounded. The data is fresh. The chatbot is trustworthy again.

---

*Part of an ongoing series about building an unofficial Adobe Experience League documentation chatbot at thelearningproject.in.*
