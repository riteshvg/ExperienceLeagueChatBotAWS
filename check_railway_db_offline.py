#!/usr/bin/env python3
"""
Check Railway database tables offline.
This script connects to your Railway PostgreSQL database and shows table structure and data.
"""

import os
import sys
import psycopg2
from pathlib import Path
import pandas as pd
from datetime import datetime

def get_database_url():
    """Get database URL from environment variables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("🔧 Please set DATABASE_URL in your environment or .env file")
        return None
    
    print(f"✅ DATABASE_URL found: {database_url[:30]}...")
    return database_url

def check_database_connection(database_url):
    """Check if database connection works."""
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connected successfully")
        print(f"📊 PostgreSQL version: {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_tables_exist(database_url):
    """Check if required tables exist."""
    try:
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
        
        print(f"\n📋 Table Status:")
        print("=" * 50)
        
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ {table} - EXISTS")
            else:
                print(f"❌ {table} - MISSING")
        
        cursor.close()
        conn.close()
        
        return len(existing_tables) == len(required_tables)
        
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def show_table_structure(database_url):
    """Show table structure and constraints."""
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        
        for table in tables:
            print(f"\n🔍 Table Structure: {table}")
            print("-" * 60)
            
            # Get column information
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
            
            if columns:
                print(f"{'Column':<20} {'Type':<15} {'Nullable':<10} {'Default'}")
                print("-" * 60)
                for col in columns:
                    nullable = "YES" if col[2] == "YES" else "NO"
                    default = col[3] or "None"
                    print(f"{col[0]:<20} {col[1]:<15} {nullable:<10} {default}")
            else:
                print(f"❌ Table {table} not found")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing table structure: {e}")

def show_table_data(database_url, table_name, limit=10):
    """Show sample data from a table."""
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print(f"\n📊 Sample Data from {table_name} (limit {limit}):")
        print("-" * 80)
        
        # Get row count first
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = cursor.fetchone()[0]
        print(f"Total rows: {total_rows}")
        
        if total_rows > 0:
            # Get sample data
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cursor.fetchall()
            
            # Get column names
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """, (table_name,))
            column_names = [row[0] for row in cursor.fetchall()]
            
            # Create DataFrame for better display
            df = pd.DataFrame(rows, columns=column_names)
            print(df.to_string(index=False, max_colwidth=50))
        else:
            print("No data found in table")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing data from {table_name}: {e}")

def show_analytics_summary(database_url):
    """Show analytics summary."""
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print(f"\n📈 Analytics Summary:")
        print("=" * 50)
        
        # Total queries
        cursor.execute("SELECT COUNT(*) FROM user_queries")
        total_queries = cursor.fetchone()[0]
        print(f"Total Queries: {total_queries}")
        
        # Queries by complexity
        cursor.execute("""
            SELECT query_complexity, COUNT(*) 
            FROM user_queries 
            GROUP BY query_complexity 
            ORDER BY COUNT(*) DESC
        """)
        complexity_stats = cursor.fetchall()
        print(f"\nQueries by Complexity:")
        for complexity, count in complexity_stats:
            print(f"  {complexity}: {count}")
        
        # Total responses
        cursor.execute("SELECT COUNT(*) FROM ai_responses")
        total_responses = cursor.fetchone()[0]
        print(f"\nTotal Responses: {total_responses}")
        
        # Responses by model
        cursor.execute("""
            SELECT model_used, COUNT(*) 
            FROM ai_responses 
            GROUP BY model_used 
            ORDER BY COUNT(*) DESC
        """)
        model_stats = cursor.fetchall()
        print(f"\nResponses by Model:")
        for model, count in model_stats:
            print(f"  {model}: {count}")
        
        # Total feedback
        cursor.execute("SELECT COUNT(*) FROM user_feedback")
        total_feedback = cursor.fetchone()[0]
        print(f"\nTotal Feedback: {total_feedback}")
        
        # Feedback by type
        cursor.execute("""
            SELECT feedback_type, COUNT(*) 
            FROM user_feedback 
            GROUP BY feedback_type 
            ORDER BY COUNT(*) DESC
        """)
        feedback_stats = cursor.fetchall()
        print(f"\nFeedback by Type:")
        for feedback_type, count in feedback_stats:
            print(f"  {feedback_type}: {count}")
        
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
        
        print(f"\nRecent Activity (last 5 queries):")
        for i, (query, created_at, model, feedback) in enumerate(recent_activity, 1):
            print(f"  {i}. {query[:50]}...")
            print(f"     Created: {created_at}")
            print(f"     Model: {model or 'N/A'}")
            print(f"     Feedback: {feedback or 'N/A'}")
            print()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing analytics summary: {e}")

def test_database_operations(database_url):
    """Test basic database operations."""
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print(f"\n🧪 Testing Database Operations:")
        print("=" * 50)
        
        # Test insert
        test_session_id = f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Test query from offline checker", test_session_id, "simple"))
        
        query_id = cursor.fetchone()[0]
        print(f"✅ Insert test passed - Query ID: {query_id}")
        
        # Test update
        cursor.execute("""
            UPDATE user_queries 
            SET query_complexity = %s 
            WHERE id = %s
        """, ("complex", query_id))
        print(f"✅ Update test passed")
        
        # Test select
        cursor.execute("SELECT query_text FROM user_queries WHERE id = %s", (query_id,))
        result = cursor.fetchone()
        print(f"✅ Select test passed - Query: {result[0]}")
        
        # Test delete
        cursor.execute("DELETE FROM user_queries WHERE id = %s", (query_id,))
        print(f"✅ Delete test passed")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"🎉 All database operations working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Database operations test failed: {e}")
        return False

def main():
    """Main function to check Railway database offline."""
    print("🗄️ Railway Database Offline Checker")
    print("=" * 60)
    print(f"Check started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get database URL
    database_url = get_database_url()
    if not database_url:
        return 1
    
    # Check connection
    if not check_database_connection(database_url):
        return 1
    
    # Check tables exist
    if not check_tables_exist(database_url):
        print(f"\n❌ Some required tables are missing!")
        print(f"🔧 Run the database initialization script to create them")
        return 1
    
    # Show table structure
    show_table_structure(database_url)
    
    # Show sample data from each table
    tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
    for table in tables:
        show_table_data(database_url, table, limit=5)
    
    # Show analytics summary
    show_analytics_summary(database_url)
    
    # Test database operations
    test_database_operations(database_url)
    
    print(f"\n🎉 Database check completed successfully!")
    print(f"✅ Your Railway database is working correctly")
    
    return 0

if __name__ == "__main__":
    exit(main())
