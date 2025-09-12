#!/usr/bin/env python3
"""
Database Query Module for Admin Dashboard
Provides functions to query database tables and display results
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
    """Get information about all database tables."""
    return {
        "user_queries": {
            "name": "User Queries",
            "description": "Stores user questions and queries",
            "columns": [
                "id", "query_text", "session_id", "query_complexity", 
                "created_at", "updated_at"
            ]
        },
        "ai_responses": {
            "name": "AI Responses", 
            "description": "Stores AI-generated responses to queries",
            "columns": [
                "id", "query_id", "response_text", "model_used", 
                "created_at", "updated_at"
            ]
        },
        "user_feedback": {
            "name": "User Feedback",
            "description": "Stores user feedback on responses",
            "columns": [
                "id", "query_id", "response_id", "feedback_type", 
                "created_at", "updated_at"
            ]
        },
        "query_sessions": {
            "name": "Query Sessions",
            "description": "Stores session information and metadata",
            "columns": [
                "id", "session_id", "user_agent", "ip_address", 
                "created_at", "updated_at"
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
    """Get data from a specific table with pagination."""
    try:
        query = f"SELECT * FROM {table_name} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        return execute_query(query, [limit, offset])
    except Exception as e:
        return False, None, str(e)

def get_table_count(table_name: str) -> Tuple[bool, int, str]:
    """Get the total count of records in a table."""
    try:
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        success, df, error = execute_query(query)
        
        if success and not df.empty:
            return True, df.iloc[0]['count'], "Count retrieved successfully"
        else:
            return False, 0, error
    except Exception as e:
        return False, 0, str(e)

def get_recent_queries_with_responses(limit: int = 50) -> Tuple[bool, Optional[pd.DataFrame], str]:
    """Get recent queries with their responses and feedback."""
    try:
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
        return execute_query(query, [limit])
    except Exception as e:
        return False, None, str(e)

def get_analytics_summary() -> Tuple[bool, Optional[Dict], str]:
    """Get analytics summary data."""
    try:
        # Get total counts
        queries_success, queries_count, queries_error = get_table_count("user_queries")
        responses_success, responses_count, responses_error = get_table_count("ai_responses")
        feedback_success, feedback_count, feedback_error = get_table_count("user_feedback")
        
        if not all([queries_success, responses_success, feedback_success]):
            return False, None, f"Error getting counts: {queries_error or responses_error or feedback_error}"
        
        # Get feedback breakdown
        feedback_query = """
            SELECT 
                feedback_type,
                COUNT(*) as count
            FROM user_feedback 
            GROUP BY feedback_type
            ORDER BY count DESC
        """
        success, feedback_df, error = execute_query(feedback_query)
        
        feedback_breakdown = {}
        if success and not feedback_df.empty:
            feedback_breakdown = dict(zip(feedback_df['feedback_type'], feedback_df['count']))
        
        # Get model usage breakdown
        model_query = """
            SELECT 
                model_used,
                COUNT(*) as count
            FROM ai_responses 
            GROUP BY model_used
            ORDER BY count DESC
        """
        success, model_df, error = execute_query(model_query)
        
        model_breakdown = {}
        if success and not model_df.empty:
            model_breakdown = dict(zip(model_df['model_used'], model_df['count']))
        
        summary = {
            "total_queries": queries_count,
            "total_responses": responses_count,
            "total_feedback": feedback_count,
            "feedback_breakdown": feedback_breakdown,
            "model_breakdown": model_breakdown
        }
        
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
    st.markdown("Query and explore your database tables directly from the admin dashboard.")
    
    # Test database connection
    with st.spinner("Testing database connection..."):
        connected, message = test_database_connection()
    
    if not connected:
        st.error(f"❌ **Database Connection Failed:** {message}")
        return
    
    st.success(f"✅ **Database Connected:** {message}")
    
    # Get table information
    table_info = get_table_info()
    
    # Table selection dropdown
    st.markdown("---")
    st.subheader("📊 Select Table to Query")
    
    table_options = {f"{table_name} - {info['name']}": table_name for table_name, info in table_info.items()}
    selected_table_display = st.selectbox(
        "Choose a table:",
        options=list(table_options.keys()),
        help="Select a table to view its data"
    )
    
    if selected_table_display:
        selected_table = table_options[selected_table_display]
        table_details = table_info[selected_table]
        
        # Display table information
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
            limit = st.number_input("Records per page:", min_value=1, max_value=1000, value=50, key=f"limit_{selected_table}")
        
        with col2:
            max_pages = max(1, (total_count // limit) + 1) if count_success else 1
            page = st.number_input("Page:", min_value=1, max_value=max_pages, value=1, key=f"page_{selected_table}")
        
        with col3:
            offset = (page - 1) * limit
            st.write(f"**Offset:** {offset}")
        
        # Query button
        if st.button("🔍 Query Table", key=f"query_{selected_table}"):
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
                            file_name=f"{selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            key=f"download_csv_{selected_table}"
                        )
                    
                    with col2:
                        json_data = df.to_json(orient='records', indent=2)
                        st.download_button(
                            label="📥 Download as JSON",
                            data=json_data,
                            file_name=f"{selected_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            key=f"download_json_{selected_table}"
                        )
                else:
                    st.info(f"No data found in {table_details['name']} for the selected page.")
            else:
                st.error(f"❌ **Query Failed:** {error}")
    
    # Quick analytics section
    st.markdown("---")
    st.subheader("📈 Quick Analytics")
    
    if st.button("📊 Get Analytics Summary", key="analytics_summary"):
        with st.spinner("Generating analytics summary..."):
            success, summary, error = get_analytics_summary()
        
        if success:
            st.success("✅ Analytics summary generated successfully!")
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Queries", summary.get('total_queries', 0))
            with col2:
                st.metric("Total Responses", summary.get('total_responses', 0))
            with col3:
                st.metric("Total Feedback", summary.get('total_feedback', 0))
            
            # Feedback breakdown
            if summary.get('feedback_breakdown'):
                st.subheader("👍👎 Feedback Breakdown")
                feedback_df = pd.DataFrame(list(summary['feedback_breakdown'].items()), 
                                         columns=['Feedback Type', 'Count'])
                st.bar_chart(feedback_df.set_index('Feedback Type'))
            
            # Model usage breakdown
            if summary.get('model_breakdown'):
                st.subheader("🤖 Model Usage Breakdown")
                model_df = pd.DataFrame(list(summary['model_breakdown'].items()), 
                                      columns=['Model', 'Count'])
                st.bar_chart(model_df.set_index('Model'))
        else:
            st.error(f"❌ **Analytics Summary Failed:** {error}")
    
    # Recent queries with responses
    st.markdown("---")
    st.subheader("🕒 Recent Queries with Responses")
    
    if st.button("📋 Get Recent Queries", key="recent_queries"):
        with st.spinner("Fetching recent queries..."):
            success, df, error = get_recent_queries_with_responses(20)
        
        if success:
            if not df.empty:
                st.success(f"✅ Retrieved {len(df)} recent query records")
                
                # Display recent queries
                st.dataframe(df, use_container_width=True)
                
                # Show summary statistics
                st.subheader("📊 Recent Activity Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    unique_queries = df['query_id'].nunique()
                    st.metric("Unique Queries", unique_queries)
                
                with col2:
                    responses_count = df['response_text'].notna().sum()
                    st.metric("Responses Generated", responses_count)
                
                with col3:
                    feedback_count = df['feedback_type'].notna().sum()
                    st.metric("Feedback Given", feedback_count)
            else:
                st.info("No recent queries found in the database.")
        else:
            st.error(f"❌ **Recent Queries Failed:** {error}")
