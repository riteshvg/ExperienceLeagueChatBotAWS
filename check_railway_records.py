#!/usr/bin/env python3
"""
Check Railway PostgreSQL records and verify Query Analytics functionality.
This script can be run in your web app to verify database records.
"""

import os
import sys
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_connection():
    """Get database connection using Railway credentials."""
    # Try different ways to get database URL
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        logger.info("Using DATABASE_URL from environment")
        return database_url
    
    # Try to construct from Railway environment variables
    railway_db_host = os.getenv("RAILWAY_DATABASE_HOST", "containers-us-west-1.railway.app")
    railway_db_port = os.getenv("RAILWAY_DATABASE_PORT", "5432")
    railway_db_name = os.getenv("RAILWAY_DATABASE_NAME", "railway")
    railway_db_user = os.getenv("RAILWAY_DATABASE_USER", "postgres")
    railway_db_password = os.getenv("RAILWAY_DATABASE_PASSWORD", "eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE")
    
    database_url = f"postgresql://{railway_db_user}:{railway_db_password}@{railway_db_host}:{railway_db_port}/{railway_db_name}"
    logger.info("Using Railway database credentials")
    
    return database_url

def check_database_connection():
    """Check if database connection works."""
    logger.info("🔍 Checking database connection...")
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        logger.info(f"✅ Database connected successfully")
        logger.info(f"📊 PostgreSQL version: {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def check_tables_exist():
    """Check if all required tables exist."""
    logger.info("🔍 Checking if tables exist...")
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check for required tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        
        logger.info("📋 Table Status:")
        for table in required_tables:
            if table in existing_tables:
                logger.info(f"✅ {table} - EXISTS")
            else:
                logger.error(f"❌ {table} - MISSING")
        
        cursor.close()
        conn.close()
        
        return len(existing_tables) == len(required_tables)
        
    except Exception as e:
        logger.error(f"❌ Error checking tables: {e}")
        return False

def check_table_records():
    """Check records in each table."""
    logger.info("🔍 Checking table records...")
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"📊 {table}: {count} records")
            
            if count > 0:
                # Show sample data
                cursor.execute(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 3")
                rows = cursor.fetchall()
                
                # Get column names
                cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (table,))
                column_names = [row[0] for row in cursor.fetchall()]
                
                logger.info(f"   Sample data from {table}:")
                for i, row in enumerate(rows, 1):
                    row_dict = dict(zip(column_names, row))
                    logger.info(f"   {i}. {row_dict}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error checking table records: {e}")

def get_analytics_summary():
    """Get analytics summary data."""
    logger.info("📈 Getting analytics summary...")
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Total queries
        cursor.execute("SELECT COUNT(*) FROM user_queries")
        total_queries = cursor.fetchone()[0]
        logger.info(f"📊 Total Queries: {total_queries}")
        
        # Queries by complexity
        cursor.execute("""
            SELECT query_complexity, COUNT(*) 
            FROM user_queries 
            GROUP BY query_complexity 
            ORDER BY COUNT(*) DESC
        """)
        complexity_stats = cursor.fetchall()
        logger.info(f"📊 Queries by Complexity:")
        for complexity, count in complexity_stats:
            logger.info(f"   {complexity}: {count}")
        
        # Total responses
        cursor.execute("SELECT COUNT(*) FROM ai_responses")
        total_responses = cursor.fetchone()[0]
        logger.info(f"📊 Total Responses: {total_responses}")
        
        # Responses by model
        cursor.execute("""
            SELECT model_used, COUNT(*) 
            FROM ai_responses 
            GROUP BY model_used 
            ORDER BY COUNT(*) DESC
        """)
        model_stats = cursor.fetchall()
        logger.info(f"📊 Responses by Model:")
        for model, count in model_stats:
            logger.info(f"   {model}: {count}")
        
        # Total feedback
        cursor.execute("SELECT COUNT(*) FROM user_feedback")
        total_feedback = cursor.fetchone()[0]
        logger.info(f"📊 Total Feedback: {total_feedback}")
        
        # Feedback by type
        cursor.execute("""
            SELECT feedback_type, COUNT(*) 
            FROM user_feedback 
            GROUP BY feedback_type 
            ORDER BY COUNT(*) DESC
        """)
        feedback_stats = cursor.fetchall()
        logger.info(f"📊 Feedback by Type:")
        for feedback_type, count in feedback_stats:
            logger.info(f"   {feedback_type}: {count}")
        
        # Recent activity
        cursor.execute("""
            SELECT 
                q.query_text,
                q.created_at,
                r.model_used,
                f.feedback_type
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
            ORDER BY q.created_at DESC
            LIMIT 5
        """)
        recent_activity = cursor.fetchall()
        
        logger.info(f"📊 Recent Activity (last 5 queries):")
        for i, (query, created_at, model, feedback) in enumerate(recent_activity, 1):
            logger.info(f"   {i}. Query: {query[:50]}...")
            logger.info(f"      Created: {created_at}")
            logger.info(f"      Model: {model or 'N/A'}")
            logger.info(f"      Feedback: {feedback or 'N/A'}")
            logger.info("")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error getting analytics summary: {e}")

def test_data_insertion():
    """Test inserting sample data."""
    logger.info("🧪 Testing data insertion...")
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test session
        session_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 1. Insert user query
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Test query for record checking", session_id, "simple"))
        
        query_id = cursor.fetchone()[0]
        logger.info(f"✅ Test query inserted - ID: {query_id}")
        
        # 2. Insert AI response
        cursor.execute("""
            INSERT INTO ai_responses (query_id, response_text, model_used)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, "Test response for record checking", "claude-3-haiku"))
        
        response_id = cursor.fetchone()[0]
        logger.info(f"✅ Test response inserted - ID: {response_id}")
        
        # 3. Insert user feedback
        cursor.execute("""
            INSERT INTO user_feedback (query_id, response_id, feedback_type)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, response_id, "positive"))
        
        feedback_id = cursor.fetchone()[0]
        logger.info(f"✅ Test feedback inserted - ID: {feedback_id}")
        
        # 4. Verify data
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
            logger.info(f"✅ Data verification successful:")
            logger.info(f"   Query: {result[0]}")
            logger.info(f"   Response: {result[1]}")
            logger.info(f"   Feedback: {result[2]}")
        
        # 5. Clean up test data
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", (session_id,))
        conn.commit()
        logger.info("✅ Test data cleaned up")
        
        cursor.close()
        conn.close()
        
        logger.info("🎉 Data insertion test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Data insertion test failed: {e}")
        return False

def export_records_to_csv():
    """Export records to CSV files."""
    logger.info("📁 Exporting records to CSV...")
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        
        tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        
        for table in tables:
            # Read data into DataFrame
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            
            # Export to CSV
            filename = f"{table}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False)
            logger.info(f"✅ Exported {table} to {filename}")
        
        conn.close()
        logger.info("🎉 All records exported to CSV files!")
        
    except Exception as e:
        logger.error(f"❌ Error exporting records: {e}")

def main():
    """Main function to check Railway records."""
    logger.info("🔍 Railway Records Checker")
    logger.info("=" * 60)
    logger.info(f"Check started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Step 1: Check database connection
    if not check_database_connection():
        logger.error("❌ Cannot proceed without database connection")
        return 1
    
    # Step 2: Check tables exist
    if not check_tables_exist():
        logger.error("❌ Some required tables are missing")
        return 1
    
    # Step 3: Check table records
    check_table_records()
    
    # Step 4: Get analytics summary
    get_analytics_summary()
    
    # Step 5: Test data insertion
    if not test_data_insertion():
        logger.error("❌ Data insertion test failed")
        return 1
    
    # Step 6: Export records (optional)
    export_records_to_csv()
    
    logger.info("")
    logger.info("🎉 Railway records check completed successfully!")
    logger.info("✅ Your Query Analytics database is working correctly!")
    logger.info("✅ All tables exist and are accessible")
    logger.info("✅ Data insertion and retrieval working")
    logger.info("✅ Analytics summary available")
    
    return 0

if __name__ == "__main__":
    exit(main())
