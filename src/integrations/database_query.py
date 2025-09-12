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
    """Get information about the query_analytics table."""
    return {
        "query_analytics": {
            "name": "Query Analytics",
            "description": "Stores user queries and feedback in a single table",
            "columns": [
                "id", "query", "userid", "date_time", "reaction"
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
    """Get data from the query_analytics table with pagination."""
    try:
        query = f"SELECT * FROM {table_name} ORDER BY date_time DESC LIMIT %s OFFSET %s"
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

def get_analytics_summary() -> Tuple[bool, Optional[Dict], str]:
    """Get analytics summary data."""
    try:
        # Get total count
        count_success, total_count, count_error = get_table_count("query_analytics")
        
        if not count_success:
            return False, None, f"Error getting count: {count_error}"
        
        # Get feedback breakdown
        feedback_query = """
            SELECT 
                reaction,
                COUNT(*) as count
            FROM query_analytics 
            WHERE reaction IS NOT NULL
            GROUP BY reaction
            ORDER BY count DESC
        """
        success, feedback_df, error = execute_query(feedback_query)
        
        feedback_breakdown = {}
        if success and not feedback_df.empty:
            feedback_breakdown = dict(zip(feedback_df['reaction'], feedback_df['count']))
        
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
        
        summary = {
            "total_queries": total_count,
            "feedback_breakdown": feedback_breakdown,
            "daily_activity": daily_activity
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
    """Render the simplified database query interface in Streamlit."""
    st.subheader("🔍 Database Query Interface")
    st.markdown("Query and explore your analytics data from the simplified single table.")
    
    # Test database connection
    with st.spinner("Testing database connection..."):
        connected, message = test_database_connection()
    
    if not connected:
        st.error(f"❌ **Database Connection Failed:** {message}")
        return
    
    st.success(f"✅ **Database Connected:** {message}")
    
    # Get table information
    table_info = get_table_info()
    table_name = "query_analytics"  # Single table
    
    # Display table information
    table_details = table_info[table_name]
    st.info(f"**Table:** {table_details['name']} | **Description:** {table_details['description']}")
    
    # Get table count
    with st.spinner("Getting table count..."):
        count_success, total_count, count_error = get_table_count(table_name)
    
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
    if st.button("🔍 Query Analytics Data", key="query_analytics"):
        with st.spinner(f"Querying {table_details['name']}..."):
            success, df, error = get_table_data(table_name, limit, offset)
        
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
            success, summary, error = get_analytics_summary()
        
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
        else:
            st.error(f"❌ **Analytics Summary Failed:** {error}")