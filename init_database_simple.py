#!/usr/bin/env python3
"""
Simple database initialization script for Railway deployment.
Creates PostgreSQL tables directly without complex imports.
"""

import os
import sys
import psycopg2
from pathlib import Path

def get_database_url():
    """Get database URL from environment variables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Construct from individual variables
        host = os.getenv("DATABASE_HOST", "localhost")
        port = os.getenv("DATABASE_PORT", "5432")
        database = os.getenv("DATABASE_NAME", "railway")
        username = os.getenv("DATABASE_USERNAME", "postgres")
        password = os.getenv("DATABASE_PASSWORD", "")
        
        database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    return database_url

def create_tables():
    """Create all required tables in PostgreSQL."""
    
    # SQL to create all tables
    create_tables_sql = """
    -- User queries table
    CREATE TABLE IF NOT EXISTS user_queries (
        id SERIAL PRIMARY KEY,
        query_text TEXT NOT NULL,
        session_id VARCHAR(255),
        query_complexity VARCHAR(50) DEFAULT 'medium',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- AI responses table
    CREATE TABLE IF NOT EXISTS ai_responses (
        id SERIAL PRIMARY KEY,
        query_id INTEGER REFERENCES user_queries(id) ON DELETE CASCADE,
        response_text TEXT NOT NULL,
        model_used VARCHAR(100),
        response_time_ms INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- User feedback table
    CREATE TABLE IF NOT EXISTS user_feedback (
        id SERIAL PRIMARY KEY,
        query_id INTEGER REFERENCES user_queries(id) ON DELETE CASCADE,
        response_id INTEGER REFERENCES ai_responses(id) ON DELETE CASCADE,
        feedback_type VARCHAR(50) NOT NULL,
        feedback_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Query sessions table
    CREATE TABLE IF NOT EXISTS query_sessions (
        id VARCHAR(255) PRIMARY KEY,
        user_id VARCHAR(255),
        session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        session_end TIMESTAMP,
        total_queries INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_user_queries_session_id ON user_queries(session_id);
    CREATE INDEX IF NOT EXISTS idx_user_queries_created_at ON user_queries(created_at);
    CREATE INDEX IF NOT EXISTS idx_ai_responses_query_id ON ai_responses(query_id);
    CREATE INDEX IF NOT EXISTS idx_user_feedback_query_id ON user_feedback(query_id);
    CREATE INDEX IF NOT EXISTS idx_user_feedback_response_id ON user_feedback(response_id);
    """
    
    try:
        database_url = get_database_url()
        print(f"🔧 Connecting to database...")
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected to PostgreSQL database")
        
        # Execute the SQL to create tables
        print("🔧 Creating database tables...")
        cursor.execute(create_tables_sql)
        
        print("✅ Database tables created successfully!")
        
        # Test the tables
        cursor.execute("SELECT COUNT(*) FROM user_queries")
        count = cursor.fetchone()[0]
        print(f"✅ user_queries table ready (rows: {count})")
        
        cursor.execute("SELECT COUNT(*) FROM ai_responses")
        count = cursor.fetchone()[0]
        print(f"✅ ai_responses table ready (rows: {count})")
        
        cursor.execute("SELECT COUNT(*) FROM user_feedback")
        count = cursor.fetchone()[0]
        print(f"✅ user_feedback table ready (rows: {count})")
        
        cursor.execute("SELECT COUNT(*) FROM query_sessions")
        count = cursor.fetchone()[0]
        print(f"✅ query_sessions table ready (rows: {count})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def main():
    """Main initialization function."""
    print("🚀 Simple Database Initialization Script")
    print("=" * 50)
    
    # Check if we're on Railway
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("DATABASE_URL"):
        print("🌐 Railway environment detected - using PostgreSQL")
        success = create_tables()
    else:
        print("💻 Local environment detected - skipping PostgreSQL setup")
        print("ℹ️  Use SQLite for local development")
        success = True
    
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
