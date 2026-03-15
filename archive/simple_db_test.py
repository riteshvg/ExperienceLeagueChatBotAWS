#!/usr/bin/env python3
"""
Simple Railway Database Test - Tests only database connection without dependencies
"""

import os
import sys

def test_database_connection():
    """Test database connection using Railway environment."""
    print("🔍 Testing Railway Database Connection...")
    print("=" * 60)
    
    # Get database URL from Railway environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    print(f"✅ DATABASE_URL found: {database_url[:50]}...")
    
    # Test if we can import psycopg2
    try:
        import psycopg2
        print("✅ psycopg2 module available")
    except ImportError:
        print("❌ psycopg2 module not available")
        print("💡 This means the database connection will fail")
        return False
    
    # Test connection
    try:
        print("🔍 Attempting database connection...")
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
                LIMIT 5
            """)
            recent = cursor.fetchall()
            print(f"📋 Recent records:")
            for record in recent:
                print(f"   ID: {record[0]}, Query: {record[1][:50]}..., User: {record[2]}, Time: {record[3]}")
            
            # Test inserting a record
            print("🔍 Testing record insertion...")
            from datetime import datetime
            test_query = f"Test query from Railway CLI - {datetime.now()}"
            test_user = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            cursor.execute("""
                INSERT INTO query_analytics (query, userid, date_time, reaction)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (test_query, test_user, datetime.now(), "none"))
            
            inserted_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ Test record inserted with ID: {inserted_id}")
            
            # Verify the insertion
            cursor.execute("SELECT * FROM query_analytics WHERE id = %s", (inserted_id,))
            verification = cursor.fetchone()
            print(f"✅ Verification: {verification}")
        
        cursor.close()
        conn.close()
        print("✅ Database connection test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run the test."""
    print("🧪 Simple Railway Database Test")
    print("=" * 80)
    print()
    
    success = test_database_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Database connection test PASSED!")
        print("💡 The database is working correctly in Railway environment")
    else:
        print("❌ Database connection test FAILED!")
        print("💡 Check the error messages above for troubleshooting")

if __name__ == "__main__":
    main()
