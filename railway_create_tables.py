#!/usr/bin/env python3
"""
Railway PostgreSQL Table Creation Script
This script creates all required tables for Query Analytics in Railway PostgreSQL.
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

def get_database_url():
    """Get DATABASE_URL from environment or construct from Railway credentials."""
    # First try to get from environment variable
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        logger.info("Using DATABASE_URL from environment")
        return database_url
    
    # If not found, try to construct from Railway environment variables
    railway_db_host = os.getenv("RAILWAY_DATABASE_HOST")
    railway_db_port = os.getenv("RAILWAY_DATABASE_PORT", "5432")
    railway_db_name = os.getenv("RAILWAY_DATABASE_NAME", "railway")
    railway_db_user = os.getenv("RAILWAY_DATABASE_USER", "postgres")
    railway_db_password = os.getenv("RAILWAY_DATABASE_PASSWORD")
    
    if railway_db_host and railway_db_password:
        database_url = f"postgresql://{railway_db_user}:{railway_db_password}@{railway_db_host}:{railway_db_port}/{railway_db_name}"
        logger.info("Constructed DATABASE_URL from Railway environment variables")
        return database_url
    
    # If still not found, use the provided credentials
    # This is for local testing or when running directly
    railway_host = "containers-us-west-1.railway.app"  # Common Railway host
    railway_port = "5432"
    railway_database = "railway"
    railway_username = "postgres"
    railway_password = "eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE"
    
    database_url = f"postgresql://{railway_username}:{railway_password}@{railway_host}:{railway_port}/{railway_database}"
    logger.info("Using hardcoded Railway credentials for table creation")
    
    return database_url

def test_connection(database_url):
    """Test database connection."""
    logger.info("Testing database connection...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        logger.info(f"Database connection successful - PostgreSQL version: {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False

def create_tables(database_url):
    """Create all required tables for Query Analytics."""
    logger.info("Creating PostgreSQL tables for Query Analytics...")
    
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
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        logger.info("Executing table creation SQL...")
        
        # Execute the SQL to create tables
        cursor.execute(create_tables_sql)
        
        logger.info("Tables created successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Created tables: {existing_tables}")
        
        # Show table structure
        for table in existing_tables:
            cursor.execute("""
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable, 
                    column_default
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """, (table,))
            
            columns = cursor.fetchall()
            logger.info(f"Table {table} structure:")
            for col in columns:
                nullable = "YES" if col[2] == "YES" else "NO"
                default = col[3] or "None"
                logger.info(f"  {col[0]:<20} {col[1]:<15} {nullable:<10} {default}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_table_operations(database_url):
    """Test basic table operations."""
    logger.info("Testing table operations...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test session
        session_id = f"railway-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 1. Insert user query
        logger.info("Testing user query insertion...")
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Railway test query", session_id, "simple"))
        
        query_id = cursor.fetchone()[0]
        logger.info(f"User query inserted - ID: {query_id}")
        
        # 2. Insert AI response
        logger.info("Testing AI response insertion...")
        cursor.execute("""
            INSERT INTO ai_responses (query_id, response_text, model_used)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, "Railway test response", "claude-3-haiku"))
        
        response_id = cursor.fetchone()[0]
        logger.info(f"AI response inserted - ID: {response_id}")
        
        # 3. Insert user feedback
        logger.info("Testing user feedback insertion...")
        cursor.execute("""
            INSERT INTO user_feedback (query_id, response_id, feedback_type)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, response_id, "positive"))
        
        feedback_id = cursor.fetchone()[0]
        logger.info(f"User feedback inserted - ID: {feedback_id}")
        
        # 4. Test query
        logger.info("Testing data retrieval...")
        cursor.execute("""
            SELECT 
                q.query_text,
                r.response_text,
                f.feedback_type
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
            WHERE q.session_id = %s
        """, (session_id,))
        
        result = cursor.fetchone()
        if result:
            logger.info(f"Data retrieval successful:")
            logger.info(f"  Query: {result[0]}")
            logger.info(f"  Response: {result[1]}")
            logger.info(f"  Feedback: {result[2]}")
        
        # 5. Clean up test data
        logger.info("Cleaning up test data...")
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", (session_id,))
        conn.commit()
        logger.info("Test data cleaned up")
        
        cursor.close()
        conn.close()
        
        logger.info("All table operations working correctly!")
        return True
        
    except Exception as e:
        logger.error(f"Table operations test failed: {e}")
        return False

def main():
    """Main function to create PostgreSQL tables in Railway."""
    logger.info("🚀 Railway PostgreSQL Table Creation Script")
    logger.info("=" * 60)
    logger.info(f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get database URL
        database_url = get_database_url()
        logger.info(f"Using database URL: {database_url[:30]}...")
        
        # Test connection
        if not test_connection(database_url):
            logger.error("Cannot proceed without database connection")
            return 1
        
        # Create tables
        if not create_tables(database_url):
            logger.error("Failed to create tables")
            return 1
        
        # Test table operations
        if not test_table_operations(database_url):
            logger.error("Table operations test failed")
            return 1
        
        logger.info("🎉 PostgreSQL tables created successfully in Railway!")
        logger.info("✅ Query Analytics database is ready!")
        logger.info("✅ Tables: user_queries, ai_responses, user_feedback, query_sessions")
        logger.info("✅ Indexes created for performance")
        logger.info("✅ All operations tested and working")
        
        return 0
        
    except Exception as e:
        logger.error(f"Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
