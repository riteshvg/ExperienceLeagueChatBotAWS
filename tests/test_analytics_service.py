"""
Unit tests for analytics service.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from src.services.analytics_service import AnalyticsService
from src.models.database_models import (
    DatabaseConfig, UserQuery, AIResponse, UserFeedback,
    QueryComplexity, QueryStatus, FeedbackType
)


class TestAnalyticsService(unittest.TestCase):
    """Test cases for AnalyticsService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_chatbot_analytics",
            username="test_user",
            password="test_password"
        )
        self.service = AnalyticsService(self.config)
    
    @patch('src.services.analytics_service.pymysql.connect')
    def test_store_user_query_success(self, mock_connect):
        """Test successful user query storage."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.lastrowid = 123
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create test query
        query = UserQuery(
            session_id="test_session_123",
            query_text="What is Adobe Analytics?",
            query_length=25,
            query_complexity=QueryComplexity.SIMPLE,
            processing_time_ms=1500,
            status=QueryStatus.SUCCESS
        )
        
        # Test storage
        query_id = self.service.store_user_query(query)
        
        # Assertions
        self.assertEqual(query_id, 123)
        mock_cursor.execute.assert_called_once()
    
    @patch('src.services.analytics_service.pymysql.connect')
    def test_store_ai_response_success(self, mock_connect):
        """Test successful AI response storage."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.lastrowid = 456
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create test response
        response = AIResponse(
            query_id=123,
            model_used="haiku",
            model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
            response_text="Adobe Analytics is a web analytics platform...",
            response_length=50,
            tokens_used=100,
            estimated_cost=0.00125,
            documents_retrieved=3
        )
        
        # Test storage
        response_id = self.service.store_ai_response(response)
        
        # Assertions
        self.assertEqual(response_id, 456)
        mock_cursor.execute.assert_called_once()
    
    @patch('src.services.analytics_service.pymysql.connect')
    def test_store_user_feedback_success(self, mock_connect):
        """Test successful user feedback storage."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.lastrowid = 789
        mock_cursor.fetchone.return_value = None  # No existing feedback
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create test feedback
        feedback = UserFeedback(
            query_id=123,
            response_id=456,
            feedback_type=FeedbackType.POSITIVE,
            additional_notes="Great response!"
        )
        
        # Test storage
        feedback_id = self.service.store_user_feedback(feedback)
        
        # Assertions
        self.assertEqual(feedback_id, 789)
        self.assertEqual(mock_cursor.execute.call_count, 2)  # Check + Insert
    
    @patch('src.services.analytics_service.pymysql.connect')
    def test_store_user_feedback_update_existing(self, mock_connect):
        """Test updating existing user feedback."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.lastrowid = 789
        mock_cursor.fetchone.return_value = {'id': 789}  # Existing feedback
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create test feedback
        feedback = UserFeedback(
            query_id=123,
            response_id=456,
            feedback_type=FeedbackType.NEGATIVE,
            additional_notes="Not helpful"
        )
        
        # Test storage
        feedback_id = self.service.store_user_feedback(feedback)
        
        # Assertions
        self.assertEqual(feedback_id, 789)
        self.assertEqual(mock_cursor.execute.call_count, 2)  # Check + Update
    
    @patch('src.services.analytics_service.pymysql.connect')
    def test_get_query_analytics_success(self, mock_connect):
        """Test successful query analytics retrieval."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.cursor.return_value = mock_cursor
        
        # Mock query results
        mock_results = [
            {
                'query_id': 123,
                'session_id': 'test_session_123',
                'query_text': 'What is Adobe Analytics?',
                'query_complexity': 'simple',
                'query_created_at': datetime.now(),
                'processing_time_ms': 1500,
                'status': 'success',
                'error_message': None,
                'response_id': 456,
                'model_used': 'haiku',
                'model_id': 'us.anthropic.claude-3-haiku-20240307-v1:0',
                'response_text': 'Adobe Analytics is a web analytics platform...',
                'response_length': 50,
                'tokens_used': 100,
                'estimated_cost': 0.00125,
                'documents_retrieved': 3,
                'relevance_score': 0.85,
                'response_created_at': datetime.now(),
                'feedback_id': 789,
                'feedback_type': 'positive',
                'feedback_timestamp': datetime.now(),
                'additional_notes': 'Great response!',
                'session_name': 'Test Session'
            }
        ]
        mock_cursor.fetchall.return_value = mock_results
        mock_connect.return_value = mock_conn
        
        # Test retrieval
        analytics = self.service.get_query_analytics(limit=10, offset=0)
        
        # Assertions
        self.assertEqual(len(analytics), 1)
        self.assertEqual(analytics[0].query.id, 123)
        self.assertEqual(analytics[0].query.query_text, 'What is Adobe Analytics?')
        self.assertEqual(analytics[0].response.model_used, 'haiku')
        self.assertEqual(analytics[0].feedback.feedback_type, FeedbackType.POSITIVE)
        self.assertEqual(analytics[0].session_name, 'Test Session')
    
    @patch('src.services.analytics_service.pymysql.connect')
    def test_get_analytics_summary_success(self, mock_connect):
        """Test successful analytics summary retrieval."""
        # Mock database connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.cursor.return_value = mock_cursor
        
        # Mock summary results
        mock_summary = {
            'total_queries': 100,
            'successful_queries': 95,
            'failed_queries': 5,
            'avg_processing_time_ms': 1500.0,
            'total_tokens_used': 10000,
            'total_cost': 0.125,
            'positive_feedback': 80,
            'negative_feedback': 10,
            'most_used_model': 'haiku'
        }
        mock_cursor.fetchone.return_value = mock_summary
        mock_connect.return_value = mock_conn
        
        # Test retrieval
        summary = self.service.get_analytics_summary()
        
        # Assertions
        self.assertEqual(summary['total_queries'], 100)
        self.assertEqual(summary['successful_queries'], 95)
        self.assertEqual(summary['failed_queries'], 5)
        self.assertEqual(summary['avg_processing_time_ms'], 1500.0)
        self.assertEqual(summary['total_tokens_used'], 10000)
        self.assertEqual(summary['total_cost'], 0.125)
        self.assertEqual(summary['positive_feedback'], 80)
        self.assertEqual(summary['negative_feedback'], 10)
        self.assertEqual(summary['most_used_model'], 'haiku')
    
    def test_export_analytics_data_csv(self):
        """Test CSV export functionality."""
        # Mock analytics data
        mock_analytics = [
            Mock(
                query=Mock(
                    id=123,
                    session_id='test_session_123',
                    query_text='What is Adobe Analytics?',
                    query_complexity=Mock(value='simple'),
                    created_at=datetime.now(),
                    processing_time_ms=1500,
                    status=Mock(value='success')
                ),
                response=Mock(
                    model_used='haiku',
                    response_length=50,
                    tokens_used=100,
                    estimated_cost=0.00125,
                    documents_retrieved=3
                ),
                feedback=Mock(
                    feedback_type=Mock(value='positive'),
                    feedback_timestamp=datetime.now()
                ),
                session_name='Test Session'
            )
        ]
        
        # Mock get_query_analytics method
        with patch.object(self.service, 'get_query_analytics', return_value=mock_analytics):
            csv_data = self.service.export_analytics_data(format='csv')
            
            # Assertions
            self.assertIn('Query ID', csv_data)
            self.assertIn('Session ID', csv_data)
            self.assertIn('Query Text', csv_data)
            self.assertIn('123', csv_data)
            self.assertIn('test_session_123', csv_data)
            self.assertIn('What is Adobe Analytics?', csv_data)
    
    def test_export_analytics_data_json(self):
        """Test JSON export functionality."""
        # Mock analytics data
        mock_analytics = [
            Mock(
                query=Mock(
                    id=123,
                    session_id='test_session_123',
                    query_text='What is Adobe Analytics?',
                    query_complexity=Mock(value='simple'),
                    created_at=datetime.now(),
                    processing_time_ms=1500,
                    status=Mock(value='success')
                ),
                response=Mock(
                    model_used='haiku',
                    response_length=50,
                    tokens_used=100,
                    estimated_cost=0.00125,
                    documents_retrieved=3
                ),
                feedback=Mock(
                    feedback_type=Mock(value='positive'),
                    feedback_timestamp=datetime.now()
                ),
                session_name='Test Session'
            )
        ]
        
        # Mock get_query_analytics method
        with patch.object(self.service, 'get_query_analytics', return_value=mock_analytics):
            json_data = self.service.export_analytics_data(format='json')
            
            # Parse JSON to verify structure
            data = json.loads(json_data)
            
            # Assertions
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['query']['id'], 123)
            self.assertEqual(data[0]['query']['query_text'], 'What is Adobe Analytics?')
            self.assertEqual(data[0]['response']['model_used'], 'haiku')
            self.assertEqual(data[0]['feedback']['feedback_type'], 'positive')
    
    def test_export_analytics_data_invalid_format(self):
        """Test export with invalid format."""
        with self.assertRaises(ValueError):
            self.service.export_analytics_data(format='invalid')
    
    @patch('src.services.analytics_service.pymysql.connect')
    def test_database_connection_error(self, mock_connect):
        """Test database connection error handling."""
        # Mock connection error
        mock_connect.side_effect = Exception("Connection failed")
        
        query = UserQuery(
            session_id="test_session_123",
            query_text="What is Adobe Analytics?",
            query_length=25,
            query_complexity=QueryComplexity.SIMPLE
        )
        
        # Test error handling
        with self.assertRaises(Exception):
            self.service.store_user_query(query)


if __name__ == '__main__':
    unittest.main()
