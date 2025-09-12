#!/usr/bin/env python3
"""
Update Railway Table Schema - Add new columns for timing and model tracking
This script will add the new columns to your existing query_analytics table.
"""

import os
import psycopg2
from datetime import datetime

def get_database_connection():
    """Get database connection using Railway credentials."""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return None
    
    return database_url

def update_table_schema():
    """Update the table schema to add new columns."""
    try:
        database_url = get_database_connection()
        if not database_url:
            return False
            
        print("🔍 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔧 Updating table schema...")
        
        # Check if new columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'query_analytics' 
            AND column_name IN ('query_time_seconds', 'model_used', 'created_at')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add new columns if they don't exist
        if 'query_time_seconds' not in existing_columns:
            cursor.execute("""
                ALTER TABLE query_analytics 
                ADD COLUMN query_time_seconds DECIMAL(10,3) DEFAULT NULL;
            """)
            print("✅ Added query_time_seconds column")
        else:
            print("ℹ️  query_time_seconds column already exists")
            
        if 'model_used' not in existing_columns:
            cursor.execute("""
                ALTER TABLE query_analytics 
                ADD COLUMN model_used VARCHAR(50) DEFAULT NULL;
            """)
            print("✅ Added model_used column")
        else:
            print("ℹ️  model_used column already exists")
            
        if 'created_at' not in existing_columns:
            cursor.execute("""
                ALTER TABLE query_analytics 
                ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """)
            print("✅ Added created_at column")
        else:
            print("ℹ️  created_at column already exists")
        
        # Update reaction column to allow longer values
        cursor.execute("""
            ALTER TABLE query_analytics 
            ALTER COLUMN reaction TYPE VARCHAR(20);
        """)
        print("✅ Updated reaction column to VARCHAR(20)")
        
        # Update userid column to allow longer values
        cursor.execute("""
            ALTER TABLE query_analytics 
            ALTER COLUMN userid TYPE VARCHAR(100);
        """)
        print("✅ Updated userid column to VARCHAR(100)")
        
        # Ensure query column is TEXT
        cursor.execute("""
            ALTER TABLE query_analytics 
            ALTER COLUMN query TYPE TEXT;
        """)
        print("✅ Updated query column to TEXT")
        
        # Add indexes for better performance
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_analytics_date_time 
                ON query_analytics(date_time);
            """)
            print("✅ Added date_time index")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_analytics_userid 
                ON query_analytics(userid);
            """)
            print("✅ Added userid index")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_analytics_model 
                ON query_analytics(model_used);
            """)
            print("✅ Added model_used index")
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_analytics_reaction 
                ON query_analytics(reaction);
            """)
            print("✅ Added reaction index")
            
        except Exception as e:
            print(f"⚠️  Some indexes may already exist: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Table schema updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        return False

def verify_schema():
    """Verify the updated schema."""
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("\n🔍 Verifying updated schema...")
        cursor.execute("""
            SELECT 
                column_name, 
                data_type, 
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'query_analytics'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        print("\n📊 Updated Table Schema:")
        print("=" * 80)
        print(f"{'Column':<20} {'Type':<20} {'Max Length':<12} {'Nullable':<8} {'Default'}")
        print("-" * 80)
        
        for col in columns:
            col_name, data_type, max_length, nullable, default = col
            max_len_str = str(max_length) if max_length else "unlimited"
            nullable_str = "YES" if nullable == "YES" else "NO"
            default_str = str(default) if default else "None"
            
            print(f"{col_name:<20} {data_type:<20} {max_len_str:<12} {nullable_str:<8} {default_str}")
        
        print("=" * 80)
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")
        return False

def test_new_schema():
    """Test inserting data with the new schema."""
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("\n🧪 Testing new schema...")
        
        # Test insert with all new fields
        cursor.execute("""
            INSERT INTO query_analytics (
                query, userid, date_time, reaction, 
                query_time_seconds, model_used
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            "Test query with new schema fields",
            "test_user_12345",
            datetime.now(),
            "positive",
            3.25,
            "claude-3-haiku"
        ))
        
        test_id = cursor.fetchone()[0]
        
        # Clean up test record
        cursor.execute("DELETE FROM query_analytics WHERE id = %s", (test_id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print("✅ Test insert successful! New schema is working.")
        return True
        
    except Exception as e:
        print(f"❌ Test insert failed: {e}")
        return False

def main():
    """Main function to update the table schema."""
    print("🚀 Railway Table Schema Updater")
    print("=" * 50)
    print("This will add new columns for timing and model tracking.")
    print()
    
    # Update schema
    print("1. Updating table schema...")
    if update_table_schema():
        print("\n2. Verifying schema...")
        if verify_schema():
            print("\n3. Testing new schema...")
            if test_new_schema():
                print("\n🎉 SUCCESS! Your table has been updated successfully!")
                print("✅ New columns added: query_time_seconds, model_used, created_at")
                print("✅ Existing columns updated: reaction, userid, query")
                print("✅ Indexes added for better performance")
                print("✅ Ready for enhanced analytics!")
            else:
                print("\n❌ Schema update succeeded but test failed.")
        else:
            print("\n❌ Schema verification failed.")
    else:
        print("\n❌ Schema update failed.")

if __name__ == "__main__":
    main()
