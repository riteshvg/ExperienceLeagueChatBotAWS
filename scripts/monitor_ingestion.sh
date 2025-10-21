#!/bin/bash
# Monitor Bedrock Knowledge Base Ingestion Job

KB_ID="NQTC3SRPZX"
DATA_SOURCE_ID="U2ZFV61LQS"
INGESTION_JOB_ID="ORYOGQ4MBK"
REGION="us-east-1"

echo "🔍 Monitoring Ingestion Job: $INGESTION_JOB_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

while true; do
    # Get current status
    STATUS=$(aws bedrock-agent get-ingestion-job \
        --knowledge-base-id $KB_ID \
        --data-source-id $DATA_SOURCE_ID \
        --ingestion-job-id $INGESTION_JOB_ID \
        --region $REGION \
        --output json 2>/dev/null)
    
    if [ $? -ne 0 ]; then
        echo "❌ Error: Could not retrieve ingestion job status"
        exit 1
    fi
    
    # Extract status and statistics
    JOB_STATUS=$(echo $STATUS | jq -r '.ingestionJob.status')
    SCANNED=$(echo $STATUS | jq -r '.ingestionJob.statistics.numberOfDocumentsScanned')
    NEW=$(echo $STATUS | jq -r '.ingestionJob.statistics.numberOfNewDocumentsIndexed')
    MODIFIED=$(echo $STATUS | jq -r '.ingestionJob.statistics.numberOfModifiedDocumentsIndexed')
    FAILED=$(echo $STATUS | jq -r '.ingestionJob.statistics.numberOfDocumentsFailed')
    UPDATED_AT=$(echo $STATUS | jq -r '.ingestionJob.updatedAt')
    
    # Clear previous line and show current status
    echo -ne "\r\033[K"
    echo -n "📊 Status: $JOB_STATUS | Scanned: $SCANNED | New: $NEW | Modified: $MODIFIED | Failed: $FAILED | Updated: $UPDATED_AT"
    
    # Check if job is complete
    if [ "$JOB_STATUS" == "COMPLETE" ]; then
        echo ""
        echo ""
        echo "✅ ✅ ✅ INGESTION COMPLETED SUCCESSFULLY! ✅ ✅ ✅"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📊 Final Statistics:"
        echo "   • Documents Scanned: $SCANNED"
        echo "   • New Documents Indexed: $NEW"
        echo "   • Modified Documents Indexed: $MODIFIED"
        echo "   • Failed Documents: $FAILED"
        echo ""
        echo "🎉 Your chatbot now has the latest documentation!"
        break
    elif [ "$JOB_STATUS" == "FAILED" ]; then
        echo ""
        echo ""
        echo "❌ ❌ ❌ INGESTION FAILED! ❌ ❌ ❌"
        echo "Check the logs for more details."
        break
    fi
    
    # Wait 10 seconds before next check
    sleep 10
done

