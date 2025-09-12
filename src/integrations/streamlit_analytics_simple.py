"""
Simplified Streamlit integration for query analytics without complex imports.
"""

import streamlit as st
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd

logger = logging.getLogger(__name__)

# Simple data classes to avoid complex imports
class SimpleUserQuery:
    def __init__(self, session_id: str, query_text: str, query_complexity: str = "medium"):
        self.session_id = session_id
        self.query_text = query_text
        self.query_complexity = query_complexity
        self.created_at = datetime.now()

class SimpleAIResponse:
    def __init__(self, query_id: int, response_text: str, model_used: str = "claude-3-haiku"):
        self.query_id = query_id
        self.response_text = response_text
        self.model_used = model_used
        self.created_at = datetime.now()

class SimpleUserFeedback:
    def __init__(self, query_id: int, response_id: int, feedback_type: str):
        self.query_id = query_id
        self.response_id = response_id
        self.feedback_type = feedback_type
        self.created_at = datetime.now()

class SimpleAnalyticsService:
    """Simplified analytics service that works without complex imports."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._connection = None
    
    def get_connection(self):
        """Get database connection."""
        if self._connection is None:
            import psycopg2
            self._connection = psycopg2.connect(self.database_url)
        return self._connection
    
    def store_user_query(self, query: SimpleUserQuery) -> int:
        """Store user query and return query ID."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_queries (query_text, session_id, query_complexity, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (query.query_text, query.session_id, query.query_complexity, query.created_at))
            
            query_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            return query_id
        except Exception as e:
            logger.error(f"Error storing user query: {e}")
            return None
    
    def store_ai_response(self, response: SimpleAIResponse) -> int:
        """Store AI response and return response ID."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ai_responses (query_id, response_text, model_used, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (response.query_id, response.response_text, response.model_used, response.created_at))
            
            response_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            return response_id
        except Exception as e:
            logger.error(f"Error storing AI response: {e}")
            return None
    
    def store_user_feedback(self, feedback: SimpleUserFeedback) -> int:
        """Store user feedback and return feedback ID."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_feedback (query_id, response_id, feedback_type, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (feedback.query_id, feedback.response_id, feedback.feedback_type, feedback.created_at))
            
            feedback_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            return feedback_id
        except Exception as e:
            logger.error(f"Error storing user feedback: {e}")
            return None
    
    def get_analytics_summary(self, start_date=None, end_date=None):
        """Get analytics summary."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build date filter
            date_filter = ""
            params = []
            if start_date and end_date:
                date_filter = "WHERE q.created_at BETWEEN %s AND %s"
                params = [start_date, end_date]
            
            # Get summary data
            cursor.execute(f"""
                SELECT 
                    COUNT(q.id) as total_queries,
                    COUNT(CASE WHEN q.status = 'success' THEN 1 END) as successful_queries,
                    AVG(q.processing_time_ms) as avg_processing_time,
                    COUNT(f.id) as total_feedback,
                    COUNT(CASE WHEN f.feedback_type = 'positive' THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN f.feedback_type = 'negative' THEN 1 END) as negative_feedback
                FROM user_queries q
                LEFT JOIN user_feedback f ON q.id = f.query_id
                {date_filter}
            """, params)
            
            result = cursor.fetchone()
            cursor.close()
            
            return {
                'total_queries': result[0] or 0,
                'successful_queries': result[1] or 0,
                'avg_processing_time_ms': result[2] or 0,
                'total_feedback': result[3] or 0,
                'positive_feedback': result[4] or 0,
                'negative_feedback': result[5] or 0,
                'total_cost': 0.0,  # Simplified - no cost tracking
                'most_used_model': 'claude-3-haiku',
                'total_tokens_used': 0
            }
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {
                'total_queries': 0,
                'successful_queries': 0,
                'avg_processing_time_ms': 0,
                'total_feedback': 0,
                'positive_feedback': 0,
                'negative_feedback': 0,
                'total_cost': 0.0,
                'most_used_model': 'N/A',
                'total_tokens_used': 0
            }
    
    def get_query_analytics(self, limit=50, offset=0, start_date=None, end_date=None):
        """Get query analytics data."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build date filter
            date_filter = ""
            params = [limit, offset]
            if start_date and end_date:
                date_filter = "WHERE q.created_at BETWEEN %s AND %s"
                params = [start_date, end_date, limit, offset]
            
            cursor.execute(f"""
                SELECT 
                    q.id as query_id,
                    q.query_text,
                    q.session_id,
                    q.query_complexity,
                    q.created_at,
                    q.processing_time_ms,
                    q.status,
                    r.model_used,
                    r.response_text,
                    f.feedback_type,
                    f.created_at as feedback_time
                FROM user_queries q
                LEFT JOIN ai_responses r ON q.id = r.query_id
                LEFT JOIN user_feedback f ON q.id = f.query_id
                {date_filter}
                ORDER BY q.created_at DESC
                LIMIT %s OFFSET %s
            """, params)
            
            results = cursor.fetchall()
            cursor.close()
            
            # Convert to simple format
            analytics = []
            for row in results:
                analytics.append({
                    'query_id': row[0],
                    'query_text': row[1],
                    'session_id': row[2],
                    'query_complexity': row[3],
                    'created_at': row[4],
                    'processing_time_ms': row[5],
                    'status': row[6],
                    'model_used': row[7],
                    'response_text': row[8],
                    'feedback_type': row[9],
                    'feedback_time': row[10]
                })
            
            return analytics
        except Exception as e:
            logger.error(f"Error getting query analytics: {e}")
            return []
    
    def export_analytics_data(self, start_date=None, end_date=None, format='csv'):
        """Export analytics data."""
        try:
            analytics = self.get_query_analytics(start_date=start_date, end_date=end_date)
            
            if format == 'csv':
                import io
                output = io.StringIO()
                df = pd.DataFrame(analytics)
                df.to_csv(output, index=False)
                return output.getvalue()
            elif format == 'json':
                import json
                return json.dumps(analytics, default=str, indent=2)
            else:
                return str(analytics)
        except Exception as e:
            logger.error(f"Error exporting analytics data: {e}")
            return ""

class StreamlitAnalyticsIntegration:
    """Simplified integration class for Streamlit analytics features."""
    
    def __init__(self, analytics_service: SimpleAnalyticsService):
        self.analytics_service = analytics_service
    
    def track_query(self, session_id: str, query_text: str, query_complexity: str = "medium") -> int:
        """Track a user query."""
        try:
            query = SimpleUserQuery(session_id, query_text, query_complexity)
            return self.analytics_service.store_user_query(query)
        except Exception as e:
            logger.error(f"Error tracking query: {e}")
            return None
    
    def track_response(self, query_id: int, response_text: str, model_used: str = "claude-3-haiku") -> int:
        """Track an AI response."""
        try:
            response = SimpleAIResponse(query_id, response_text, model_used)
            return self.analytics_service.store_ai_response(response)
        except Exception as e:
            logger.error(f"Error tracking response: {e}")
            return None
    
    def track_feedback(self, query_id: int, response_id: int, feedback_type: str) -> int:
        """Track user feedback."""
        try:
            feedback = SimpleUserFeedback(query_id, response_id, feedback_type)
            return self.analytics_service.store_user_feedback(feedback)
        except Exception as e:
            logger.error(f"Error tracking feedback: {e}")
            return None
    
    def render_analytics_dashboard(self):
        """Render the analytics dashboard in Streamlit."""
        st.header("📊 Query Analytics Dashboard")
        st.markdown("**Track and analyze user queries, responses, and feedback**")
        st.markdown("---")
        
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=7),
                help="Select start date for analytics"
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now(),
                help="Select end date for analytics"
            )
        
        # Convert dates to datetime
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Analytics summary
        try:
            summary = self.analytics_service.get_analytics_summary(
                start_date=start_datetime,
                end_date=end_datetime
            )
            
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Queries", summary['total_queries'])
            with col2:
                success_rate = (summary['successful_queries']/max(summary['total_queries'], 1)*100)
                st.metric("Success Rate", f"{success_rate:.1f}%")
            with col3:
                st.metric("Avg Processing Time", f"{summary['avg_processing_time_ms']:.0f}ms")
            with col4:
                st.metric("Total Feedback", summary['total_feedback'])
            
            # Feedback metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Positive Feedback", summary['positive_feedback'])
            with col2:
                st.metric("Negative Feedback", summary['negative_feedback'])
            with col3:
                total_feedback = summary['positive_feedback'] + summary['negative_feedback']
                satisfaction_rate = (summary['positive_feedback'] / max(total_feedback, 1)) * 100
                st.metric("Satisfaction Rate", f"{satisfaction_rate:.1f}%")
            
        except Exception as e:
            st.error(f"Error loading analytics summary: {e}")
            return
        
        # Query history table
        st.markdown("---")
        st.subheader("📋 Query History")
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)
        with col2:
            page_number = st.number_input("Page", min_value=1, value=1)
        
        offset = (page_number - 1) * page_size
        
        try:
            # Get query analytics
            analytics = self.analytics_service.get_query_analytics(
                limit=page_size,
                offset=offset,
                start_date=start_datetime,
                end_date=end_datetime
            )
            
            if analytics:
                # Convert to DataFrame for display
                data = []
                for item in analytics:
                    data.append({
                        'Query ID': item['query_id'],
                        'Session ID': item['session_id'],
                        'Query Text': item['query_text'][:100] + '...' if len(item['query_text']) > 100 else item['query_text'],
                        'Complexity': item['query_complexity'],
                        'Created At': item['created_at'].strftime('%Y-%m-%d %H:%M:%S') if item['created_at'] else 'N/A',
                        'Processing Time (ms)': item['processing_time_ms'] or 'N/A',
                        'Status': item['status'] or 'N/A',
                        'Model Used': item['model_used'] or 'N/A',
                        'Feedback': item['feedback_type'] or 'N/A',
                        'Feedback Time': item['feedback_time'].strftime('%Y-%m-%d %H:%M:%S') if item['feedback_time'] else 'N/A'
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
                
                # Download buttons
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📥 Download CSV", key="download_csv"):
                        try:
                            csv_data = self.analytics_service.export_analytics_data(
                                start_date=start_datetime,
                                end_date=end_datetime,
                                format='csv'
                            )
                            st.download_button(
                                label="Download CSV",
                                data=csv_data,
                                file_name=f"query_analytics_{start_date}_{end_date}.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.error(f"Error generating CSV: {e}")
                
                with col2:
                    if st.button("📥 Download JSON", key="download_json"):
                        try:
                            json_data = self.analytics_service.export_analytics_data(
                                start_date=start_datetime,
                                end_date=end_datetime,
                                format='json'
                            )
                            st.download_button(
                                label="Download JSON",
                                data=json_data,
                                file_name=f"query_analytics_{start_date}_{end_date}.json",
                                mime="application/json"
                            )
                        except Exception as e:
                            st.error(f"Error generating JSON: {e}")
                
            else:
                st.info("No query data found for the selected date range.")
                
        except Exception as e:
            st.error(f"Error loading query history: {e}")

def initialize_analytics_service() -> Optional[StreamlitAnalyticsIntegration]:
    """Initialize simplified analytics service for Streamlit."""
    try:
        # Get database URL
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("DATABASE_URL not found in environment variables")
            return None
        
        # Create simplified analytics service
        analytics_service = SimpleAnalyticsService(database_url)
        return StreamlitAnalyticsIntegration(analytics_service)
        
    except Exception as e:
        logger.error(f"Error initializing analytics service: {e}")
        return None
