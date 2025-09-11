"""
Streamlit integration for query analytics and user feedback tracking.
"""

import streamlit as st
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd

from ..services.analytics_service import AnalyticsService
from ..models.database_models import (
    DatabaseConfig, UserQuery, AIResponse, UserFeedback,
    QueryComplexity, QueryStatus, FeedbackType
)

logger = logging.getLogger(__name__)


class StreamlitAnalyticsIntegration:
    """Integration class for Streamlit analytics features."""
    
    def __init__(self, analytics_service: AnalyticsService):
        self.analytics_service = analytics_service
    
    def track_query(self, 
                   session_id: str,
                   query_text: str,
                   query_complexity: str,
                   processing_time_ms: int,
                   status: str = "success",
                   error_message: Optional[str] = None) -> int:
        """Track a user query."""
        try:
            # Convert string complexity to enum
            complexity_map = {
                "simple": QueryComplexity.SIMPLE,
                "complex": QueryComplexity.COMPLEX,
                "extremely_complex": QueryComplexity.EXTREMELY_COMPLEX
            }
            
            # Convert string status to enum
            status_map = {
                "success": QueryStatus.SUCCESS,
                "error": QueryStatus.ERROR,
                "timeout": QueryStatus.TIMEOUT
            }
            
            query = UserQuery(
                session_id=session_id,
                query_text=query_text,
                query_length=len(query_text),
                query_complexity=complexity_map.get(query_complexity, QueryComplexity.SIMPLE),
                processing_time_ms=processing_time_ms,
                status=status_map.get(status, QueryStatus.SUCCESS),
                error_message=error_message
            )
            
            return self.analytics_service.store_user_query(query)
            
        except Exception as e:
            logger.error(f"Error tracking query: {e}")
            return None
    
    def track_response(self,
                      query_id: int,
                      model_used: str,
                      model_id: str,
                      response_text: str,
                      tokens_used: int,
                      estimated_cost: float,
                      documents_retrieved: int = 0,
                      relevance_score: Optional[float] = None) -> int:
        """Track an AI response."""
        try:
            response = AIResponse(
                query_id=query_id,
                model_used=model_used,
                model_id=model_id,
                response_text=response_text,
                response_length=len(response_text),
                tokens_used=tokens_used,
                estimated_cost=estimated_cost,
                documents_retrieved=documents_retrieved,
                relevance_score=relevance_score
            )
            
            return self.analytics_service.store_ai_response(response)
            
        except Exception as e:
            logger.error(f"Error tracking response: {e}")
            return None
    
    def track_feedback(self,
                      query_id: int,
                      response_id: int,
                      feedback_type: str,
                      additional_notes: Optional[str] = None) -> int:
        """Track user feedback."""
        try:
            # Convert string feedback type to enum
            feedback_map = {
                "positive": FeedbackType.POSITIVE,
                "negative": FeedbackType.NEGATIVE,
                "neutral": FeedbackType.NEUTRAL
            }
            
            feedback = UserFeedback(
                query_id=query_id,
                response_id=response_id,
                feedback_type=feedback_map.get(feedback_type, FeedbackType.NEUTRAL),
                additional_notes=additional_notes
            )
            
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
                st.metric("Success Rate", f"{(summary['successful_queries']/max(summary['total_queries'], 1)*100):.1f}%")
            with col3:
                st.metric("Avg Processing Time", f"{summary['avg_processing_time_ms']:.0f}ms")
            with col4:
                st.metric("Total Cost", f"${summary['total_cost']:.4f}")
            
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
                        'Query ID': item.query.id,
                        'Session ID': item.query.session_id,
                        'Session Name': item.session_name or 'N/A',
                        'Query Text': item.query.query_text[:100] + '...' if len(item.query.query_text) > 100 else item.query.query_text,
                        'Complexity': item.query.query_complexity.value,
                        'Created At': item.query.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.query.created_at else 'N/A',
                        'Processing Time (ms)': item.query.processing_time_ms or 'N/A',
                        'Status': item.query.status.value,
                        'Model Used': item.response.model_used if item.response else 'N/A',
                        'Response Length': item.response.response_length if item.response else 'N/A',
                        'Tokens Used': item.response.tokens_used if item.response else 'N/A',
                        'Estimated Cost': f"${item.response.estimated_cost:.4f}" if item.response else 'N/A',
                        'Documents Retrieved': item.response.documents_retrieved if item.response else 'N/A',
                        'Feedback': item.feedback.feedback_type.value if item.feedback else 'N/A',
                        'Feedback Time': item.feedback.feedback_timestamp.strftime('%Y-%m-%d %H:%M:%S') if item.feedback and item.feedback.feedback_timestamp else 'N/A'
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
    
    def render_feedback_analysis(self):
        """Render feedback analysis section."""
        st.subheader("💬 Feedback Analysis")
        
        try:
            # Get recent analytics for feedback analysis
            analytics = self.analytics_service.get_query_analytics(limit=100)
            
            if analytics:
                # Filter analytics with feedback
                feedback_data = [item for item in analytics if item.feedback]
                
                if feedback_data:
                    # Feedback distribution
                    feedback_counts = {}
                    for item in feedback_data:
                        feedback_type = item.feedback.feedback_type.value
                        feedback_counts[feedback_type] = feedback_counts.get(feedback_type, 0) + 1
                    
                    # Display feedback distribution
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Feedback Distribution:**")
                        for feedback_type, count in feedback_counts.items():
                            st.write(f"• {feedback_type.title()}: {count}")
                    
                    with col2:
                        # Create a simple bar chart
                        if feedback_counts:
                            feedback_df = pd.DataFrame(list(feedback_counts.items()), columns=['Feedback Type', 'Count'])
                            st.bar_chart(feedback_df.set_index('Feedback Type'))
                    
                    # Recent feedback
                    st.write("**Recent Feedback:**")
                    recent_feedback = feedback_data[:10]  # Show last 10
                    
                    for item in recent_feedback:
                        with st.expander(f"Query: {item.query.query_text[:50]}..."):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write(f"**Feedback:** {item.feedback.feedback_type.value.title()}")
                                st.write(f"**Query:** {item.query.query_text}")
                                st.write(f"**Model:** {item.response.model_used if item.response else 'N/A'}")
                            
                            with col2:
                                st.write(f"**Date:** {item.feedback.feedback_timestamp.strftime('%Y-%m-%d %H:%M:%S') if item.feedback.feedback_timestamp else 'N/A'}")
                                st.write(f"**Response Length:** {item.response.response_length if item.response else 'N/A'}")
                                if item.feedback.additional_notes:
                                    st.write(f"**Notes:** {item.feedback.additional_notes}")
                else:
                    st.info("No feedback data available.")
            else:
                st.info("No query data available for feedback analysis.")
                
        except Exception as e:
            st.error(f"Error loading feedback analysis: {e}")
    
    def render_model_usage_analysis(self):
        """Render model usage analysis section."""
        st.subheader("🤖 Model Usage Analysis")
        
        try:
            # Get analytics summary
            summary = self.analytics_service.get_analytics_summary()
            
            if summary['total_queries'] > 0:
                # Model usage metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Most Used Model", summary['most_used_model'] or 'N/A')
                with col2:
                    st.metric("Total Tokens Used", f"{summary['total_tokens_used']:,}")
                with col3:
                    st.metric("Total Cost", f"${summary['total_cost']:.4f}")
                
                # Cost analysis
                st.write("**Cost Analysis:**")
                if summary['total_cost'] > 0:
                    cost_per_query = summary['total_cost'] / summary['total_queries']
                    st.write(f"• Average cost per query: ${cost_per_query:.4f}")
                    st.write(f"• Total cost: ${summary['total_cost']:.4f}")
                    st.write(f"• Total tokens: {summary['total_tokens_used']:,}")
                else:
                    st.write("No cost data available.")
                
            else:
                st.info("No query data available for model usage analysis.")
                
        except Exception as e:
            st.error(f"Error loading model usage analysis: {e}")


def initialize_analytics_service() -> Optional[StreamlitAnalyticsIntegration]:
    """Initialize analytics service for Streamlit."""
    try:
        # Check if using SQLite for local testing
        if os.getenv("USE_SQLITE", "false").lower() == "true":
            from ..services.sqlite_analytics_service import SQLiteAnalyticsService
            database_path = os.getenv("SQLITE_DATABASE", "analytics.db")
            analytics_service = SQLiteAnalyticsService(database_path)
            return StreamlitAnalyticsIntegration(analytics_service)
        elif os.getenv("DATABASE_URL") or os.getenv("RAILWAY_ENVIRONMENT"):
            # Use PostgreSQL for Railway deployment
            from ..services.postgresql_analytics_service import PostgreSQLAnalyticsService
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                # Fallback to constructing URL from individual variables
                from ..utils.database_config import get_database_config
                config = get_database_config()
                database_url = f"postgresql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
            analytics_service = PostgreSQLAnalyticsService(database_url)
            return StreamlitAnalyticsIntegration(analytics_service)
        else:
            # Use regular analytics service for MySQL/PostgreSQL
            from ..utils.database_config import get_database_config
            config = get_database_config()
            analytics_service = AnalyticsService(config)
            return StreamlitAnalyticsIntegration(analytics_service)
        
    except Exception as e:
        logger.error(f"Error initializing analytics service: {e}")
        return None
