#!/usr/bin/env python3
"""
Database initialization script for Railway deployment.
Creates all necessary tables for the analytics system.
"""

import os
import sys
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

def init_postgresql_database():
    """Initialize PostgreSQL database with required tables."""
    try:
        from src.integrations.streamlit_analytics import initialize_analytics_service
        
        print("🔧 Initializing PostgreSQL database...")
        
        # Initialize analytics service (this will create tables)
        analytics_service = initialize_analytics_service()
        
        if analytics_service:
            print("✅ Database tables created successfully!")
            print("✅ Analytics service initialized")
            return True
        else:
            print("❌ Failed to initialize analytics service")
            return False
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def init_sqlite_database():
    """Initialize SQLite database for local testing."""
    try:
        from src.services.sqlite_analytics_service import SQLiteAnalyticsService
        
        print("🔧 Initializing SQLite database...")
        
        # Create SQLite database
        db_path = "analytics.db"
        analytics_service = SQLiteAnalyticsService(db_path)
        
        print("✅ SQLite database created successfully!")
        print(f"✅ Database file: {db_path}")
        return True
        
    except Exception as e:
        print(f"❌ SQLite initialization failed: {e}")
        return False

def main():
    """Main initialization function."""
    print("🚀 Database Initialization Script")
    print("=" * 50)
    
    # Check if we're on Railway (PostgreSQL) or local (SQLite)
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("DATABASE_URL"):
        print("🌐 Railway environment detected - using PostgreSQL")
        success = init_postgresql_database()
    else:
        print("💻 Local environment detected - using SQLite")
        success = init_sqlite_database()
    
    if success:
        print("\n🎉 Database initialization completed successfully!")
        print("✅ Your application is ready to run")
        return 0
    else:
        print("\n❌ Database initialization failed!")
        print("🔧 Please check the error messages above")
        return 1

if __name__ == "__main__":
    exit(main())
