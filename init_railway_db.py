#!/usr/bin/env python3
"""
Railway-specific database initialization with better error handling.
"""

import os
import sys
import psycopg2
from pathlib import Path
import time

def get_database_url():
    """Get database URL from Railway environment variables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return None
    
    print(f"✅ DATABASE_URL found: {database_url[:20]}...")
    return database_url

def wait_for_database(database_url, max_retries=10):
    """Wait for database to be ready."""
    print("⏳ Waiting for database to be ready...")
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(database_url)
            conn.close()
            print("✅ Database is ready")
            return True
        except Exception as e:
            print(f"⏳ Attempt {attempt + 1}/{max_retries}: Database not ready yet ({e})")
            time.sleep(2)
    
    print("❌ Database not ready after maximum retries")
    return False

def create_tables(database_url):
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
        print("🔧 Connecting to Railway PostgreSQL database...")
        
        # Wait for database to be ready
        if not wait_for_database(database_url):
            return False
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected to Railway PostgreSQL database")
        
        # Check if tables already exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Existing tables: {existing_tables}")
        
        required_tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            print(f"🔧 Creating missing tables: {missing_tables}")
            
            # Execute the SQL to create tables
            cursor.execute(create_tables_sql)
            
            print("✅ Database tables created successfully!")
        else:
            print("✅ All required tables already exist")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
        """)
        
        final_tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Final tables: {final_tables}")
        
        # Test inserting sample data
        print("🧪 Testing database functionality...")
        
        # Insert sample query
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Railway test query", "railway-test-session", "simple"))
        
        query_id = cursor.fetchone()[0]
        print(f"✅ Sample query inserted with ID: {query_id}")
        
        # Insert sample response
        cursor.execute("""
            INSERT INTO ai_responses (query_id, response_text, model_used, response_time_ms)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (query_id, "Railway test response", "claude-3-haiku", 1200))
        
        response_id = cursor.fetchone()[0]
        print(f"✅ Sample response inserted with ID: {response_id}")
        
        # Insert sample feedback
        cursor.execute("""
            INSERT INTO user_feedback (query_id, response_id, feedback_type, feedback_text)
            VALUES (%s, %s, %s, %s)
        """, (query_id, response_id, "positive", "Railway test feedback"))
        
        print("✅ Sample feedback inserted")
        
        # Test querying data
        cursor.execute("""
            SELECT COUNT(*) FROM user_queries WHERE session_id = %s
        """, ("railway-test-session",))
        
        count = cursor.fetchone()[0]
        print(f"✅ Query test successful: {count} records found")
        
        # Clean up test data
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", ("railway-test-session",))
        print("✅ Test data cleaned up")
        
        cursor.close()
        conn.close()
        
        print("🎉 Railway database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Railway database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main initialization function."""
    print("🚀 Railway Database Initialization")
    print("=" * 50)
    print(f"Initialization started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get database URL
    database_url = get_database_url()
    if not database_url:
        print("❌ Cannot proceed without DATABASE_URL")
        return 1
    
    # Create tables
    success = create_tables(database_url)
    
    if success:
        print("\n🎉 Railway database is ready!")
        print("✅ Query Analytics should work now")
        return 0
    else:
        print("\n❌ Railway database initialization failed!")
        print("🔧 Check Railway logs for more details")
        return 1

if __name__ == "__main__":
    exit(main())
