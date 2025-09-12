# Railway Database Check Guide

## 🔍 How to Check Your Railway Database Tables Offline

### Method 1: Check Database Structure (No Connection Required)

```bash
python check_db_structure.py
```

This shows you:

- ✅ Expected table structure
- ✅ Column definitions and types
- ✅ Indexes and relationships
- ✅ Sample queries
- ✅ Connection requirements

### Method 2: Check Live Database (Requires DATABASE_URL)

```bash
python check_railway_db_offline.py
```

This connects to your Railway database and shows:

- ✅ Connection status
- ✅ Table existence check
- ✅ Table structure
- ✅ Sample data from each table
- ✅ Analytics summary
- ✅ Database operation tests

## 🔧 Prerequisites for Live Check

### 1. Get Your Railway DATABASE_URL

1. Go to your Railway project dashboard
2. Click on your PostgreSQL service
3. Go to "Connect" tab
4. Copy the "DATABASE_URL" connection string

### 2. Set Environment Variable

**Option A: Create .env file**

```bash
echo "DATABASE_URL=postgresql://username:password@host:port/database" > .env
```

**Option B: Export in terminal**

```bash
export DATABASE_URL="postgresql://username:password@host:port/database"
```

**Option C: Set in Railway dashboard**

- Go to your Railway project
- Click on "Variables" tab
- Add `DATABASE_URL` with your connection string

### 3. Install Required Packages

```bash
pip install psycopg2-binary pandas
```

## 📊 What You'll See

### Database Structure Check

```
🗄️ Expected Railway Database Schema
============================================================

📋 Table: user_queries
Description: Stores user queries and metadata
------------------------------------------------------------
Column               Type                           Description
------------------------------------------------------------
id                   SERIAL PRIMARY KEY             Auto-incrementing unique ID
query_text           TEXT NOT NULL                  The actual query text
session_id           VARCHAR(255)                   Session identifier
...
```

### Live Database Check

```
🗄️ Railway Database Offline Checker
============================================================
Check started at: 2025-01-12 12:30:00

✅ DATABASE_URL found: postgresql://postgres:pass...
✅ Database connected successfully
📊 PostgreSQL version: PostgreSQL 15.4

📋 Table Status:
==================================================
✅ user_queries - EXISTS
✅ ai_responses - EXISTS
✅ user_feedback - EXISTS
✅ query_sessions - EXISTS
```

## 🚨 Troubleshooting

### Error: "DATABASE_URL not found"

- **Solution**: Set the DATABASE_URL environment variable
- **Check**: Run `echo $DATABASE_URL` to verify

### Error: "Database connection failed"

- **Solution**: Check your DATABASE_URL format
- **Format**: `postgresql://username:password@host:port/database`

### Error: "Some required tables are missing"

- **Solution**: Run database initialization on Railway
- **Check**: Railway logs for `init_railway_db.py` execution

### Error: "No module named 'psycopg2'"

- **Solution**: Install PostgreSQL driver
- **Command**: `pip install psycopg2-binary`

## 🎯 Expected Results

### ✅ Successful Check

- All 4 tables exist (user_queries, ai_responses, user_feedback, query_sessions)
- Database operations work (insert, update, select, delete)
- Analytics summary shows data
- Recent queries are displayed

### ❌ Failed Check

- Missing tables → Run database initialization
- Connection failed → Check DATABASE_URL
- Import errors → Install required packages

## 📈 What This Tells You

### Database Health

- **Connection**: Can connect to Railway PostgreSQL
- **Tables**: All required tables exist
- **Structure**: Tables have correct columns and types
- **Data**: Sample data can be inserted and retrieved

### Analytics Status

- **Queries**: How many user queries have been recorded
- **Responses**: How many AI responses have been generated
- **Feedback**: How much user feedback has been collected
- **Sessions**: How many user sessions have been tracked

## 🔄 Next Steps After Check

### If Database is Working

1. ✅ Your Query Analytics should work in the app
2. ✅ User queries will be recorded
3. ✅ Feedback system will work
4. ✅ Export functionality will work

### If Database Needs Fixing

1. 🔧 Check Railway logs for initialization errors
2. 🔧 Verify DATABASE_URL is correct
3. 🔧 Run database initialization manually
4. 🔧 Check Railway PostgreSQL service status

## 📞 Support

If you encounter issues:

1. Check Railway logs first
2. Verify your DATABASE_URL format
3. Ensure all required packages are installed
4. Check Railway PostgreSQL service is running

The database check scripts will help you diagnose exactly what's working and what needs to be fixed!
