# 📊 Knowledge Base Update Monitoring Guide

## Quick Start

### Start Monitoring (Interactive)

```bash
cd /Users/ritesh/ExperienceLeagueChatBotAWS
./scripts/start_monitoring.sh
```

Or use the Python script directly:

```bash
source venv/bin/activate
python scripts/monitor_kb_update.py
```

### Check Status Once

```bash
python scripts/monitor_kb_update.py --once
```

## Monitoring Features

The monitoring script tracks:

1. **Update Script Status**
   - Whether the update script is running
   - Process information (PID, CPU, memory, runtime)

2. **S3 Upload Progress**
   - Total files uploaded
   - Total size
   - Recent file uploads (last hour)

3. **Knowledge Base Data Sources**
   - Data source status
   - Latest ingestion job information
   - Document counts

4. **Active Ingestion Jobs**
   - Real-time job status
   - Progress indicators
   - Document processing statistics

## Usage Options

### Basic Monitoring (30 second intervals)

```bash
python scripts/monitor_kb_update.py
```

### Custom Check Interval

```bash
# Check every 10 seconds
python scripts/monitor_kb_update.py --interval 10

# Check every 60 seconds
python scripts/monitor_kb_update.py --interval 60
```

### Limited Duration Monitoring

```bash
# Monitor for 60 minutes maximum
python scripts/monitor_kb_update.py --max-duration 60
```

### One-Time Status Check

```bash
# Check status once and exit
python scripts/monitor_kb_update.py --once
```

## What You'll See

The monitor displays:

```
================================================================================
📊 Knowledge Base Update Monitor
⏰ Elapsed Time: 0:15:32
================================================================================

🔄 Update Script Status:
   ✅ Script is running
   📋 PID: 11792
   💻 CPU: 0.3%
   🧠 Memory: 0.4%
   ⏱️  Runtime: 0:14.03

📦 S3 Upload Status:
   📄 Total Files: 1,234
   💾 Total Size: 245.67 MB
   🆕 Recent Files (last hour): 45
   📝 Recent uploads:
      - README.md (2.3 KB)
      - guide.md (15.6 KB)

📚 Knowledge Base Data Sources:
   📦 knowledge-base-quick-start-v22fc-data-source
      Status: AVAILABLE
      Latest Job: COMPLETE (started 186 days ago)
      Documents: 1346 scanned, 0 indexed

🔄 Active Ingestion Jobs:
   ✅ knowledge-base-quick-start-v22fc-data-source
      Job ID: ABC123XYZ
      Status: IN_PROGRESS
      Progress: 500 scanned, 450 indexed
```

## Monitoring in Background

### Using Screen

```bash
# Start a screen session
screen -S kb-monitor

# Run monitor
./scripts/start_monitoring.sh

# Detach: Ctrl+A then D
# Reattach: screen -r kb-monitor
```

### Using nohup

```bash
# Run in background with output to file
nohup python scripts/monitor_kb_update.py --interval 60 > monitor.log 2>&1 &

# Check status
tail -f monitor.log
```

### Using tmux

```bash
# Start tmux session
tmux new -s kb-monitor

# Run monitor
./scripts/start_monitoring.sh

# Detach: Ctrl+B then D
# Reattach: tmux attach -t kb-monitor
```

## Automated Monitoring Script

Create a cron job to check status periodically:

```bash
# Edit crontab
crontab -e

# Add this line to check every 5 minutes and log to file
*/5 * * * * cd /path/to/project && source venv/bin/activate && python scripts/monitor_kb_update.py --once >> /path/to/monitor.log 2>&1
```

## Status Indicators

### ✅ Success Indicators

- Update script is running
- Files are being uploaded to S3
- Ingestion jobs are active
- Document counts are increasing

### ⚠️ Warning Indicators

- Update script stopped unexpectedly
- No recent file uploads
- Ingestion jobs stuck in STARTING
- No active ingestion jobs after script completion

### ❌ Error Indicators

- Script errors
- S3 access errors
- Knowledge Base connection errors
- Ingestion job failures

## Troubleshooting

### Monitor Not Showing Updates

1. **Check AWS credentials**
   ```bash
   aws sts get-caller-identity
   ```

2. **Verify Knowledge Base ID**
   ```bash
   python -c "from config.settings import Settings; print(Settings().bedrock_knowledge_base_id)"
   ```

3. **Check S3 bucket access**
   ```bash
   aws s3 ls s3://experienceleaguechatbot/adobe-docs/ --recursive | head -10
   ```

### Monitor Shows Errors

1. **Check Python dependencies**
   ```bash
   pip install boto3
   ```

2. **Verify environment variables**
   ```bash
   python scripts/get_aws_env_vars.py --source cli
   ```

3. **Check AWS permissions**
   - Bedrock Agent permissions
   - S3 read permissions
   - CloudWatch logs (if enabled)

## Integration with Alerts

### Email Notifications

Add email alerts to the monitor script:

```python
import smtplib
from email.mime.text import MIMEText

def send_alert(message):
    # Configure your email settings
    msg = MIMEText(message)
    msg['Subject'] = 'KB Update Status'
    msg['From'] = 'monitor@example.com'
    msg['To'] = 'admin@example.com'
    
    # Send email
    # ... email sending code ...
```

### Slack Notifications

```python
import requests

def send_slack_alert(message):
    webhook_url = "YOUR_SLACK_WEBHOOK_URL"
    payload = {"text": message}
    requests.post(webhook_url, json=payload)
```

## Best Practices

1. **Monitor Regularly**: Check status every 30-60 seconds during updates
2. **Log Everything**: Save monitor output for troubleshooting
3. **Set Alerts**: Configure notifications for completion or errors
4. **Review Logs**: Check logs after updates complete
5. **Verify Results**: Always verify ingestion completed successfully

## Next Steps After Monitoring

Once monitoring shows completion:

1. **Verify Update**
   ```bash
   python scripts/validate_knowledge_base.py
   ```

2. **Test Queries**
   ```bash
   python scripts/test_knowledge_base_questions.py
   ```

3. **Check Document Counts**
   - Compare before/after document counts
   - Verify new content is searchable

4. **Review Costs**
   - Check AWS costs for the update
   - Review ingestion job statistics

---

**Happy Monitoring! 📊**

