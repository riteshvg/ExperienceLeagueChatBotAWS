# Railway Deployment Guide

## Overview
This guide explains how to deploy the Experience League Chatbot to Railway.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Code should be pushed to GitHub
3. **AWS Credentials**: Have AWS credentials ready for environment variables

## Deployment Steps

### 1. Connect GitHub Repository

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose `riteshvg/ExperienceLeagueChatBotAWS`
5. Railway will automatically detect the project

### 2. Configure Environment Variables

In Railway project settings, add these environment variables:

#### AWS Configuration
```
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=your-s3-bucket-name
```

#### Bedrock Configuration
```
BEDROCK_KNOWLEDGE_BASE_ID=your_knowledge_base_id
BEDROCK_MODEL_ID=us.anthropic.claude-3-7-sonnet-20250219-v1:0
BEDROCK_REGION=us-east-1
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
```

#### Application Configuration
```
ENVIRONMENT=production
LOG_LEVEL=INFO
PORT=8000
```

#### Frontend Configuration (Optional)
```
VITE_API_URL=https://your-backend-url.railway.app
```

### 3. Railway Configuration Files

The project includes:
- **`railway.toml`**: Railway deployment configuration
- **`Procfile`**: Process file for Railway
- **`start.sh`**: Startup script for Railway

### 4. Build Configuration

Railway will automatically:
1. Detect the project structure
2. Install backend dependencies (`pip install -r backend/requirements.txt`)
3. Install frontend dependencies (`npm install` in `frontend/`)
4. Build frontend (`npm run build`)
5. Start services using `start.sh`

### 5. Service Architecture

#### Option 1: Single Service (Recommended)
- Backend and frontend run in the same Railway service
- Backend serves API on port 8000
- Frontend serves static files on port 3000
- Both proxied through Railway's load balancer

#### Option 2: Separate Services
- Create two Railway services:
  - **Backend Service**: FastAPI application
  - **Frontend Service**: Static site with Vite build

### 6. Health Check

Railway will check health at:
- **Path**: `/api/v1/health`
- **Timeout**: 100 seconds

### 7. Custom Domain (Optional)

1. Go to project settings
2. Click "Generate Domain" or add custom domain
3. Update `VITE_API_URL` if using separate frontend service

## Deployment Scripts

### `start.sh`
Main deployment script that:
- Detects Railway environment
- Installs dependencies
- Builds frontend
- Starts backend and frontend services

### `railway.toml`
Railway-specific configuration:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "./start.sh"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
```

## Troubleshooting

### Build Failures

1. **Python Dependencies**: Check `backend/requirements.txt` is correct
2. **Node Dependencies**: Check `frontend/package.json` is correct
3. **Build Logs**: Check Railway build logs for errors

### Runtime Errors

1. **Environment Variables**: Verify all required env vars are set
2. **Port Configuration**: Ensure `PORT` env var is set (Railway sets this automatically)
3. **AWS Credentials**: Verify AWS credentials have correct permissions

### Health Check Failures

1. **Backend Not Starting**: Check backend logs in Railway
2. **Port Issues**: Verify backend is listening on correct port
3. **Dependencies**: Ensure all Python packages are installed

## Monitoring

- **Logs**: View real-time logs in Railway dashboard
- **Metrics**: Monitor CPU, memory, and network usage
- **Deployments**: Track deployment history and rollbacks

## Cost Optimization

1. **Sleep on Idle**: Enable sleep mode for development environments
2. **Resource Limits**: Set appropriate CPU/memory limits
3. **Auto-scaling**: Configure auto-scaling based on traffic

## Next Steps

After deployment:
1. Test the health endpoint: `https://your-app.railway.app/api/v1/health`
2. Test the frontend: `https://your-app.railway.app`
3. Monitor logs for any errors
4. Set up custom domain if needed

## Support

For Railway-specific issues:
- [Railway Documentation](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)

