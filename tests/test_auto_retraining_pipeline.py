"""
Unit tests for auto-retraining pipeline.
"""

import asyncio
import time
from unittest.mock import Mock, patch
from datetime import datetime

# Import the auto-retraining pipeline
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.retraining.auto_retraining_pipeline import AutoRetrainingPipeline


class TestAutoRetrainingPipeline:
    """Test cases for AutoRetrainingPipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'retraining_threshold': 5,
            'quality_threshold': 4,
            'retraining_cooldown': 60,  # 1 minute for testing
            'aws_region': 'us-east-1',
            's3_bucket': 'test-bucket',
            'bedrock_role_arn': 'arn:aws:iam::123456789012:role/TestRole',
            'gcp_project_id': 'test-project',
            'gcs_bucket': 'test-bucket',
            'enable_claude_retraining': True,
            'enable_gemini_retraining': True
        }

        self.pipeline = AutoRetrainingPipeline(self.config)

        # Sample feedback data
        self.sample_feedback = {
            'query': 'How do I set up Adobe Analytics tracking?',
            'gemini_response': 'To set up Adobe Analytics tracking, you need to...',
            'claude_response': 'Setting up Adobe Analytics tracking involves...',
            'selected_model': 'claude',
            'user_rating': 4,
            'response_quality': {
                'accuracy': 4,
                'relevance': 5,
                'clarity': 4,
                'completeness': 5
            },
            'timestamp': datetime.now().isoformat()
        }

    def test_initialization(self):
        """Test pipeline initialization."""
        assert self.pipeline.retraining_threshold == 5
        assert self.pipeline.quality_threshold == 4
        assert self.pipeline.retraining_cooldown == 60
        assert self.pipeline.processing_status == "idle"
        assert len(self.pipeline.feedback_queue) == 0
        assert self.pipeline.last_retraining is None

    def test_config_update(self):
        """Test configuration update."""
        new_config = {
            'retraining_threshold': 10,
            'quality_threshold': 3,
            'retraining_cooldown': 120
        }

        self.pipeline.update_config(new_config)

        assert self.pipeline.retraining_threshold == 10
        assert self.pipeline.quality_threshold == 3
        assert self.pipeline.retraining_cooldown == 120

    def test_feedback_queuing(self):
        """Test feedback queuing without triggering retraining."""
        # Add feedback below threshold
        for i in range(3):
            feedback = self.sample_feedback.copy()
            feedback['query'] = f"Test query {i}"

            result = asyncio.run(self.pipeline.process_feedback_async(feedback))

            assert result['status'] == 'queued'
            assert result['queue_size'] == i + 1
            assert len(self.pipeline.feedback_queue) == i + 1

    def test_retraining_trigger(self):
        """Test retraining trigger when threshold is reached."""
        # Add enough high-quality feedback to trigger retraining
        for i in range(5):
            feedback = self.sample_feedback.copy()
            feedback['query'] = f"Test query {i}"
            feedback['user_rating'] = 4  # High quality

            self.pipeline.feedback_queue.append(feedback)

        # Mock the retraining methods
        with patch.object(self.pipeline, '_trigger_auto_retraining') as mock_trigger:
            mock_trigger.return_value = {
                'status': 'retraining_started',
                'message': 'Retraining started',
                'jobs': [],
                'training_data_size': 5
            }

            result = asyncio.run(self.pipeline.process_feedback_async(self.sample_feedback))

            assert result['status'] == 'retraining_started'
            mock_trigger.assert_called_once()

    def test_quality_threshold_filtering(self):
        """Test that low-quality feedback is filtered out."""
        # Add low-quality feedback
        low_quality_feedback = self.sample_feedback.copy()
        low_quality_feedback['user_rating'] = 2  # Low quality

        self.pipeline.feedback_queue.append(low_quality_feedback)

        # Prepare training data
        training_data = self.pipeline._prepare_training_data()

        # Should be empty because quality is below threshold
        assert len(training_data['claude']) == 0
        assert len(training_data['gemini']) == 0

    def test_high_quality_training_data_preparation(self):
        """Test training data preparation with high-quality feedback."""
        # Add high-quality feedback
        high_quality_feedback = self.sample_feedback.copy()
        high_quality_feedback['user_rating'] = 4
        high_quality_feedback['selected_model'] = 'claude'

        self.pipeline.feedback_queue.append(high_quality_feedback)

        # Prepare training data
        training_data = self.pipeline._prepare_training_data()

        # Should have Claude training data
        assert len(training_data['claude']) == 1
        assert len(training_data['gemini']) == 0

        # Check training data format
        claude_data = training_data['claude'][0]
        assert 'prompt' in claude_data
        assert 'completion' in claude_data
        assert 'rating' in claude_data
        assert 'quality_scores' in claude_data
        assert claude_data['rating'] == 4

    def test_cooldown_period(self):
        """Test cooldown period prevents too frequent retraining."""
        # Set last retraining to recent time
        self.pipeline.last_retraining = time.time() - 30  # 30 seconds ago
        self.pipeline.retraining_cooldown = 60  # 1 minute cooldown

        # Add enough feedback to trigger retraining
        for i in range(5):
            feedback = self.sample_feedback.copy()
            feedback['query'] = f"Test query {i}"
            feedback['user_rating'] = 4
            self.pipeline.feedback_queue.append(feedback)

        # Should not trigger retraining due to cooldown
        assert not self.pipeline._should_trigger_retraining()

    def test_pipeline_status(self):
        """Test pipeline status reporting."""
        # Add some feedback
        self.pipeline.feedback_queue.append(self.sample_feedback)
        self.pipeline.last_retraining = time.time() - 120  # 2 minutes ago

        status = self.pipeline.get_pipeline_status()

        assert status['status'] == 'idle'
        assert status['queue_size'] == 1
        assert status['retraining_threshold'] == 5
        assert status['last_retraining'] is not None
        assert status['cooldown_remaining'] == 0  # Cooldown expired

    def test_pipeline_reset(self):
        """Test pipeline reset functionality."""
        # Add some feedback and set status
        self.pipeline.feedback_queue.append(self.sample_feedback)
        self.pipeline.processing_status = "retraining"
        self.pipeline.last_retraining = time.time()

        # Reset pipeline
        self.pipeline.reset_pipeline()

        assert len(self.pipeline.feedback_queue) == 0
        assert self.pipeline.processing_status == "idle"
        assert self.pipeline.last_retraining is None

    @patch('boto3.client')
    def test_claude_retraining_job_creation(self, mock_boto_client):
        """Test Claude retraining job creation."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client

        # Mock Bedrock client
        mock_bedrock_client = Mock()
        mock_bedrock_client.create_model_customization_job.return_value = {
            'jobArn': 'arn:aws:bedrock:us-east-1:123456789012:model-customization-job/test-job'
        }

        self.pipeline.aws_client = mock_bedrock_client

        # Test data
        training_data = [{
            'prompt': 'Question: Test query\n\nAnswer:',
            'completion': 'Test response',
            'rating': 4,
            'quality_scores': {'accuracy': 4}
        }]

        # Run async method
        result = asyncio.run(self.pipeline._start_claude_retraining(training_data))

        # Verify result
        assert result['status'] == 'started'
        assert result['model_type'] == 'claude'
        assert result['training_examples'] == 1
        assert 'job_name' in result
        assert 'job_arn' in result

    def test_error_handling(self):
        """Test error handling in feedback processing."""
        # Test with invalid feedback data
        invalid_feedback = {'invalid': 'data'}

        result = asyncio.run(self.pipeline.process_feedback_async(invalid_feedback))

        # Should handle error gracefully
        assert result['status'] in ['queued', 'error']

    def test_mixed_quality_feedback(self):
        """Test handling of mixed quality feedback."""
        # Add mixed quality feedback
        feedbacks = [
            {**self.sample_feedback, 'user_rating': 5, 'selected_model': 'claude'},
            {**self.sample_feedback, 'user_rating': 2, 'selected_model': 'gemini'},  # Low quality
            {**self.sample_feedback, 'user_rating': 4, 'selected_model': 'both'},
        ]

        for feedback in feedbacks:
            self.pipeline.feedback_queue.append(feedback)

        # Prepare training data
        training_data = self.pipeline._prepare_training_data()

        # Should only include high-quality feedback (rating >= 4)
        assert len(training_data['claude']) == 2  # 5 and 4 ratings
        assert len(training_data['gemini']) == 1  # Only 4 rating (both includes gemini)

    def test_should_trigger_retraining_logic(self):
        """Test the retraining trigger logic comprehensively."""
        # Test case 1: Not enough feedback
        self.pipeline.feedback_queue = []
        assert not self.pipeline._should_trigger_retraining()

        # Test case 2: Enough feedback but in cooldown
        for i in range(5):
            self.pipeline.feedback_queue.append({**self.sample_feedback, 'user_rating': 4})
        self.pipeline.last_retraining = time.time() - 30  # 30 seconds ago
        assert not self.pipeline._should_trigger_retraining()

        # Test case 3: Enough feedback, no cooldown, but low quality
        self.pipeline.last_retraining = None
        self.pipeline.feedback_queue = []
        for i in range(5):
            self.pipeline.feedback_queue.append({**self.sample_feedback, 'user_rating': 2})  # Low quality
        assert not self.pipeline._should_trigger_retraining()

        # Test case 4: All conditions met
        self.pipeline.feedback_queue = []
        for i in range(5):
            self.pipeline.feedback_queue.append({**self.sample_feedback, 'user_rating': 4})  # High quality
        assert self.pipeline._should_trigger_retraining()

    def test_training_data_format(self):
        """Test that training data is formatted correctly."""
        # Add feedback for both models
        claude_feedback = {**self.sample_feedback, 'selected_model': 'claude', 'user_rating': 4}
        gemini_feedback = {**self.sample_feedback, 'selected_model': 'gemini', 'user_rating': 4}
        both_feedback = {**self.sample_feedback, 'selected_model': 'both', 'user_rating': 4}

        self.pipeline.feedback_queue = [claude_feedback, gemini_feedback, both_feedback]

        training_data = self.pipeline._prepare_training_data()

        # Check Claude data
        assert len(training_data['claude']) == 2  # claude + both
        for item in training_data['claude']:
            assert 'prompt' in item
            assert 'completion' in item
            assert 'rating' in item
            assert 'quality_scores' in item
            assert item['prompt'].startswith('Question:')
            assert item['prompt'].endswith('\n\nAnswer:')

        # Check Gemini data
        assert len(training_data['gemini']) == 2  # gemini + both
        for item in training_data['gemini']:
            assert 'prompt' in item
            assert 'completion' in item
            assert 'rating' in item
            assert 'quality_scores' in item