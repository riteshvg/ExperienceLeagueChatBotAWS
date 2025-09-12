#!/usr/bin/env python3
"""
Test Railway database connection and table creation.
"""

import os
import sys
import psycopg2
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

def test_database_connection():
    """Test database connection and table creation."""
    print("🗄️ Testing Railway Database Connection")
    print("=" * 50)
    
    # Check environment variables
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    print(f"✅ DATABASE_URL found: {database_url[:20]}...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        print("✅ Database connection successful")
        
        # Check if tables exist
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
            print(f"❌ Missing tables: {missing_tables}")
            print("🔧 Creating missing tables...")
            
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
            
            cursor.execute(create_tables_sql)
            conn.commit()
            print("✅ Tables created successfully")
            
            # Verify tables were created
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
            """)
            
            new_tables = [row[0] for row in cursor.fetchall()]
            print(f"📊 Tables after creation: {new_tables}")
            
        else:
            print("✅ All required tables exist")
        
        # Test inserting sample data
        print("\n🧪 Testing data insertion...")
        
        # Insert sample query
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Test query from Railway", "test-session-railway", "simple"))
        
        query_id = cursor.fetchone()[0]
        print(f"✅ Sample query inserted with ID: {query_id}")
        
        # Insert sample response
        cursor.execute("""
            INSERT INTO ai_responses (query_id, response_text, model_used, response_time_ms)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (query_id, "Test response from Railway", "claude-3-haiku", 1500))
        
        response_id = cursor.fetchone()[0]
        print(f"✅ Sample response inserted with ID: {response_id}")
        
        # Insert sample feedback
        cursor.execute("""
            INSERT INTO user_feedback (query_id, response_id, feedback_type, feedback_text)
            VALUES (%s, %s, %s, %s)
        """, (query_id, response_id, "positive", "Test feedback"))
        
        print("✅ Sample feedback inserted")
        
        # Test querying data
        cursor.execute("""
            SELECT q.query_text, r.response_text, f.feedback_type
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
            WHERE q.session_id = %s
        """, ("test-session-railway",))
        
        results = cursor.fetchall()
        print(f"✅ Query test successful: {len(results)} records found")
        
        # Clean up test data
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", ("test-session-railway",))
        conn.commit()
        print("✅ Test data cleaned up")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 Database test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Railway Database Test")
    print("=" * 50)
    
    success = test_database_connection()
    
    if success:
        print("\n✅ Database is working correctly!")
        print("🔧 Next steps:")
        print("1. Deploy this fix to Railway")
        print("2. Restart your Railway application")
        print("3. Check Query Analytics tab - it should work now")
        return 0
    else:
        print("\n❌ Database test failed!")
        print("🔧 Check your Railway database configuration")
        return 1

if __name__ == "__main__":
    exit(main())
