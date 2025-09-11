# Railway Deployment Guide for Query Analytics

## 🚀 **Recommended Database: PostgreSQL**

### **Why PostgreSQL?**

- ✅ **Native Railway Support**: One-click deployment
- ✅ **Free Tier**: 1GB storage, 1GB RAM
- ✅ **Streamlit Compatible**: Excellent Python support
- ✅ **Production Ready**: Enterprise-grade reliability
- ✅ **Easy Migration**: Simple schema conversion

## 📋 **Step-by-Step Deployment**

### **1. Prepare Your Project**

#### **Update requirements.txt**

```bash
# Add PostgreSQL support
psycopg2-binary>=2.9.0
```

#### **Create Railway Configuration**

Create `railway.toml`:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "streamlit run app.py --server.port=$PORT --server.address=0.0.0.0"
healthcheckPath = "/"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
```

### **2. Deploy to Railway**

#### **Option A: Railway CLI (Recommended)**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Add PostgreSQL database
railway add postgresql

# Deploy
railway up
```

#### **Option B: Railway Dashboard**

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Connect your GitHub repository
4. Add PostgreSQL service
5. Deploy

### **3. Configure Environment Variables**

In Railway dashboard, add these environment variables:

```bash
# Database Configuration
DATABASE_HOST=your_postgres_host
DATABASE_PORT=5432
DATABASE_NAME=railway
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your_postgres_password
DATABASE_TYPE=postgresql

# AWS Configuration (existing)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=us-east-1
BEDROCK_KNOWLEDGE_BASE_ID=your_kb_id
```

### **4. Initialize Database**

#### **Run Migration Script**

```bash
# Connect to Railway PostgreSQL
railway connect postgresql

# Run the migration script
psql -f database/migrate_to_postgresql.sql
```

#### **Or use Railway Dashboard**

1. Go to your PostgreSQL service
2. Click "Query"
3. Copy and paste the contents of `database/migrate_to_postgresql.sql`
4. Execute

### **5. Update Streamlit App**

#### **Modify Database Configuration**

Update your Streamlit app to use PostgreSQL:

```python
# In your app.py or config
def initialize_analytics_service():
    config = DatabaseConfig(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", 5432)),
        database=os.getenv("DATABASE_NAME", "chatbot_analytics"),
        username=os.getenv("DATABASE_USERNAME", "postgres"),
        password=os.getenv("DATABASE_PASSWORD", ""),
        database_type=os.getenv("DATABASE_TYPE", "postgresql")
    )
    return StreamlitAnalyticsIntegration(AnalyticsService(config))
```

## 🔄 **Alternative Database Options**

### **Option 2: SQLite (Simplest)**

**Pros:**

- ✅ Zero setup
- ✅ File-based
- ✅ Perfect for development

**Cons:**

- ❌ Limited scale
- ❌ No concurrent writes
- ❌ Not ideal for production

**Setup:**

```python
# Use SQLite for simple deployment
config = DatabaseConfig(
    database_type="sqlite",
    database="analytics.db"
)
```

### **Option 3: PlanetScale (MySQL)**

**Pros:**

- ✅ MySQL compatible
- ✅ Serverless scaling
- ✅ Free tier available

**Cons:**

- ❌ External service
- ❌ Additional complexity

**Setup:**

1. Create PlanetScale account
2. Create database
3. Get connection string
4. Update environment variables

## 📊 **Database Comparison**

| Feature              | PostgreSQL   | SQLite    | PlanetScale   |
| -------------------- | ------------ | --------- | ------------- |
| **Setup Complexity** | Easy         | Very Easy | Medium        |
| **Railway Support**  | Native       | Native    | External      |
| **Free Tier**        | 1GB          | Unlimited | 1B reads      |
| **Production Ready** | ✅           | ❌        | ✅            |
| **Concurrent Users** | High         | Low       | High          |
| **Cost**             | Free → $5/mo | Free      | Free → $29/mo |

## 🚀 **Deployment Commands**

### **Local Development**

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
streamlit run app.py
```

### **Railway Deployment**

```bash
# Deploy to Railway
railway up

# View logs
railway logs

# Connect to database
railway connect postgresql
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### **1. Database Connection Error**

```bash
# Check environment variables
railway variables

# Test connection
railway connect postgresql
```

#### **2. Migration Issues**

```bash
# Check database exists
railway connect postgresql
\dt

# Re-run migration
psql -f database/migrate_to_postgresql.sql
```

#### **3. Streamlit App Not Starting**

```bash
# Check logs
railway logs

# Verify port configuration
# Ensure PORT environment variable is set
```

## 📈 **Monitoring & Analytics**

### **Railway Dashboard**

- View deployment status
- Monitor resource usage
- Check logs and errors

### **Database Monitoring**

- Query performance
- Connection counts
- Storage usage

### **Application Analytics**

- User queries tracked
- Response times
- Cost analysis
- User feedback

## 🎯 **Next Steps**

1. **Choose Database**: PostgreSQL (recommended)
2. **Deploy to Railway**: Follow step-by-step guide
3. **Configure Environment**: Set all required variables
4. **Initialize Database**: Run migration script
5. **Test Deployment**: Verify everything works
6. **Monitor Usage**: Track analytics and performance

## 💡 **Pro Tips**

- **Start with PostgreSQL**: Best balance of features and ease
- **Use Railway CLI**: Faster deployment and management
- **Monitor Costs**: Keep track of usage and costs
- **Backup Data**: Regular database backups
- **Scale Gradually**: Start small, scale as needed

Your query analytics system will be fully functional once deployed to Railway with PostgreSQL! 🎉
