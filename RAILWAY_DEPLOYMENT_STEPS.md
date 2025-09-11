# 🚀 Railway Deployment Guide

## Prerequisites
- GitHub account
- Railway account (free at [railway.app](https://railway.app))
- Your code pushed to GitHub

## Step 1: Push Code to GitHub

```bash
# Add all files
git add .

# Commit changes
git commit -m "Add Railway deployment configuration and PostgreSQL support"

# Push to GitHub
git push origin main
```

## Step 2: Deploy to Railway

### Option A: Railway Dashboard (Recommended)

1. **Go to [railway.app](https://railway.app)**
2. **Click "New Project"**
3. **Select "Deploy from GitHub repo"**
4. **Choose your repository**: `riteshvg/ExperienceLeagueChatBotAWS`
5. **Click "Deploy"**

### Option B: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

## Step 3: Add PostgreSQL Database

1. **In Railway Dashboard**:
   - Go to your project
   - Click "New Service"
   - Select "Database" → "PostgreSQL"
   - Wait for database to provision

2. **Get Database URL**:
   - Click on PostgreSQL service
   - Go to "Variables" tab
   - Copy the `DATABASE_URL`

## Step 4: Set Environment Variables

In Railway Dashboard → Your App → Variables tab, add:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1

# Bedrock Configuration
BEDROCK_KNOWLEDGE_BASE_ID=your_kb_id
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-3-haiku-20240307-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# S3 Configuration
AWS_S3_BUCKET=your_s3_bucket_name

# Database (Railway will set this automatically)
DATABASE_URL=postgresql://user:pass@host:port/db

# Optional: Disable SQLite for production
USE_SQLITE=false
```

## Step 5: Initialize Database

1. **Connect to your Railway PostgreSQL**:
   - Go to PostgreSQL service
   - Click "Query" tab
   - Run the migration script

2. **Copy and paste this SQL**:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address INET
);

-- Query sessions table
CREATE TABLE IF NOT EXISTS query_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    session_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_queries INTEGER DEFAULT 0,
    total_feedback_positive INTEGER DEFAULT 0,
    total_feedback_negative INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE
);

-- User queries table
CREATE TABLE IF NOT EXISTS user_queries (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    query_session_id INTEGER,
    query_text TEXT NOT NULL,
    query_length INTEGER,
    query_complexity VARCHAR(20) DEFAULT 'simple' CHECK (query_complexity IN ('simple', 'complex', 'extremely_complex')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'error', 'timeout')),
    error_message TEXT,
    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE,
    FOREIGN KEY (query_session_id) REFERENCES query_sessions(id) ON DELETE SET NULL
);

-- AI responses table
CREATE TABLE IF NOT EXISTS ai_responses (
    id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL,
    model_used VARCHAR(100) NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    response_text TEXT NOT NULL,
    response_length INTEGER,
    tokens_used INTEGER,
    estimated_cost DECIMAL(10, 6),
    documents_retrieved INTEGER DEFAULT 0,
    relevance_score DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE
);

-- User feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    query_id INTEGER NOT NULL,
    response_id INTEGER NOT NULL,
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('positive', 'negative', 'neutral')),
    feedback_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    additional_notes TEXT,
    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE,
    FOREIGN KEY (response_id) REFERENCES ai_responses(id) ON DELETE CASCADE,
    CONSTRAINT unique_query_response_feedback UNIQUE (query_id, response_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_session_id ON users(session_id);
CREATE INDEX IF NOT EXISTS idx_query_sessions_session_id ON query_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_queries_session_id ON user_queries(session_id);
CREATE INDEX IF NOT EXISTS idx_user_queries_created_at ON user_queries(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_responses_query_id ON ai_responses(query_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_query_id ON user_feedback(query_id);
```

## Step 6: Deploy and Test

1. **Railway will automatically deploy** when you push to GitHub
2. **Check deployment logs** in Railway Dashboard
3. **Visit your app URL** (provided by Railway)
4. **Test the analytics** by asking questions and checking Admin Dashboard

## Step 7: Monitor and Scale

- **View logs**: Railway Dashboard → Your App → Deployments
- **Monitor usage**: Railway Dashboard → Usage tab
- **Scale if needed**: Railway Dashboard → Settings → Scale

## Troubleshooting

### Common Issues:

1. **Database Connection Error**:
   - Check `DATABASE_URL` is set correctly
   - Verify PostgreSQL service is running

2. **AWS Credentials Error**:
   - Verify all AWS environment variables are set
   - Check AWS credentials have proper permissions

3. **Build Errors**:
   - Check `requirements.txt` has all dependencies
   - Verify Python version compatibility

4. **App Not Starting**:
   - Check logs in Railway Dashboard
   - Verify `railway.toml` configuration

## Cost Estimation

- **Railway Free Tier**: $5/month credit
- **PostgreSQL**: ~$1-2/month for small usage
- **App Hosting**: ~$1-3/month
- **Total**: ~$2-5/month for moderate usage

## Next Steps

1. **Set up monitoring**: Add error tracking
2. **Configure custom domain**: Add your own domain
3. **Set up CI/CD**: Automatic deployments on git push
4. **Add SSL**: Railway provides free SSL certificates

Your Adobe Analytics RAG chatbot will be live on Railway! 🎉
