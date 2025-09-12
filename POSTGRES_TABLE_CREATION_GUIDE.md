# 🗄️ PostgreSQL Table Creation Guide

## 🎯 **Two Ways to Create Tables in Your Railway PostgreSQL Service**

### **Method 1: Python Script (Recommended)**

```bash
python create_postgres_tables.py
```

### **Method 2: SQL Script (Direct)**

Run `create_tables.sql` in Railway PostgreSQL console

## 🚀 **Method 1: Python Script**

### **Step 1: Get Your DATABASE_URL**

1. Go to Railway dashboard
2. Click on your PostgreSQL service
3. Go to "Connect" tab
4. Copy the "DATABASE_URL" connection string

### **Step 2: Run the Script**

```bash
# Option A: Set environment variable
export DATABASE_URL="postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway"
python create_postgres_tables.py

# Option B: Script will ask for DATABASE_URL
python create_postgres_tables.py
```

### **Step 3: What the Script Does**

- ✅ Tests database connection
- ✅ Creates all 4 required tables
- ✅ Creates indexes for performance
- ✅ Tests table operations (insert, select, delete)
- ✅ Shows table structure
- ✅ Provides usage instructions

## 🚀 **Method 2: SQL Script (Direct)**

### **Step 1: Access Railway PostgreSQL Console**

1. Go to Railway dashboard
2. Click on your PostgreSQL service
3. Go to "Query" tab
4. This opens the PostgreSQL console

### **Step 2: Run SQL Script**

1. Copy the contents of `create_tables.sql`
2. Paste into the PostgreSQL console
3. Click "Run" or press Ctrl+Enter

### **Step 3: Verify Tables Created**

The script will show:

- List of created tables
- Table structure with columns
- Confirmation that tables exist

## 📊 **Tables That Will Be Created**

### **1. user_queries**

- Stores user questions
- Columns: id, query_text, session_id, query_complexity, created_at, updated_at

### **2. ai_responses**

- Stores AI responses
- Columns: id, query_id, response_text, model_used, response_time_ms, created_at

### **3. user_feedback**

- Stores user feedback
- Columns: id, query_id, response_id, feedback_type, feedback_text, created_at

### **4. query_sessions**

- Stores session information
- Columns: id, user_id, session_start, session_end, total_queries, created_at

## 🔧 **After Creating Tables**

### **Step 1: Set DATABASE_URL in Web Service**

1. Go to Railway dashboard
2. Click on your Web Service (Streamlit app)
3. Go to "Variables" tab
4. Add `DATABASE_URL` with the value from PostgreSQL service

### **Step 2: Add Other Environment Variables**

```
DATABASE_URL=postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
BEDROCK_KNOWLEDGE_BASE_ID=your_kb_id
ADOBE_CLIENT_ID=your_adobe_client_id
ADOBE_CLIENT_SECRET=your_adobe_client_secret
ADOBE_ORGANIZATION_ID=your_adobe_org_id
```

### **Step 3: Redeploy Web Service**

1. Click "Deploy" in your Web Service
2. Wait for deployment to complete
3. Check logs for successful initialization

## 🧪 **Testing the Setup**

### **Test Database Connection**

```bash
python check_railway_db_offline.py
```

### **Test Analytics Functionality**

```bash
python test_analytics_manual.py
```

### **Test Full Diagnostic**

```bash
python debug_analytics_issue.py
```

## 🎯 **Expected Results**

### **✅ After Table Creation**

- 4 tables created in PostgreSQL
- Indexes created for performance
- Tables ready for data insertion

### **✅ After Web Service Setup**

- DATABASE_URL set in Web Service
- App connects to PostgreSQL
- Query Analytics dashboard works
- Queries are recorded and displayed

### **✅ Success Indicators**

- No "database configuration error" messages
- Query Analytics shows data
- User queries are recorded
- Feedback system works
- Export functionality works

## 🚨 **Troubleshooting**

### **Issue 1: "DATABASE_URL not found"**

- **Solution**: Set DATABASE_URL environment variable

### **Issue 2: "Database connection failed"**

- **Solution**: Check DATABASE_URL format and PostgreSQL service status

### **Issue 3: "Tables already exist"**

- **Solution**: This is normal, script uses CREATE TABLE IF NOT EXISTS

### **Issue 4: "Permission denied"**

- **Solution**: Check PostgreSQL service permissions

## 🎉 **Next Steps After Success**

1. **Test your app** - Ask a few questions
2. **Check Query Analytics** - Verify queries appear
3. **Test feedback** - Click thumbs up/down buttons
4. **Export data** - Test CSV/JSON export
5. **Monitor logs** - Check for any errors

Your PostgreSQL tables will be ready for Query Analytics! 🎯
