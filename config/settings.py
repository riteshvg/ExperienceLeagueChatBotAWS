"""
Configuration management for Adobe Analytics RAG Chatbot.
"""

import os
from pathlib import Path
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # AWS Configuration
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_default_region: str = Field(default="us-east-1", env="AWS_DEFAULT_REGION")
    aws_s3_bucket: Optional[str] = Field(None, env="AWS_S3_BUCKET")
    
    # Adobe Analytics API Configuration (OAuth Server-to-Server)
    adobe_client_id: Optional[str] = Field(None, env="ADOBE_CLIENT_ID")
    adobe_client_secret: Optional[str] = Field(None, env="ADOBE_CLIENT_SECRET")
    adobe_organization_id: Optional[str] = Field(None, env="ADOBE_ORGANIZATION_ID")
    # Note: JWT authentication deprecated, using OAuth Server-to-Server
    
    # AI/LLM Configuration
    # Option 1: OpenAI
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    
    # Option 2: AWS Bedrock (recommended for AWS-native setup)
    bedrock_model_id: str = Field(default="us.anthropic.claude-3-7-sonnet-20250219-v1:0", env="BEDROCK_MODEL_ID")
    bedrock_region: str = Field(default="us-east-1", env="BEDROCK_REGION")
    bedrock_embedding_model_id: str = Field(default="amazon.titan-embed-text-v2:0", env="BEDROCK_EMBEDDING_MODEL_ID")
    bedrock_knowledge_base_id: Optional[str] = Field(None, env="BEDROCK_KNOWLEDGE_BASE_ID")
    
    # Application Configuration
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./adobe_analytics_rag.db", env="DATABASE_URL")
    
    # Streamlit Configuration
    streamlit_server_port: int = Field(default=8501, env="STREAMLIT_SERVER_PORT")
    streamlit_server_address: str = Field(default="0.0.0.0", env="STREAMLIT_SERVER_ADDRESS")
    
    # RAG Configuration
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    vector_store_path: str = Field(default="./vector_store", env="VECTOR_STORE_PATH")
    
    # Retrieval Configuration
    similarity_threshold: float = Field(default=0.6, env="SIMILARITY_THRESHOLD")
    min_retrieval_results: int = Field(default=3, env="MIN_RETRIEVAL_RESULTS")
    max_retrieval_results: int = Field(default=8, env="MAX_RETRIEVAL_RESULTS")
    
    # Citation URL Validation
    validate_citation_urls: bool = Field(default=True, env="VALIDATE_CITATION_URLS")
    citation_url_timeout: int = Field(default=3, env="CITATION_URL_TIMEOUT")
    
    # Data Pipeline Configuration
    data_refresh_interval: int = Field(default=3600, env="DATA_REFRESH_INTERVAL")  # 1 hour
    max_documents: int = Field(default=10000, env="MAX_DOCUMENTS")
    
    # Query Enhancement Configuration
    query_enhancement_enabled: bool = Field(default=True, env="QUERY_ENHANCEMENT_ENABLED")
    query_enhancement_max_queries: int = Field(default=3, env="QUERY_ENHANCEMENT_MAX_QUERIES")
    query_enhancement_cache_size: int = Field(default=500, env="QUERY_ENHANCEMENT_CACHE_SIZE")
    query_enhancement_timeout_ms: int = Field(default=400, env="QUERY_ENHANCEMENT_TIMEOUT_MS")
    query_enhancement_fallback: bool = Field(default=True, env="QUERY_ENHANCEMENT_FALLBACK")
    
    # Hybrid Model Configuration
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    demo_password: str = Field(default="demo123", env="DEMO_PASSWORD")
    
    # Auto-Retraining Configuration
    retraining_s3_bucket: Optional[str] = Field(None, env="RETRAINING_S3_BUCKET")
    bedrock_role_arn: Optional[str] = Field(None, env="BEDROCK_ROLE_ARN")
    retraining_threshold: int = Field(default=3, env="RETRAINING_THRESHOLD")
    quality_threshold: int = Field(default=3, env="QUALITY_THRESHOLD")
    retraining_cooldown: int = Field(default=60, env="RETRAINING_COOLDOWN")
    enable_claude_retraining: bool = Field(default=True, env="ENABLE_CLAUDE_RETRAINING")
    enable_gemini_retraining: bool = Field(default=False, env="ENABLE_GEMINI_RETRAINING")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields to be ignored


def get_settings() -> Settings:
    """Get application settings instance."""
    try:
        return Settings()
    except Exception as e:
        print(f"⚠️  Warning: Some environment variables are missing: {e}")
        print("🔧 Using default values for missing configuration")
        return Settings()


# Global settings instance - load lazily to avoid import-time errors
_settings_instance = None

def get_settings_instance() -> Settings:
    """Get or create settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = get_settings()
    return _settings_instance

# For backward compatibility
settings = get_settings_instance()


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """Get the data directory path."""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """Get the logs directory path."""
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


def get_models_dir() -> Path:
    """Get the models directory path."""
    models_dir = get_project_root() / "models"
    models_dir.mkdir(exist_ok=True)
    return models_dir


def get_vector_store_dir() -> Path:
    """Get the vector store directory path."""
    vector_store_dir = get_project_root() / settings.vector_store_path
    vector_store_dir.mkdir(exist_ok=True)
    return vector_store_dir
