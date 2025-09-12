"""
SQLite-specific analytics service for local testing.
"""

import logging
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from src.models.database_models import (
    UserQuery, AIResponse, UserFeedback, QueryAnalytics,
    QueryComplexity, QueryStatus, FeedbackType
)

logger = logging.getLogger(__name__)


class SQLiteAnalyticsService:
    """SQLite-specific analytics service for local testing."""
    
    def __init__(self, database_path: str = "analytics.db"):
        self.database_path = database_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    ip_address TEXT
                )
                """)
                
                # Create query_sessions table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    session_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    total_queries INTEGER DEFAULT 0,
                    total_feedback_positive INTEGER DEFAULT 0,
                    total_feedback_negative INTEGER DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES users(session_id)
                )
                """)
                
                # Create user_queries table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    query_session_id INTEGER,
                    query_text TEXT NOT NULL,
                    query_length INTEGER,
                    query_complexity TEXT DEFAULT 'simple',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms INTEGER,
                    status TEXT DEFAULT 'success',
                    error_message TEXT,
                    FOREIGN KEY (session_id) REFERENCES users(session_id),
                    FOREIGN KEY (query_session_id) REFERENCES query_sessions(id)
                )
                """)
                
                # Create ai_responses table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id INTEGER NOT NULL,
                    model_used TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    response_length INTEGER,
                    tokens_used INTEGER,
                    estimated_cost REAL,
                    documents_retrieved INTEGER DEFAULT 0,
                    relevance_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (query_id) REFERENCES user_queries(id)
                )
                """)
                
                # Create user_feedback table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id INTEGER NOT NULL,
                    response_id INTEGER NOT NULL,
                    feedback_type TEXT NOT NULL,
                    feedback_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    additional_notes TEXT,
                    FOREIGN KEY (query_id) REFERENCES user_queries(id),
                    FOREIGN KEY (response_id) REFERENCES ai_responses(id),
                    UNIQUE(query_id, response_id)
                )
                """)
                
                conn.commit()
                logger.info("SQLite database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing SQLite database: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get SQLite database connection with context manager."""
        connection = None
        try:
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row  # Enable dict-like access
            yield connection
        except Exception as e:
            logger.error(f"SQLite connection error: {e}")
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
                cursor.execute("""
                INSERT INTO user_queries 
                (session_id, query_session_id, query_text, query_length, query_complexity, 
                 created_at, processing_time_ms, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                
                cursor.execute("""
                INSERT INTO ai_responses 
                (query_id, model_used, model_id, response_text, response_length, 
                 tokens_used, estimated_cost, documents_retrieved, relevance_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                cursor.execute("""
                SELECT id FROM user_feedback 
                WHERE query_id = ? AND response_id = ?
                """, (feedback.query_id, feedback.response_id))
                
                if cursor.fetchone():
                    # Update existing feedback
                    cursor.execute("""
                    UPDATE user_feedback 
                    SET feedback_type = ?, additional_notes = ?, feedback_timestamp = ?
                    WHERE query_id = ? AND response_id = ?
                    """, (
                        feedback.feedback_type.value,
                        feedback.additional_notes,
                        feedback.feedback_timestamp or datetime.now(),
                        feedback.query_id,
                        feedback.response_id
                    ))
                    feedback_id = cursor.lastrowid
                else:
                    # Insert new feedback
                    cursor.execute("""
                    INSERT INTO user_feedback 
                    (query_id, response_id, feedback_type, feedback_timestamp, additional_notes)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
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
                    query += " AND uq.created_at >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND uq.created_at <= ?"
                    params.append(end_date)
                
                if session_id:
                    query += " AND uq.session_id = ?"
                    params.append(session_id)
                
                query += " ORDER BY uq.created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                cursor.execute(query, params)
                
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
                    query += " AND uq.created_at >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND uq.created_at <= ?"
                    params.append(end_date)
                
                cursor.execute(query, params)
                
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
                    'most_used_model': None
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            raise
