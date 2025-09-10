# .env Configuration Setup Guide

This guide will walk you through setting up your environment configuration step by step.

## 🚀 Quick Start

```bash
# 1. Copy the template
cp env.template .env

# 2. Edit the .env file with your actual values
nano .env  # or use your preferred editor
```

## 📋 Step-by-Step Configuration

### Step 1: Basic Application Setup

Start with these essential settings:

```bash
# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=false

# Generate a secret key (run this command)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### Step 2: AWS Configuration

#### Option A: Using AWS Access Keys (Recommended for development)

1. **Get AWS Credentials:**

   - Go to [AWS IAM Console](https://console.aws.amazon.com/iam/)
   - Create a new user or use existing user
   - Attach policies: `AmazonS3FullAccess`, `AmazonBedrockFullAccess`, `IAMFullAccess`
   - Create access keys

2. **Configure in .env:**
   ```bash
   AWS_ACCESS_KEY_ID=AKIA...
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_DEFAULT_REGION=us-east-1
   AWS_S3_BUCKET=adobe-analytics-rag-docs-your-unique-name
   ```

#### Option B: Using AWS Profile (Recommended for production)

1. **Configure AWS CLI:**

   ```bash
   aws configure --profile adobe-rag
   ```

2. **Set in .env:**
   ```bash
   AWS_PROFILE=adobe-rag
   # Comment out or remove AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
   ```

### Step 3: Adobe Analytics API Setup (OAuth Server-to-Server)

1. **Go to Adobe Developer Console:**

   - Visit [https://developer.adobe.com/](https://developer.adobe.com/)
   - Sign in with your Adobe ID

2. **Create a New Project:**

   - Click "Create new project"
   - Choose "API" → "Adobe Analytics API"
   - Select your organization

3. **Create OAuth Server-to-Server Credentials:**

   - In your project, go to "API" tab
   - Click "Add to project" → "API"
   - Select "Adobe Analytics API"
   - Choose "OAuth Server-to-Server" (not JWT - deprecated as of June 2025)

4. **Get Required Credentials:**

   - **Client ID**: Found in project overview
   - **Client Secret**: Generate if not exists
   - **Organization ID**: Found in project overview

5. **Configure in .env:**
   ```bash
   ADOBE_CLIENT_ID=your_client_id
   ADOBE_CLIENT_SECRET=your_client_secret
   ADOBE_ORGANIZATION_ID=your_org_id
   ```

**Note:** JWT authentication with private keys is deprecated. Adobe now requires OAuth Server-to-Server credentials for all server-to-server integrations.

### Step 4: AI/LLM Configuration

#### Option A: OpenAI (Recommended)

1. **Get OpenAI API Key:**

   - Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Create a new API key

2. **Configure in .env:**
   ```bash
   OPENAI_API_KEY=sk-...
   ```

#### Option B: Azure OpenAI

1. **Get Azure OpenAI credentials:**

   - Go to Azure Portal
   - Create Azure OpenAI resource
   - Get endpoint and API key

2. **Configure in .env:**

   ```bash
   # Comment out OPENAI_API_KEY
   # OPENAI_API_KEY=sk-...

   # Uncomment and configure Azure settings
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your_azure_key
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
   ```

### Step 5: RAG Configuration (Optional)

For advanced users, you can customize the RAG settings:

```bash
# Text chunking (adjust based on your document types)
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Embedding model (faster vs more accurate)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Fast
# EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2  # More accurate

# Vector store location
VECTOR_STORE_PATH=./vector_store
```

### Step 6: Database Configuration

#### Option A: SQLite (Default - No setup required)

```bash
DATABASE_URL=sqlite:///./adobe_analytics_rag.db
```

#### Option B: PostgreSQL (For production)

```bash
# Install PostgreSQL first
# sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian
# brew install postgresql  # macOS

# Create database
createdb adobe_analytics_rag

# Configure in .env
DATABASE_URL=postgresql://username:password@localhost:5432/adobe_analytics_rag
```

## 🔧 Configuration Validation

### Test Your Configuration

Create a simple test script to validate your setup:

```python
# test_config.py
import os
from dotenv import load_dotenv
from config.settings import get_settings

# Load environment variables
load_dotenv()

try:
    settings = get_settings()
    print("✅ Configuration loaded successfully!")
    print(f"Environment: {settings.environment}")
    print(f"AWS Region: {settings.aws_default_region}")
    print(f"S3 Bucket: {settings.aws_s3_bucket}")
    print(f"Adobe Org ID: {settings.adobe_organization_id}")
    print(f"OpenAI API Key: {'Set' if settings.openai_api_key else 'Not set'}")
except Exception as e:
    print(f"❌ Configuration error: {e}")
```

Run the test:

```bash
python test_config.py
```

## 🚨 Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'boto3'"

**Solution:**

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Issue 2: "AWS credentials not found"

**Solution:**

```bash
# Option 1: Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Option 2: Configure AWS CLI
aws configure

# Option 3: Use AWS profile in .env
AWS_PROFILE=your_profile_name
```

### Issue 3: "Adobe private key not found"

**Solution:**

1. Download the private key from Adobe Developer Console
2. Place it in your project root
3. Update the path in .env:
   ```bash
   ADOBE_PRIVATE_KEY_PATH=./adobe_private_key.pem
   ```

### Issue 4: "OpenAI API key invalid"

**Solution:**

1. Check your API key at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Ensure you have credits in your OpenAI account
3. Verify the key is correctly set in .env

## 🔒 Security Best Practices

1. **Never commit .env to version control**
2. **Use environment-specific .env files** (.env.dev, .env.prod)
3. **Rotate API keys regularly**
4. **Use IAM roles instead of access keys when possible**
5. **Store sensitive data in AWS Secrets Manager for production**

## 📝 Next Steps

After completing the .env setup:

1. **Run the AWS infrastructure setup:**

   ```bash
   python scripts/setup_aws_infrastructure.py
   ```

2. **Test the configuration:**

   ```bash
   python test_config.py
   ```

3. **Start the application:**
   ```bash
   streamlit run src/app.py
   ```

## 🆘 Need Help?

- Check the logs in `./logs/` directory
- Run with debug mode: `DEBUG=true python your_script.py`
- Verify each service individually before running the full application
