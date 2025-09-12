#!/usr/bin/env python3
"""
Simple Railway Table Fix - Run this on Railway
This script modifies your table to handle longer values.
"""

import os
import psycopg2
from datetime import datetime

def fix_railway_table():
    """Fix the Railway table schema."""
    try:
        # Get DATABASE_URL from Railway environment
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        print(f"🔍 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔧 Modifying table schema...")
        
        # Modify reaction column to allow longer values
        cursor.execute("""
            ALTER TABLE query_analytics 
            ALTER COLUMN reaction TYPE VARCHAR(20);
        """)
        print("✅ Modified reaction column to VARCHAR(20)")
        
        # Modify userid column to allow longer values
        cursor.execute("""
            ALTER TABLE query_analytics 
            ALTER COLUMN userid TYPE VARCHAR(100);
        """)
        print("✅ Modified userid column to VARCHAR(100)")
        
        # Ensure query column is TEXT
        cursor.execute("""
            ALTER TABLE query_analytics 
            ALTER COLUMN query TYPE TEXT;
        """)
        print("✅ Modified query column to TEXT")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Table schema updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    fix_railway_table()
