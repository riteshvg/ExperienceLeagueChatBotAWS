# AGENTS.md — Rovr (Experience League Chatbot)

Instructions for AI agents and IDEs working in this repo.

## Railway deployment (read before every prod deploy)

**Mandatory:** satisfy `.cursor/rules/railway-pre-deploy-checklist.mdc` before any Railway or `main` push deploy.

### Architecture

- **Code** deploys via Railway git integration on push to `main`, or `railway up` from repo root.
- **Chroma index** (~41k chunks) lives in S3: `s3://experienceleaguechatbot/chroma_db/chroma_db.tar.gz`.
- **GHA** (`refresh-docs.yml`) updates S3 incrementally; Railway pulls on startup when local index is empty.
- On Railway, Chroma restores to a **fresh temp dir** (`/tmp/chroma_data_*`) — not `/app/chroma_db` or `/tmp/chroma_db`.

### URLs

| Component | URL |
|-----------|-----|
| Backend health | `https://experienceleaguechatbotaws-production.up.railway.app/api/health` |
| Backend ping | `https://experienceleaguechatbotaws-production.up.railway.app/api/ping` |
| Frontend | `https://thelearningproject.in/tools/rovr` |
| Railway | project `experienceleaguechatbot`, service `ExperienceLeagueChatBotAWS` |

### Code-only deploy (most common)

```bash
# Pre-flight
railway deployment list | head -3
railway variables -k | grep -E 'CHROMA|KNOWLEDGE|FORCE'
curl -s https://experienceleaguechatbotaws-production.up.railway.app/api/health

# Deploy (pick ONE — not both unless you cancel the duplicate)
git push origin main          # triggers Railway build from git
# OR
railway up --detach           # deploy local tree directly

# Post-flight (after ~3 min — S3 restore on cold start)
curl -s .../api/health   # status=ok, document_count>=40000
curl -s .../api/ping     # ok:true
```

**Do not:** set `FORCE_CHROMA_RESTORE=true`, loop redeploys, or redeploy after unsetting flags.

### Index refresh (after GHA doc ingest)

Only when user explicitly requests or GHA just uploaded a new S3 tarball:

```bash
gh workflow run refresh-docs.yml --ref main
# Wait for GHA: ~41k chunks, S3 upload ~400MB

./scripts/railway_chroma_reload.sh --expected-chunks 41005
```

Or manual (single redeploy only):

```bash
STARTED=$(date -u +%Y-%m-%dT%H:%M:%SZ)
railway variables \
  --set "KNOWLEDGE_BANK_UPDATING=true" \
  --set "KNOWLEDGE_BANK_UPDATE_STARTED_AT=$STARTED" \
  --set "FORCE_CHROMA_RESTORE=true"
railway redeploy -y
# Poll health until chunks>=40000, then unset flags WITHOUT redeploy:
railway variables \
  --set "FORCE_CHROMA_RESTORE=false" \
  --set "KNOWLEDGE_BANK_UPDATING=false" \
  --set "KNOWLEDGE_BANK_UPDATE_STARTED_AT="
```

### Incident rules (2026-06-20)

1. `railway redeploy` alone re-runs the **last built image** — not latest git fixes.
2. Multiple redeploys + stale `KNOWLEDGE_BANK_UPDATING` caused stuck maintenance banner with 41k chunks loaded.
3. Copy/move to `/app/chroma_db` or `/tmp/chroma_db` → Chroma sees 0 chunks; extract to `chroma_data_*` works.
4. `/api/health` returns 503 while `document_count=0` → Railway kills the deployment.

### Frontend deploy (separate)

```bash
./deploy.sh --frontend-only
```

### Do NOT without explicit user request

- Upload local Chroma to S3
- Run `FORCE_CHROMA_RESTORE` or `./scripts/railway_chroma_reload.sh`
- Commit `data/metadata_registry.json` without `git add -f`
- GHA `force=true` (full rebuild, hours)
