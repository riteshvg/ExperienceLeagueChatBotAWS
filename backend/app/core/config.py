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
    print("✅ Settings module imported successfully")
except Exception as e:
    print(f"⚠️  Warning: Failed to import Settings: {e}")
    raise

# Create global settings instance with error handling
try:
    settings = Settings()
    print("✅ Settings instance created successfully")
except Exception as e:
    print(f"⚠️  Warning: Failed to create Settings instance: {e}")
    print("⚠️  Using default values - some features may not work")
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

