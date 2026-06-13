#!/bin/bash
# Deploy backend to Railway and frontend to Cloudflare Pages.
# Run from anywhere: ./deploy.sh
set -euo pipefail

CHATBOT_ROOT="/Users/riteshg/Documents/Learnings/experienceleaguechatbot"
BLOG_ROOT="/Users/riteshg/Documents/Learnings/tlp/tlp"
STATIC_DIR="$BLOG_ROOT/static/tools/exlunofficialchatbot"

echo ""
echo "══════════════════════════════════════════════"
echo "  Experience League Chatbot — Deploy"
echo "══════════════════════════════════════════════"

# ── 1. Railway (backend) ───────────────────────────────────────────────────
echo ""
echo "▶ [1/5] Deploying backend → Railway…"
cd "$CHATBOT_ROOT"
railway up
echo "  ✓ Railway deploy triggered"

# ── 2. Build React frontend ────────────────────────────────────────────────
echo ""
echo "▶ [2/5] Building React frontend…"
cd "$CHATBOT_ROOT/frontend"
npm run build
echo "  ✓ Build complete → frontend/dist/"

# ── 3. Copy dist into Hugo static folder ──────────────────────────────────
echo ""
echo "▶ [3/5] Copying dist → Hugo static…"
mkdir -p "$STATIC_DIR"
cp -r "$CHATBOT_ROOT/frontend/dist/." "$STATIC_DIR/"
echo "  ✓ Copied to $STATIC_DIR"

# ── 4. Commit + push Hugo blog repo ───────────────────────────────────────
echo ""
echo "▶ [4/5] Committing blog repo…"
cd "$BLOG_ROOT"
git add static/tools/exlunofficialchatbot
if ! git diff --cached --quiet; then
  git commit -m "chore: update chatbot build $(date '+%Y-%m-%d')"
  git push origin main
  echo "  ✓ Blog repo pushed"
else
  echo "  — No frontend changes to commit"
fi

# ── 5. Hugo build + Cloudflare Pages deploy ────────────────────────────────
echo ""
echo "▶ [5/5] Building Hugo site and deploying → Cloudflare Pages…"
cd "$BLOG_ROOT"
hugo
wrangler pages deploy "$BLOG_ROOT/public/"
echo "  ✓ Cloudflare Pages deploy complete"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════"
echo "  All done ✓"
echo "  Frontend : https://thelearningproject.in/tools/exlunofficialchatbot"
echo "  Backend  : https://experienceleaguechatbotaws-production.up.railway.app/api/health"
echo "══════════════════════════════════════════════"
echo ""
