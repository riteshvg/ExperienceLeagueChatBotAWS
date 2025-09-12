#!/usr/bin/env python3
"""
Railway Table Creator - Simple script to create tables on Railway deployment.
This script will run automatically when Railway deploys your app.
"""

import os
import sys
import psycopg2
from pathlib import Path
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_railway_database_url():
    """Get Railway database URL from environment variables."""
    # Try different ways to get the database URL
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        logger.info("Using DATABASE_URL from environment")
        return database_url
    
    # Try to construct from Railway environment variables
    railway_db_host = os.getenv("RAILWAY_DATABASE_HOST")
    railway_db_port = os.getenv("RAILWAY_DATABASE_PORT", "5432")
    railway_db_name = os.getenv("RAILWAY_DATABASE_NAME", "railway")
    railway_db_user = os.getenv("RAILWAY_DATABASE_USER", "postgres")
    railway_db_password = os.getenv("RAILWAY_DATABASE_PASSWORD")
    
    if railway_db_host and railway_db_password:
        database_url = f"postgresql://{railway_db_user}:{railway_db_password}@{railway_db_host}:{railway_db_port}/{railway_db_name}"
        logger.info("Constructed DATABASE_URL from Railway environment variables")
        return database_url
    
    # Fallback to hardcoded credentials (for Railway deployment)
    railway_host = os.getenv("RAILWAY_DATABASE_HOST", "containers-us-west-1.railway.app")
    railway_port = os.getenv("RAILWAY_DATABASE_PORT", "5432")
    railway_database = os.getenv("RAILWAY_DATABASE_NAME", "railway")
    railway_username = os.getenv("RAILWAY_DATABASE_USER", "postgres")
    railway_password = os.getenv("RAILWAY_DATABASE_PASSWORD", "eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE")
    
    database_url = f"postgresql://{railway_username}:{railway_password}@{railway_host}:{railway_port}/{railway_database}"
    logger.info("Using hardcoded Railway credentials for table creation")
    
    return database_url

def create_analytics_tables():
    """Create all required tables for Query Analytics."""
    logger.info("🗄️ Creating Query Analytics tables...")
    
    database_url = get_railway_database_url()
    if not database_url:
        logger.error("❌ No database URL available")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        logger.info("✅ Connected to Railway PostgreSQL database")
        
        # Create tables SQL
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
        
        # Execute table creation
        cursor.execute(create_tables_sql)
        conn.commit()
        
        logger.info("✅ Tables created successfully")
        
        # Verify tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"📊 Created tables: {existing_tables}")
        
        # Test table operations
        logger.info("🧪 Testing table operations...")
        
        # Insert test data
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Railway table creation test", "railway-test-123", "simple"))
        
        query_id = cursor.fetchone()[0]
        logger.info(f"✅ Test query inserted - ID: {query_id}")
        
        # Insert test response
        cursor.execute("""
            INSERT INTO ai_responses (query_id, response_text, model_used)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, "Railway test response", "claude-3-haiku"))
        
        response_id = cursor.fetchone()[0]
        logger.info(f"✅ Test response inserted - ID: {response_id}")
        
        # Insert test feedback
        cursor.execute("""
            INSERT INTO user_feedback (query_id, response_id, feedback_type)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, response_id, "positive"))
        
        feedback_id = cursor.fetchone()[0]
        logger.info(f"✅ Test feedback inserted - ID: {feedback_id}")
        
        # Test data retrieval
        cursor.execute("""
            SELECT 
                q.query_text,
                r.response_text,
                f.feedback_type
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
            WHERE q.session_id = %s
        """, ("railway-test-123",))
        
        result = cursor.fetchone()
        if result:
            logger.info(f"✅ Data retrieval test successful:")
            logger.info(f"   Query: {result[0]}")
            logger.info(f"   Response: {result[1]}")
            logger.info(f"   Feedback: {result[2]}")
        
        # Clean up test data
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", ("railway-test-123",))
        conn.commit()
        logger.info("✅ Test data cleaned up")
        
        cursor.close()
        conn.close()
        
        logger.info("🎉 Query Analytics tables created and tested successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    logger.info("🚀 Railway Table Creator")
    logger.info("=" * 50)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if we're running on Railway
    if os.getenv("RAILWAY_ENVIRONMENT"):
        logger.info("🌐 Running on Railway - creating tables...")
    else:
        logger.info("💻 Running locally - testing table creation...")
    
    # Create tables
    success = create_analytics_tables()
    
    if success:
        logger.info("✅ Table creation completed successfully!")
        logger.info("🎯 Query Analytics should now work in your app")
        return 0
    else:
        logger.error("❌ Table creation failed!")
        logger.error("🔧 Check Railway logs for more details")
        return 1

if __name__ == "__main__":
    exit(main())
