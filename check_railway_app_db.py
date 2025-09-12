#!/usr/bin/env python3
"""
Check Railway app database status and configuration.
This script helps you verify your Railway database setup.
"""

import os
import sys
import requests
import json
from pathlib import Path
from datetime import datetime

def check_railway_environment():
    """Check Railway environment variables."""
    print("🔍 Step 1: Checking Railway Environment Variables")
    print("=" * 60)
    
    # Check for Railway-specific environment variables
    railway_env = os.getenv("RAILWAY_ENVIRONMENT")
    database_url = os.getenv("DATABASE_URL")
    
    print(f"🌐 Railway Environment: {railway_env or 'Not set'}")
    print(f"🗄️ DATABASE_URL: {'Set' if database_url else 'Not set'}")
    
    if database_url:
        # Parse DATABASE_URL to show connection details
        try:
            if database_url.startswith("postgresql://"):
                # Extract connection details
                url_parts = database_url.replace("postgresql://", "").split("@")
                if len(url_parts) == 2:
                    user_pass = url_parts[0].split(":")
                    host_port_db = url_parts[1].split("/")
                    
                    if len(user_pass) == 2 and len(host_port_db) == 2:
                        username = user_pass[0]
                        password = user_pass[1][:3] + "..." if len(user_pass[1]) > 3 else user_pass[1]
                        host_port = host_port_db[0].split(":")
                        database = host_port_db[1]
                        
                        host = host_port[0]
                        port = host_port[1] if len(host_port) > 1 else "5432"
                        
                        print(f"   Username: {username}")
                        print(f"   Password: {password}")
                        print(f"   Host: {host}")
                        print(f"   Port: {port}")
                        print(f"   Database: {database}")
                        print(f"   ✅ DATABASE_URL format looks correct")
                    else:
                        print(f"   ⚠️ DATABASE_URL format may be incorrect")
                else:
                    print(f"   ⚠️ DATABASE_URL format may be incorrect")
            else:
                print(f"   ⚠️ DATABASE_URL is not a PostgreSQL URL")
        except Exception as e:
            print(f"   ⚠️ Error parsing DATABASE_URL: {e}")
    else:
        print(f"   ❌ DATABASE_URL not found - this is the main issue!")
    
    return database_url is not None

def check_railway_app_status():
    """Check if Railway app is running and accessible."""
    print("\n🔍 Step 2: Checking Railway App Status")
    print("=" * 60)
    
    # Try to get Railway app URL from environment or use default
    railway_url = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    if not railway_url:
        # Try to construct from Railway environment
        railway_url = os.getenv("RAILWAY_STATIC_URL")
    
    if not railway_url:
        print("❌ Railway app URL not found in environment variables")
        print("🔧 Check Railway dashboard for your app URL")
        return False
    
    print(f"🌐 Railway App URL: {railway_url}")
    
    try:
        # Test if app is accessible
        response = requests.get(f"https://{railway_url}", timeout=10)
        if response.status_code == 200:
            print(f"✅ Railway app is accessible (Status: {response.status_code})")
            return True
        else:
            print(f"⚠️ Railway app returned status: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot access Railway app: {e}")
        return False

def check_database_connection():
    """Check database connection if DATABASE_URL is available."""
    print("\n🔍 Step 3: Checking Database Connection")
    print("=" * 60)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not available - cannot test database connection")
        return False
    
    try:
        import psycopg2
        
        # Test database connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Database connection successful")
        print(f"📊 PostgreSQL version: {version}")
        
        # Check if analytics tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        
        print(f"\n📋 Analytics Tables Status:")
        for table in required_tables:
            if table in existing_tables:
                print(f"   ✅ {table} - EXISTS")
            else:
                print(f"   ❌ {table} - MISSING")
        
        # Check data in tables
        print(f"\n📊 Table Data Counts:")
        for table in existing_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   {table}: {count} records")
        
        cursor.close()
        conn.close()
        
        return len(existing_tables) == len(required_tables)
        
    except ImportError:
        print("❌ psycopg2 not installed - cannot test database connection")
        print("🔧 Install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_railway_logs():
    """Provide instructions for checking Railway logs."""
    print("\n🔍 Step 4: Checking Railway Logs")
    print("=" * 60)
    
    print("📋 To check Railway logs:")
    print("1. Go to https://railway.app")
    print("2. Click on your project")
    print("3. Click on 'Deployments' tab")
    print("4. Click on the latest deployment")
    print("5. Check the logs for any errors")
    
    print(f"\n🔍 Look for these in the logs:")
    print("✅ 'Railway database initialization completed successfully'")
    print("✅ 'Analytics integration loaded successfully'")
    print("❌ 'Database connection failed'")
    print("❌ 'No module named src.models'")
    print("❌ 'DATABASE_URL not found'")
    
    print(f"\n📊 Common log patterns:")
    print("- Database initialization: 'init_railway_db.py' execution")
    print("- Analytics setup: 'Analytics integration loaded successfully'")
    print("- App startup: 'Starting Streamlit app...'")
    print("- Errors: Any red error messages")

def check_railway_variables():
    """Provide instructions for checking Railway environment variables."""
    print("\n🔍 Step 5: Checking Railway Environment Variables")
    print("=" * 60)
    
    print("📋 To check Railway environment variables:")
    print("1. Go to https://railway.app")
    print("2. Click on your project")
    print("3. Click on 'Variables' tab")
    print("4. Check if these variables are set:")
    
    required_vars = [
        "DATABASE_URL",
        "AWS_ACCESS_KEY_ID", 
        "AWS_SECRET_ACCESS_KEY",
        "BEDROCK_KNOWLEDGE_BASE_ID",
        "ADOBE_CLIENT_ID",
        "ADOBE_CLIENT_SECRET",
        "ADOBE_ORGANIZATION_ID"
    ]
    
    for var in required_vars:
        print(f"   {'✅' if os.getenv(var) else '❌'} {var}")
    
    print(f"\n🔧 If any variables are missing:")
    print("1. Click 'New Variable' in Railway dashboard")
    print("2. Add the missing variable name and value")
    print("3. Click 'Deploy' to redeploy with new variables")

def provide_railway_troubleshooting():
    """Provide Railway-specific troubleshooting steps."""
    print("\n🔧 Railway Troubleshooting Steps")
    print("=" * 60)
    
    print("🚨 If Query Analytics is not working:")
    print()
    
    print("1. 🗄️ Database Issues:")
    print("   - Check if PostgreSQL service is running")
    print("   - Verify DATABASE_URL is set correctly")
    print("   - Check if database tables were created")
    print()
    
    print("2. 🔄 Deployment Issues:")
    print("   - Check if latest code is deployed")
    print("   - Look for build errors in Railway logs")
    print("   - Verify all environment variables are set")
    print()
    
    print("3. 📊 Analytics Issues:")
    print("   - Check if analytics service is initialized")
    print("   - Look for 'No module named src.models' errors")
    print("   - Verify database connection in app logs")
    print()
    
    print("4. 🔍 Debug Steps:")
    print("   - Check Railway logs for errors")
    print("   - Test database connection manually")
    print("   - Verify environment variables")
    print("   - Check if app is using latest code")

def main():
    """Main function to check Railway app database."""
    print("🚀 Railway App Database Checker")
    print("=" * 60)
    print(f"Check started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Check environment variables
    env_ok = check_railway_environment()
    
    # Step 2: Check app status
    app_ok = check_railway_app_status()
    
    # Step 3: Check database connection
    db_ok = check_database_connection()
    
    # Step 4: Provide log checking instructions
    check_railway_logs()
    
    # Step 5: Provide variable checking instructions
    check_railway_variables()
    
    # Step 6: Provide troubleshooting
    provide_railway_troubleshooting()
    
    # Summary
    print("\n📊 Summary")
    print("=" * 60)
    print(f"Environment Variables: {'✅ OK' if env_ok else '❌ Issues'}")
    print(f"App Status: {'✅ OK' if app_ok else '❌ Issues'}")
    print(f"Database Connection: {'✅ OK' if db_ok else '❌ Issues'}")
    
    if env_ok and app_ok and db_ok:
        print("\n🎉 Railway app database is working correctly!")
        print("✅ Query Analytics should be working")
    else:
        print("\n⚠️ Railway app database has issues")
        print("🔧 Follow the troubleshooting steps above")
    
    return 0

if __name__ == "__main__":
    exit(main())
