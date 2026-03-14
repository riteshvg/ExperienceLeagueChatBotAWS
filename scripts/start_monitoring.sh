#!/bin/bash
# Start Knowledge Base Update Monitoring

cd "$(dirname "$0")/.."
source venv/bin/activate

echo "🚀 Starting Knowledge Base Update Monitor"
echo "=========================================="
echo ""
echo "This will monitor:"
echo "  • Update script progress"
echo "  • S3 upload status"
echo "  • Ingestion job progress"
echo "  • Overall completion status"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

python scripts/monitor_kb_update.py --interval 30

