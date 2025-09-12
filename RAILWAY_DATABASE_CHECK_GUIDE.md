# 🚀 Railway Database Check Guide

## 🚨 **Current Status: Environment Variables Missing**

The diagnostic shows that your Railway app is missing critical environment variables, which is why Query Analytics isn't working.

## 🔍 **Step-by-Step Railway Database Check**

### **Step 1: Check Railway Dashboard**

1. **Go to Railway Dashboard**

   - Visit [https://railway.app](https://railway.app)
   - Click on your project

2. **Check PostgreSQL Service**

   - Look for a PostgreSQL service in your project
   - If missing, you need to add one

3. **Get Database Connection String**
   - Click on your PostgreSQL service
   - Go to "Connect" tab
   - Copy the "DATABASE_URL" connection string

### **Step 2: Check Environment Variables**

1. **Go to Variables Tab**

   - In your Railway project dashboard
   - Click on "Variables" tab

2. **Check Required Variables**

   - `DATABASE_URL` (from PostgreSQL service)
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `BEDROCK_KNOWLEDGE_BASE_ID`
   - `ADOBE_CLIENT_ID`
   - `ADOBE_CLIENT_SECRET`
   - `ADOBE_ORGANIZATION_ID`

3. **Add Missing Variables**
   - Click "New Variable" for each missing one
   - Add the variable name and value
   - Click "Deploy" to redeploy with new variables

### **Step 3: Check Railway Logs**

1. **Go to Deployments Tab**

   - Click on "Deployments" in your project
   - Click on the latest deployment

2. **Look for These Success Messages**

   - ✅ "Railway database initialization completed successfully"
   - ✅ "Analytics integration loaded successfully"
   - ✅ "Starting Streamlit app..."

3. **Look for These Error Messages**
   - ❌ "DATABASE_URL not found"
   - ❌ "Database connection failed"
   - ❌ "No module named src.models"

### **Step 4: Test Your App**

1. **Get Your App URL**

   - In Railway dashboard, look for "Domains" or "Public URL"
   - Copy your app URL (e.g., `https://your-app-name.up.railway.app`)

2. **Test Query Analytics**
   - Go to your app URL
   - Click on "Admin Panel" tab
   - Click on "Query Analytics" tab
   - Check if it shows data instead of setup error

## 🔧 **Common Issues & Solutions**

### **Issue 1: No PostgreSQL Service**

- **Problem**: No database service in Railway project
- **Solution**: Add PostgreSQL service from Railway marketplace

### **Issue 2: DATABASE_URL Not Set**

- **Problem**: Environment variable missing
- **Solution**: Copy DATABASE_URL from PostgreSQL service and add to Variables

### **Issue 3: Database Tables Missing**

- **Problem**: Tables not created during deployment
- **Solution**: Check logs for `init_railway_db.py` execution errors

### **Issue 4: App Not Deploying**

- **Problem**: Build or deployment errors
- **Solution**: Check Railway logs for specific error messages

## 📊 **Expected Railway Dashboard Setup**

### **Services You Should Have:**

1. **PostgreSQL Service** (for database)
2. **Web Service** (for your Streamlit app)

### **Environment Variables You Should Have:**

```
DATABASE_URL=postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
BEDROCK_KNOWLEDGE_BASE_ID=your_kb_id
ADOBE_CLIENT_ID=your_adobe_client_id
ADOBE_CLIENT_SECRET=your_adobe_client_secret
ADOBE_ORGANIZATION_ID=your_adobe_org_id
```

## 🧪 **Testing Steps**

### **1. Test Database Connection**

```bash
# Set DATABASE_URL locally for testing
export DATABASE_URL="your-railway-database-url"

# Test connection
python check_railway_db_offline.py
```

### **2. Test Analytics Functionality**

```bash
# Test analytics
python test_analytics_manual.py
```

### **3. Test Full Diagnostic**

```bash
# Run complete diagnostic
python debug_analytics_issue.py
```

## 🎯 **Success Indicators**

### **✅ Railway Dashboard Should Show:**

- PostgreSQL service running
- All environment variables set
- Latest deployment successful
- No error messages in logs

### **✅ App Should Show:**

- Query Analytics tab works
- Queries are recorded
- Feedback is tracked
- Export functionality works

### **✅ Logs Should Show:**

- "Railway database initialization completed successfully"
- "Analytics integration loaded successfully"
- "Starting Streamlit app..."

## 🚀 **Quick Fix Checklist**

- [ ] PostgreSQL service added to Railway project
- [ ] DATABASE_URL copied from PostgreSQL service
- [ ] All environment variables set in Railway
- [ ] App redeployed with new variables
- [ ] Railway logs show successful initialization
- [ ] Query Analytics tab shows data

## 📞 **If Still Not Working**

1. **Check Railway Logs** for specific error messages
2. **Verify Environment Variables** are set correctly
3. **Test Database Connection** manually
4. **Check App URL** is accessible
5. **Redeploy** if needed

The main issue is missing environment variables in Railway. Once you set them correctly, your Query Analytics will work perfectly! 🎉
