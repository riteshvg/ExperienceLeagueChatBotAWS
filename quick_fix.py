#!/usr/bin/env python3
"""
Quick Fix for Railway Table - One-liner solution
Run this script to fix your table schema immediately.
"""

import os, psycopg2

# Get database URL and fix table
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("❌ DATABASE_URL not found. Set it in Railway environment variables.")
    exit(1)

try:
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    print("🔧 Fixing table schema...")
    
    # Fix all columns in one go
    cursor.execute("ALTER TABLE query_analytics ALTER COLUMN reaction TYPE VARCHAR(20);")
    cursor.execute("ALTER TABLE query_analytics ALTER COLUMN userid TYPE VARCHAR(100);") 
    cursor.execute("ALTER TABLE query_analytics ALTER COLUMN query TYPE TEXT;")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("✅ Table fixed! You can now store longer values.")
    
except Exception as e:
    print(f"❌ Error: {e}")
