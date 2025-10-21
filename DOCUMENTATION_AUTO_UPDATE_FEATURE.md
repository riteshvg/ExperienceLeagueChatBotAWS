# Documentation Auto-Update Feature

## Implementation Date: October 20, 2025

### 🎯 Objective
Create an automated documentation update pipeline in the Administrator panel that:
1. Monitors documentation freshness
2. Compares local docs with GitHub repos
3. Auto-updates when docs are >7 days old
4. Provides a comprehensive dashboard

---

## 📊 Features Implemented

### 1. **Documentation Manager** (`src/admin/documentation_manager.py`)

**Purpose**: Core logic for documentation management

**Key Functions**:
- `check_documentation_freshness()`: Check all docs for staleness
- `trigger_documentation_update()`: Update specific documentation source
- `trigger_ingestion_job()`: Start ingestion after upload
- `auto_update_stale_docs()`: Auto-update all stale docs
- `get_documentation_stats()`: Get overall statistics

**Documentation Sources**:
```python
DOC_SOURCES = {
    "adobe-experience-platform": {
        "update_frequency_days": 7,  # Weekly
        "display_name": "Adobe Experience Platform"
    },
    "adobe-analytics": {
        "update_frequency_days": 30,  # Monthly
        "display_name": "Adobe Analytics"
    },
    "customer-journey-analytics": {
        "update_frequency_days": 30,  # Monthly
        "display_name": "Customer Journey Analytics"
    },
    "analytics-apis": {
        "update_frequency_days": 30,  # Monthly
        "display_name": "Analytics 2.0 APIs"
    }
}
```

---

### 2. **Documentation Dashboard** (`src/admin/documentation_dashboard.py`)

**Purpose**: Streamlit UI for documentation management

**Key Components**:
- Status cards with color coding (🟢 current, 🟡 stale, 🔴 error)
- Detailed status table
- Auto-update recommendations
- Update buttons for individual sources
- Documentation statistics

**Dashboard Sections**:
1. **Status Cards**: Visual overview of each documentation source
2. **Detailed Table**: Comprehensive status information
3. **Recommendations**: Suggestions for updates
4. **Statistics**: Overall documentation metrics

---

### 3. **Admin Panel Integration** (`src/admin/admin_panel.py`)

**Changes**:
- Added new tab: "📚 Documentation Management"
- Integrated DocumentationManager
- Integrated DocumentationDashboard
- Error handling for dependencies

---

## 🔧 How It Works

### **Step 1: Check Freshness**
```python
freshness_status = doc_manager.check_documentation_freshness()
```

For each documentation source:
1. Get last commit date from GitHub repo
2. Get last upload date from S3
3. Calculate days behind
4. Compare with update frequency threshold
5. Mark as "needs_update" if > threshold

### **Step 2: Display Status**
```python
doc_dashboard.render_dashboard()
```

Shows:
- 🟢 Green: Current (within threshold)
- 🟡 Yellow: Stale (needs update)
- 🔴 Red: Error (can't determine status)

### **Step 3: Auto-Update**
```python
results = doc_manager.auto_update_stale_docs()
```

For each stale source:
1. Clone/pull latest from GitHub
2. Upload to S3
3. Trigger ingestion job
4. Return success/failure status

---

## 📋 Dashboard Features

### **Status Cards**
- Visual color-coded cards
- Days behind indicator
- Last update timestamp
- Quick update button

### **Detailed Table**
| Column | Description |
|--------|-------------|
| Documentation Source | Name of the documentation |
| Status | Current/Stale/Error |
| GitHub Last Commit | Latest commit from GitHub |
| S3 Last Upload | Last upload to S3 |
| Days Behind | Days since last update |
| Update Frequency | Recommended update frequency |
| Needs Update | Yes/No |

### **Auto-Update Recommendations**
- Lists all stale documentation sources
- Shows days behind for each
- Provides "Auto-Update All Stale" button

### **Statistics**
- Total files count
- Total size in MB
- Knowledge Base ID
- S3 bucket name
- AWS region

---

## 🚀 Usage

### **Access the Dashboard**

1. **Navigate to Admin Panel**
   - Click "Admin Panel" in sidebar
   - Enter admin password

2. **Go to Documentation Management Tab**
   - Click "📚 Documentation Management" tab

3. **View Status**
   - See color-coded status cards
   - Check detailed table
   - Review recommendations

4. **Update Documentation**
   - **Individual**: Click "Update" button on stale source
   - **All Stale**: Click "Auto-Update All Stale" button

---

## 🔄 Update Process

### **Manual Update**
1. Click "Update [Source Name]" button
2. System clones/pulls latest from GitHub
3. Uploads to S3
4. Triggers ingestion job
5. Shows success/failure message

### **Auto-Update All**
1. Click "Auto-Update All Stale" button
2. System checks all sources
3. Updates only stale sources
4. Shows results for each
5. Refreshes dashboard automatically

---

## 📊 Monitoring

### **Real-Time Status**
- Dashboard refreshes on button click
- Shows current status immediately
- Updates progress in real-time

### **Update Frequency**
- **Adobe Experience Platform**: Weekly (7 days)
- **Adobe Analytics**: Monthly (30 days)
- **Customer Journey Analytics**: Monthly (30 days)
- **Analytics APIs**: Monthly (30 days)

---

## 🎯 Benefits

### **1. Automated Monitoring**
- ✅ No manual checking needed
- ✅ Automatic staleness detection
- ✅ Visual status indicators

### **2. One-Click Updates**
- ✅ Update individual sources
- ✅ Update all stale sources at once
- ✅ Automatic ingestion trigger

### **3. Comprehensive Dashboard**
- ✅ Visual status cards
- ✅ Detailed information table
- ✅ Update recommendations
- ✅ Statistics overview

### **4. Error Handling**
- ✅ Graceful error handling
- ✅ Clear error messages
- ✅ Fallback mechanisms

---

## 🔍 Configuration

### **Update Frequency Settings**
```python
DOC_SOURCES = {
    "adobe-experience-platform": {
        "update_frequency_days": 7,  # Change to 14 for bi-weekly
    },
    "adobe-analytics": {
        "update_frequency_days": 30,  # Change to 15 for bi-weekly
    }
}
```

### **Customization Options**
- Adjust update frequency per source
- Add new documentation sources
- Modify status thresholds
- Customize dashboard appearance

---

## 📝 Files Created/Modified

### **New Files**:
1. ✅ `src/admin/documentation_manager.py` - Core management logic
2. ✅ `src/admin/documentation_dashboard.py` - Dashboard UI

### **Modified Files**:
1. ✅ `src/admin/admin_panel.py` - Added documentation tab

---

## 🧪 Testing

### **Test Scenarios**

1. **Check Freshness**
   - Access admin panel
   - Go to Documentation Management tab
   - Verify status cards show correct colors

2. **Manual Update**
   - Click "Update" on a stale source
   - Verify upload progress
   - Check ingestion job started

3. **Auto-Update All**
   - Click "Auto-Update All Stale"
   - Verify all stale sources updated
   - Check dashboard refreshes

4. **Statistics**
   - Click "View Statistics"
   - Verify total files and size
   - Check KB and bucket info

---

## ✅ Features Checklist

- [x] Documentation freshness monitoring
- [x] GitHub vs S3 comparison
- [x] Days behind calculation
- [x] Auto-update trigger (>7 days)
- [x] Status dashboard
- [x] Color-coded status cards
- [x] Detailed status table
- [x] Update recommendations
- [x] Individual source updates
- [x] Bulk auto-update
- [x] Documentation statistics
- [x] Error handling
- [x] Admin panel integration

---

## 🎉 Result

The Administrator panel now has a comprehensive documentation management system that:
- ✅ Monitors all documentation sources
- ✅ Shows freshness status with visual indicators
- ✅ Provides one-click updates
- ✅ Auto-updates stale documentation
- ✅ Displays comprehensive statistics
- ✅ Integrates seamlessly with existing admin panel

---

**Status**: ✅ COMPLETED  
**Branch**: enhancements  
**Date**: October 20, 2025  
**Location**: Admin Panel → Documentation Management Tab
