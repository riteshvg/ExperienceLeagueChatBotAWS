#!/usr/bin/env python3
"""
Add database checker to your existing Streamlit app.
This script shows how to integrate the database checker into your app.py
"""

def add_database_checker_tab():
    """
    Add this function to your app.py to include a database checker tab.
    Call this function in your render_admin_page() function.
    """
    
    # Add this to your app.py in the render_admin_page() function
    # after the existing tabs
    
    st.subheader("🔍 Database Records Checker")
    st.markdown("Check your PostgreSQL database records and analytics data")
    st.markdown("---")
    
    # Check database status
    with st.spinner("Checking database connection..."):
        status = check_database_status()
    
    if status["connected"]:
        st.success("✅ Database connected successfully")
        st.info(f"📊 PostgreSQL version: {status['version']}")
        
        # Show table status
        st.subheader("📋 Table Status")
        required_tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        
        for table in required_tables:
            if table in status["tables"]:
                st.success(f"✅ {table} - EXISTS")
            else:
                st.error(f"❌ {table} - MISSING")
        
        # Get table counts
        with st.spinner("Getting record counts..."):
            counts = get_table_counts()
        
        if "error" not in counts:
            st.subheader("📊 Record Counts")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("User Queries", counts.get('user_queries', 0))
            with col2:
                st.metric("AI Responses", counts.get('ai_responses', 0))
            with col3:
                st.metric("User Feedback", counts.get('user_feedback', 0))
            with col4:
                st.metric("Query Sessions", counts.get('query_sessions', 0))
        
        # Get recent queries
        with st.spinner("Getting recent queries..."):
            recent_queries = get_recent_queries(5)
        
        if "error" not in recent_queries.columns:
            st.subheader("📋 Recent Queries")
            if not recent_queries.empty:
                for idx, row in recent_queries.iterrows():
                    with st.expander(f"Query {row['query_id']}: {row['query_text'][:50]}..."):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Query:** {row['query_text']}")
                            st.write(f"**Session:** {row['session_id']}")
                            st.write(f"**Complexity:** {row['query_complexity']}")
                        
                        with col2:
                            st.write(f"**Response:** {row['response_text'] or 'No response'}")
                            st.write(f"**Model:** {row['model_used'] or 'N/A'}")
                            st.write(f"**Feedback:** {row['feedback_type'] or 'No feedback'}")
            else:
                st.info("No queries found in the database")
        
        # Test data insertion
        st.subheader("🧪 Test Data Insertion")
        if st.button("Test Insert Sample Data", key="test_insert_data"):
            with st.spinner("Testing data insertion..."):
                try:
                    database_url = get_database_connection()
                    conn = psycopg2.connect(database_url)
                    cursor = conn.cursor()
                    
                    # Insert test data
                    session_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    cursor.execute("""
                        INSERT INTO user_queries (query_text, session_id, query_complexity)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, ("Streamlit test query", session_id, "simple"))
                    
                    query_id = cursor.fetchone()[0]
                    
                    cursor.execute("""
                        INSERT INTO ai_responses (query_id, response_text, model_used)
                        VALUES (%s, %s, %s)
                    """, (query_id, "Streamlit test response", "claude-3-haiku"))
                    
                    cursor.execute("""
                        INSERT INTO user_feedback (query_id, response_id, feedback_type)
                        VALUES (%s, %s, %s)
                    """, (query_id, query_id, "positive"))
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    st.success("✅ Test data inserted successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Test data insertion failed: {e}")
    
    else:
        st.error("❌ Database connection failed")
        st.error(f"Error: {status['error']}")
        st.info("🔧 Check your Railway database configuration")

# Add these helper functions to your app.py
def get_database_connection():
    """Get database connection using Railway credentials."""
    import os
    import psycopg2
    
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        return database_url
    
    railway_db_host = os.getenv("RAILWAY_DATABASE_HOST", "containers-us-west-1.railway.app")
    railway_db_port = os.getenv("RAILWAY_DATABASE_PORT", "5432")
    railway_db_name = os.getenv("RAILWAY_DATABASE_NAME", "railway")
    railway_db_user = os.getenv("RAILWAY_DATABASE_USER", "postgres")
    railway_db_password = os.getenv("RAILWAY_DATABASE_PASSWORD", "eeEcTALmHMkWxbKGKIEHRnMmYSEjbTDE")
    
    database_url = f"postgresql://{railway_db_user}:{railway_db_password}@{railway_db_host}:{railway_db_port}/{railway_db_name}"
    return database_url

def check_database_status():
    """Check database connection and table status."""
    import psycopg2
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('user_queries', 'ai_responses', 'user_feedback', 'query_sessions')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            "connected": True,
            "version": version,
            "tables": existing_tables
        }
        
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "tables": []
        }

def get_table_counts():
    """Get record counts for each table."""
    import psycopg2
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        tables = ['user_queries', 'ai_responses', 'user_feedback', 'query_sessions']
        counts = {}
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return counts
        
    except Exception as e:
        return {"error": str(e)}

def get_recent_queries(limit=5):
    """Get recent queries with responses and feedback."""
    import psycopg2
    import pandas as pd
    
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        
        query = """
            SELECT 
                q.id as query_id,
                q.query_text,
                q.session_id,
                q.query_complexity,
                q.created_at as query_time,
                r.response_text,
                r.model_used,
                r.created_at as response_time,
                f.feedback_type,
                f.created_at as feedback_time
            FROM user_queries q
            LEFT JOIN ai_responses r ON q.id = r.query_id
            LEFT JOIN user_feedback f ON q.id = f.query_id
            ORDER BY q.created_at DESC
            LIMIT %s
        """
        
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        
        return df
        
    except Exception as e:
        return pd.DataFrame({"error": [str(e)]})

# Instructions for integration:
print("""
🔧 How to integrate this into your app.py:

1. Add the helper functions (get_database_connection, check_database_status, etc.) to your app.py

2. In your render_admin_page() function, add a new tab:
   st.subheader("🔍 Database Records Checker")
   add_database_checker_tab()

3. Or run the standalone version:
   streamlit run streamlit_db_checker.py

4. Or run the command line version:
   python check_railway_records.py
""")
