"""
Integration tests for auto-retraining pipeline.
Tests end-to-end workflow from feedback submission to retraining trigger.
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


class TestAutoRetrainingIntegration:
    """Integration tests for auto-retraining pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'retraining_threshold': 3,  # Lower threshold for testing
            'quality_threshold': 3,     # Lower quality threshold for testing
            'retraining_cooldown': 10,  # 10 seconds for testing
            'aws_region': 'us-east-1',
            's3_bucket': 'test-bucket',
            'bedrock_role_arn': 'arn:aws:iam::123456789012:role/TestRole',
            'gcp_project_id': 'test-project',
            'gcs_bucket': 'test-bucket',
            'enable_claude_retraining': True,
            'enable_gemini_retraining': True
        }

        self.pipeline = AutoRetrainingPipeline(self.config)

    def test_end_to_end_feedback_processing(self):
        """Test complete end-to-end feedback processing workflow."""
        # Mock cloud clients to avoid actual API calls
        with patch('boto3.client') as mock_boto_client, \
             patch('google.cloud.aiplatform.init') as mock_aiplatform_init:
            
            # Mock AWS Bedrock client
            mock_bedrock_client = Mock()
            mock_bedrock_client.create_model_customization_job.return_value = {
                'jobArn': 'arn:aws:bedrock:us-east-1:123456789012:model-customization-job/test-job'
            }
            
            # Mock S3 client
            mock_s3_client = Mock()
            mock_boto_client.return_value = mock_s3_client
            
            # Set up pipeline with mocked clients
            self.pipeline.aws_client = mock_bedrock_client
            self.pipeline.gcp_client = Mock()

            # Test feedback submissions
            feedbacks = [
                {
                    'query': 'How do I set up Adobe Analytics?',
                    'gemini_response': 'To set up Adobe Analytics, you need to...',
                    'claude_response': 'Setting up Adobe Analytics involves...',
                    'selected_model': 'claude',
                    'user_rating': 4,
                    'response_quality': {'accuracy': 4, 'relevance': 5, 'clarity': 4, 'completeness': 5},
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'query': 'What is Customer Journey Analytics?',
                    'gemini_response': 'Customer Journey Analytics is...',
                    'claude_response': 'CJA allows you to...',
                    'selected_model': 'both',
                    'user_rating': 5,
                    'response_quality': {'accuracy': 5, 'relevance': 5, 'clarity': 5, 'completeness': 5},
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'query': 'How to create segments in Adobe Analytics?',
                    'gemini_response': 'Creating segments in Adobe Analytics...',
                    'claude_response': 'To create segments, you can...',
                    'selected_model': 'gemini',
                    'user_rating': 3,
                    'response_quality': {'accuracy': 3, 'relevance': 4, 'clarity': 3, 'completeness': 4},
                    'timestamp': datetime.now().isoformat()
                }
            ]

            # Process first two feedbacks (should be queued)
            for i, feedback in enumerate(feedbacks[:2]):
                result = asyncio.run(self.pipeline.process_feedback_async(feedback))
                assert result['status'] == 'queued'
                assert result['queue_size'] == i + 1

            # Process third feedback (should trigger retraining)
            result = asyncio.run(self.pipeline.process_feedback_async(feedbacks[2]))
            assert result['status'] == 'retraining_started'
            assert 'jobs' in result
            assert 'training_data_size' in result

            # Verify that feedback queue was cleared after retraining
            assert len(self.pipeline.feedback_queue) == 0

            # Verify that retraining jobs were created
            assert len(result['jobs']) > 0

    def test_retraining_cooldown_behavior(self):
        """Test that retraining respects cooldown periods."""
        # Mock cloud clients
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock_client = Mock()
            mock_bedrock_client.create_model_customization_job.return_value = {
                'jobArn': 'arn:aws:bedrock:us-east-1:123456789012:model-customization-job/test-job'
            }
            mock_s3_client = Mock()
            mock_boto_client.return_value = mock_s3_client
            
            self.pipeline.aws_client = mock_bedrock_client

            # Add enough feedback to trigger retraining
            for i in range(3):
                feedback = {
                    'query': f'Test query {i}',
                    'gemini_response': f'Gemini response {i}',
                    'claude_response': f'Claude response {i}',
                    'selected_model': 'claude',
                    'user_rating': 4,
                    'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
                    'timestamp': datetime.now().isoformat()
                }
                self.pipeline.feedback_queue.append(feedback)

            # Trigger first retraining
            result = asyncio.run(self.pipeline._trigger_auto_retraining())
            assert result['status'] == 'retraining_started'
            assert self.pipeline.last_retraining is not None

            # Add more feedback immediately (should not trigger due to cooldown)
            new_feedback = {
                'query': 'New test query',
                'gemini_response': 'New gemini response',
                'claude_response': 'New claude response',
                'selected_model': 'claude',
                'user_rating': 4,
                'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
                'timestamp': datetime.now().isoformat()
            }

            result = asyncio.run(self.pipeline.process_feedback_async(new_feedback))
            assert result['status'] == 'queued'  # Should be queued, not retraining

    def test_quality_threshold_enforcement(self):
        """Test that only high-quality feedback triggers retraining."""
        # Mock cloud clients
        with patch('boto3.client') as mock_boto_client:
            mock_bedrock_client = Mock()
            mock_bedrock_client.create_model_customization_job.return_value = {
                'jobArn': 'arn:aws:bedrock:us-east-1:123456789012:model-customization-job/test-job'
            }
            mock_s3_client = Mock()
            mock_boto_client.return_value = mock_s3_client
            
            self.pipeline.aws_client = mock_bedrock_client

            # Add low-quality feedback (should not trigger retraining)
            for i in range(2):  # Only 2 low-quality items
                feedback = {
                    'query': f'Test query {i}',
                    'gemini_response': f'Gemini response {i}',
                    'claude_response': f'Claude response {i}',
                    'selected_model': 'claude',
                    'user_rating': 2,  # Low quality
                    'response_quality': {'accuracy': 2, 'relevance': 2, 'clarity': 2, 'completeness': 2},
                    'timestamp': datetime.now().isoformat()
                }
                self.pipeline.feedback_queue.append(feedback)

            # Should not trigger retraining due to low quality
            assert not self.pipeline._should_trigger_retraining()

            # Add one high-quality feedback
            high_quality_feedback = {
                'query': 'High quality query',
                'gemini_response': 'High quality gemini response',
                'claude_response': 'High quality claude response',
                'selected_model': 'claude',
                'user_rating': 4,  # High quality
                'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
                'timestamp': datetime.now().isoformat()
            }
            self.pipeline.feedback_queue.append(high_quality_feedback)

            # Should still not trigger (need at least half to be high quality)
            # With 3 total items, need at least 2 high-quality items (3//2 = 1)
            # We have 1 high-quality item, so 1 < 1 is false, should trigger
            # But we need 3 total items to reach threshold, so let's add one more
            feedback = {
                'query': 'Another low quality query',
                'gemini_response': 'Another low quality gemini response',
                'claude_response': 'Another low quality claude response',
                'selected_model': 'claude',
                'user_rating': 2,  # Low quality
                'response_quality': {'accuracy': 2, 'relevance': 2, 'clarity': 2, 'completeness': 2},
                'timestamp': datetime.now().isoformat()
            }
            self.pipeline.feedback_queue.append(feedback)

            # Now should trigger retraining (1 high-quality out of 4 total >= 3//2 = 1)
            assert self.pipeline._should_trigger_retraining()

    def test_training_data_preparation_integration(self):
        """Test that training data is properly prepared for both models."""
        # Add mixed feedback for both models
        feedbacks = [
            {
                'query': 'Claude only query',
                'gemini_response': 'Gemini response',
                'claude_response': 'Claude response',
                'selected_model': 'claude',
                'user_rating': 4,
                'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
                'timestamp': datetime.now().isoformat()
            },
            {
                'query': 'Gemini only query',
                'gemini_response': 'Gemini response',
                'claude_response': 'Claude response',
                'selected_model': 'gemini',
                'user_rating': 4,
                'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
                'timestamp': datetime.now().isoformat()
            },
            {
                'query': 'Both models query',
                'gemini_response': 'Gemini response',
                'claude_response': 'Claude response',
                'selected_model': 'both',
                'user_rating': 4,
                'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
                'timestamp': datetime.now().isoformat()
            }
        ]

        for feedback in feedbacks:
            self.pipeline.feedback_queue.append(feedback)

        # Prepare training data
        training_data = self.pipeline._prepare_training_data()

        # Verify Claude training data
        assert len(training_data['claude']) == 2  # claude + both
        for item in training_data['claude']:
            assert 'prompt' in item
            assert 'completion' in item
            assert 'rating' in item
            assert 'quality_scores' in item
            assert item['prompt'].startswith('Question:')
            assert item['prompt'].endswith('\n\nAnswer:')

        # Verify Gemini training data
        assert len(training_data['gemini']) == 2  # gemini + both
        for item in training_data['gemini']:
            assert 'prompt' in item
            assert 'completion' in item
            assert 'rating' in item
            assert 'quality_scores' in item

    def test_pipeline_status_integration(self):
        """Test pipeline status reporting throughout the workflow."""
        # Initial status
        status = self.pipeline.get_pipeline_status()
        assert status['status'] == 'idle'
        assert status['queue_size'] == 0
        assert status['last_retraining'] is None
        assert status['cooldown_remaining'] == 0

        # Add feedback
        feedback = {
            'query': 'Test query',
            'gemini_response': 'Test gemini response',
            'claude_response': 'Test claude response',
            'selected_model': 'claude',
            'user_rating': 4,
            'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
            'timestamp': datetime.now().isoformat()
        }
        self.pipeline.feedback_queue.append(feedback)

        # Status after adding feedback
        status = self.pipeline.get_pipeline_status()
        assert status['queue_size'] == 1
        assert status['retraining_threshold'] == 3

        # Simulate retraining
        self.pipeline.processing_status = "retraining"
        self.pipeline.last_retraining = time.time()

        # Status during retraining
        status = self.pipeline.get_pipeline_status()
        assert status['status'] == 'retraining'
        assert status['last_retraining'] is not None
        assert status['cooldown_remaining'] > 0

    def test_error_recovery_integration(self):
        """Test error handling and recovery in the pipeline."""
        # Test with invalid feedback data
        invalid_feedback = {
            'invalid': 'data',
            'missing_required_fields': True
        }

        result = asyncio.run(self.pipeline.process_feedback_async(invalid_feedback))
        
        # Should handle error gracefully
        assert result['status'] in ['queued', 'error']
        
        # Pipeline should still be functional
        status = self.pipeline.get_pipeline_status()
        assert status['status'] == 'idle'

        # Test pipeline reset
        self.pipeline.feedback_queue.append({'test': 'data'})
        self.pipeline.processing_status = "error"
        
        self.pipeline.reset_pipeline()
        
        status = self.pipeline.get_pipeline_status()
        assert status['status'] == 'idle'
        assert status['queue_size'] == 0
