# 📊 Monitoring Files Reference

Complete list of all monitoring-related files in the project.

## 🎯 Knowledge Base Update Monitoring

### Primary Monitoring Script
**`scripts/monitor_kb_update.py`**
- **Purpose**: Main monitoring script for Knowledge Base updates
- **Features**:
  - Monitors update script process status
  - Tracks S3 upload progress
  - Shows ingestion job status
  - Displays real-time progress
- **Usage**:
  ```bash
  python scripts/monitor_kb_update.py --once          # Check once
  python scripts/monitor_kb_update.py --interval 30  # Continuous monitoring
  ```

### Quick Start Script
**`scripts/start_monitoring.sh`**
- **Purpose**: Convenience script to start monitoring
- **Usage**:
  ```bash
  ./scripts/start_monitoring.sh
  ```

### Supporting Scripts

**`scripts/check_ingestion_status.py`**
- **Purpose**: Check status of Knowledge Base ingestion jobs
- **Usage**:
  ```bash
  python scripts/check_ingestion_status.py \
    --kb-id NQTC3SRPZX \
    --data-source-id I3Q6GSOOLR \
    --monitor
  ```

**`scripts/validate_knowledge_base.py`**
- **Purpose**: Validate Knowledge Base setup and functionality
- **Usage**:
  ```bash
  python scripts/validate_knowledge_base.py
  ```

**`check_kb_status.sh`**
- **Purpose**: Quick status check script
- **Usage**:
  ```bash
  ./check_kb_status.sh
  ```

## 📚 Documentation Files

### Monitoring Guide
**`MONITORING_GUIDE.md`**
- Complete guide on how to use monitoring
- Usage examples
- Troubleshooting tips
- Best practices

### Monitoring Status
**`MONITORING_STATUS.md`**
- Current monitoring status
- Quick reference for status checks

## 🔍 Other Monitoring Files

### Performance Monitoring
**`src/performance/performance_monitor.py`**
- Application performance monitoring
- Response time tracking
- Resource usage monitoring

### Security Monitoring
**`src/security/security_monitor.py`**
- Security event monitoring
- Access logging
- Threat detection

## 📋 File Structure

```
ExperienceLeagueChatBotAWS/
├── scripts/
│   ├── monitor_kb_update.py          # Main KB update monitor
│   ├── start_monitoring.sh            # Quick start script
│   ├── check_ingestion_status.py      # Ingestion job status
│   └── validate_knowledge_base.py     # KB validation
│
├── MONITORING_GUIDE.md               # Complete monitoring guide
├── MONITORING_STATUS.md               # Current status reference
├── MONITORING_FILES.md                # This file
│
├── check_kb_status.sh                 # Quick status check
│
└── src/
    ├── performance/
    │   └── performance_monitor.py     # Performance monitoring
    └── security/
        └── security_monitor.py        # Security monitoring
```

## 🚀 Quick Reference

### Check Status Once
```bash
python scripts/monitor_kb_update.py --once
```

### Start Continuous Monitoring
```bash
./scripts/start_monitoring.sh
# OR
python scripts/monitor_kb_update.py --interval 30
```

### Check Ingestion Jobs
```bash
python scripts/check_ingestion_status.py \
  --kb-id NQTC3SRPZX \
  --data-source-id I3Q6GSOOLR
```

### Validate Knowledge Base
```bash
python scripts/validate_knowledge_base.py
```

### Quick Status Check
```bash
./check_kb_status.sh
```

## 📊 What Each File Monitors

| File | Monitors | Frequency |
|------|----------|-----------|
| `monitor_kb_update.py` | Update script, S3 uploads, ingestion jobs | Configurable (default: 30s) |
| `check_ingestion_status.py` | Ingestion job status only | On-demand |
| `validate_knowledge_base.py` | KB health and functionality | On-demand |
| `check_kb_status.sh` | Quick overall status | On-demand |
| `performance_monitor.py` | Application performance | Continuous |
| `security_monitor.py` | Security events | Continuous |

## 🎯 Primary Monitoring Workflow

1. **Start Update**: `python scripts/update_knowledge_base_latest.py`
2. **Start Monitoring**: `./scripts/start_monitoring.sh`
3. **Check Status**: Monitor shows real-time progress
4. **Verify Completion**: `python scripts/validate_knowledge_base.py`
5. **Test**: Use test questions to verify new content

## 💡 Tips

- Use `--once` flag for quick status checks
- Use `--interval` to adjust check frequency
- Use `--max-duration` to limit monitoring time
- Check logs if monitoring shows errors
- Use `check_kb_status.sh` for quick overview

---

**All monitoring files are ready to use! 📊**

