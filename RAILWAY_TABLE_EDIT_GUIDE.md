# Railway PostgreSQL Table Editing Guide

## 🎯 **Problem**: Your `query_analytics` table has CHAR(1) constraints that prevent storing longer values.

## 🔧 **Solution Options**

### **Option 1: Railway CLI (Recommended)**

1. **Install Railway CLI** (if not already installed):
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**:
   ```bash
   railway login
   ```

3. **Connect to your project**:
   ```bash
   railway link
   ```

4. **Connect to PostgreSQL**:
   ```bash
   railway connect postgres
   ```

5. **Run SQL commands**:
   ```sql
   -- Modify reaction column to allow longer values
   ALTER TABLE query_analytics 
   ALTER COLUMN reaction TYPE VARCHAR(20);
   
   -- Modify userid column to allow longer values  
   ALTER TABLE query_analytics 
   ALTER COLUMN userid TYPE VARCHAR(100);
   
   -- Ensure query column is TEXT
   ALTER TABLE query_analytics 
   ALTER COLUMN query TYPE TEXT;
   ```

### **Option 2: Python Script on Railway**

1. **Upload the fix script** to your Railway project
2. **Set environment variables** in Railway dashboard
3. **Run the script**:
   ```bash
   python railway_table_fix.py
   ```

### **Option 3: External Database Tool**

1. **Use pgAdmin, DBeaver, or similar**
2. **Connect using Railway credentials**:
   - Host: `containers-us-west-1.railway.app`
   - Port: `5432`
   - Database: `railway`
   - Username: `postgres`
   - Password: `[your_password]`

3. **Run the ALTER TABLE commands** from Option 1

### **Option 4: Railway Dashboard (Limited)**

1. Go to your Railway project dashboard
2. Click on your PostgreSQL service
3. Look for "Connect" or "Query" options
4. Run the ALTER TABLE commands

## 🚀 **Quick Fix Commands**

Run these SQL commands to fix your table:

```sql
-- Check current schema
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'query_analytics';

-- Fix the columns
ALTER TABLE query_analytics 
ALTER COLUMN reaction TYPE VARCHAR(20);

ALTER TABLE query_analytics 
ALTER COLUMN userid TYPE VARCHAR(100);

ALTER TABLE query_analytics 
ALTER COLUMN query TYPE TEXT;

-- Verify the changes
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'query_analytics';
```

## ✅ **Expected Result**

After running these commands, your table will have:
- `reaction`: VARCHAR(20) - can store "positive", "negative", etc.
- `userid`: VARCHAR(100) - can store longer usernames
- `query`: TEXT - can store very long queries
- `id`: SERIAL PRIMARY KEY (unchanged)
- `date_time`: TIMESTAMP (unchanged)

## 🔍 **Verification**

After making changes, test with:
```sql
INSERT INTO query_analytics (query, userid, date_time, reaction)
VALUES ('Test long query', 'test_user_123', NOW(), 'positive')
RETURNING id;
```

This should work without any length errors!

## 📞 **Need Help?**

If you're still having issues:
1. Check Railway logs for error messages
2. Verify your DATABASE_URL environment variable
3. Make sure you have the correct permissions
4. Try the Python script approach as a backup
