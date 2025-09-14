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
        try:
            if self._connection is None:
                import psycopg2
                print(f"🔍 Connecting to database with URL: {self.database_url[:50]}...")
                self._connection = psycopg2.connect(self.database_url)
                print("✅ Database connection established")
            return self._connection
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print(f"❌ Connection error type: {type(e).__name__}")
            return None
    
    def health_check(self):
        """Perform comprehensive database health check."""
        try:
            print("🔍 Performing database health check...")
            
            # Test connection
            conn = self.get_connection()
            if not conn:
                print("❌ Health check failed: No database connection")
                return False
                
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result[0] != 1:
                print("❌ Health check failed: Basic query test failed")
                return False
                
            # Test if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'query_analytics'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print("❌ Health check failed: Table 'query_analytics' does not exist")
                return False
                
            # Test table structure
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'query_analytics'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print(f"✅ Table structure: {columns}")
            
            # Test insert permission
            cursor.execute("""
                INSERT INTO query_analytics (query, userid, date_time, reaction)
                VALUES ('health_check_test', 'system', NOW(), NULL)
                RETURNING id
            """)
            test_id = cursor.fetchone()[0]
            
            # Clean up test record
            cursor.execute("DELETE FROM query_analytics WHERE id = %s", (test_id,))
            conn.commit()
            
            cursor.close()
            print("✅ Health check passed: Database is ready")
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            print(f"❌ Health check error type: {type(e).__name__}")
            return False
    
    def store_query_with_feedback(self, query: str, userid: str = "anonymous", reaction: str = "none", 
                                 query_time_seconds: float = None, model_used: str = None,
                                 products: str = "[]", question_type: str = "unknown", 
                                 technical_level: str = "unknown", topics: str = "[]", 
                                 urgency: str = "low", confidence_score: float = 0.0) -> int:
        """Store query and feedback in single table with timing and model info."""
        conn = None
        cursor = None
        try:
            print(f"🔍 Attempting to store query: '{query[:50]}...' for user: {userid}")
            print(f"🔍 Query time: {query_time_seconds}s, Model: {model_used}")
            
            # Test database connection first
            conn = self.get_connection()
            if not conn:
                print("❌ Failed to get database connection")
                return None
                
            cursor = conn.cursor()
            
            # Test if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'query_analytics'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print("❌ Table 'query_analytics' does not exist")
                return None
            
            # Test table structure
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'query_analytics'
                ORDER BY ordinal_position;
            """)
            columns = cursor.fetchall()
            print(f"🔍 Table structure: {columns}")
            
            # Insert the query - handle length constraints
            safe_reaction = reaction[:20] if reaction and len(reaction) > 20 else (reaction or "none")
            safe_userid = userid[:100] if len(userid) > 100 else userid
            safe_model = model_used[:50] if model_used and len(model_used) > 50 else model_used
            
            cursor.execute("""
                INSERT INTO query_analytics (query, userid, date_time, reaction, query_time_seconds, model_used,
                                           products, question_type, technical_level, topics, urgency, confidence_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (query, safe_userid, datetime.now(), safe_reaction, query_time_seconds, safe_model,
                  products, question_type, technical_level, topics, urgency, confidence_score))
            
            result = cursor.fetchone()
            if not result:
                print("❌ INSERT query returned no result")
                return None
                
            query_id = result[0]
            conn.commit()
            
            print(f"✅ Successfully stored query with ID: {query_id}")
            return query_id
            
        except Exception as e:
            print(f"❌ Error storing query: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            logger.error(f"Error storing query: {e}")
            
            # Rollback on error
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            return None
        finally:
            # Ensure cleanup
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def update_feedback(self, query_id: int, reaction: str) -> bool:
        """Update feedback for existing query."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Truncate reaction to 20 characters if it's too long
            safe_reaction = reaction[:20] if reaction and len(reaction) > 20 else (reaction or "none")
            
            cursor.execute("""
                UPDATE query_analytics 
                SET reaction = %s 
                WHERE id = %s
            """, (safe_reaction, query_id))
            
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
            
            # Get summary data - handle new reaction values
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_queries,
                    COUNT(CASE WHEN reaction = 'positive' THEN 1 END) as positive_feedback,
                    COUNT(CASE WHEN reaction = 'negative' THEN 1 END) as negative_feedback,
                    COUNT(CASE WHEN reaction IS NOT NULL AND reaction != 'none' THEN 1 END) as total_feedback,
                    AVG(query_time_seconds) as avg_query_time,
                    COUNT(DISTINCT model_used) as unique_models
                FROM query_analytics
                {date_filter}
            """, params)
            
            result = cursor.fetchone()
            cursor.close()
            
            total_queries = result[0] or 0
            positive_feedback = result[1] or 0
            negative_feedback = result[2] or 0
            total_feedback = result[3] or 0
            avg_query_time = result[4] or 0
            unique_models = result[5] or 0
            
            return {
                'total_queries': total_queries,
                'total_feedback': total_feedback,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback,
                'avg_query_time': round(avg_query_time, 2),
                'unique_models': unique_models,
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
                    reaction,
                    query_time_seconds,
                    model_used
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
                    'reaction': row[4],
                    'query_time_seconds': row[5],
                    'model_used': row[6]
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
    
    def track_query(self, session_id: str, query_text: str, query_complexity: str = "medium", 
                   query_time_seconds: float = None, model_used: str = None, 
                   tagging_result: dict = None) -> int:
        """Track a user query with timing, model info, and tagging data."""
        try:
            print(f"🔍 [TRACK_QUERY] Starting query tracking...")
            print(f"🔍 [TRACK_QUERY] Session ID: {session_id}")
            print(f"🔍 [TRACK_QUERY] Query: {query_text[:100]}...")
            print(f"🔍 [TRACK_QUERY] Complexity: {query_complexity}")
            print(f"🔍 [TRACK_QUERY] Query time: {query_time_seconds}s")
            print(f"🔍 [TRACK_QUERY] Model: {model_used}")
            print(f"🔍 [TRACK_QUERY] Tagging result: {tagging_result}")
            
            # Extract tagging information if available
            products = "[]"
            question_type = "unknown"
            technical_level = "unknown"
            topics = "[]"
            urgency = "low"
            confidence_score = 0.0
            
            if tagging_result and not tagging_result.get('error'):
                tagging_data = tagging_result.get('tagging_result', {})
                if tagging_data:
                    products = json.dumps(tagging_data.get('products', []))
                    question_type = tagging_data.get('question_type', 'unknown')
                    technical_level = tagging_data.get('technical_level', 'unknown')
                    topics = json.dumps(tagging_data.get('topics', []))
                    urgency = tagging_data.get('urgency', 'low')
                    confidence_score = tagging_data.get('confidence_score', 0.0)
                    print(f"🔍 [TRACK_QUERY] Extracted tagging data: products={products}, type={question_type}")
            
            print(f"🔍 [TRACK_QUERY] Calling store_query_with_feedback...")
            result = self.analytics_service.store_query_with_feedback(
                query=query_text, 
                userid=session_id, 
                reaction="none",
                query_time_seconds=query_time_seconds,
                model_used=model_used,
                products=products,
                question_type=question_type,
                technical_level=technical_level,
                topics=topics,
                urgency=urgency,
                confidence_score=confidence_score
            )
            
            if result:
                print(f"✅ [TRACK_QUERY] Query tracked successfully with ID: {result}")
            else:
                print(f"❌ [TRACK_QUERY] Query tracking failed - no ID returned")
            
            return result
            
        except Exception as e:
            print(f"❌ [TRACK_QUERY] Error tracking query: {e}")
            print(f"❌ [TRACK_QUERY] Error type: {type(e).__name__}")
            import traceback
            print(f"❌ [TRACK_QUERY] Traceback: {traceback.format_exc()}")
            logger.error(f"Error tracking query: {e}")
            return None
    
    def track_feedback(self, query_id: int, response_id: int = None, feedback_type: str = None) -> bool:
        """Track user feedback."""
        try:
            # Map feedback types to proper values
            if feedback_type == "p":
                feedback_type = "positive"
            elif feedback_type == "n":
                feedback_type = "negative"
            elif feedback_type is None:
                feedback_type = "none"
                
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
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Satisfaction Rate", f"{summary['satisfaction_rate']:.1f}%")
            with col2:
                st.metric("Feedback Rate", f"{summary['feedback_rate']:.1f}%")
            with col3:
                st.metric("Avg Query Time", f"{summary['avg_query_time']:.2f}s")
            with col4:
                st.metric("Models Used", summary['unique_models'])
            
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
                        'Reaction': item['reaction'] or 'No feedback',
                        'Query Time': f"{item['query_time_seconds']:.2f}s" if item['query_time_seconds'] else 'N/A',
                        'Model Used': item['model_used'] or 'N/A'
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
        
        # If DATABASE_URL is SQLite or not set, try Railway PostgreSQL
        if not database_url or database_url.startswith("sqlite"):
            print("🔍 DATABASE_URL is SQLite or not set, trying Railway PostgreSQL...")
            
            # Try to construct Railway database URL using actual Railway environment variables
            railway_db_host = os.getenv("PGHOST", "postgres.railway.internal")
            railway_db_port = os.getenv("PGPORT", "5432")
            railway_db_name = os.getenv("RAILWAY_DATABASE_NAME", "railway")
            railway_db_user = os.getenv("RAILWAY_DATABASE_USER", "postgres")
            railway_db_password = os.getenv("RAILWAY_DATABASE_PASSWORD", "qGEbKXpzCeRFqFTdrBIhcSbxvGQBtexn")
            
            database_url = f"postgresql://{railway_db_user}:{railway_db_password}@{railway_db_host}:{railway_db_port}/{railway_db_name}"
            print(f"🔍 Using Railway database URL: {database_url[:50]}...")
        else:
            print(f"🔍 Found DATABASE_URL: {database_url[:50]}...")
        
        # Create simplified analytics service
        analytics_service = SimpleAnalyticsService(database_url)
        
        # Run health check
        if analytics_service.health_check():
            integration = StreamlitAnalyticsIntegration(analytics_service)
            print("✅ Analytics service initialized successfully")
            return integration
        else:
            print("❌ Analytics service health check failed")
            return None
        
    except Exception as e:
        print(f"❌ Error initializing analytics service: {e}")
        logger.error(f"Error initializing analytics service: {e}")
        return None