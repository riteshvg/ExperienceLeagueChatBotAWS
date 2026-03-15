# 📚 Update Knowledge Base with Latest Experience League Articles

## Overview

This guide explains how to update your AWS Bedrock Knowledge Base with the latest articles from Adobe Experience League.

## Quick Update

Run the update script:

```bash
cd /Users/ritesh/ExperienceLeagueChatBotAWS
source venv/bin/activate
python scripts/update_knowledge_base_latest.py
```

## What the Script Does

1. **Fetches Latest Articles**
   - Clones/updates GitHub repositories from Adobe Experience League
   - Sources include:
     - Adobe Analytics documentation
     - Customer Journey Analytics documentation
     - Analytics APIs documentation
     - Adobe Experience Platform documentation

2. **Uploads to S3**
   - Uploads all documentation files to your S3 bucket
   - Organizes files by source in `adobe-docs/` prefix
   - Skips non-document files (config, git files, etc.)

3. **Triggers Knowledge Base Sync**
   - Starts an ingestion job to process new/updated documents
   - Bedrock automatically indexes the new content

4. **Monitors Progress** (optional)
   - Tracks ingestion job status
   - Shows document counts and progress

## Script Options

### Basic Update (No Monitoring)

```bash
python scripts/update_knowledge_base_latest.py --no-monitor
```

This will:
- Update all documentation
- Start sync job
- Exit immediately (you can check status later)

### Update with Monitoring

```bash
python scripts/update_knowledge_base_latest.py
```

This will:
- Update all documentation
- Start sync job
- Monitor progress until completion (up to 60 minutes)

### Custom Wait Time

```bash
python scripts/update_knowledge_base_latest.py --max-wait 120
```

Monitor for up to 120 minutes instead of default 60.

## Check Ingestion Status

After starting the update, you can check status:

```bash
# Get your data source ID first
python scripts/list_knowledge_bases.py

# Then check status
python scripts/check_ingestion_status.py \
  --kb-id NQTC3SRPZX \
  --data-source-id I3Q6GSOOLR \
  --monitor
```

## Current Configuration

- **Knowledge Base ID**: `NQTC3SRPZX`
- **S3 Bucket**: `experienceleaguechatbot`
- **Data Source ID**: `I3Q6GSOOLR` (primary)
- **S3 Prefix**: `adobe-docs/`

## What Gets Updated

The script updates documentation from these sources:

1. **Adobe Analytics** (`analytics.en`)
   - User guides
   - Implementation guides
   - Best practices
   - Troubleshooting

2. **Customer Journey Analytics** (`customer-journey-analytics-learn.en`)
   - CJA user documentation
   - Cross-channel analytics guides
   - Journey analysis guides

3. **Analytics APIs** (`analytics-2.0-apis`)
   - API reference
   - Code examples
   - Integration guides

4. **Adobe Experience Platform** (`experience-platform.en`)
   - AEP documentation
   - Data ingestion guides
   - Schema documentation

## Expected Duration

- **Document Download**: 5-15 minutes (depends on repo sizes)
- **S3 Upload**: 10-30 minutes (depends on file count)
- **Knowledge Base Ingestion**: 15-60 minutes (depends on document count)

**Total**: Approximately 30-105 minutes for complete update

## Troubleshooting

### Issue: "S3 bucket name not found"

**Solution**: The script will automatically find the bucket from your Knowledge Base. If it fails:
1. Check your `.env` file has `BEDROCK_KNOWLEDGE_BASE_ID` set
2. Or manually set `AWS_S3_BUCKET=experienceleaguechatbot` in `.env`

### Issue: "Git clone failed"

**Solution**: 
- Check internet connection
- GitHub may be rate-limiting - wait a few minutes and retry
- Some repos may be private - ensure you have access

### Issue: "Ingestion job already running"

**Solution**: 
- Wait for current job to complete
- Or check status and cancel if needed in AWS console
- The script will skip starting a new job if one is already running

### Issue: "Upload taking too long"

**Solution**:
- This is normal for large documentation sets
- The script shows progress every 50 files
- You can stop and resume - it will update existing repos

## Manual Update Steps

If you prefer to update manually:

1. **Update Documentation Repos**
   ```bash
   # The script does this automatically, but you can do it manually:
   git clone https://github.com/AdobeDocs/analytics.en.git
   # Or update existing: git pull
   ```

2. **Upload to S3**
   ```bash
   aws s3 sync ./analytics.en s3://experienceleaguechatbot/adobe-docs/adobe-analytics/
   ```

3. **Trigger Sync in AWS Console**
   - Go to Bedrock → Knowledge Bases
   - Select your Knowledge Base
   - Go to Data Sources
   - Click "Sync" button

## Verification

After update completes, verify it worked:

```bash
# Test retrieval
python scripts/validate_knowledge_base.py

# Or test with a query
python scripts/test_knowledge_base_questions.py
```

## Schedule Regular Updates

To keep your Knowledge Base up-to-date, you can:

1. **Run weekly/monthly**:
   ```bash
   # Add to crontab (runs every Sunday at 2 AM)
   0 2 * * 0 cd /path/to/project && source venv/bin/activate && python scripts/update_knowledge_base_latest.py --no-monitor
   ```

2. **Use AWS EventBridge** to trigger the script automatically

3. **Set up GitHub Actions** to trigger on repo updates

## Next Steps

After updating:
1. ✅ Verify ingestion completed successfully
2. ✅ Test queries to ensure new content is available
3. ✅ Check document counts in AWS console
4. ✅ Monitor for any errors or warnings

