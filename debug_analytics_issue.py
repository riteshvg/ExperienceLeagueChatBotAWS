#!/usr/bin/env python3
"""
Debug analytics issue - check why queries aren't being recorded.
"""

import os
import sys
import psycopg2
from pathlib import Path
import pandas as pd
from datetime import datetime

def check_database_connection():
    """Check if we can connect to the database."""
    print("🔍 Step 1: Checking Database Connection")
    print("=" * 50)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("🔧 Please set DATABASE_URL in your .env file or environment")
        return None
    
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
        return database_url
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def check_tables_exist(database_url):
    """Check if analytics tables exist."""
    print("\n🔍 Step 2: Checking Analytics Tables")
    print("=" * 50)
    
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
        
        print("📋 Table Status:")
        for table in required_tables:
            if table in existing_tables:
                print(f"✅ {table} - EXISTS")
            else:
                print(f"❌ {table} - MISSING")
        
        if len(existing_tables) != len(required_tables):
            print(f"\n❌ Missing tables detected!")
            print(f"🔧 Run database initialization to create missing tables")
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def check_table_data(database_url):
    """Check if there's any data in the tables."""
    print("\n🔍 Step 3: Checking Table Data")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"📊 {table}: {count} records")
            
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
                
                print(f"   Sample data:")
                for i, row in enumerate(rows, 1):
                    print(f"   {i}. {dict(zip(column_names, row))}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking table data: {e}")

def test_analytics_insertion(database_url):
    """Test if we can insert analytics data."""
    print("\n🔍 Step 4: Testing Analytics Data Insertion")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test insert user query
        test_session_id = f"debug-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute("""
            INSERT INTO user_queries (query_text, session_id, query_complexity)
            VALUES (%s, %s, %s)
            RETURNING id
        """, ("Debug test query", test_session_id, "simple"))
        
        query_id = cursor.fetchone()[0]
        print(f"✅ User query inserted - ID: {query_id}")
        
        # Test insert AI response
        cursor.execute("""
            INSERT INTO ai_responses (query_id, response_text, model_used)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, "Debug test response", "claude-3-haiku"))
        
        response_id = cursor.fetchone()[0]
        print(f"✅ AI response inserted - ID: {response_id}")
        
        # Test insert user feedback
        cursor.execute("""
            INSERT INTO user_feedback (query_id, response_id, feedback_type)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (query_id, response_id, "positive"))
        
        feedback_id = cursor.fetchone()[0]
        print(f"✅ User feedback inserted - ID: {feedback_id}")
        
        # Verify data was inserted
        cursor.execute("""
            SELECT q.query_text, r.response_text, f.feedback_type
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
            WHERE q.session_id = %s
        """, (test_session_id,))
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Data verification successful:")
            print(f"   Query: {result[0]}")
            print(f"   Response: {result[1]}")
            print(f"   Feedback: {result[2]}")
        
        # Clean up test data
        cursor.execute("DELETE FROM user_queries WHERE session_id = %s", (test_session_id,))
        conn.commit()
        print(f"✅ Test data cleaned up")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error testing analytics insertion: {e}")
        return False

def check_analytics_service_import():
    """Check if analytics service can be imported."""
    print("\n🔍 Step 5: Checking Analytics Service Import")
    print("=" * 50)
    
    try:
        # Add project root to path
        project_root = Path(__file__).parent
        sys.path.append(str(project_root))
        sys.path.append(str(project_root / "src"))
        
        # Try to import simplified analytics service
        from src.integrations.streamlit_analytics_simple import initialize_analytics_service
        print("✅ Analytics service import successful")
        
        # Try to initialize the service
        analytics_service = initialize_analytics_service()
        if analytics_service:
            print("✅ Analytics service initialization successful")
            return True
        else:
            print("❌ Analytics service initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error importing analytics service: {e}")
        return False

def check_app_analytics_integration():
    """Check if app.py has analytics integration."""
    print("\n🔍 Step 6: Checking App Analytics Integration")
    print("=" * 50)
    
    try:
        app_file = Path("app.py")
        if not app_file.exists():
            print("❌ app.py not found")
            return False
        
        content = app_file.read_text()
        
        # Check for analytics imports
        if "streamlit_analytics_simple" in content:
            print("✅ Simplified analytics service imported")
        else:
            print("❌ Simplified analytics service not imported")
        
        # Check for analytics initialization
        if "initialize_analytics_service" in content:
            print("✅ Analytics service initialization found")
        else:
            print("❌ Analytics service initialization not found")
        
        # Check for analytics tracking calls
        if "analytics_service.track_query" in content:
            print("✅ Query tracking found")
        else:
            print("❌ Query tracking not found")
        
        if "analytics_service.track_response" in content:
            print("✅ Response tracking found")
        else:
            print("❌ Response tracking not found")
        
        if "analytics_service.track_feedback" in content:
            print("✅ Feedback tracking found")
        else:
            print("❌ Feedback tracking not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking app analytics integration: {e}")
        return False

def provide_solutions():
    """Provide solutions based on the diagnosis."""
    print("\n🔧 Solutions Based on Diagnosis")
    print("=" * 50)
    
    print("If queries aren't being recorded, here are the most likely causes:")
    print()
    
    print("1. 🗄️ Database Tables Missing")
    print("   - Run: python init_railway_db.py")
    print("   - Or check Railway logs for database initialization")
    print()
    
    print("2. 🔗 Database Connection Issues")
    print("   - Check DATABASE_URL is set correctly")
    print("   - Verify Railway PostgreSQL service is running")
    print()
    
    print("3. 📊 Analytics Service Not Initialized")
    print("   - Check if analytics_available is True in session state")
    print("   - Verify analytics service is created in main()")
    print()
    
    print("4. 🚫 Analytics Tracking Not Called")
    print("   - Check if process_query_with_smart_routing calls analytics")
    print("   - Verify analytics_service is passed to the function")
    print()
    
    print("5. 🔄 App Not Using Latest Code")
    print("   - Redeploy to Railway with latest changes")
    print("   - Check Railway logs for any errors")
    print()
    
    print("6. 🧪 Test Analytics Manually")
    print("   - Try asking a question in the app")
    print("   - Check if query appears in database")
    print("   - Look for analytics errors in Railway logs")

def main():
    """Main diagnostic function."""
    print("🔍 Analytics Issue Diagnostic Tool")
    print("=" * 60)
    print(f"Diagnosis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Check database connection
    database_url = check_database_connection()
    if not database_url:
        print("\n❌ Cannot proceed without database connection")
        provide_solutions()
        return 1
    
    # Step 2: Check tables exist
    if not check_tables_exist(database_url):
        print("\n❌ Database tables are missing")
        provide_solutions()
        return 1
    
    # Step 3: Check table data
    check_table_data(database_url)
    
    # Step 4: Test analytics insertion
    if not test_analytics_insertion(database_url):
        print("\n❌ Cannot insert analytics data")
        provide_solutions()
        return 1
    
    # Step 5: Check analytics service import
    if not check_analytics_service_import():
        print("\n❌ Analytics service import failed")
        provide_solutions()
        return 1
    
    # Step 6: Check app analytics integration
    check_app_analytics_integration()
    
    print("\n🎯 Diagnosis Complete!")
    print("=" * 50)
    print("If all steps passed but queries still aren't recorded:")
    print("1. Check Railway logs for runtime errors")
    print("2. Verify the app is using the latest deployed code")
    print("3. Test by asking a question in the app")
    print("4. Check if analytics_available is True in session state")
    
    return 0

if __name__ == "__main__":
    exit(main())
