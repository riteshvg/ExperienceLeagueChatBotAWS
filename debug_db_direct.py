#!/usr/bin/env python3
"""
Direct database test without streamlit dependencies
"""

import os
import sys
from datetime import datetime

def test_direct_database_insertion():
    """Test direct database insertion without streamlit."""
    print("🔍 Testing Direct Database Insertion...")
    print("=" * 60)
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    print(f"✅ DATABASE_URL: {database_url[:50]}...")
    
    try:
        import psycopg2
        print("✅ psycopg2 available")
    except ImportError:
        print("❌ psycopg2 not available")
        return False
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        print("✅ Database connection established")
        
        # Check current record count
        cursor.execute("SELECT COUNT(*) FROM query_analytics")
        count_before = cursor.fetchone()[0]
        print(f"📊 Records before: {count_before}")
        
        # Insert test record
        test_query = f"Direct test query - {datetime.now()}"
        test_user = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        cursor.execute("""
            INSERT INTO query_analytics (query, userid, date_time, reaction, query_time_seconds, model_used)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (test_query, test_user, datetime.now(), "none", 1.0, "claude-3-haiku"))
        
        inserted_id = cursor.fetchone()[0]
        conn.commit()
        print(f"✅ Test record inserted with ID: {inserted_id}")
        
        # Check new record count
        cursor.execute("SELECT COUNT(*) FROM query_analytics")
        count_after = cursor.fetchone()[0]
        print(f"📊 Records after: {count_after}")
        
        # Verify the insertion
        cursor.execute("SELECT * FROM query_analytics WHERE id = %s", (inserted_id,))
        record = cursor.fetchone()
        print(f"✅ Verification: {record}")
        
        cursor.close()
        conn.close()
        
        if count_after > count_before:
            print("✅ Database insertion test PASSED!")
            return True
        else:
            print("❌ Database insertion test FAILED - no new records")
            return False
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_direct_database_insertion()
    print(f"\n📊 Test Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
