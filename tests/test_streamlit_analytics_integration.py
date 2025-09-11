"""
Integration tests for Streamlit analytics integration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

from src.integrations.streamlit_analytics import StreamlitAnalyticsIntegration
from src.services.analytics_service import AnalyticsService
from src.models.database_models import DatabaseConfig, QueryAnalytics, UserQuery, AIResponse, UserFeedback, QueryComplexity, QueryStatus, FeedbackType


class TestStreamlitAnalyticsIntegration(unittest.TestCase):
    """Test cases for StreamlitAnalyticsIntegration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_analytics_service = Mock(spec=AnalyticsService)
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
        
        # Verify the query object passed to service
        call_args = self.mock_analytics_service.store_user_query.call_args[0][0]
        self.assertEqual(call_args.session_id, "test_session_123")
        self.assertEqual(call_args.query_text, "What is Adobe Analytics?")
        self.assertEqual(call_args.query_complexity, QueryComplexity.SIMPLE)
        self.assertEqual(call_args.processing_time_ms, 1500)
        self.assertEqual(call_args.status, QueryStatus.SUCCESS)
    
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
        self.assertEqual(call_args.status, QueryStatus.ERROR)
        self.assertEqual(call_args.error_message, "Processing failed")
    
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
            estimated_cost=0.00125,
            documents_retrieved=3,
            relevance_score=0.85
        )
        
        # Assertions
        self.assertEqual(response_id, 456)
        self.mock_analytics_service.store_ai_response.assert_called_once()
        
        # Verify the response object passed to service
        call_args = self.mock_analytics_service.store_ai_response.call_args[0][0]
        self.assertEqual(call_args.query_id, 123)
        self.assertEqual(call_args.model_used, "haiku")
        self.assertEqual(call_args.response_text, "Adobe Analytics is a web analytics platform...")
        self.assertEqual(call_args.tokens_used, 100)
        self.assertEqual(call_args.estimated_cost, 0.00125)
        self.assertEqual(call_args.documents_retrieved, 3)
        self.assertEqual(call_args.relevance_score, 0.85)
    
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
        
        # Verify the feedback object passed to service
        call_args = self.mock_analytics_service.store_user_feedback.call_args[0][0]
        self.assertEqual(call_args.query_id, 123)
        self.assertEqual(call_args.response_id, 456)
        self.assertEqual(call_args.feedback_type, FeedbackType.POSITIVE)
        self.assertEqual(call_args.additional_notes, "Great response!")
    
    def test_track_feedback_negative(self):
        """Test negative feedback tracking."""
        # Mock service response
        self.mock_analytics_service.store_user_feedback.return_value = 790
        
        # Test tracking
        feedback_id = self.integration.track_feedback(
            query_id=123,
            response_id=456,
            feedback_type="negative",
            additional_notes="Not helpful"
        )
        
        # Assertions
        self.assertEqual(feedback_id, 790)
        
        # Verify the feedback object passed to service
        call_args = self.mock_analytics_service.store_user_feedback.call_args[0][0]
        self.assertEqual(call_args.feedback_type, FeedbackType.NEGATIVE)
        self.assertEqual(call_args.additional_notes, "Not helpful")
    
    def test_track_query_service_error(self):
        """Test query tracking when service raises an error."""
        # Mock service error
        self.mock_analytics_service.store_user_query.side_effect = Exception("Database error")
        
        # Test tracking
        query_id = self.integration.track_query(
            session_id="test_session_123",
            query_text="What is Adobe Analytics?",
            query_complexity="simple",
            processing_time_ms=1500
        )
        
        # Assertions
        self.assertIsNone(query_id)
    
    def test_track_response_service_error(self):
        """Test response tracking when service raises an error."""
        # Mock service error
        self.mock_analytics_service.store_ai_response.side_effect = Exception("Database error")
        
        # Test tracking
        response_id = self.integration.track_response(
            query_id=123,
            model_used="haiku",
            model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
            response_text="Response text",
            tokens_used=100,
            estimated_cost=0.00125
        )
        
        # Assertions
        self.assertIsNone(response_id)
    
    def test_track_feedback_service_error(self):
        """Test feedback tracking when service raises an error."""
        # Mock service error
        self.mock_analytics_service.store_user_feedback.side_effect = Exception("Database error")
        
        # Test tracking
        feedback_id = self.integration.track_feedback(
            query_id=123,
            response_id=456,
            feedback_type="positive"
        )
        
        # Assertions
        self.assertIsNone(feedback_id)
    
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


class TestStreamlitAnalyticsIntegrationInitialization(unittest.TestCase):
    """Test cases for analytics service initialization."""
    
    @patch('src.integrations.streamlit_analytics.StreamlitAnalyticsIntegration')
    @patch('src.integrations.streamlit_analytics.AnalyticsService')
    @patch('src.integrations.streamlit_analytics.DatabaseConfig')
    def test_initialize_analytics_service_success(self, mock_config_class, mock_service_class, mock_integration_class):
        """Test successful analytics service initialization."""
        # Mock configuration
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        # Mock service
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock integration
        mock_integration = Mock()
        mock_integration_class.return_value = mock_integration
        
        # Mock streamlit secrets
        with patch('src.integrations.streamlit_analytics.st') as mock_st:
            mock_st.secrets.get.return_value = {
                "host": "localhost",
                "port": 3306,
                "name": "test_db",
                "username": "test_user",
                "password": "test_password"
            }
            
            from src.integrations.streamlit_analytics import initialize_analytics_service
            result = initialize_analytics_service()
            
            # Assertions
            self.assertEqual(result, mock_integration)
            mock_config_class.assert_called_once()
            mock_service_class.assert_called_once_with(mock_config)
            mock_integration_class.assert_called_once_with(mock_service)
    
    @patch('src.integrations.streamlit_analytics.AnalyticsService')
    @patch('src.integrations.streamlit_analytics.DatabaseConfig')
    def test_initialize_analytics_service_error(self, mock_config_class, mock_service_class):
        """Test analytics service initialization with error."""
        # Mock service error
        mock_service_class.side_effect = Exception("Database connection failed")
        
        # Mock streamlit secrets
        with patch('src.integrations.streamlit_analytics.st') as mock_st:
            mock_st.secrets.get.return_value = {}
            
            from src.integrations.streamlit_analytics import initialize_analytics_service
            result = initialize_analytics_service()
            
            # Assertions
            self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
