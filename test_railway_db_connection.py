#!/usr/bin/env python3
"""
Comprehensive Railway Database Connection Test
This script tests the database connection and analytics service in the Railway environment.
"""

import os
import sys
import json
from datetime import datetime

# Add project root and src to path
sys.path.append('.')
sys.path.append('src')

def test_environment_variables():
    """Test if all required environment variables are available."""
    print("🔍 Testing Environment Variables...")
    print("=" * 60)
    
    required_vars = [
        'DATABASE_URL',
        'PGHOST', 
        'PGPORT',
        'RAILWAY_DATABASE_USER',
        'RAILWAY_DATABASE_PASSWORD'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'PASSWORD' in var or 'SECRET' in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: Not set")
    
    print()

def test_database_connection():
    """Test direct database connection."""
    print("🔍 Testing Direct Database Connection...")
    print("=" * 60)
    
    try:
        import psycopg2
        print("✅ psycopg2 module available")
    except ImportError:
        print("❌ psycopg2 module not available")
        print("💡 This is expected in local environment - should work in Railway")
        return False
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    print(f"🔍 Using DATABASE_URL: {database_url[:50]}...")
    
    try:
        # Test connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"✅ Basic query successful: {result}")
        
        # Check if query_analytics table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'query_analytics'
            );
        """)
        table_exists = cursor.fetchone()[0]
        print(f"📊 query_analytics table exists: {table_exists}")
        
        if table_exists:
            # Check table structure
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'query_analytics'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print(f"📋 Table columns: {columns}")
            
            # Check current record count
            cursor.execute("SELECT COUNT(*) FROM query_analytics")
            count = cursor.fetchone()[0]
            print(f"📈 Current record count: {count}")
            
            # Show recent records
            cursor.execute("""
                SELECT id, query, userid, date_time, reaction 
                FROM query_analytics 
                ORDER BY date_time DESC 
                LIMIT 3
            """)
            recent = cursor.fetchall()
            print(f"📋 Recent records: {recent}")
        
        cursor.close()
        conn.close()
        print("✅ Database connection test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def test_analytics_service():
    """Test analytics service initialization and functionality."""
    print("🔍 Testing Analytics Service...")
    print("=" * 60)
    
    try:
        # Import analytics service
        from src.integrations.streamlit_analytics_simple import initialize_analytics_service
        print("✅ Analytics service module imported successfully")
        
        # Initialize service
        analytics_service = initialize_analytics_service()
        print(f"🔍 Analytics service initialized: {analytics_service is not None}")
        
        if analytics_service:
            print("✅ Analytics service created successfully")
            
            # Test health check
            print("🔍 Running health check...")
            health_ok = analytics_service.health_check()
            print(f"📊 Health check result: {health_ok}")
            
            if health_ok:
                # Test query tracking
                print("🔍 Testing query tracking...")
                test_query = f"Test query from Railway CLI - {datetime.now()}"
                test_session = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                query_id = analytics_service.track_query(
                    session_id=test_session,
                    query_text=test_query,
                    query_complexity="simple",
                    query_time_seconds=1.0,
                    model_used="claude-3-haiku"
                )
                
                if query_id:
                    print(f"✅ Query tracked successfully with ID: {query_id}")
                    
                    # Test response tracking
                    print("🔍 Testing response tracking...")
                    response_id = analytics_service.track_response(
                        query_id=query_id,
                        response_text="Test response from Railway CLI",
                        model_used="claude-3-haiku"
                    )
                    
                    if response_id:
                        print(f"✅ Response tracked successfully with ID: {response_id}")
                        return True
                    else:
                        print("❌ Response tracking failed")
                        return False
                else:
                    print("❌ Query tracking failed")
                    return False
            else:
                print("❌ Health check failed")
                return False
        else:
            print("❌ Analytics service initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Analytics service test failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def test_railway_cli_commands():
    """Test Railway CLI commands for database access."""
    print("🔍 Testing Railway CLI Commands...")
    print("=" * 60)
    
    import subprocess
    
    # Test railway variables command
    try:
        result = subprocess.run(['railway', 'variables'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Railway variables command successful")
            print("📋 Available variables:")
            lines = result.stdout.split('\n')
            for line in lines[:10]:  # Show first 10 lines
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"❌ Railway variables command failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Railway CLI test failed: {e}")
    
    print()

def main():
    """Run all tests."""
    print("🧪 Railway Database Connection Test")
    print("=" * 80)
    print()
    
    # Test 1: Environment variables
    env_ok = test_environment_variables()
    
    # Test 2: Direct database connection
    db_ok = test_database_connection()
    
    # Test 3: Analytics service
    analytics_ok = test_analytics_service()
    
    # Test 4: Railway CLI
    test_railway_cli_commands()
    
    # Summary
    print("📊 Test Results Summary")
    print("=" * 60)
    print(f"Environment Variables: {'✅ PASSED' if env_ok else '❌ FAILED'}")
    print(f"Database Connection: {'✅ PASSED' if db_ok else '❌ FAILED'}")
    print(f"Analytics Service: {'✅ PASSED' if analytics_ok else '❌ FAILED'}")
    
    if not analytics_ok:
        print("\n💡 Troubleshooting Tips:")
        print("1. Check if all environment variables are set correctly")
        print("2. Verify Railway database credentials")
        print("3. Check if query_analytics table exists")
        print("4. Look for any error messages in the logs above")
        print("5. Try running this script in the Railway environment: railway run python3 test_railway_db_connection.py")

if __name__ == "__main__":
    main()
