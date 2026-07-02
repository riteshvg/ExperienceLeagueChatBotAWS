# Deployment

How to ship a feature branch to production: merge it into `main` via a GitHub
PR, then deploy the backend (Railway) and, if the frontend changed, Cloudflare
Pages.

## Repo

- Chatbot repo: `riteshvg/ExperienceLeagueChatBotAWS` (this repo)
- Blog repo (hosts the built frontend + triggers Cloudflare Pages): `riteshvg/tlp`

---

## 1. Feature branch → `main` → PR (GitHub)

Prerequisites: `gh` CLI installed and authenticated (`gh auth status`).

1. **Verify the branch is clean and ready:**

   ```bash
   git status --short
   git diff --stat
   ```

   Commit any outstanding work — do not open a PR with uncommitted changes sitting
   in the working tree.

2. **Run the checks that must pass before opening the PR:**

   ```bash
   venv/bin/python -m pytest tests/ -q
   cd frontend && npx tsc -b && npm run build && cd ..
   ```

   Compare failures against a clean checkout of `main` if anything fails — this
   repo has a handful of known pre-existing failures in `tests/test_users.py`
   (legacy auth endpoints) that are unrelated to most feature work.

3. **Push the branch:**

   ```bash
   git push -u origin <branch-name>
   ```

4. **Open the PR:**

   ```bash
   gh pr create --base main --head <branch-name> \
     --title "pushing changes for session id" \
     --body "$(cat <<'EOF'
   ## Summary
   - Session ID generation
   - Fixing citations with CJA

   ## Test plan
   - [ ] pytest
   - [ ] tsc -b / vite build
   - [ ] manual smoke test
   EOF
   )"
   ```

   If `main` locally is itself ahead of `origin/main` (e.g. earlier work never got
   pushed), the PR diff will include those commits too — check
   `git log origin/main..<branch-name> --oneline` before opening the PR so the
   PR description matches what's actually in it.

5. **Merge** (this repo merges rather than squashes, per existing history —
   see `git log --oneline` for the "Merge pull request #N" pattern):

   ```bash
   gh pr merge <branch-name> --merge
   ```

   Or merge via the GitHub UI.

6. **Sync local `main`:**
   ```bash
   git checkout main
   git pull origin main
   ```

---

## 2. Railway (backend) deployment

The standard method in this repo is the `deploy.sh` script, which shells out to
`railway up` — this uploads and deploys the current local directory directly,
independent of GitHub:

```bash
./deploy.sh --backend-only
```

Separately, **Railway's GitHub integration also auto-deploys on push to
`origin/main`** (confirmed empirically — a deploy completed within ~30s of a
merge landing on `main`). So merging the PR in step 1 may already trigger a
deploy on its own; running `./deploy.sh --backend-only` afterward is a safe,
idempotent way to force/confirm a deploy rather than waiting on the webhook.

**Manual fallback**, if `deploy.sh` or the Railway CLI link is unavailable:

```bash
railway login       # opens browser → Authorize
railway up
railway logs --tail # watch startup
```

**Verify:**

```bash
curl https://experienceleaguechatbotaws-production.up.railway.app/api/health
```

Expect `{"status": "ok", "chromadb": {"document_count": <N>}}`.

**Environment variables** (set in the Railway dashboard, not in this repo):
`ANTHROPIC_API_KEY`, `DATABASE_URL`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_DEFAULT_REGION`, `BEDROCK_REGION`, `BEDROCK_EMBEDDING_MODEL_ID`,
`AWS_S3_BUCKET`, `ADOBE_CLIENT_ID`, `ADOBE_CLIENT_SECRET`, `ADOBE_ORGANIZATION_ID`,
`SITE_USERNAME`, `SITE_PASSWORD`, `ADMIN_PASSWORD`, `SIMILARITY_THRESHOLD`,
`MAX_RETRIEVAL_RESULTS`, `ENVIRONMENT`, `LOG_LEVEL`, `DEBUG`,
`LANGCHAIN_TRACING_V2`/`LANGCHAIN_API_KEY`/`LANGCHAIN_PROJECT`/`LANGCHAIN_ENDPOINT`
(optional, for LangSmith tracing). No new variables are required for a typical
feature deploy — check `deploy.sh` and `backend/main.py` startup if a change
introduces a new one.

---

## 3. Frontend (Cloudflare Pages) — only if `frontend/` changed

Bundled into the same script:

```bash
./deploy.sh --frontend-only   # or omit the flag to deploy backend + frontend together
```

This builds `frontend/`, copies `dist/` into the blog repo's
`static/tools/rovr/`, commits + pushes the blog repo, builds Hugo, and deploys
via `wrangler pages deploy`. See `deploy.sh` for the exact steps if you need to
run any of them individually.

**Verify:** visit `https://thelearningproject.in/tools/rovr/`.
