#!/usr/bin/env python3
"""
Verify Table Fix - Check if your Railway table was updated correctly
"""

import os
import psycopg2
from datetime import datetime

def verify_table_schema():
    """Check the current table schema and verify it's correct."""
    try:
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        print("🔍 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("📋 Checking current table schema...")
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                character_maximum_length,
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'query_analytics'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        print("\n📊 Current Table Schema:")
        print("=" * 60)
        print(f"{'Column':<15} {'Type':<20} {'Max Length':<12} {'Nullable'}")
        print("-" * 60)
        
        schema_correct = True
        
        for col in columns:
            col_name, data_type, max_length, nullable = col
            max_len_str = str(max_length) if max_length else "unlimited"
            nullable_str = "YES" if nullable == "YES" else "NO"
            
            print(f"{col_name:<15} {data_type:<20} {max_len_str:<12} {nullable_str}")
            
            # Check if schema is correct
            if col_name == "reaction" and (data_type != "character varying" or max_length < 20):
                print(f"❌ {col_name} column needs to be VARCHAR(20) or larger")
                schema_correct = False
            elif col_name == "userid" and (data_type != "character varying" or max_length < 100):
                print(f"❌ {col_name} column needs to be VARCHAR(100) or larger")
                schema_correct = False
            elif col_name == "query" and data_type != "text":
                print(f"❌ {col_name} column needs to be TEXT")
                schema_correct = False
        
        print("=" * 60)
        
        if schema_correct:
            print("✅ Table schema looks correct!")
        else:
            print("❌ Table schema needs to be fixed")
        
        cursor.close()
        conn.close()
        
        return schema_correct
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return False

def test_insert_functionality():
    """Test if we can insert longer values."""
    try:
        database_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("\n🧪 Testing insert functionality...")
        
        # Test with longer values
        test_data = {
            'query': 'This is a very long test query that should work now with the updated schema',
            'userid': 'test_user_with_very_long_username_12345',
            'reaction': 'positive'
        }
        
        cursor.execute("""
            INSERT INTO query_analytics (query, userid, date_time, reaction)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (test_data['query'], test_data['userid'], datetime.now(), test_data['reaction']))
        
        test_id = cursor.fetchone()[0]
        print(f"✅ Test insert successful! Record ID: {test_id}")
        
        # Clean up test record
        cursor.execute("DELETE FROM query_analytics WHERE id = %s", (test_id,))
        conn.commit()
        print("🧹 Test record cleaned up")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Test insert failed: {e}")
        return False

def check_existing_data():
    """Check if there's existing data in the table."""
    try:
        database_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("\n📊 Checking existing data...")
        
        # Count total records
        cursor.execute("SELECT COUNT(*) FROM query_analytics")
        total_count = cursor.fetchone()[0]
        print(f"Total records: {total_count}")
        
        if total_count > 0:
            # Show recent records
            cursor.execute("""
                SELECT id, LEFT(query, 50) as query_preview, userid, date_time, reaction
                FROM query_analytics 
                ORDER BY date_time DESC 
                LIMIT 5
            """)
            
            records = cursor.fetchall()
            print("\nRecent records:")
            print("-" * 80)
            print(f"{'ID':<5} {'Query Preview':<30} {'User':<15} {'Date':<20} {'Reaction'}")
            print("-" * 80)
            
            for record in records:
                id_val, query_preview, userid, date_time, reaction = record
                date_str = date_time.strftime("%Y-%m-%d %H:%M") if date_time else "N/A"
                print(f"{id_val:<5} {query_preview:<30} {userid:<15} {date_str:<20} {reaction or 'N/A'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")

def main():
    """Main verification function."""
    print("🔍 Railway Table Fix Verification")
    print("=" * 50)
    
    # Check schema
    schema_ok = verify_table_schema()
    
    if schema_ok:
        # Test functionality
        insert_ok = test_insert_functionality()
        
        if insert_ok:
            print("\n🎉 SUCCESS! Your table is working correctly!")
            print("✅ Schema is correct")
            print("✅ Can insert longer values")
            print("✅ Ready for production use")
        else:
            print("\n⚠️  Schema looks correct but insert failed")
            print("Check your database permissions")
    else:
        print("\n❌ FAILED! Table schema needs to be fixed")
        print("Run the ALTER TABLE commands first")
    
    # Check existing data
    check_existing_data()

if __name__ == "__main__":
    main()
