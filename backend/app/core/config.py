"""
Core configuration management for FastAPI backend.
Reuses existing Settings from config/settings.py
"""
import sys
from pathlib import Path

# Add project root to path to import existing config
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.settings import Settings
    print("[OK] Settings module imported successfully")
except Exception as e:
    print(f"[WARN] Failed to import Settings: {e}")
    print("[WARN] This may cause issues - attempting to continue...")
    # Don't raise - let the Settings() call below handle it with fallback
    Settings = None

# Create global settings instance with error handling
if Settings is None:
    print("[WARN] Settings class not available - using minimal defaults")
    class MinimalSettings:
        aws_default_region = "us-east-1"
        bedrock_region = "us-east-1"
        bedrock_model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        bedrock_embedding_model_id = "amazon.titan-embed-text-v2:0"
        bedrock_knowledge_base_id = None
        aws_access_key_id = None
        aws_secret_access_key = None
        aws_s3_bucket = None
        database_url = "sqlite:///./adobe_analytics_rag.db"
        def validate_aws_config(self):
            return ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"]
    settings = MinimalSettings()
else:
    try:
        settings = Settings()
        print("[OK] Settings instance created successfully")
        # Validate AWS configuration at startup
        missing_aws = settings.validate_aws_config()
        if missing_aws:
            print(f"[WARN] Missing AWS environment variables: {', '.join(missing_aws)}")
            print("[WARN] AWS features will not work until these are configured")
        else:
            print("[OK] AWS environment variables configured")
    except Exception as e:
        print(f"[WARN] Failed to create Settings instance: {e}")
        print("[WARN] Using default values - some features may not work")
        # Create a minimal settings object to prevent crashes
        class MinimalSettings:
            aws_default_region = "us-east-1"
            bedrock_region = "us-east-1"
            bedrock_model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
            bedrock_embedding_model_id = "amazon.titan-embed-text-v2:0"
            bedrock_knowledge_base_id = None
            aws_access_key_id = None
            aws_secret_access_key = None
            aws_s3_bucket = None
            database_url = "sqlite:///./adobe_analytics_rag.db"
            def validate_aws_config(self):
                return ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"]
        settings = MinimalSettings()

# API Configuration
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "Adobe Experience League Chatbot API"
VERSION = "1.0.0"

# CORS Configuration
# In production (Railway), frontend is served from the same origin, so CORS is less critical
# But we allow common origins for development and flexibility
import os
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    # Allow all origins in production (Railway) - frontend is served from same domain anyway
    # For stricter security, you can restrict this to specific domains
] if os.getenv("RAILWAY_ENVIRONMENT") is None else ["*"]

# Security
SECRET_KEY = settings.secret_key if hasattr(settings, 'secret_key') else "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

