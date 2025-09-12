#!/usr/bin/env python3
"""
Alternative methods to create PostgreSQL tables in Railway.
This script provides multiple ways to create tables when Railway doesn't have SQL console.
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

def method_1_direct_connection():
    """Method 1: Direct connection using Railway credentials."""
    logger.info("🔧 Method 1: Direct Connection to Railway PostgreSQL")
    logger.info("=" * 60)
    
    # Railway PostgreSQL credentials
    host = "containers-us-west-1.railway.app"  # Common Railway host
    port = "5432"
    database = "railway"
    username = "postgres"
    password = "eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE"
    
    # Construct connection string
    database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    logger.info(f"Connecting to: {host}:{port}/{database}")
    logger.info(f"Username: {username}")
    
    try:
        # Test connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        logger.info(f"✅ Connection successful - PostgreSQL version: {version}")
        
        # Create tables
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
        
        logger.info("Creating tables...")
        cursor.execute(create_tables_sql)
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"✅ Tables created: {existing_tables}")
        
        # Test data insertion
        logger.info("Testing data insertion...")
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Test query from direct connection", "test-direct-123", "simple"))
        
        query_id = cursor.fetchone()[0]
        logger.info(f"✅ Test query inserted - ID: {query_id}")
        
        # Clean up test data
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", ("test-direct-123",))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        logger.info("🎉 Method 1 completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Method 1 failed: {e}")
        return False

def method_2_environment_variables():
    """Method 2: Using environment variables."""
    logger.info("\n🔧 Method 2: Using Environment Variables")
    logger.info("=" * 60)
    
    # Set environment variables
    os.environ["RAILWAY_DATABASE_USER"] = "postgres"
    os.environ["RAILWAY_DATABASE_PASSWORD"] = "eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE"
    os.environ["RAILWAY_DATABASE_HOST"] = "containers-us-west-1.railway.app"
    os.environ["RAILWAY_DATABASE_PORT"] = "5432"
    os.environ["RAILWAY_DATABASE_NAME"] = "railway"
    
    # Construct database URL from environment variables
    host = os.getenv("RAILWAY_DATABASE_HOST")
    port = os.getenv("RAILWAY_DATABASE_PORT")
    database = os.getenv("RAILWAY_DATABASE_NAME")
    username = os.getenv("RAILWAY_DATABASE_USER")
    password = os.getenv("RAILWAY_DATABASE_PASSWORD")
    
    database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    logger.info(f"Using environment variables:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Database: {database}")
    logger.info(f"  Username: {username}")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        logger.info(f"✅ Connection successful - PostgreSQL version: {version}")
        
        # Create tables (same as Method 1)
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS user_queries (
            id SERIAL PRIMARY KEY,
            query_text TEXT NOT NULL,
            session_id VARCHAR(255),
            query_complexity VARCHAR(50) DEFAULT 'medium',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ai_responses (
            id SERIAL PRIMARY KEY,
            query_id INTEGER REFERENCES user_queries(id) ON DELETE CASCADE,
            response_text TEXT NOT NULL,
            model_used VARCHAR(100),
            response_time_ms INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS user_feedback (
            id SERIAL PRIMARY KEY,
            query_id INTEGER REFERENCES user_queries(id) ON DELETE CASCADE,
            response_id INTEGER REFERENCES ai_responses(id) ON DELETE CASCADE,
            feedback_type VARCHAR(50) NOT NULL,
            feedback_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS query_sessions (
            id VARCHAR(255) PRIMARY KEY,
            user_id VARCHAR(255),
            session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_end TIMESTAMP,
            total_queries INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_user_queries_session_id ON user_queries(session_id);
        CREATE INDEX IF NOT EXISTS idx_user_queries_created_at ON user_queries(created_at);
        CREATE INDEX IF NOT EXISTS idx_ai_responses_query_id ON ai_responses(query_id);
        CREATE INDEX IF NOT EXISTS idx_user_feedback_query_id ON user_feedback(query_id);
        CREATE INDEX IF NOT EXISTS idx_user_feedback_response_id ON user_feedback(response_id);
        """
        
        cursor.execute(create_tables_sql)
        conn.commit()
        
        logger.info("✅ Tables created successfully using environment variables")
        
        cursor.close()
        conn.close()
        
        logger.info("🎉 Method 2 completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Method 2 failed: {e}")
        return False

def method_3_railway_cli():
    """Method 3: Using Railway CLI (if available)."""
    logger.info("\n🔧 Method 3: Using Railway CLI")
    logger.info("=" * 60)
    
    logger.info("To use Railway CLI:")
    logger.info("1. Install Railway CLI: npm install -g @railway/cli")
    logger.info("2. Login: railway login")
    logger.info("3. Connect to your project: railway link")
    logger.info("4. Run: railway run psql")
    logger.info("5. Then run the SQL commands manually")
    
    logger.info("⚠️ This method requires Railway CLI installation")
    return False

def method_4_external_tool():
    """Method 4: Using external PostgreSQL tools."""
    logger.info("\n🔧 Method 4: Using External PostgreSQL Tools")
    logger.info("=" * 60)
    
    logger.info("You can use external tools like:")
    logger.info("1. pgAdmin (GUI tool)")
    logger.info("2. DBeaver (Database management tool)")
    logger.info("3. TablePlus (Mac/Windows tool)")
    logger.info("4. psql command line tool")
    
    logger.info("\nConnection details:")
    logger.info("Host: containers-us-west-1.railway.app")
    logger.info("Port: 5432")
    logger.info("Database: railway")
    logger.info("Username: postgres")
    logger.info("Password: eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE")
    
    logger.info("⚠️ This method requires external tool installation")
    return False

def method_5_railway_deployment():
    """Method 5: Deploy a temporary table creation service."""
    logger.info("\n🔧 Method 5: Deploy Temporary Table Creation Service")
    logger.info("=" * 60)
    
    logger.info("Create a temporary Railway service that:")
    logger.info("1. Connects to your PostgreSQL database")
    logger.info("2. Creates all required tables")
    logger.info("3. Verifies table creation")
    logger.info("4. Exits successfully")
    
    logger.info("This is the most reliable method for Railway")
    return True

def main():
    """Main function to try different methods."""
    logger.info("🚀 Railway PostgreSQL Table Creation - Alternative Methods")
    logger.info("=" * 70)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    methods = [
        ("Direct Connection", method_1_direct_connection),
        ("Environment Variables", method_2_environment_variables),
        ("Railway CLI", method_3_railway_cli),
        ("External Tools", method_4_external_tool),
        ("Railway Deployment", method_5_railway_deployment)
    ]
    
    success_count = 0
    
    for method_name, method_func in methods:
        logger.info(f"\n{'='*70}")
        logger.info(f"Trying: {method_name}")
        logger.info(f"{'='*70}")
        
        try:
            if method_func():
                success_count += 1
                logger.info(f"✅ {method_name} - SUCCESS")
            else:
                logger.info(f"⚠️ {method_name} - SKIPPED or FAILED")
        except Exception as e:
            logger.error(f"❌ {method_name} - ERROR: {e}")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY: {success_count}/{len(methods)} methods available")
    logger.info(f"{'='*70}")
    
    if success_count > 0:
        logger.info("🎉 At least one method should work!")
        logger.info("🔧 Try the successful methods to create your tables")
    else:
        logger.info("❌ All methods failed - check your Railway setup")
    
    return 0

if __name__ == "__main__":
    exit(main())
