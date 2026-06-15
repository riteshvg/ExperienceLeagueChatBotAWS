#!/bin/bash
# Deploy Rovr — backend, frontend, and/or GitHub Actions data refresh.
#
# Usage:
#   ./deploy.sh                  — deploy backend (Railway) + frontend (Cloudflare)
#   ./deploy.sh --backend-only   — Railway only, skip frontend build/deploy
#   ./deploy.sh --frontend-only  — skip Railway, build + deploy frontend only
#   ./deploy.sh --actions        — trigger GitHub Actions data-refresh workflow only
#   ./deploy.sh --actions --force — trigger with force=true
#
set -euo pipefail

CHATBOT_ROOT="/Users/riteshg/Documents/Learnings/experienceleaguechatbot"
BLOG_ROOT="/Users/riteshg/Documents/Learnings/tlp/tlp"
STATIC_DIR="$BLOG_ROOT/static/tools/rovr"

BACKEND_ONLY=false
FRONTEND_ONLY=false
ACTIONS_ONLY=false
FORCE=false

for arg in "$@"; do
  case "$arg" in
    --backend-only)  BACKEND_ONLY=true ;;
    --frontend-only) FRONTEND_ONLY=true ;;
    --actions)       ACTIONS_ONLY=true ;;
    --force)         FORCE=true ;;
  esac
done

# ── GitHub Actions data-refresh trigger ───────────────────────────────────────
if [ "$ACTIONS_ONLY" = true ]; then
  echo ""
  echo "══════════════════════════════════════════════"
  echo "  Rovr — Trigger GitHub Actions Data Refresh"
  [ "$FORCE" = true ] && echo "  (force full sync)"
  echo "══════════════════════════════════════════════"

  TOKEN="${GITHUB_TOKEN:-}"
  if [ -z "$TOKEN" ]; then
    echo "  ✗ GITHUB_TOKEN is not set. Export it before running:" >&2
    echo "    export GITHUB_TOKEN=ghp_..." >&2
    exit 1
  fi

  FORCE_INPUT="false"
  [ "$FORCE" = true ] && FORCE_INPUT="true"

  echo ""
  echo "▶ Dispatching refresh-docs.yml workflow…"
  HTTP_STATUS=$(curl -s -o /tmp/gh_dispatch_resp.json -w "%{http_code}" \
    -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    -H "Content-Type: application/json" \
    -d "{\"ref\":\"main\",\"inputs\":{\"force\":\"$FORCE_INPUT\"}}" \
    "https://api.github.com/repos/riteshvg/ExperienceLeagueChatBotAWS/actions/workflows/refresh-docs.yml/dispatches")

  if [ "$HTTP_STATUS" = "204" ]; then
    echo "  ✓ Workflow dispatched (force=$FORCE_INPUT)"
    echo "  View progress: https://github.com/riteshvg/ExperienceLeagueChatBotAWS/actions"
  else
    echo "  ✗ GitHub API returned HTTP $HTTP_STATUS" >&2
    cat /tmp/gh_dispatch_resp.json >&2
    exit 1
  fi

  echo ""
  echo "══════════════════════════════════════════════"
  echo "  Done ✓"
  echo "══════════════════════════════════════════════"
  echo ""
  exit 0
fi

# ── Normal deploy: backend and/or frontend ─────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  Rovr — Deploy"
if [ "$BACKEND_ONLY" = true ]; then
  echo "  (backend only — frontend skipped)"
elif [ "$FRONTEND_ONLY" = true ]; then
  echo "  (frontend only — Railway skipped)"
fi
echo "══════════════════════════════════════════════"

# ── Step 1: Railway (backend) ──────────────────────────────────────────────────
if [ "$FRONTEND_ONLY" = false ]; then
  echo ""
  echo "▶ [1/4] Deploying backend → Railway…"
  echo "  (Press Ctrl+C once 'Deploy complete' appears to continue)"
  cd "$CHATBOT_ROOT"
  set +e
  railway up
  RAILWAY_EXIT=$?
  set -e
  if [ $RAILWAY_EXIT -ne 0 ] && [ $RAILWAY_EXIT -ne 130 ]; then
    echo "  ✗ Railway deploy failed (exit $RAILWAY_EXIT)" >&2
    exit $RAILWAY_EXIT
  fi
  echo "  ✓ Railway deploy complete"
else
  echo ""
  echo "  — [1/4] Railway skipped"
fi

# ── Steps 2-4: Frontend build + Cloudflare deploy ─────────────────────────────
if [ "$BACKEND_ONLY" = false ]; then
  # Step 2: Build React frontend
  echo ""
  echo "▶ [2/4] Building React frontend…"
  cd "$CHATBOT_ROOT/frontend"
  npm run build
  echo "  ✓ Build complete → frontend/dist/"

  # Step 3: Copy dist into Hugo static folder (clean replace — no stale assets)
  echo ""
  echo "▶ [3/4] Copying dist → Hugo static…"
  rm -rf "$STATIC_DIR"
  mkdir -p "$STATIC_DIR"
  cp -r "$CHATBOT_ROOT/frontend/dist/." "$STATIC_DIR/"
  # Cloudflare Pages 200 rewrites for sub-paths are unreliable.
  # Copy index.html into each SPA route directory so Cloudflare finds a real file.
  for route in callback login admin; do
    mkdir -p "$STATIC_DIR/$route"
    cp "$STATIC_DIR/index.html" "$STATIC_DIR/$route/index.html"
  done
  echo "  ✓ Copied to $STATIC_DIR"

  # Step 4: Build Hugo, commit ALL changes in the blog repo, deploy to Cloudflare Pages
  echo ""
  echo "▶ [4/4] Building Hugo site and deploying → Cloudflare Pages…"
  cd "$BLOG_ROOT"
  # Run Hugo so public/ is fully generated
  hugo --quiet
  # Stage everything that changed — static source, generated public/, content edits.
  # Using -A on specific subtrees avoids accidentally staging unrelated files
  # while still catching deletions (old hashed assets removed by rm -rf above).
  git add -A static/tools/rovr public/tools/rovr
  git add static/_redirects public/_redirects
  git add content/tools/
  if ! git diff --cached --quiet; then
    git commit -m "chore: update chatbot build $(date '+%Y-%m-%d %H:%M')"
    git push origin main
    echo "  ✓ Blog repo pushed → Cloudflare Pages git build will trigger"
  else
    echo "  — No frontend changes to commit"
  fi
  npx wrangler pages deploy "$BLOG_ROOT/public/"
  echo "  ✓ Wrangler direct deploy complete"
else
  echo ""
  echo "  — [2/4] Frontend build skipped"
  echo "  — [3/4] Hugo copy skipped"
  echo "  — [4/4] Cloudflare deploy skipped"
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  All done ✓"
if [ "$FRONTEND_ONLY" = false ]; then
  echo "  Backend  : https://experienceleaguechatbotaws-production.up.railway.app/api/health"
fi
if [ "$BACKEND_ONLY" = false ]; then
  echo "  Frontend : https://thelearningproject.in/tools/rovr"
fi
echo "══════════════════════════════════════════════"
echo ""
