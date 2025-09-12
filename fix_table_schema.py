#!/usr/bin/env python3
"""
Railway PostgreSQL Table Schema Fixer
This script will modify your query_analytics table to handle longer values.
"""

import os
import psycopg2
from datetime import datetime

def get_database_connection():
    """Get database connection using Railway credentials."""
    # Try different ways to get database URL
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        return database_url
    
    # Try to construct from Railway environment variables
    railway_db_host = os.getenv("RAILWAY_DATABASE_HOST", "containers-us-west-1.railway.app")
    railway_db_port = os.getenv("RAILWAY_DATABASE_PORT", "5432")
    railway_db_name = os.getenv("RAILWAY_DATABASE_NAME", "railway")
    railway_db_user = os.getenv("RAILWAY_DATABASE_USER", "postgres")
    railway_db_password = os.getenv("RAILWAY_DATABASE_PASSWORD", "eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE")
    
    database_url = f"postgresql://{railway_db_user}:{railway_db_password}@{railway_db_host}:{railway_db_port}/{railway_db_name}"
    return database_url

def check_current_schema():
    """Check the current table schema."""
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔍 Current table schema:")
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'query_analytics'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]}: {col[1]}{f'({col[2]})' if col[2] else ''} {'NULL' if col[3] == 'YES' else 'NOT NULL'}")
        
        cursor.close()
        conn.close()
        return columns
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return None

def fix_table_schema():
    """Fix the table schema to handle longer values."""
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔧 Fixing table schema...")
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'query_analytics'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("❌ Table 'query_analytics' does not exist. Creating it...")
            cursor.execute("""
                CREATE TABLE query_analytics (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    userid VARCHAR(100) DEFAULT 'anonymous',
                    date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reaction VARCHAR(20) DEFAULT NULL
                );
            """)
            print("✅ Table created successfully!")
        else:
            print("📋 Table exists. Modifying columns...")
            
            # Modify reaction column to allow longer values
            try:
                cursor.execute("""
                    ALTER TABLE query_analytics 
                    ALTER COLUMN reaction TYPE VARCHAR(20);
                """)
                print("✅ Modified reaction column to VARCHAR(20)")
            except Exception as e:
                print(f"⚠️  Could not modify reaction column: {e}")
            
            # Modify userid column if needed
            try:
                cursor.execute("""
                    ALTER TABLE query_analytics 
                    ALTER COLUMN userid TYPE VARCHAR(100);
                """)
                print("✅ Modified userid column to VARCHAR(100)")
            except Exception as e:
                print(f"⚠️  Could not modify userid column: {e}")
            
            # Ensure query column is TEXT
            try:
                cursor.execute("""
                    ALTER TABLE query_analytics 
                    ALTER COLUMN query TYPE TEXT;
                """)
                print("✅ Modified query column to TEXT")
            except Exception as e:
                print(f"⚠️  Could not modify query column: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Table schema fixed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        return False

def test_insert():
    """Test inserting data with the new schema."""
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🧪 Testing insert with new schema...")
        
        # Test insert with longer values
        cursor.execute("""
            INSERT INTO query_analytics (query, userid, date_time, reaction)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, ("Test query with longer text", "test_user_123", datetime.now(), "positive"))
        
        test_id = cursor.fetchone()[0]
        
        # Clean up test record
        cursor.execute("DELETE FROM query_analytics WHERE id = %s", (test_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Test insert successful!")
        return True
        
    except Exception as e:
        print(f"❌ Test insert failed: {e}")
        return False

def main():
    """Main function to fix the table schema."""
    print("🚀 Railway PostgreSQL Table Schema Fixer")
    print("=" * 50)
    
    # Check current schema
    print("\n1. Checking current schema...")
    current_schema = check_current_schema()
    
    if not current_schema:
        print("❌ Could not check current schema. Exiting.")
        return
    
    # Fix schema
    print("\n2. Fixing table schema...")
    if fix_table_schema():
        print("\n3. Testing new schema...")
        if test_insert():
            print("\n✅ All done! Your table is now ready for longer values.")
        else:
            print("\n❌ Schema fix succeeded but test failed.")
    else:
        print("\n❌ Schema fix failed.")

if __name__ == "__main__":
    main()
