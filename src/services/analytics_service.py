"""
Analytics service for storing and retrieving query analytics data.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import sqlite3
from contextlib import contextmanager

from src.models.database_models import (
    User, QuerySession, UserQuery, AIResponse, UserFeedback,
    QueryAnalytics, AnalyticsSummary, DatabaseConfig,
    QueryComplexity, QueryStatus, FeedbackType
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for managing query analytics data."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager."""
        connection = None
        try:
            if self.config.database_type == "sqlite":
                connection = sqlite3.connect(self.config.database)
                connection.row_factory = sqlite3.Row  # Enable dict-like access
            else:
                # For MySQL/PostgreSQL, use pymysql
                import pymysql
                connection = pymysql.connect(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.username,
                    password=self.config.password,
                    database=self.config.database,
                    charset=self.config.charset,
                    autocommit=True
                )
            yield connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()
    
    def store_user_query(self, query: UserQuery) -> int:
        """Store a user query and return the query ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert user query
                if self.config.database_type == "sqlite":
                    query_sql = """
                    INSERT INTO user_queries 
                    (session_id, query_session_id, query_text, query_length, query_complexity, 
                     created_at, processing_time_ms, status, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                else:
                    query_sql = """
                    INSERT INTO user_queries 
                    (session_id, query_session_id, query_text, query_length, query_complexity, 
                     created_at, processing_time_ms, status, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                
                cursor.execute(query_sql, (
                    query.session_id,
                    query.query_session_id,
                    query.query_text,
                    query.query_length,
                    query.query_complexity.value,
                    query.created_at or datetime.now(),
                    query.processing_time_ms,
                    query.status.value,
                    query.error_message
                ))
                
                query_id = cursor.lastrowid
                logger.info(f"Stored user query with ID: {query_id}")
                return query_id
                
        except Exception as e:
            logger.error(f"Error storing user query: {e}")
            raise
    
    def store_ai_response(self, response: AIResponse) -> int:
        """Store an AI response and return the response ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                response_sql = """
                INSERT INTO ai_responses 
                (query_id, model_used, model_id, response_text, response_length, 
                 tokens_used, estimated_cost, documents_retrieved, relevance_score, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(response_sql, (
                    response.query_id,
                    response.model_used,
                    response.model_id,
                    response.response_text,
                    response.response_length,
                    response.tokens_used,
                    response.estimated_cost,
                    response.documents_retrieved,
                    response.relevance_score,
                    response.created_at or datetime.now()
                ))
                
                response_id = cursor.lastrowid
                logger.info(f"Stored AI response with ID: {response_id}")
                return response_id
                
        except Exception as e:
            logger.error(f"Error storing AI response: {e}")
            raise
    
    def store_user_feedback(self, feedback: UserFeedback) -> int:
        """Store user feedback and return the feedback ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if feedback already exists for this query-response pair
                check_sql = """
                SELECT id FROM user_feedback 
                WHERE query_id = %s AND response_id = %s
                """
                cursor.execute(check_sql, (feedback.query_id, feedback.response_id))
                
                if cursor.fetchone():
                    # Update existing feedback
                    update_sql = """
                    UPDATE user_feedback 
                    SET feedback_type = %s, additional_notes = %s, feedback_timestamp = %s
                    WHERE query_id = %s AND response_id = %s
                    """
                    cursor.execute(update_sql, (
                        feedback.feedback_type.value,
                        feedback.additional_notes,
                        feedback.feedback_timestamp or datetime.now(),
                        feedback.query_id,
                        feedback.response_id
                    ))
                    feedback_id = cursor.lastrowid
                else:
                    # Insert new feedback
                    feedback_sql = """
                    INSERT INTO user_feedback 
                    (query_id, response_id, feedback_type, feedback_timestamp, additional_notes)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(feedback_sql, (
                        feedback.query_id,
                        feedback.response_id,
                        feedback.feedback_type.value,
                        feedback.feedback_timestamp or datetime.now(),
                        feedback.additional_notes
                    ))
                    feedback_id = cursor.lastrowid
                
                logger.info(f"Stored user feedback with ID: {feedback_id}")
                return feedback_id
                
        except Exception as e:
            logger.error(f"Error storing user feedback: {e}")
            raise
    
    def get_query_analytics(self, 
                           limit: int = 100, 
                           offset: int = 0,
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None,
                           session_id: Optional[str] = None) -> List[QueryAnalytics]:
        """Get query analytics data with optional filtering."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
                # Build query with filters
                base_query = """
                SELECT 
                    uq.id as query_id,
                    uq.session_id,
                    uq.query_text,
                    uq.query_complexity,
                    uq.created_at as query_created_at,
                    uq.processing_time_ms,
                    uq.status,
                    uq.error_message,
                    ar.id as response_id,
                    ar.model_used,
                    ar.model_id,
                    ar.response_text,
                    ar.response_length,
                    ar.tokens_used,
                    ar.estimated_cost,
                    ar.documents_retrieved,
                    ar.relevance_score,
                    ar.created_at as response_created_at,
                    uf.id as feedback_id,
                    uf.feedback_type,
                    uf.feedback_timestamp,
                    uf.additional_notes,
                    qs.session_name
                FROM user_queries uq
                LEFT JOIN ai_responses ar ON uq.id = ar.query_id
                LEFT JOIN user_feedback uf ON uq.id = uf.query_id
                LEFT JOIN query_sessions qs ON uq.query_session_id = qs.id
                WHERE 1=1
                """
                
                params = []
                
                if start_date:
                    base_query += " AND uq.created_at >= %s"
                    params.append(start_date)
                
                if end_date:
                    base_query += " AND uq.created_at <= %s"
                    params.append(end_date)
                
                if session_id:
                    base_query += " AND uq.session_id = %s"
                    params.append(session_id)
                
                base_query += " ORDER BY uq.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(base_query, params)
                results = cursor.fetchall()
                
                # Convert to QueryAnalytics objects
                analytics = []
                for row in results:
                    query = UserQuery(
                        id=row['query_id'],
                        session_id=row['session_id'],
                        query_text=row['query_text'],
                        query_length=len(row['query_text']),
                        query_complexity=QueryComplexity(row['query_complexity']),
                        created_at=row['query_created_at'],
                        processing_time_ms=row['processing_time_ms'],
                        status=QueryStatus(row['status']),
                        error_message=row['error_message']
                    )
                    
                    response = None
                    if row['response_id']:
                        response = AIResponse(
                            id=row['response_id'],
                            query_id=row['query_id'],
                            model_used=row['model_used'],
                            model_id=row['model_id'],
                            response_text=row['response_text'],
                            response_length=row['response_length'],
                            tokens_used=row['tokens_used'],
                            estimated_cost=float(row['estimated_cost']),
                            documents_retrieved=row['documents_retrieved'],
                            relevance_score=float(row['relevance_score']) if row['relevance_score'] else None,
                            created_at=row['response_created_at']
                        )
                    
                    feedback = None
                    if row['feedback_id']:
                        feedback = UserFeedback(
                            id=row['feedback_id'],
                            query_id=row['query_id'],
                            response_id=row['response_id'],
                            feedback_type=FeedbackType(row['feedback_type']),
                            feedback_timestamp=row['feedback_timestamp'],
                            additional_notes=row['additional_notes']
                        )
                    
                    analytics.append(QueryAnalytics(
                        query=query,
                        response=response,
                        feedback=feedback,
                        session_name=row['session_name']
                    ))
                
                return analytics
                
        except Exception as e:
            logger.error(f"Error getting query analytics: {e}")
            raise
    
    def get_analytics_summary(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get analytics summary for the specified date range."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
                # Build summary query
                summary_query = """
                SELECT 
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_queries,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_queries,
                    AVG(processing_time_ms) as avg_processing_time_ms,
                    SUM(ar.tokens_used) as total_tokens_used,
                    SUM(ar.estimated_cost) as total_cost,
                    SUM(CASE WHEN uf.feedback_type = 'positive' THEN 1 ELSE 0 END) as positive_feedback,
                    SUM(CASE WHEN uf.feedback_type = 'negative' THEN 1 ELSE 0 END) as negative_feedback,
                    ar.model_used as most_used_model
                FROM user_queries uq
                LEFT JOIN ai_responses ar ON uq.id = ar.query_id
                LEFT JOIN user_feedback uf ON uq.id = uf.query_id
                WHERE 1=1
                """
                
                params = []
                
                if start_date:
                    summary_query += " AND uq.created_at >= %s"
                    params.append(start_date)
                
                if end_date:
                    summary_query += " AND uq.created_at <= %s"
                    params.append(end_date)
                
                cursor.execute(summary_query, params)
                result = cursor.fetchone()
                
                return {
                    'total_queries': result['total_queries'] or 0,
                    'successful_queries': result['successful_queries'] or 0,
                    'failed_queries': result['failed_queries'] or 0,
                    'avg_processing_time_ms': float(result['avg_processing_time_ms'] or 0),
                    'total_tokens_used': result['total_tokens_used'] or 0,
                    'total_cost': float(result['total_cost'] or 0),
                    'positive_feedback': result['positive_feedback'] or 0,
                    'negative_feedback': result['negative_feedback'] or 0,
                    'most_used_model': result['most_used_model']
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            raise
    
    def export_analytics_data(self, 
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             format: str = 'csv') -> str:
        """Export analytics data in specified format."""
        try:
            analytics = self.get_query_analytics(
                limit=10000,  # Large limit for export
                start_date=start_date,
                end_date=end_date
            )
            
            if format.lower() == 'csv':
                return self._export_to_csv(analytics)
            elif format.lower() == 'json':
                return self._export_to_json(analytics)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting analytics data: {e}")
            raise
    
    def _export_to_csv(self, analytics: List[QueryAnalytics]) -> str:
        """Export analytics data to CSV format."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Query ID', 'Session ID', 'Session Name', 'Query Text', 'Query Complexity',
            'Created At', 'Processing Time (ms)', 'Status', 'Model Used', 'Response Length',
            'Tokens Used', 'Estimated Cost', 'Documents Retrieved', 'Feedback Type',
            'Feedback Timestamp'
        ])
        
        # Write data
        for item in analytics:
            writer.writerow([
                item.query.id,
                item.query.session_id,
                item.session_name or '',
                item.query.query_text,
                item.query.query_complexity.value,
                item.query.created_at.isoformat() if item.query.created_at else '',
                item.query.processing_time_ms or '',
                item.query.status.value,
                item.response.model_used if item.response else '',
                item.response.response_length if item.response else '',
                item.response.tokens_used if item.response else '',
                item.response.estimated_cost if item.response else '',
                item.response.documents_retrieved if item.response else '',
                item.feedback.feedback_type.value if item.feedback else '',
                item.feedback.feedback_timestamp.isoformat() if item.feedback and item.feedback.feedback_timestamp else ''
            ])
        
        return output.getvalue()
    
    def _export_to_json(self, analytics: List[QueryAnalytics]) -> str:
        """Export analytics data to JSON format."""
        import json
        
        data = []
        for item in analytics:
            data.append({
                'query': {
                    'id': item.query.id,
                    'session_id': item.query.session_id,
                    'query_text': item.query.query_text,
                    'query_complexity': item.query.query_complexity.value,
                    'created_at': item.query.created_at.isoformat() if item.query.created_at else None,
                    'processing_time_ms': item.query.processing_time_ms,
                    'status': item.query.status.value
                },
                'response': {
                    'model_used': item.response.model_used if item.response else None,
                    'response_length': item.response.response_length if item.response else None,
                    'tokens_used': item.response.tokens_used if item.response else None,
                    'estimated_cost': item.response.estimated_cost if item.response else None,
                    'documents_retrieved': item.response.documents_retrieved if item.response else None
                } if item.response else None,
                'feedback': {
                    'feedback_type': item.feedback.feedback_type.value if item.feedback else None,
                    'feedback_timestamp': item.feedback.feedback_timestamp.isoformat() if item.feedback and item.feedback.feedback_timestamp else None
                } if item.feedback else None,
                'session_name': item.session_name
            })
        
        return json.dumps(data, indent=2)
