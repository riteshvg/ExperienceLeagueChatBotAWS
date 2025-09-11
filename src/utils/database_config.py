"""
Database configuration utilities for different deployment environments.
"""

import os
from typing import Optional
from ..models.database_models import DatabaseConfig


def get_database_config() -> DatabaseConfig:
    """Get database configuration based on environment variables."""
    
    # Check if we're running on Railway
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("DATABASE_URL"):
        # Parse Railway DATABASE_URL if available
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            # Parse PostgreSQL URL: postgresql://user:password@host:port/database
            import urllib.parse
            parsed = urllib.parse.urlparse(database_url)
            return DatabaseConfig(
                host=parsed.hostname or "localhost",
                port=parsed.port or 5432,
                database=parsed.path.lstrip('/') or "railway",
                username=parsed.username or "postgres",
                password=parsed.password or "",
                database_type="postgresql"
            )
        else:
            # Fallback to individual environment variables
            return DatabaseConfig(
                host=os.getenv("DATABASE_HOST", "localhost"),
                port=int(os.getenv("DATABASE_PORT", "5432")),
                database=os.getenv("DATABASE_NAME", "railway"),
                username=os.getenv("DATABASE_USERNAME", "postgres"),
                password=os.getenv("DATABASE_PASSWORD", ""),
                database_type="postgresql"
            )
    
    # Check if we're using SQLite for local development
    elif os.getenv("USE_SQLITE", "false").lower() == "true":
        return DatabaseConfig(
            database_type="sqlite",
            database=os.getenv("SQLITE_DATABASE", "analytics.db")
        )
    
    # Default to MySQL for local development
    else:
        return DatabaseConfig(
            host=os.getenv("DATABASE_HOST", "localhost"),
            port=int(os.getenv("DATABASE_PORT", "3306")),
            database=os.getenv("DATABASE_NAME", "chatbot_analytics"),
            username=os.getenv("DATABASE_USERNAME", "root"),
            password=os.getenv("DATABASE_PASSWORD", ""),
            database_type=os.getenv("DATABASE_TYPE", "mysql")
        )


def get_connection_string() -> str:
    """Get database connection string for current environment."""
    config = get_database_config()
    return config.connection_string


def is_railway_deployment() -> bool:
    """Check if running on Railway."""
    return os.getenv("RAILWAY_ENVIRONMENT") is not None


def is_sqlite_deployment() -> bool:
    """Check if using SQLite."""
    return os.getenv("USE_SQLITE", "false").lower() == "true"


def get_database_info() -> dict:
    """Get database information for debugging."""
    config = get_database_config()
    return {
        "type": config.database_type,
        "host": config.host,
        "port": config.port,
        "database": config.database,
        "username": config.username,
        "is_railway": is_railway_deployment(),
        "is_sqlite": is_sqlite_deployment()
    }
