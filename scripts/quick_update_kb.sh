#!/bin/bash
# Quick script to update Knowledge Base

echo "🚀 Updating Knowledge Base with Latest Experience League Articles"
echo "=================================================================="
echo ""

cd "$(dirname "$0")/.."
source venv/bin/activate

echo "📚 Starting update process..."
echo "   This will:"
echo "   1. Fetch latest articles from Experience League"
echo "   2. Upload to S3 bucket"
echo "   3. Trigger Knowledge Base sync"
echo ""
echo "⏰ Estimated time: 30-60 minutes"
echo ""

python scripts/update_knowledge_base_latest.py

echo ""
echo "✅ Update process completed!"
echo ""
echo "📋 Next steps:"
echo "   - Check ingestion status: python scripts/check_ingestion_status.py --kb-id NQTC3SRPZX --data-source-id I3Q6GSOOLR"
echo "   - Test queries to verify new content is available"

