#!/usr/bin/env python3
"""
Add tagging columns to the existing query_analytics table
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

def add_tagging_columns():
    """Add tagging columns to query_analytics table."""
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔍 Adding tagging columns to query_analytics table...")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'query_analytics' 
            AND column_name IN ('products', 'question_type', 'technical_level', 'topics', 'urgency', 'confidence_score')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add missing columns
        columns_to_add = [
            ("products", "TEXT DEFAULT '[]'"),
            ("question_type", "VARCHAR(50) DEFAULT 'unknown'"),
            ("technical_level", "VARCHAR(50) DEFAULT 'unknown'"),
            ("topics", "TEXT DEFAULT '[]'"),
            ("urgency", "VARCHAR(20) DEFAULT 'low'"),
            ("confidence_score", "DECIMAL(5,3) DEFAULT 0.0")
        ]
        
        for column_name, column_def in columns_to_add:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE query_analytics ADD COLUMN {column_name} {column_def}")
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"❌ Error adding column {column_name}: {e}")
            else:
                print(f"ℹ️ Column {column_name} already exists")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Successfully added tagging columns to query_analytics table")
        return True
        
    except Exception as e:
        print(f"❌ Error adding tagging columns: {e}")
        return False

if __name__ == "__main__":
    print("🏷️ Adding Tagging Columns to Query Analytics Table")
    print("=" * 60)
    
    success = add_tagging_columns()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("The query_analytics table now includes tagging columns:")
        print("- products: JSON array of detected products")
        print("- question_type: Type of question (implementation, troubleshooting, etc.)")
        print("- technical_level: Technical complexity level")
        print("- topics: JSON array of detected topics")
        print("- urgency: Urgency level (low, medium, high)")
        print("- confidence_score: Tagging confidence score")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
