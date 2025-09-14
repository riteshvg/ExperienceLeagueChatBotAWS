#!/usr/bin/env python3
"""
Check current database status and test insertion
"""

import os
import sys
from datetime import datetime

# Add project root and src to path
sys.path.append('.')
sys.path.append('src')

def check_database_status():
    """Check current database status."""
    print("🔍 Checking Database Status...")
    print("=" * 60)
    
    try:
        import psycopg2
        print("✅ psycopg2 available")
    except ImportError:
        print("❌ psycopg2 not available - this is expected locally")
        return False
    
    # Get database URL
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    print(f"✅ DATABASE_URL found: {database_url[:50]}...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check current record count
        cursor.execute("SELECT COUNT(*) FROM query_analytics")
        count = cursor.fetchone()[0]
        print(f"📊 Current query count: {count}")
        
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
        
        # Test insertion
        print("\n🔍 Testing record insertion...")
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
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM query_analytics")
        new_count = cursor.fetchone()[0]
        print(f"📊 New query count: {new_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    check_database_status()
