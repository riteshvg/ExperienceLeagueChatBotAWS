"""
PostgreSQL-specific analytics service for Railway deployment.
"""

import logging
import psycopg2
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from ..models.database_models import (
    UserQuery, AIResponse, UserFeedback, QueryAnalytics,
    QueryComplexity, QueryStatus, FeedbackType
)

logger = logging.getLogger(__name__)


class PostgreSQLAnalyticsService:
    """PostgreSQL-specific analytics service for Railway deployment."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._init_database()
    
    def _init_database(self):
        """Initialize PostgreSQL database with required tables."""
        try:
            with psycopg2.connect(self.database_url) as conn:
                conn.autocommit = True
                cursor = conn.cursor()
                
                # Enable UUID extension
                cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
                
                # Create users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    ip_address INET
                )
                """)
                
                # Create query_sessions table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    session_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    total_queries INTEGER DEFAULT 0,
                    total_feedback_positive INTEGER DEFAULT 0,
                    total_feedback_negative INTEGER DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE
                )
                """)
                
                # Create user_queries table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_queries (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    query_session_id INTEGER,
                    query_text TEXT NOT NULL,
                    query_length INTEGER,
                    query_complexity VARCHAR(20) DEFAULT 'simple' CHECK (query_complexity IN ('simple', 'complex', 'extremely_complex')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms INTEGER,
                    status VARCHAR(20) DEFAULT 'success' CHECK (status IN ('success', 'error', 'timeout')),
                    error_message TEXT,
                    FOREIGN KEY (session_id) REFERENCES users(session_id) ON DELETE CASCADE,
                    FOREIGN KEY (query_session_id) REFERENCES query_sessions(id) ON DELETE SET NULL
                )
                """)
                
                # Create ai_responses table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_responses (
                    id SERIAL PRIMARY KEY,
                    query_id INTEGER NOT NULL,
                    model_used VARCHAR(100) NOT NULL,
                    model_id VARCHAR(255) NOT NULL,
                    response_text TEXT NOT NULL,
                    response_length INTEGER,
                    tokens_used INTEGER,
                    estimated_cost DECIMAL(10, 6),
                    documents_retrieved INTEGER DEFAULT 0,
                    relevance_score DECIMAL(3, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE
                )
                """)
                
                # Create user_feedback table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id SERIAL PRIMARY KEY,
                    query_id INTEGER NOT NULL,
                    response_id INTEGER NOT NULL,
                    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('positive', 'negative', 'neutral')),
                    feedback_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    additional_notes TEXT,
                    FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE,
                    FOREIGN KEY (response_id) REFERENCES ai_responses(id) ON DELETE CASCADE,
                    CONSTRAINT unique_query_response_feedback UNIQUE (query_id, response_id)
                )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_session_id ON users(session_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_sessions_session_id ON query_sessions(session_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_queries_session_id ON user_queries(session_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_queries_created_at ON user_queries(created_at);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_responses_query_id ON ai_responses(query_id);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_feedback_query_id ON user_feedback(query_id);")
                
                logger.info("PostgreSQL database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing PostgreSQL database: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get PostgreSQL database connection with context manager."""
        connection = None
        try:
            connection = psycopg2.connect(self.database_url)
            yield connection
        except Exception as e:
            logger.error(f"PostgreSQL connection error: {e}")
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
                
                cursor.execute("""
                INSERT INTO user_queries 
                (session_id, query_session_id, query_text, query_length, query_complexity, 
                 created_at, processing_time_ms, status, error_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """, (
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
                
                query_id = cursor.fetchone()[0]
                conn.commit()
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
                
                cursor.execute("""
                INSERT INTO ai_responses 
                (query_id, model_used, model_id, response_text, response_length, 
                 tokens_used, estimated_cost, documents_retrieved, relevance_score, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """, (
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
                
                response_id = cursor.fetchone()[0]
                conn.commit()
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
                cursor.execute("""
                SELECT id FROM user_feedback 
                WHERE query_id = %s AND response_id = %s
                """, (feedback.query_id, feedback.response_id))
                
                if cursor.fetchone():
                    # Update existing feedback
                    cursor.execute("""
                    UPDATE user_feedback 
                    SET feedback_type = %s, additional_notes = %s, feedback_timestamp = %s
                    WHERE query_id = %s AND response_id = %s
                    RETURNING id
                    """, (
                        feedback.feedback_type.value,
                        feedback.additional_notes,
                        feedback.feedback_timestamp or datetime.now(),
                        feedback.query_id,
                        feedback.response_id
                    ))
                    feedback_id = cursor.fetchone()[0]
                else:
                    # Insert new feedback
                    cursor.execute("""
                    INSERT INTO user_feedback 
                    (query_id, response_id, feedback_type, feedback_timestamp, additional_notes)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """, (
                        feedback.query_id,
                        feedback.response_id,
                        feedback.feedback_type.value,
                        feedback.feedback_timestamp or datetime.now(),
                        feedback.additional_notes
                    ))
                    feedback_id = cursor.fetchone()[0]
                
                conn.commit()
                logger.info(f"Stored user feedback with ID: {feedback_id}")
                return feedback_id
                
        except Exception as e:
            logger.error(f"Error storing user feedback: {e}")
            raise
    
    def get_query_analytics(self, limit: int = 100, offset: int = 0, start_date=None, end_date=None, session_id=None) -> List[QueryAnalytics]:
        """Get query analytics data."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with optional filtering
                query = """
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
                    uf.additional_notes
                FROM user_queries uq
                LEFT JOIN ai_responses ar ON uq.id = ar.query_id
                LEFT JOIN user_feedback uf ON uq.id = uf.query_id
                WHERE 1=1
                """
                
                params = []
                
                if start_date:
                    query += " AND uq.created_at >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND uq.created_at <= %s"
                    params.append(end_date)
                
                if session_id:
                    query += " AND uq.session_id = %s"
                    params.append(session_id)
                
                query += " ORDER BY uq.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                # Convert to QueryAnalytics objects
                analytics = []
                for row in results:
                    query = UserQuery(
                        id=row[0],
                        session_id=row[1],
                        query_text=row[2],
                        query_length=len(row[2]),
                        query_complexity=QueryComplexity(row[3]),
                        created_at=row[4],
                        processing_time_ms=row[5],
                        status=QueryStatus(row[6]),
                        error_message=row[7]
                    )
                    
                    response = None
                    if row[8]:  # response_id
                        response = AIResponse(
                            id=row[8],
                            query_id=row[0],
                            model_used=row[9],
                            model_id=row[10],
                            response_text=row[11],
                            response_length=row[12],
                            tokens_used=row[13],
                            estimated_cost=float(row[14]) if row[14] else 0,
                            documents_retrieved=row[15],
                            relevance_score=float(row[16]) if row[16] else None,
                            created_at=row[17]
                        )
                    
                    feedback = None
                    if row[18]:  # feedback_id
                        feedback = UserFeedback(
                            id=row[18],
                            query_id=row[0],
                            response_id=row[8],
                            feedback_type=FeedbackType(row[19]),
                            feedback_timestamp=row[20],
                            additional_notes=row[21]
                        )
                    
                    analytics.append(QueryAnalytics(
                        query=query,
                        response=response,
                        feedback=feedback,
                        session_name=None
                    ))
                
                return analytics
                
        except Exception as e:
            logger.error(f"Error getting query analytics: {e}")
            raise
    
    def get_analytics_summary(self, start_date=None, end_date=None) -> Dict[str, Any]:
        """Get analytics summary."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with optional date filtering
                query = """
                SELECT 
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_queries,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed_queries,
                    AVG(processing_time_ms) as avg_processing_time_ms,
                    SUM(ar.tokens_used) as total_tokens_used,
                    SUM(ar.estimated_cost) as total_cost,
                    SUM(CASE WHEN uf.feedback_type = 'positive' THEN 1 ELSE 0 END) as positive_feedback,
                    SUM(CASE WHEN uf.feedback_type = 'negative' THEN 1 ELSE 0 END) as negative_feedback
                FROM user_queries uq
                LEFT JOIN ai_responses ar ON uq.id = ar.query_id
                LEFT JOIN user_feedback uf ON uq.id = uf.query_id
                WHERE 1=1
                """
                
                params = []
                
                if start_date:
                    query += " AND uq.created_at >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND uq.created_at <= %s"
                    params.append(end_date)
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                return {
                    'total_queries': result[0] or 0,
                    'successful_queries': result[1] or 0,
                    'failed_queries': result[2] or 0,
                    'avg_processing_time_ms': float(result[3] or 0),
                    'total_tokens_used': result[4] or 0,
                    'total_cost': float(result[5] or 0),
                    'positive_feedback': result[6] or 0,
                    'negative_feedback': result[7] or 0,
                    'most_used_model': None
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            raise
