"""
Simple tests for analytics functionality without database dependencies.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from src.models.database_models import (
    UserQuery, AIResponse, UserFeedback, QueryComplexity, 
    QueryStatus, FeedbackType, DatabaseConfig
)


class TestAnalyticsModels(unittest.TestCase):
    """Test cases for analytics data models."""
    
    def test_user_query_creation(self):
        """Test UserQuery model creation."""
        query = UserQuery(
            session_id="test_session_123",
            query_text="What is Adobe Analytics?",
            query_length=25,
            query_complexity=QueryComplexity.SIMPLE,
            processing_time_ms=1500,
            status=QueryStatus.SUCCESS
        )
        
        self.assertEqual(query.session_id, "test_session_123")
        self.assertEqual(query.query_text, "What is Adobe Analytics?")
        self.assertEqual(query.query_length, 25)
        self.assertEqual(query.query_complexity, QueryComplexity.SIMPLE)
        self.assertEqual(query.processing_time_ms, 1500)
        self.assertEqual(query.status, QueryStatus.SUCCESS)
    
    def test_ai_response_creation(self):
        """Test AIResponse model creation."""
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
        
        self.assertEqual(response.query_id, 123)
        self.assertEqual(response.model_used, "haiku")
        self.assertEqual(response.response_text, "Adobe Analytics is a web analytics platform...")
        self.assertEqual(response.response_length, 50)
        self.assertEqual(response.tokens_used, 100)
        self.assertEqual(response.estimated_cost, 0.00125)
        self.assertEqual(response.documents_retrieved, 3)
    
    def test_user_feedback_creation(self):
        """Test UserFeedback model creation."""
        feedback = UserFeedback(
            query_id=123,
            response_id=456,
            feedback_type=FeedbackType.POSITIVE,
            additional_notes="Great response!"
        )
        
        self.assertEqual(feedback.query_id, 123)
        self.assertEqual(feedback.response_id, 456)
        self.assertEqual(feedback.feedback_type, FeedbackType.POSITIVE)
        self.assertEqual(feedback.additional_notes, "Great response!")
    
    def test_database_config_creation(self):
        """Test DatabaseConfig model creation."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 3306)
        self.assertEqual(config.database, "test_db")
        self.assertEqual(config.username, "test_user")
        self.assertEqual(config.password, "test_password")
    
    def test_database_config_connection_string(self):
        """Test DatabaseConfig connection string generation."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        expected = "mysql+pymysql://test_user:test_password@localhost:3306/test_db?charset=utf8mb4"
        self.assertEqual(config.connection_string, expected)
    
    def test_database_config_to_dict(self):
        """Test DatabaseConfig to_dict method."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password="test_password"
        )
        
        config_dict = config.to_dict()
        
        self.assertEqual(config_dict["host"], "localhost")
        self.assertEqual(config_dict["port"], 3306)
        self.assertEqual(config_dict["database"], "test_db")
        self.assertEqual(config_dict["username"], "test_user")
        self.assertEqual(config_dict["password"], "test_password")
        self.assertEqual(config_dict["charset"], "utf8mb4")


class TestStreamlitAnalyticsIntegration(unittest.TestCase):
    """Test cases for Streamlit analytics integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_analytics_service = Mock()
        from src.integrations.streamlit_analytics import StreamlitAnalyticsIntegration
        self.integration = StreamlitAnalyticsIntegration(self.mock_analytics_service)
    
    def test_track_query_success(self):
        """Test successful query tracking."""
        # Mock service response
        self.mock_analytics_service.store_user_query.return_value = 123
        
        # Test tracking
        query_id = self.integration.track_query(
            session_id="test_session_123",
            query_text="What is Adobe Analytics?",
            query_complexity="simple",
            processing_time_ms=1500
        )
        
        # Assertions
        self.assertEqual(query_id, 123)
        self.mock_analytics_service.store_user_query.assert_called_once()
    
    def test_track_response_success(self):
        """Test successful response tracking."""
        # Mock service response
        self.mock_analytics_service.store_ai_response.return_value = 456
        
        # Test tracking
        response_id = self.integration.track_response(
            query_id=123,
            model_used="haiku",
            model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
            response_text="Adobe Analytics is a web analytics platform...",
            tokens_used=100,
            estimated_cost=0.00125
        )
        
        # Assertions
        self.assertEqual(response_id, 456)
        self.mock_analytics_service.store_ai_response.assert_called_once()
    
    def test_track_feedback_success(self):
        """Test successful feedback tracking."""
        # Mock service response
        self.mock_analytics_service.store_user_feedback.return_value = 789
        
        # Test tracking
        feedback_id = self.integration.track_feedback(
            query_id=123,
            response_id=456,
            feedback_type="positive",
            additional_notes="Great response!"
        )
        
        # Assertions
        self.assertEqual(feedback_id, 789)
        self.mock_analytics_service.store_user_feedback.assert_called_once()
    
    def test_track_query_with_error(self):
        """Test query tracking with error status."""
        # Mock service response
        self.mock_analytics_service.store_user_query.return_value = 124
        
        # Test tracking with error
        query_id = self.integration.track_query(
            session_id="test_session_123",
            query_text="Invalid query",
            query_complexity="complex",
            processing_time_ms=5000,
            status="error",
            error_message="Processing failed"
        )
        
        # Assertions
        self.assertEqual(query_id, 124)
        
        # Verify the query object passed to service
        call_args = self.mock_analytics_service.store_user_query.call_args[0][0]
        self.assertEqual(call_args.session_id, "test_session_123")
        self.assertEqual(call_args.query_text, "Invalid query")
        self.assertEqual(call_args.query_complexity, QueryComplexity.COMPLEX)
        self.assertEqual(call_args.status, QueryStatus.ERROR)
        self.assertEqual(call_args.error_message, "Processing failed")
    
    def test_invalid_complexity_defaults_to_simple(self):
        """Test that invalid complexity defaults to simple."""
        # Mock service response
        self.mock_analytics_service.store_user_query.return_value = 123
        
        # Test tracking with invalid complexity
        query_id = self.integration.track_query(
            session_id="test_session_123",
            query_text="What is Adobe Analytics?",
            query_complexity="invalid_complexity",
            processing_time_ms=1500
        )
        
        # Verify the query object passed to service
        call_args = self.mock_analytics_service.store_user_query.call_args[0][0]
        self.assertEqual(call_args.query_complexity, QueryComplexity.SIMPLE)
    
    def test_invalid_status_defaults_to_success(self):
        """Test that invalid status defaults to success."""
        # Mock service response
        self.mock_analytics_service.store_user_query.return_value = 123
        
        # Test tracking with invalid status
        query_id = self.integration.track_query(
            session_id="test_session_123",
            query_text="What is Adobe Analytics?",
            query_complexity="simple",
            processing_time_ms=1500,
            status="invalid_status"
        )
        
        # Verify the query object passed to service
        call_args = self.mock_analytics_service.store_user_query.call_args[0][0]
        self.assertEqual(call_args.status, QueryStatus.SUCCESS)
    
    def test_invalid_feedback_type_defaults_to_neutral(self):
        """Test that invalid feedback type defaults to neutral."""
        # Mock service response
        self.mock_analytics_service.store_user_feedback.return_value = 789
        
        # Test tracking with invalid feedback type
        feedback_id = self.integration.track_feedback(
            query_id=123,
            response_id=456,
            feedback_type="invalid_feedback"
        )
        
        # Verify the feedback object passed to service
        call_args = self.mock_analytics_service.store_user_feedback.call_args[0][0]
        self.assertEqual(call_args.feedback_type, FeedbackType.NEUTRAL)


if __name__ == '__main__':
    unittest.main()
