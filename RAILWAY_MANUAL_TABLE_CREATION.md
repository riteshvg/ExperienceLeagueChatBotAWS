# 🗄️ Manual Table Creation in Railway PostgreSQL

## 🚨 **Table Creation Failed - Manual Setup Required**

Since the automatic table creation failed, you can create the tables manually in Railway PostgreSQL console.

## 🔧 **Step-by-Step Manual Creation**

### **Step 1: Access Railway PostgreSQL Console**

1. Go to [https://railway.app](https://railway.app)
2. Click on your project
3. Click on your **PostgreSQL service**
4. Click on **"Query"** tab
5. This opens the PostgreSQL console

### **Step 2: Run SQL Commands**

Copy and paste the following SQL commands one by one:

## 📋 **Table 1: user_queries**

```sql
CREATE TABLE user_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    session_id VARCHAR(255),
    query_complexity VARCHAR(50) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Stores user questions and metadata
**Columns**:

- `id` - Auto-incrementing primary key
- `query_text` - The actual question text
- `session_id` - Session identifier
- `query_complexity` - Complexity level (simple/medium/complex)
- `created_at` - When query was created
- `updated_at` - When query was last updated

## 📋 **Table 2: ai_responses**

```sql
CREATE TABLE ai_responses (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES user_queries(id) ON DELETE CASCADE,
    response_text TEXT NOT NULL,
    model_used VARCHAR(100),
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Stores AI responses to queries
**Columns**:

- `id` - Auto-incrementing primary key
- `query_id` - Foreign key to user_queries table
- `response_text` - The AI response text
- `model_used` - Which AI model was used
- `response_time_ms` - Response time in milliseconds
- `created_at` - When response was created

## 📋 **Table 3: user_feedback**

```sql
CREATE TABLE user_feedback (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES user_queries(id) ON DELETE CASCADE,
    response_id INTEGER REFERENCES ai_responses(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL,
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Stores user feedback on responses
**Columns**:

- `id` - Auto-incrementing primary key
- `query_id` - Foreign key to user_queries table
- `response_id` - Foreign key to ai_responses table
- `feedback_type` - Type of feedback (positive/negative/neutral)
- `feedback_text` - Additional feedback text
- `created_at` - When feedback was given

## 📋 **Table 4: query_sessions**

```sql
CREATE TABLE query_sessions (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255),
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    total_queries INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Stores session information
**Columns**:

- `id` - Session identifier (primary key)
- `user_id` - User identifier
- `session_start` - When session started
- `session_end` - When session ended
- `total_queries` - Number of queries in session
- `created_at` - When session was created

## 🔍 **Step 3: Create Indexes for Performance**

```sql
-- Create indexes for better performance
CREATE INDEX idx_user_queries_session_id ON user_queries(session_id);
CREATE INDEX idx_user_queries_created_at ON user_queries(created_at);
CREATE INDEX idx_ai_responses_query_id ON ai_responses(query_id);
CREATE INDEX idx_user_feedback_query_id ON user_feedback(query_id);
CREATE INDEX idx_user_feedback_response_id ON user_feedback(response_id);
```

## ✅ **Step 4: Verify Tables Created**

```sql
-- Check if all tables were created
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
ORDER BY table_name;
```

**Expected Result**: Should show all 4 table names

## 🧪 **Step 5: Test Table Structure**

```sql
-- Check table structure
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
ORDER BY table_name, ordinal_position;
```

## 🚀 **Step 6: Test Data Insertion**

```sql
-- Test inserting sample data
INSERT INTO user_queries (query_text, session_id, query_complexity)
VALUES ('Test query for manual setup', 'test-session-123', 'simple');

-- Check if data was inserted
SELECT * FROM user_queries WHERE session_id = 'test-session-123';

-- Clean up test data
DELETE FROM user_queries WHERE session_id = 'test-session-123';
```

## 🎯 **After Manual Creation**

### **1. Set Environment Variables in Web Service**

Go to your Railway Web Service and add:

```
RAILWAY_DATABASE_USER=postgres
RAILWAY_DATABASE_PASSWORD=eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_DEFAULT_REGION=us-east-1
BEDROCK_KNOWLEDGE_BASE_ID=your_knowledge_base_id_here
ADOBE_CLIENT_ID=your_adobe_client_id_here
ADOBE_CLIENT_SECRET=your_adobe_client_secret_here
ADOBE_ORGANIZATION_ID=your_adobe_organization_id_here
AWS_S3_BUCKET=your_s3_bucket_name_here
RAILWAY_ENVIRONMENT=production
```

### **2. Redeploy Web Service**

1. Click "Deploy" in your Web Service
2. Wait for deployment to complete
3. Check logs for successful startup

### **3. Test Query Analytics**

1. Go to your app URL
2. Ask a question
3. Check Query Analytics tab
4. Verify query appears in dashboard

## 🎉 **Success Indicators**

### **✅ Tables Created Successfully**

- All 4 tables exist in PostgreSQL
- Indexes created for performance
- Foreign key relationships established

### **✅ Query Analytics Working**

- No "database configuration error" messages
- Queries are recorded and displayed
- Feedback system works
- Export functionality works

## 🚨 **Troubleshooting**

### **Issue 1: "Table already exists"**

- **Solution**: This is normal, tables might already exist

### **Issue 2: "Permission denied"**

- **Solution**: Check PostgreSQL service permissions

### **Issue 3: "Syntax error"**

- **Solution**: Copy SQL commands exactly as shown

### **Issue 4: "Connection failed"**

- **Solution**: Check PostgreSQL service is running

## 📊 **Quick Reference - Column Names**

### **user_queries**

- id, query_text, session_id, query_complexity, created_at, updated_at

### **ai_responses**

- id, query_id, response_text, model_used, response_time_ms, created_at

### **user_feedback**

- id, query_id, response_id, feedback_type, feedback_text, created_at

### **query_sessions**

- id, user_id, session_start, session_end, total_queries, created_at

Your manual table creation should work perfectly! 🎯
