# 🔧 Fix Analytics Issue - No Queries in Dashboard

## 🚨 **Root Cause Identified**

The Query Analytics dashboard shows no queries because the `DATABASE_URL` environment variable is not set, so the analytics service can't connect to the Railway database.

## 🎯 **Quick Fix Steps**

### **Step 1: Get Your Railway DATABASE_URL**

1. **Go to Railway Dashboard**

   - Visit [railway.app](https://railway.app)
   - Click on your project
   - Click on your PostgreSQL service

2. **Get Connection String**
   - Click on "Connect" tab
   - Copy the "DATABASE_URL" connection string
   - It looks like: `postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway`

### **Step 2: Set DATABASE_URL Locally (For Testing)**

**Option A: Create .env file**

```bash
echo "DATABASE_URL=postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway" > .env
```

**Option B: Export in terminal**

```bash
export DATABASE_URL="postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway"
```

### **Step 3: Test Database Connection**

```bash
# Test if database is accessible
python check_railway_db_offline.py

# Test analytics functionality
python test_analytics_manual.py

# Run full diagnostic
python debug_analytics_issue.py
```

### **Step 4: Verify Railway Environment Variables**

1. **Go to Railway Dashboard**

   - Click on your project
   - Click on "Variables" tab
   - Make sure `DATABASE_URL` is set

2. **Check Other Required Variables**
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `BEDROCK_KNOWLEDGE_BASE_ID`
   - `ADOBE_CLIENT_ID`
   - `ADOBE_CLIENT_SECRET`
   - `ADOBE_ORGANIZATION_ID`

## 🔍 **Diagnostic Commands**

### **1. Check Database Structure (No Connection Required)**

```bash
python check_db_structure.py
```

### **2. Check Live Database (Requires DATABASE_URL)**

```bash
python check_railway_db_offline.py
```

### **3. Test Analytics Manually**

```bash
python test_analytics_manual.py
```

### **4. Full Diagnostic**

```bash
python debug_analytics_issue.py
```

## 🚨 **Common Issues & Solutions**

### **Issue 1: "DATABASE_URL not found"**

- **Cause**: Environment variable not set
- **Solution**: Set DATABASE_URL as shown above

### **Issue 2: "Database connection failed"**

- **Cause**: Wrong DATABASE_URL format or Railway service down
- **Solution**: Check Railway PostgreSQL service status

### **Issue 3: "Some required tables are missing"**

- **Cause**: Database initialization didn't run
- **Solution**: Check Railway logs for `init_railway_db.py` execution

### **Issue 4: "Analytics service import failed"**

- **Cause**: Code not deployed or import errors
- **Solution**: Redeploy to Railway with latest code

### **Issue 5: "Queries not being recorded"**

- **Cause**: Analytics service not initialized in app
- **Solution**: Check Railway logs for analytics initialization

## 📊 **Expected Results After Fix**

### **Database Check Should Show:**

```
✅ Database connected successfully
📊 PostgreSQL version: PostgreSQL 15.4

📋 Table Status:
==================================================
✅ user_queries - EXISTS
✅ ai_responses - EXISTS
✅ user_feedback - EXISTS
✅ query_sessions - EXISTS

📊 Sample Data from user_queries (limit 5):
------------------------------------------------------------
Total rows: 12
  id  query_text                    session_id    query_complexity  created_at
   1  How do I set up Adobe Analytics?  session-123  simple           2025-01-12 10:30:00
```

### **Analytics Dashboard Should Show:**

- ✅ Total Queries count
- ✅ Success Rate percentage
- ✅ Recent query history
- ✅ Feedback statistics
- ✅ Export functionality

## 🔄 **Railway-Specific Fixes**

### **1. Check Railway Logs**

- Go to Railway dashboard → Your project → Deployments
- Click on latest deployment
- Check logs for any errors

### **2. Verify Environment Variables**

- Go to Railway dashboard → Your project → Variables
- Ensure all required variables are set
- Redeploy if any variables were missing

### **3. Force Database Initialization**

- The `init_railway_db.py` should run automatically on startup
- If it fails, check Railway logs for errors
- You can manually run it by adding it to Railway startup

### **4. Redeploy with Latest Code**

- Push latest changes to GitHub
- Railway will auto-deploy
- Check logs for successful deployment

## 🧪 **Testing Steps**

### **1. Test Locally First**

```bash
# Set DATABASE_URL
export DATABASE_URL="your-railway-database-url"

# Test connection
python check_railway_db_offline.py

# Test analytics
python test_analytics_manual.py
```

### **2. Test on Railway**

1. Ask a question in the app
2. Check Query Analytics tab
3. Verify query appears in dashboard
4. Check Railway logs for any errors

### **3. Verify Data Flow**

1. User asks question → Query recorded in `user_queries`
2. AI responds → Response recorded in `ai_responses`
3. User gives feedback → Feedback recorded in `user_feedback`
4. Analytics dashboard shows all data

## 🎯 **Success Indicators**

### **✅ Database Working**

- Can connect to Railway PostgreSQL
- All 4 tables exist
- Can insert/retrieve data

### **✅ Analytics Working**

- Queries appear in dashboard
- Feedback is recorded
- Export functionality works

### **✅ App Working**

- No errors in Railway logs
- Analytics service initialized
- Queries are being tracked

## 🚀 **Next Steps After Fix**

1. **Test the app** - Ask a few questions
2. **Check analytics** - Verify queries appear in dashboard
3. **Test feedback** - Click thumbs up/down buttons
4. **Export data** - Test CSV/JSON export
5. **Monitor logs** - Check Railway logs for any issues

The main issue is the missing `DATABASE_URL` environment variable. Once you set it correctly, the analytics should work perfectly! 🎉
