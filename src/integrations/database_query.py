#!/usr/bin/env python3
"""
Simplified Database Query Module for Admin Dashboard
Uses single query_analytics table structure
"""

import os
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
from typing import Dict, List, Optional, Tuple

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

def get_table_info() -> Dict[str, Dict]:
    """Get information about all available tables."""
    return {
        "query_analytics": {
            "name": "Query Analytics",
            "description": "Stores user queries and feedback with tagging information",
            "columns": [
                "id", "query", "userid", "date_time", "reaction", "query_time_seconds", "model_used",
                "products", "question_type", "technical_level", "topics", "urgency", "confidence_score"
            ]
        },
        "questions": {
            "name": "Questions",
            "description": "Stores user questions with metadata for tagging system",
            "columns": [
                "id", "question", "user_id", "session_id", "timestamp", "context", "created_at"
            ]
        },
        "tags": {
            "name": "Tags",
            "description": "Stores question tags and classifications",
            "columns": [
                "id", "question_id", "products", "question_type", "technical_level", 
                "topics", "urgency", "confidence_score", "raw_analysis", "created_at"
            ]
        }
    }

def execute_query(query: str, params: Optional[List] = None) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """Execute a SQL query and return results as DataFrame."""
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return True, df, "Query executed successfully"
        
    except Exception as e:
        return False, None, str(e)

def get_table_data(table_name: str, limit: int = 100, offset: int = 0) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """Get data from any table with pagination."""
    try:
        # Determine the appropriate ORDER BY column based on table
        if table_name == "query_analytics":
            # For query_analytics, join with tags table to get tagging information
            query = """
                SELECT 
                    qa.id, qa.query, qa.userid, qa.date_time, qa.reaction, 
                    qa.query_time_seconds, qa.model_used,
                    COALESCE(t.products, '[]') as products,
                    COALESCE(t.question_type, 'unknown') as question_type,
                    COALESCE(t.technical_level, 'unknown') as technical_level,
                    COALESCE(t.topics, '[]') as topics,
                    COALESCE(t.urgency, 'low') as urgency,
                    COALESCE(t.confidence_score, 0.0) as confidence_score
                FROM query_analytics qa
                LEFT JOIN questions q ON qa.query = q.question
                LEFT JOIN tags t ON q.id = t.question_id
                ORDER BY qa.date_time DESC 
                LIMIT %s OFFSET %s
            """
            return execute_query(query, [limit, offset])
        elif table_name == "questions":
            order_by = "created_at DESC"
            query = f"SELECT * FROM {table_name} ORDER BY {order_by} LIMIT %s OFFSET %s"
            return execute_query(query, [limit, offset])
        elif table_name == "tags":
            order_by = "created_at DESC"
            query = f"SELECT * FROM {table_name} ORDER BY {order_by} LIMIT %s OFFSET %s"
            return execute_query(query, [limit, offset])
        else:
            order_by = "id DESC"
            query = f"SELECT * FROM {table_name} ORDER BY {order_by} LIMIT %s OFFSET %s"
            return execute_query(query, [limit, offset])
    except Exception as e:
        return False, None, str(e)

def get_table_count(table_name: str) -> Tuple[bool, int, str]:
    """Get the total count of records in the table."""
    try:
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        success, df, error = execute_query(query)
        
        if success and not df.empty:
            return True, df.iloc[0]['count'], "Count retrieved successfully"
        else:
            return False, 0, error
    except Exception as e:
        return False, 0, str(e)

def get_analytics_summary(table_name: str = "query_analytics") -> Tuple[bool, Optional[Dict], str]:
    """Get analytics summary data for a specific table."""
    try:
        # Get total count
        count_success, total_count, count_error = get_table_count(table_name)
        
        if not count_success:
            return False, None, f"Error getting count: {count_error}"
        
        summary = {"total_records": total_count}
        
        # Add table-specific analytics
        if table_name == "query_analytics":
            # Get feedback breakdown - handle new reaction values
            feedback_query = """
                SELECT 
                    CASE 
                        WHEN reaction = 'positive' THEN 'positive'
                        WHEN reaction = 'negative' THEN 'negative'
                        WHEN reaction = 'none' THEN 'none'
                        ELSE reaction
                    END as reaction_display,
                    COUNT(*) as count
                FROM query_analytics 
                WHERE reaction IS NOT NULL
                GROUP BY reaction
                ORDER BY count DESC
            """
            success, feedback_df, error = execute_query(feedback_query)
            
            feedback_breakdown = {}
            if success and not feedback_df.empty:
                feedback_breakdown = dict(zip(feedback_df['reaction_display'], feedback_df['count']))
            
            # Get daily activity
            daily_query = """
                SELECT 
                    DATE(date_time) as date,
                    COUNT(*) as queries
                FROM query_analytics 
                GROUP BY DATE(date_time)
                ORDER BY date DESC
                LIMIT 7
            """
            success, daily_df, error = execute_query(daily_query)
            
            daily_activity = {}
            if success and not daily_df.empty:
                daily_activity = dict(zip(daily_df['date'], daily_df['queries']))
            
            # Get tagging analytics for query_analytics
            tagging_query = """
                SELECT 
                    COALESCE(t.question_type, 'unknown') as question_type,
                    COALESCE(t.technical_level, 'unknown') as technical_level,
                    COALESCE(t.urgency, 'low') as urgency,
                    COUNT(*) as count
                FROM query_analytics qa
                LEFT JOIN questions q ON qa.query = q.question
                LEFT JOIN tags t ON q.id = t.question_id
                GROUP BY t.question_type, t.technical_level, t.urgency
                ORDER BY count DESC
            """
            success, tagging_df, error = execute_query(tagging_query)
            
            tagging_breakdown = {}
            if success and not tagging_df.empty:
                # Group by question type
                question_types = tagging_df.groupby('question_type')['count'].sum().to_dict()
                technical_levels = tagging_df.groupby('technical_level')['count'].sum().to_dict()
                urgency_levels = tagging_df.groupby('urgency')['count'].sum().to_dict()
                
                tagging_breakdown = {
                    "question_types": question_types,
                    "technical_levels": technical_levels,
                    "urgency_levels": urgency_levels
                }
            
            summary.update({
                "feedback_breakdown": feedback_breakdown,
                "daily_activity": daily_activity,
                "tagging_breakdown": tagging_breakdown
            })
        
        elif table_name == "questions":
            # Get questions by user
            user_query = """
                SELECT user_id, COUNT(*) as question_count
                FROM questions 
                GROUP BY user_id
                ORDER BY question_count DESC
                LIMIT 10
            """
            success, user_df, error = execute_query(user_query)
            if success and not user_df.empty:
                summary["top_users"] = user_df.to_dict('records')
        
        elif table_name == "tags":
            # Get tags by question type
            type_query = """
                SELECT question_type, COUNT(*) as count
                FROM tags 
                GROUP BY question_type
                ORDER BY count DESC
            """
            success, type_df, error = execute_query(type_query)
            if success and not type_df.empty:
                summary["question_types"] = type_df.to_dict('records')
            
            # Get confidence distribution
            confidence_query = """
                SELECT 
                    CASE 
                        WHEN confidence_score >= 0.8 THEN 'high'
                        WHEN confidence_score >= 0.6 THEN 'medium'
                        ELSE 'low'
                    END as confidence_level,
                    COUNT(*) as count
                FROM tags 
                GROUP BY confidence_level
                ORDER BY count DESC
            """
            success, conf_df, error = execute_query(confidence_query)
            if success and not conf_df.empty:
                summary["confidence_distribution"] = conf_df.to_dict('records')
        
        return True, summary, "Summary retrieved successfully"
        
    except Exception as e:
        return False, None, str(e)

def test_database_connection() -> Tuple[bool, str]:
    """Test database connection."""
    try:
        database_url = get_database_connection()
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return True, f"Connected successfully. PostgreSQL version: {version}"
        
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def render_database_query_interface():
    """Render the database query interface in Streamlit."""
    st.subheader("🔍 Database Query Interface")
    st.markdown("Query and explore your analytics data from all available tables.")
    
    # Test database connection
    with st.spinner("Testing database connection..."):
        connected, message = test_database_connection()
    
    if not connected:
        st.error(f"❌ **Database Connection Failed:** {message}")
        return
    
    st.success(f"✅ **Database Connected:** {message}")
    
    # Get table information
    table_info = get_table_info()
    
    # Table selection
    st.markdown("---")
    st.subheader("📊 Select Table to Query")
    
    table_options = {name: info["name"] for name, info in table_info.items()}
    selected_table = st.selectbox(
        "Choose a table to explore:",
        options=list(table_options.keys()),
        format_func=lambda x: f"{table_options[x]} - {table_info[x]['description']}"
    )
    
    # Display table information
    table_details = table_info[selected_table]
    st.write(f"**Table:** {table_details['name']}")
    st.write(f"**Description:** {table_details['description']}")
    st.write(f"**Columns:** {', '.join(table_details['columns'])}")
    
    # Add manual test section
    st.markdown("---")
    st.subheader("🧪 Database Test")
    
    if st.button("🔍 Test Database Insert", key="test_db_insert"):
        with st.spinner("Testing database insert..."):
            try:
                database_url = get_database_connection()
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()
                
                # Test insert with new fields
                cursor.execute("""
                    INSERT INTO query_analytics (query, userid, date_time, reaction, query_time_seconds, model_used)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, ("Test query with new fields", "admin", datetime.now(), "positive", 2.5, "claude-3-haiku"))
                
                test_id = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                conn.close()
                
                st.success(f"✅ **Test Insert Successful!** ID: `{test_id}`")
                
            except Exception as e:
                st.error(f"❌ **Test Insert Failed:** {str(e)}")
                st.error(f"Error type: {type(e).__name__}")
    
    if st.button("🔍 Check Table Structure", key="check_table_structure"):
        with st.spinner("Checking table structure..."):
            try:
                database_url = get_database_connection()
                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'query_analytics'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                
                if columns:
                    st.success("✅ **Table Structure Found:**")
                    df = pd.DataFrame(columns, columns=['Column', 'Type', 'Nullable', 'Default'])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.error("❌ **No columns found** - Table might not exist")
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                st.error(f"❌ **Structure Check Failed:** {str(e)}")
    
    # Get table information
    table_info = get_table_info()
    
    # Display table information
    table_details = table_info[selected_table]
    st.info(f"**Table:** {table_details['name']} | **Description:** {table_details['description']}")
    
    # Get table count
    with st.spinner("Getting table count..."):
        count_success, total_count, count_error = get_table_count(selected_table)
    
    if count_success:
        st.metric("Total Records", total_count)
    else:
        st.error(f"Error getting count: {count_error}")
    
    # Pagination controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        limit = st.number_input("Records per page:", min_value=1, max_value=1000, value=50, key="limit_analytics")
    
    with col2:
        max_pages = max(1, (total_count // limit) + 1) if count_success else 1
        page = st.number_input("Page:", min_value=1, max_value=max_pages, value=1, key="page_analytics")
    
    with col3:
        offset = (page - 1) * limit
        st.write(f"**Offset:** {offset}")
    
    # Query button
    if st.button("🔍 Query Table Data", key="query_table"):
        with st.spinner(f"Querying {table_details['name']}..."):
            success, df, error = get_table_data(selected_table, limit, offset)
        
        if success:
            if not df.empty:
                st.success(f"✅ Retrieved {len(df)} records from {table_details['name']}")
                
                # Display the data
                st.subheader(f"📋 {table_details['name']} Data")
                st.dataframe(df, use_container_width=True)
                
                # Show column information
                with st.expander("📝 Column Information", expanded=False):
                    st.write("**Available Columns:**")
                    for col in table_details['columns']:
                        if col in df.columns:
                            st.write(f"• **{col}** - {df[col].dtype}")
                        else:
                            st.write(f"• **{col}** - Not in current result set")
                
                # Export options
                st.subheader("📁 Export Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_csv_analytics"
                    )
                
                with col2:
                    json_data = df.to_json(orient='records', indent=2)
                    st.download_button(
                        label="📥 Download as JSON",
                        data=json_data,
                        file_name=f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        key="download_json_analytics"
                    )
            else:
                st.info(f"No data found in {table_details['name']} for the selected page.")
        else:
            st.error(f"❌ **Query Failed:** {error}")
    
    # Analytics summary
    st.markdown("---")
    st.subheader("📊 Analytics Summary")
    
    if st.button("📈 Get Analytics Summary", key="analytics_summary"):
        with st.spinner("Generating analytics summary..."):
            success, summary, error = get_analytics_summary(selected_table)
        
        if success:
            st.success("✅ Analytics summary generated successfully!")
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Queries", summary.get('total_queries', 0))
            
            # Feedback breakdown
            if summary.get('feedback_breakdown'):
                with col2:
                    positive = summary['feedback_breakdown'].get('positive', 0)
                    st.metric("Positive Feedback", positive)
                with col3:
                    negative = summary['feedback_breakdown'].get('negative', 0)
                    st.metric("Negative Feedback", negative)
            
            # Display charts
            if summary.get('feedback_breakdown'):
                st.subheader("👍👎 Feedback Breakdown")
                feedback_df = pd.DataFrame(list(summary['feedback_breakdown'].items()), 
                                         columns=['Reaction Type', 'Count'])
                st.bar_chart(feedback_df.set_index('Reaction Type'))
            
            if summary.get('daily_activity'):
                st.subheader("📈 Daily Activity (Last 7 Days)")
                daily_df = pd.DataFrame(list(summary['daily_activity'].items()), 
                                      columns=['Date', 'Queries'])
                st.line_chart(daily_df.set_index('Date'))
            
            # Display tagging breakdown
            if summary.get('tagging_breakdown'):
                st.subheader("🏷️ Tagging Breakdown")
                tagging_data = summary['tagging_breakdown']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if tagging_data.get('question_types'):
                        st.write("**Question Types:**")
                        for qtype, count in tagging_data['question_types'].items():
                            st.write(f"• {qtype}: {count}")
                
                with col2:
                    if tagging_data.get('technical_levels'):
                        st.write("**Technical Levels:**")
                        for level, count in tagging_data['technical_levels'].items():
                            st.write(f"• {level}: {count}")
                
                with col3:
                    if tagging_data.get('urgency_levels'):
                        st.write("**Urgency Levels:**")
                        for urgency, count in tagging_data['urgency_levels'].items():
                            st.write(f"• {urgency}: {count}")
        else:
            st.error(f"❌ **Analytics Summary Failed:** {error}")