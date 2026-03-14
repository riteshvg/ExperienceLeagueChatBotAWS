"""
Core configuration management for FastAPI backend.
Reuses existing Settings from config/settings.py
"""
import sys
from pathlib import Path

# Add project root to path to import existing config
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings

# Create global settings instance
settings = Settings()

# API Configuration
API_V1_PREFIX = "/api/v1"
PROJECT_NAME = "Adobe Experience League Chatbot API"
VERSION = "1.0.0"

# CORS Configuration
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite default
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# Security
SECRET_KEY = settings.secret_key if hasattr(settings, 'secret_key') else "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

