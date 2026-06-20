#!/usr/bin/env bash
# Controlled production Chroma reload after GHA uploads chroma_db.tar.gz to S3.
#
# Safe pattern (avoids the repeated 0-chunk / maintenance loop):
#   1. GHA refresh-docs completes and uploads S3
#   2. Run this script ONCE — single redeploy with FORCE restore
#   3. Poll until /api/health is ok
#   4. Unset flags WITHOUT redeploy (next code deploy reuses /app/chroma_db volume)
#
# Usage:
#   ./scripts/railway_chroma_reload.sh
#   ./scripts/railway_chroma_reload.sh --expected-chunks 41005
#   ./scripts/railway_chroma_reload.sh --dry-run
#
# Requires: railway CLI linked, curl, aws/gh optional for chunk hint

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HEALTH_URL="${ROVR_HEALTH_URL:-https://experienceleaguechatbotaws-production.up.railway.app/api/health}"
EXPECTED_CHUNKS="${EXPECTED_CHUNKS:-0}"
DRY_RUN=false
POLL_SECS=15
MAX_POLLS=40

while [[ $# -gt 0 ]]; do
  case "$1" in
    --expected-chunks) EXPECTED_CHUNKS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --health-url) HEALTH_URL="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ "$EXPECTED_CHUNKS" -eq 0 ]] && command -v aws >/dev/null 2>&1; then
  hint="$(aws s3 cp "s3://experienceleaguechatbot/state/chroma_last_refreshed.json" - 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('chunks',0))" 2>/dev/null || echo 0)"
  if [[ -n "$hint" && "$hint" -gt 0 ]]; then
    EXPECTED_CHUNKS="$hint"
    echo "Expected chunks from S3 state: $EXPECTED_CHUNKS"
  fi
fi

run_railway() {
  if $DRY_RUN; then
    echo "[dry-run] railway $*"
  else
    railway "$@"
  fi
}

echo "=== Rovr production Chroma reload ==="
echo "Health URL: $HEALTH_URL"

echo ""
echo "Step 1: Use /tmp for Chroma (Railway volume mount breaks SQLite restore)"
run_railway variables --set "CHROMA_PERSIST_DIR=/tmp/chroma_db"

echo ""
echo "Step 2: Enable maintenance + FORCE restore (single redeploy)"
STARTED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
run_railway variables \
  --set "KNOWLEDGE_BANK_UPDATING=true" \
  --set "KNOWLEDGE_BANK_UPDATE_STARTED_AT=$STARTED" \
  --set "FORCE_CHROMA_RESTORE=true" \
  --set "CHROMA_RESTORE_ETA_MINUTES=4"
run_railway redeploy -y

echo ""
echo "Step 3: Poll /api/health until status=ok"
for i in $(seq 1 "$MAX_POLLS"); do
  resp="$(curl -s "$HEALTH_URL" || echo '{}')"
  status="$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")"
  count="$(echo "$resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('chromadb',{}).get('document_count',0))" 2>/dev/null || echo 0)"
  echo "  [$i/$MAX_POLLS] status=$status chunks=$count"
  if [[ "$status" == "ok" && "$count" -gt 0 ]]; then
    if [[ "$EXPECTED_CHUNKS" -gt 0 && "$count" -lt "$EXPECTED_CHUNKS" ]]; then
      echo "  WARN: count $count < expected $EXPECTED_CHUNKS — continuing to wait"
    else
      echo "  Index live with $count chunks"
      break
    fi
  fi
  # During maintenance window status stays "updating" even when index is loaded.
  if [[ "$status" == "updating" && "$count" -ge "$EXPECTED_CHUNKS" && "$EXPECTED_CHUNKS" -gt 0 ]]; then
    echo "  Index loaded ($count chunks) under maintenance — proceeding to unset flags"
    break
  fi
  if [[ "$i" -eq "$MAX_POLLS" ]]; then
    echo "ERROR: Timed out waiting for healthy index" >&2
    exit 1
  fi
  sleep "$POLL_SECS"
done

echo ""
echo "Step 4: Unset flags WITHOUT redeploy (critical — do not railway redeploy here)"
run_railway variables \
  --set "FORCE_CHROMA_RESTORE=false" \
  --set "KNOWLEDGE_BANK_UPDATING=false" \
  --set "KNOWLEDGE_BANK_UPDATE_STARTED_AT="

echo ""
echo "=== Done ==="
echo "Verify chat: curl -s ${HEALTH_URL%/health}/ping"
echo "Future git pushes redeploy code only — Chroma lives in /tmp until volume restore is verified."
