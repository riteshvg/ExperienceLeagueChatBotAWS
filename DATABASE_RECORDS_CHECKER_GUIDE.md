# 🔍 Database Records Checker - Usage Guide

## ✅ **Tables Created Successfully!**

Since you've manually created the tables, here are the Python scripts to check your records and verify everything is working.

## 🚀 **Three Ways to Check Your Records**

### **Method 1: Command Line Script (Quickest)**
```bash
python check_railway_records.py
```

**What it does:**
- ✅ Tests database connection
- ✅ Checks if all tables exist
- ✅ Shows record counts for each table
- ✅ Displays analytics summary
- ✅ Tests data insertion and retrieval
- ✅ Exports records to CSV files

### **Method 2: Streamlit Standalone App**
```bash
streamlit run streamlit_db_checker.py
```

**What it does:**
- ✅ Beautiful web interface
- ✅ Real-time database status
- ✅ Interactive record viewing
- ✅ Test data insertion
- ✅ CSV export functionality
- ✅ Recent queries display

### **Method 3: Integrate into Your Existing App**
Add the database checker to your existing Streamlit app by following the instructions in `add_db_checker_to_app.py`

## 📊 **What You'll See**

### **Database Status:**
```
✅ Database connected successfully
📊 PostgreSQL version: PostgreSQL 15.4
✅ user_queries - EXISTS
✅ ai_responses - EXISTS
✅ user_feedback - EXISTS
✅ query_sessions - EXISTS
```

### **Record Counts:**
```
📊 user_queries: 0 records
📊 ai_responses: 0 records
📊 user_feedback: 0 records
📊 query_sessions: 0 records
```

### **Analytics Summary:**
```
📊 Total Queries: 0
📊 Total Responses: 0
📊 Total Feedback: 0
📊 Positive Feedback: 0
📊 Negative Feedback: 0
```

## 🧪 **Testing Your Setup**

### **Step 1: Run the Command Line Checker**
```bash
python check_railway_records.py
```

### **Step 2: Test Data Insertion**
The script will automatically test inserting sample data to verify everything works.

### **Step 3: Check Your Streamlit App**
1. Go to your Railway app URL
2. Ask a question
3. Check if it appears in the Query Analytics tab

## 🔧 **Environment Variables Needed**

Make sure these are set in your Railway Web Service:

```
RAILWAY_DATABASE_USER=postgres
RAILWAY_DATABASE_PASSWORD=eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE
RAILWAY_DATABASE_HOST=containers-us-west-1.railway.app
RAILWAY_DATABASE_PORT=5432
RAILWAY_DATABASE_NAME=railway
RAILWAY_ENVIRONMENT=production
```

## 📁 **Files Created**

### **1. `check_railway_records.py`**
- Command line script
- Comprehensive database checking
- CSV export functionality
- Detailed logging

### **2. `streamlit_db_checker.py`**
- Standalone Streamlit app
- Beautiful web interface
- Interactive features
- Real-time updates

### **3. `add_db_checker_to_app.py`**
- Integration guide
- Helper functions
- Instructions for adding to existing app

## 🎯 **Expected Results**

### **✅ After Running the Scripts:**
- Database connection successful
- All 4 tables exist
- Record counts displayed
- Test data insertion works
- CSV files exported (if data exists)

### **✅ After Testing Your App:**
- Query Analytics tab shows data
- User queries are recorded
- Feedback system works
- Export functionality works

## 🚨 **Troubleshooting**

### **Issue 1: "Database connection failed"**
- **Solution**: Check environment variables are set correctly

### **Issue 2: "Tables missing"**
- **Solution**: Verify tables were created manually in Railway

### **Issue 3: "No records found"**
- **Solution**: This is normal for a new database - test by asking questions in your app

### **Issue 4: "Permission denied"**
- **Solution**: Check Railway PostgreSQL service permissions

## 🎉 **Success Indicators**

### **✅ Database Working:**
- Connection successful
- All tables exist
- Data insertion works
- Data retrieval works

### **✅ Query Analytics Working:**
- No "database configuration error" messages
- Queries appear in dashboard
- Feedback is recorded
- Export functionality works

## 🚀 **Next Steps**

1. **Run the checker scripts** to verify everything works
2. **Test your Streamlit app** by asking questions
3. **Check Query Analytics tab** to see if data appears
4. **Test feedback system** by clicking thumbs up/down
5. **Test export functionality** in the analytics dashboard

Your database is now ready for Query Analytics! 🎯
