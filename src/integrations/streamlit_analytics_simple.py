"""
Simplified Streamlit integration for query analytics using single table structure.
"""

import streamlit as st
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd

logger = logging.getLogger(__name__)

class SimpleAnalyticsService:
    """Simplified analytics service using single query_analytics table."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._connection = None
    
    def get_connection(self):
        """Get database connection."""
        if self._connection is None:
            import psycopg2
            self._connection = psycopg2.connect(self.database_url)
        return self._connection
    
    def store_query_with_feedback(self, query: str, userid: str = "anonymous", reaction: str = None) -> int:
        """Store query and feedback in single table."""
        try:
            print(f"🔍 Attempting to store query: '{query[:50]}...' for user: {userid}")
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO query_analytics (query, userid, date_time, reaction)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (query, userid, datetime.now(), reaction))
            
            query_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            
            print(f"✅ Successfully stored query with ID: {query_id}")
            return query_id
        except Exception as e:
            print(f"❌ Error storing query: {e}")
            logger.error(f"Error storing query: {e}")
            return None
    
    def update_feedback(self, query_id: int, reaction: str) -> bool:
        """Update feedback for existing query."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE query_analytics 
                SET reaction = %s 
                WHERE id = %s
            """, (reaction, query_id))
            
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            logger.error(f"Error updating feedback: {e}")
            return False
    
    def get_analytics_summary(self, start_date=None, end_date=None):
        """Get analytics summary from single table."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build date filter
            date_filter = ""
            params = []
            if start_date and end_date:
                date_filter = "WHERE date_time BETWEEN %s AND %s"
                params = [start_date, end_date]
            
            # Get summary data
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(CASE WHEN reaction = 'positive' THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN reaction = 'negative' THEN 1 END) as negative_feedback,
                    COUNT(CASE WHEN reaction IS NOT NULL THEN 1 END) as total_feedback
                FROM query_analytics
                {date_filter}
            """, params)
            
            result = cursor.fetchone()
            cursor.close()
            
            total_queries = result[0] or 0
            positive_feedback = result[1] or 0
            negative_feedback = result[2] or 0
            total_feedback = result[3] or 0
            
            return {
                'total_queries': total_queries,
                'total_feedback': total_feedback,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback,
                'satisfaction_rate': (positive_feedback / max(total_feedback, 1)) * 100,
                'feedback_rate': (total_feedback / max(total_queries, 1)) * 100
            }
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {
                'total_queries': 0,
                'total_feedback': 0,
                'positive_feedback': 0,
                'negative_feedback': 0,
                'satisfaction_rate': 0.0,
                'feedback_rate': 0.0
            }
    
    def get_query_analytics(self, limit=50, offset=0, start_date=None, end_date=None):
        """Get query analytics data from single table."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build date filter
            date_filter = ""
            params = [limit, offset]
            if start_date and end_date:
                date_filter = "WHERE date_time BETWEEN %s AND %s"
                params = [start_date, end_date, limit, offset]
            
            cursor.execute(f"""
                SELECT 
                    id,
                    query,
                    userid,
                    date_time,
                    reaction
                FROM query_analytics
                {date_filter}
                ORDER BY date_time DESC
                LIMIT %s OFFSET %s
            """, params)
            
            results = cursor.fetchall()
            cursor.close()
            
            # Convert to simple format
            analytics = []
            for row in results:
                analytics.append({
                    'id': row[0],
                    'query': row[1],
                    'userid': row[2],
                    'date_time': row[3],
                    'reaction': row[4]
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
            return self.analytics_service.store_query_with_feedback(
                query=query_text, 
                userid=session_id, 
                reaction=None
            )
        except Exception as e:
            logger.error(f"Error tracking query: {e}")
            return None
    
    def track_feedback(self, query_id: int, response_id: int = None, feedback_type: str = None) -> bool:
        """Track user feedback."""
        try:
            return self.analytics_service.update_feedback(query_id, feedback_type)
        except Exception as e:
            logger.error(f"Error tracking feedback: {e}")
            return False
    
    def track_response(self, query_id: int, response_text: str = None, model_used: str = None) -> int:
        """Track an AI response (simplified - just return query_id)."""
        return query_id
    
    def render_analytics_dashboard(self):
        """Render the analytics dashboard in Streamlit."""
        st.header("📊 Query Analytics Dashboard")
        st.markdown("**Track and analyze user queries and feedback**")
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
                st.metric("Total Feedback", summary['total_feedback'])
            with col3:
                st.metric("Positive Feedback", summary['positive_feedback'])
            with col4:
                st.metric("Negative Feedback", summary['negative_feedback'])
            
            # Additional metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Satisfaction Rate", f"{summary['satisfaction_rate']:.1f}%")
            with col2:
                st.metric("Feedback Rate", f"{summary['feedback_rate']:.1f}%")
            
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
                        'ID': item['id'],
                        'Query': item['query'][:100] + '...' if len(item['query']) > 100 else item['query'],
                        'User ID': item['userid'],
                        'Date & Time': item['date_time'].strftime('%Y-%m-%d %H:%M:%S') if item['date_time'] else 'N/A',
                        'Reaction': item['reaction'] or 'No feedback'
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
            print("❌ DATABASE_URL not found in environment variables")
            logger.error("DATABASE_URL not found in environment variables")
            return None
        
        print(f"🔍 Found DATABASE_URL: {database_url[:50]}...")
        
        # Create simplified analytics service
        analytics_service = SimpleAnalyticsService(database_url)
        integration = StreamlitAnalyticsIntegration(analytics_service)
        
        print("✅ Analytics service initialized successfully")
        return integration
        
    except Exception as e:
        print(f"❌ Error initializing analytics service: {e}")
        logger.error(f"Error initializing analytics service: {e}")
        return None