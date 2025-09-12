#!/usr/bin/env python3
"""
Check database structure and show what tables should exist.
This script shows the expected database schema without connecting to Railway.
"""

def show_expected_schema():
    """Show the expected database schema."""
    print("🗄️ Expected Railway Database Schema")
    print("=" * 60)
    
    schema = {
        "user_queries": {
            "description": "Stores user queries and metadata",
            "columns": [
                ("id", "SERIAL PRIMARY KEY", "Auto-incrementing unique ID"),
                ("query_text", "TEXT NOT NULL", "The actual query text"),
                ("session_id", "VARCHAR(255)", "Session identifier"),
                ("query_complexity", "VARCHAR(50) DEFAULT 'medium'", "Query complexity level"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "Creation timestamp"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "Last update timestamp")
            ]
        },
        "ai_responses": {
            "description": "Stores AI responses to queries",
            "columns": [
                ("id", "SERIAL PRIMARY KEY", "Auto-incrementing unique ID"),
                ("query_id", "INTEGER REFERENCES user_queries(id)", "Foreign key to user_queries"),
                ("response_text", "TEXT NOT NULL", "The AI response text"),
                ("model_used", "VARCHAR(100)", "Model used for response"),
                ("response_time_ms", "INTEGER", "Response time in milliseconds"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "Creation timestamp")
            ]
        },
        "user_feedback": {
            "description": "Stores user feedback on responses",
            "columns": [
                ("id", "SERIAL PRIMARY KEY", "Auto-incrementing unique ID"),
                ("query_id", "INTEGER REFERENCES user_queries(id)", "Foreign key to user_queries"),
                ("response_id", "INTEGER REFERENCES ai_responses(id)", "Foreign key to ai_responses"),
                ("feedback_type", "VARCHAR(50) NOT NULL", "Type of feedback (positive/negative)"),
                ("feedback_text", "TEXT", "Additional feedback text"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "Creation timestamp")
            ]
        },
        "query_sessions": {
            "description": "Stores session information",
            "columns": [
                ("id", "VARCHAR(255) PRIMARY KEY", "Session identifier"),
                ("user_id", "VARCHAR(255)", "User identifier"),
                ("session_start", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "Session start time"),
                ("session_end", "TIMESTAMP", "Session end time"),
                ("total_queries", "INTEGER DEFAULT 0", "Total queries in session"),
                ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "Creation timestamp")
            ]
        }
    }
    
    for table_name, table_info in schema.items():
        print(f"\n📋 Table: {table_name}")
        print(f"Description: {table_info['description']}")
        print("-" * 60)
        print(f"{'Column':<20} {'Type':<30} {'Description'}")
        print("-" * 60)
        
        for column, data_type, description in table_info['columns']:
            print(f"{column:<20} {data_type:<30} {description}")
    
    print(f"\n🔍 Indexes:")
    print("-" * 60)
    indexes = [
        ("idx_user_queries_session_id", "user_queries(session_id)", "Fast session lookups"),
        ("idx_user_queries_created_at", "user_queries(created_at)", "Fast date-based queries"),
        ("idx_ai_responses_query_id", "ai_responses(query_id)", "Fast response lookups"),
        ("idx_user_feedback_query_id", "user_feedback(query_id)", "Fast feedback lookups"),
        ("idx_user_feedback_response_id", "user_feedback(response_id)", "Fast response feedback lookups")
    ]
    
    for index_name, table_column, description in indexes:
        print(f"{index_name:<30} {table_column:<25} {description}")

def show_expected_queries():
    """Show expected query patterns."""
    print(f"\n📊 Expected Query Patterns:")
    print("=" * 60)
    
    queries = [
        ("Insert User Query", 
         "INSERT INTO user_queries (query_text, session_id, query_complexity) VALUES (?, ?, ?)"),
        
        ("Insert AI Response", 
         "INSERT INTO ai_responses (query_id, response_text, model_used) VALUES (?, ?, ?)"),
        
        ("Insert User Feedback", 
         "INSERT INTO user_feedback (query_id, response_id, feedback_type) VALUES (?, ?, ?)"),
        
        ("Get Analytics Summary", 
         "SELECT COUNT(*), AVG(processing_time_ms) FROM user_queries WHERE created_at BETWEEN ? AND ?"),
        
        ("Get Recent Queries", 
         "SELECT * FROM user_queries ORDER BY created_at DESC LIMIT ?"),
        
        ("Get Query with Response", 
         "SELECT q.*, r.* FROM user_queries q LEFT JOIN ai_responses r ON q.id = r.query_id WHERE q.id = ?"),
        
        ("Get Feedback Stats", 
         "SELECT feedback_type, COUNT(*) FROM user_feedback GROUP BY feedback_type")
    ]
    
    for description, query in queries:
        print(f"\n{description}:")
        print(f"  {query}")

def show_railway_connection_info():
    """Show Railway connection information."""
    print(f"\n🔗 Railway Connection Information:")
    print("=" * 60)
    
    print("To connect to your Railway database, you need:")
    print("1. DATABASE_URL environment variable")
    print("2. Format: postgresql://username:password@host:port/database")
    print("3. Example: postgresql://postgres:password@containers-us-west-1.railway.app:5432/railway")
    
    print(f"\nEnvironment Variables to Check:")
    print("- DATABASE_URL (required)")
    print("- RAILWAY_ENVIRONMENT (optional)")
    
    print(f"\nTo test connection locally:")
    print("1. Set DATABASE_URL in your .env file")
    print("2. Run: python check_railway_db_offline.py")
    print("3. Or run: python test_railway_database.py")

def main():
    """Main function."""
    show_expected_schema()
    show_expected_queries()
    show_railway_connection_info()
    
    print(f"\n🎯 Next Steps:")
    print("=" * 60)
    print("1. Check if DATABASE_URL is set in your environment")
    print("2. Run 'python check_railway_db_offline.py' to test connection")
    print("3. Check Railway logs for database initialization status")
    print("4. Verify tables exist in Railway dashboard")

if __name__ == "__main__":
    main()
