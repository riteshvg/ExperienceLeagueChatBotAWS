#!/bin/bash
# Quick script to check Knowledge Base update status

cd "$(dirname "$0")"
source venv/bin/activate

echo "📊 Knowledge Base Update Status Check"
echo "======================================"
echo ""

# Check if update script is running
if ps aux | grep -v grep | grep -q "update_knowledge_base_latest"; then
    echo "✅ Update script is currently running"
    echo ""
else
    echo "ℹ️  Update script is not running"
    echo ""
fi

# Check Knowledge Base status
python -c "
import boto3
from config.settings import Settings
from datetime import datetime

settings = Settings()
kb_id = settings.bedrock_knowledge_base_id
bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')

print('📚 Knowledge Base Status:')
print(f'   ID: {kb_id}')
print()

# Get data sources
response = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
for ds in response.get('dataSourceSummaries', []):
    print(f'📦 Data Source: {ds[\"name\"]}')
    print(f'   Status: {ds[\"status\"]}')
    
    # Get latest ingestion job
    try:
        jobs = bedrock_agent.list_ingestion_jobs(
            knowledgeBaseId=kb_id,
            dataSourceId=ds['dataSourceId'],
            maxResults=1
        )
        
        if jobs.get('ingestionJobSummaries'):
            job = jobs['ingestionJobSummaries'][0]
            print(f'   Latest Job: {job[\"status\"]}')
            print(f'   Started: {job[\"startedAt\"]}')
            
            if 'statistics' in job:
                stats = job['statistics']
                print(f'   Documents: {stats.get(\"numberOfDocumentsScanned\", 0)} scanned, {stats.get(\"numberOfDocumentsIndexed\", 0)} indexed')
        else:
            print('   No ingestion jobs found')
    except Exception as e:
        print(f'   Error: {e}')
    
    print()
"

echo ""
echo "💡 To trigger a new sync after uploads complete:"
echo "   python scripts/update_knowledge_base_latest.py"
echo ""
echo "💡 To check ingestion status:"
echo "   python scripts/check_ingestion_status.py --kb-id NQTC3SRPZX --data-source-id I3Q6GSOOLR"

