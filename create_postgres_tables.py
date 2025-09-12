#!/usr/bin/env python3
"""
Create PostgreSQL tables for Query Analytics.
This script connects to your Railway PostgreSQL service and creates all required tables.
"""

import os
import sys
import psycopg2
from pathlib import Path
from datetime import datetime

def get_database_url():
    """Get DATABASE_URL from environment or user input."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("\n🔧 Please provide your Railway PostgreSQL connection string:")
        print("Format: postgresql://username:password@host:port/database")
        print("Example: postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway")
        print()
        
        database_url = input("Enter your DATABASE_URL: ").strip()
        
        if not database_url:
            print("❌ No DATABASE_URL provided. Exiting.")
            return None
    
    print(f"✅ DATABASE_URL found: {database_url[:30]}...")
    return database_url

def test_connection(database_url):
    """Test database connection."""
    print("\n🔍 Testing database connection...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful")
        print(f"📊 PostgreSQL version: {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_tables(database_url):
    """Create all required tables for Query Analytics."""
    print("\n🔧 Creating PostgreSQL tables...")
    
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
        
        print("📋 Creating tables...")
        
        # Execute the SQL to create tables
        cursor.execute(create_tables_sql)
        
        print("✅ Tables created successfully!")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📊 Created tables: {existing_tables}")
        
        # Show table structure
        print(f"\n🔍 Table Structure:")
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
            print(f"\n📋 {table}:")
            for col in columns:
                nullable = "YES" if col[2] == "YES" else "NO"
                default = col[3] or "None"
                print(f"   {col[0]:<20} {col[1]:<15} {nullable:<10} {default}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_table_operations(database_url):
    """Test basic table operations."""
    print("\n🧪 Testing table operations...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test session
        session_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 1. Insert user query
        print("1️⃣ Testing user query insertion...")
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Test query for table creation", session_id, "simple"))
        
        query_id = cursor.fetchone()[0]
        print(f"✅ User query inserted - ID: {query_id}")
        
        # 2. Insert AI response
        print("2️⃣ Testing AI response insertion...")
        cursor.execute("""
            INSERT INTO ai_responses (query_id, response_text, model_used)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, "Test response for table creation", "claude-3-haiku"))
        
        response_id = cursor.fetchone()[0]
        print(f"✅ AI response inserted - ID: {response_id}")
        
        # 3. Insert user feedback
        print("3️⃣ Testing user feedback insertion...")
        cursor.execute("""
            INSERT INTO user_feedback (query_id, response_id, feedback_type)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, response_id, "positive"))
        
        feedback_id = cursor.fetchone()[0]
        print(f"✅ User feedback inserted - ID: {feedback_id}")
        
        # 4. Test query
        print("4️⃣ Testing data retrieval...")
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
            print(f"✅ Data retrieval successful:")
            print(f"   Query: {result[0]}")
            print(f"   Response: {result[1]}")
            print(f"   Feedback: {result[2]}")
        
        # 5. Clean up test data
        print("5️⃣ Cleaning up test data...")
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", (session_id,))
        conn.commit()
        print("✅ Test data cleaned up")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 All table operations working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Table operations test failed: {e}")
        return False

def show_usage_instructions():
    """Show instructions for using the created tables."""
    print("\n📚 Usage Instructions:")
    print("=" * 50)
    
    print("1. 🗄️ Database Tables Created:")
    print("   - user_queries: Stores user questions")
    print("   - ai_responses: Stores AI responses")
    print("   - user_feedback: Stores user feedback")
    print("   - query_sessions: Stores session information")
    
    print("\n2. 🔗 How to Use in Your App:")
    print("   - Set DATABASE_URL in your Railway Web Service")
    print("   - Your Streamlit app will connect to these tables")
    print("   - Query Analytics will show data from these tables")
    
    print("\n3. 📊 What Happens Next:")
    print("   - User asks question → stored in user_queries")
    print("   - AI responds → stored in ai_responses")
    print("   - User gives feedback → stored in user_feedback")
    print("   - Analytics dashboard shows all data")
    
    print("\n4. 🔧 Environment Variables Needed:")
    print("   - DATABASE_URL (from PostgreSQL service)")
    print("   - AWS_ACCESS_KEY_ID")
    print("   - AWS_SECRET_ACCESS_KEY")
    print("   - BEDROCK_KNOWLEDGE_BASE_ID")
    print("   - ADOBE_CLIENT_ID")
    print("   - ADOBE_CLIENT_SECRET")
    print("   - ADOBE_ORGANIZATION_ID")
    
    print("\n5. 🚀 Next Steps:")
    print("   - Set DATABASE_URL in Railway Web Service")
    print("   - Redeploy your Streamlit app")
    print("   - Test Query Analytics dashboard")

def main():
    """Main function to create PostgreSQL tables."""
    print("🗄️ PostgreSQL Table Creation Script")
    print("=" * 60)
    print(f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get database URL
    database_url = get_database_url()
    if not database_url:
        return 1
    
    # Test connection
    if not test_connection(database_url):
        return 1
    
    # Create tables
    if not create_tables(database_url):
        return 1
    
    # Test table operations
    if not test_table_operations(database_url):
        return 1
    
    # Show usage instructions
    show_usage_instructions()
    
    print("\n🎉 PostgreSQL tables created successfully!")
    print("✅ Your Query Analytics database is ready!")
    
    return 0

if __name__ == "__main__":
    exit(main())
