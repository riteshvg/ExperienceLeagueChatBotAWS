"""
Auto-retraining pipeline for single-click model improvement.
Processes feedback in real-time and triggers retraining automatically.
"""

import json
import logging
import time
import os
from typing import Dict, Any, List
from datetime import datetime
import boto3
from google.cloud import aiplatform

logger = logging.getLogger(__name__)


class AutoRetrainingPipeline:
    """Automated retraining pipeline for single-click model improvement."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize auto-retraining pipeline."""
        self.config = config
        self.feedback_queue: List[Dict[str, Any]] = []
        self.processing_status = "idle"
        self.retraining_threshold = config.get('retraining_threshold', 10)
        self.quality_threshold = config.get('quality_threshold', 4)
        self.retraining_cooldown = config.get('retraining_cooldown', 3600)
        self.last_retraining: float = None
        
        # Retraining history and monitoring
        self.retraining_history: List[Dict[str, Any]] = []
        self.training_data_history: List[Dict[str, Any]] = []
        self.job_status_history: List[Dict[str, Any]] = []
        
        # Initialize cloud clients
        self.aws_client = None
        self.gcp_client = None
        self._initialize_cloud_clients()

    def _initialize_cloud_clients(self):
        """Initialize cloud service clients with real credentials."""
        try:
            # AWS Bedrock for Claude
            if self.config.get('aws_region') and self.config.get('aws_access_key_id'):
                self.aws_client = boto3.client(
                    'bedrock',
                    region_name=self.config['aws_region'],
                    aws_access_key_id=self.config['aws_access_key_id'],
                    aws_secret_access_key=self.config['aws_secret_access_key']
                )
                # Also initialize S3 client for data upload
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.config['aws_region'],
                    aws_access_key_id=self.config['aws_access_key_id'],
                    aws_secret_access_key=self.config['aws_secret_access_key']
                )
                logger.info("AWS Bedrock and S3 clients initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize AWS client: {e}")
            self.aws_client = None
            self.s3_client = None

        try:
            # Google Cloud for Gemini
            if self.config.get('gcp_project_id'):
                # Set up authentication
                if self.config.get('google_application_credentials'):
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config['google_application_credentials']
                
                aiplatform.init(project=self.config['gcp_project_id'])
                self.gcp_client = aiplatform
                
                # Initialize GCS client for data upload
                from google.cloud import storage
                self.gcs_client = storage.Client(project=self.config['gcp_project_id'])
                logger.info("Google Cloud and GCS clients initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize GCP client: {e}")
            self.gcp_client = None
            self.gcs_client = None

    async def process_feedback_async(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Process feedback asynchronously and trigger retraining if needed."""
        try:
            # Add feedback to queue
            self.feedback_queue.append(feedback)

            # Check if we should trigger retraining
            if self._should_trigger_retraining():
                logger.info("Retraining threshold reached, starting auto-retraining...")
                return await self._trigger_auto_retraining()
            else:
                logger.info(f"Feedback processed. Queue size: {len(self.feedback_queue)}")
                return {
                    'status': 'queued',
                    'message': f'Feedback queued. {len(self.feedback_queue)}/{self.retraining_threshold} feedback items collected.',
                    'queue_size': len(self.feedback_queue)
                }

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            return {
                'status': 'error',
                'message': f'Failed to process feedback: {str(e)}'
            }

    def _should_trigger_retraining(self) -> bool:
        """Check if retraining should be triggered."""
        # Check if we have enough feedback
        if len(self.feedback_queue) < self.retraining_threshold:
            return False

        # Check cooldown period
        if self.last_retraining:
            time_since_last = time.time() - self.last_retraining
            if time_since_last < self.retraining_cooldown:
                logger.info(f"Retraining cooldown active. {self.retraining_cooldown - time_since_last:.0f}s remaining")
                return False

        # Check if we have high-quality feedback
        high_quality_count = sum(1 for f in self.feedback_queue
                               if f.get('user_rating', 0) >= self.quality_threshold)

        if high_quality_count < self.retraining_threshold // 2:
            logger.info(f"Insufficient high-quality feedback: {high_quality_count}/{self.retraining_threshold // 2}")
            return False

        return True

    async def _trigger_auto_retraining(self) -> Dict[str, Any]:
        """Trigger automatic retraining process."""
        try:
            self.processing_status = "retraining"
            self.last_retraining = time.time()

            # Prepare training data
            training_data = self._prepare_training_data()

            # Start retraining jobs
            retraining_jobs: List[Dict[str, Any]] = []

            # Claude retraining
            if self.aws_client and training_data.get('claude'):
                claude_job = await self._start_claude_retraining(training_data['claude'])
                retraining_jobs.append(claude_job)

            # Gemini retraining
            if self.gcp_client and training_data.get('gemini'):
                gemini_job = await self._start_gemini_retraining(training_data['gemini'])
                retraining_jobs.append(gemini_job)

            # Clear processed feedback
            self.feedback_queue = []

            return {
                'status': 'retraining_started',
                'message': f'Retraining started for {len(retraining_jobs)} models',
                'jobs': retraining_jobs,
                'training_data_size': len(training_data.get('claude', [])) + len(training_data.get('gemini', []))
            }

        except Exception as e:
            logger.error(f"Error triggering retraining: {e}")
            self.processing_status = "error"
            return {
                'status': 'error',
                'message': f'Failed to start retraining: {str(e)}'
            }
        finally:
            self.processing_status = "idle"

    def _prepare_training_data(self) -> Dict[str, List[Dict]]:
        """Prepare training data from feedback queue."""
        training_data: Dict[str, List[Dict]] = {'claude': [], 'gemini': []}

        for feedback in self.feedback_queue:
            if feedback.get('user_rating', 0) >= self.quality_threshold:
                query = feedback.get('query', '')
                gemini_response = feedback.get('gemini_response', '')
                claude_response = feedback.get('claude_response', '')
                selected_model = feedback.get('selected_model', '')

                # Add to Claude training data
                if claude_response and selected_model in ['claude', 'both']:
                    training_data['claude'].append({
                        'prompt': f"Question: {query}\n\nAnswer:",
                        'completion': claude_response,
                        'rating': feedback.get('user_rating', 0),
                        'quality_scores': feedback.get('response_quality', {})
                    })

                # Add to Gemini training data
                if gemini_response and selected_model in ['gemini', 'both']:
                    training_data['gemini'].append({
                        'prompt': f"Question: {query}\n\nAnswer:",
                        'completion': gemini_response,
                        'rating': feedback.get('user_rating', 0),
                        'quality_scores': feedback.get('response_quality', {})
                    })

        return training_data

    async def _start_claude_retraining(self, training_data: List[Dict]) -> Dict[str, Any]:
        """Start Claude retraining job with real AWS integration."""
        try:
            if not self.aws_client or not self.s3_client:
                return {'status': 'error', 'message': 'AWS clients not initialized. Check credentials.'}
            
            # Upload training data to S3
            s3_bucket = self.config.get('s3_bucket')
            s3_key = f"training-data/claude-{int(time.time())}.jsonl"

            # Convert to JSONL format
            jsonl_data = '\n'.join(json.dumps(item) for item in training_data)

            # Save training data locally for monitoring
            if self.config.get('save_training_data_locally'):
                os.makedirs(self.config.get('local_data_path', './training_data'), exist_ok=True)
                local_path = os.path.join(self.config.get('local_data_path', './training_data'), f"claude-{int(time.time())}.jsonl")
                with open(local_path, 'w') as f:
                    f.write(jsonl_data)
                logger.info(f"Training data saved locally: {local_path}")

            # Upload to S3
            self.s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=jsonl_data,
                ContentType='application/json'
            )
            logger.info(f"Training data uploaded to S3: s3://{s3_bucket}/{s3_key}")

            # Create retraining job
            job_name = f"claude-auto-retrain-{int(time.time())}"

            response = self.aws_client.create_model_customization_job(
                jobName=job_name,
                customModelName=f"claude-analytics-expert-{int(time.time())}",
                baseModelIdentifier="anthropic.claude-3-5-sonnet-20240620-v1:0",
                trainingDataConfig={'s3Uri': f"s3://{s3_bucket}/{s3_key}"},
                validationDataConfig={'s3Uri': f"s3://{s3_bucket}/{s3_key}"},
                roleArn=self.config.get('bedrock_role_arn'),
                outputDataConfig={'s3Uri': f"s3://{s3_bucket}/output/"}
            )

            job_info = {
                'job_name': job_name,
                'job_arn': response['jobArn'],
                'model_type': 'claude',
                'training_examples': len(training_data),
                'status': 'started',
                'estimated_completion': datetime.now().timestamp() + 7200,
                's3_location': f"s3://{s3_bucket}/{s3_key}",
                'timestamp': datetime.now().isoformat()
            }

            # Add to retraining history
            self.retraining_history.append(job_info)
            self.training_data_history.append({
                'model_type': 'claude',
                's3_location': f"s3://{s3_bucket}/{s3_key}",
                'training_examples': len(training_data),
                'timestamp': datetime.now().isoformat()
            })

            logger.info(f"Claude retraining job started: {job_name}")
            return job_info

        except Exception as e:
            logger.error(f"Error starting Claude retraining: {e}")
            return {'status': 'error', 'message': str(e)}

    async def _start_gemini_retraining(self, training_data: List[Dict]) -> Dict[str, Any]:
        """Start Gemini retraining job with real GCP integration."""
        try:
            if not self.gcp_client or not self.gcs_client:
                return {'status': 'error', 'message': 'GCP clients not initialized. Check credentials.'}
            
            # Upload training data to GCS
            gcs_bucket = self.config.get('gcs_bucket')
            gcs_path = f"training-data/gemini-{int(time.time())}.jsonl"

            # Convert to JSONL format
            jsonl_data = '\n'.join(json.dumps(item) for item in training_data)

            # Save training data locally for monitoring
            if self.config.get('save_training_data_locally'):
                os.makedirs(self.config.get('local_data_path', './training_data'), exist_ok=True)
                local_path = os.path.join(self.config.get('local_data_path', './training_data'), f"gemini-{int(time.time())}.jsonl")
                with open(local_path, 'w') as f:
                    f.write(jsonl_data)
                logger.info(f"Training data saved locally: {local_path}")

            # Upload to GCS
            bucket = self.gcs_client.bucket(gcs_bucket)
            blob = bucket.blob(gcs_path)
            blob.upload_from_string(jsonl_data, content_type='application/json')
            logger.info(f"Training data uploaded to GCS: gs://{gcs_bucket}/{gcs_path}")

            # Create retraining job
            job_name = f"gemini-auto-retrain-{int(time.time())}"

            # Use AI Platform for custom training
            job = aiplatform.CustomTrainingJob(
                display_name=job_name,
                script_path="gemini_training_script.py",
                container_uri="gcr.io/cloud-aiplatform/training/tf-cpu.2-8:latest",
                requirements=["google-cloud-aiplatform"],
                model_serving_container_image_uri="gcr.io/cloud-aiplatform/prediction/tf-cpu.2-8:latest"
            )

            model = job.run(
                dataset=f"gs://{gcs_bucket}/{gcs_path}",
                model_display_name=job_name,
                args=["--training-data", f"gs://{gcs_bucket}/{gcs_path}"]
            )

            job_info = {
                'job_name': job_name,
                'model_resource_name': model.resource_name,
                'model_type': 'gemini',
                'training_examples': len(training_data),
                'status': 'started',
                'estimated_completion': datetime.now().timestamp() + 3600,
                'gcs_location': f"gs://{gcs_bucket}/{gcs_path}",
                'timestamp': datetime.now().isoformat()
            }

            # Add to retraining history
            self.retraining_history.append(job_info)
            self.training_data_history.append({
                'model_type': 'gemini',
                'gcs_location': f"gs://{gcs_bucket}/{gcs_path}",
                'training_examples': len(training_data),
                'timestamp': datetime.now().isoformat()
            })

            logger.info(f"Gemini retraining job started: {job_name}")
            return job_info

        except Exception as e:
            logger.error(f"Error starting Gemini retraining: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        cooldown_remaining = 0
        if self.last_retraining:
            cooldown_remaining = max(0, self.retraining_cooldown - (time.time() - self.last_retraining))
        
        return {
            'status': self.processing_status,
            'queue_size': len(self.feedback_queue),
            'retraining_threshold': self.retraining_threshold,
            'last_retraining': self.last_retraining,
            'cooldown_remaining': cooldown_remaining,
            'total_retraining_jobs': len(self.retraining_history),
            'aws_available': self.aws_client is not None,
            'gcp_available': self.gcp_client is not None
        }
    
    def get_retraining_history(self) -> List[Dict[str, Any]]:
        """Get retraining job history."""
        return self.retraining_history
    
    def get_training_data_history(self) -> List[Dict[str, Any]]:
        """Get training data upload history."""
        return self.training_data_history
    
    def get_job_status(self, job_name: str) -> Dict[str, Any]:
        """Get status of a specific retraining job."""
        for job in self.retraining_history:
            if job.get('job_name') == job_name:
                return job
        return {'status': 'not_found', 'message': 'Job not found'}
    
    def get_cloud_credentials_status(self) -> Dict[str, Any]:
        """Get status of cloud credentials and connectivity."""
        return {
            'aws': {
                'available': self.aws_client is not None,
                's3_available': self.s3_client is not None,
                'region': self.config.get('aws_region'),
                'bucket': self.config.get('s3_bucket')
            },
            'gcp': {
                'available': self.gcp_client is not None,
                'gcs_available': self.gcs_client is not None,
                'project_id': self.config.get('gcp_project_id'),
                'bucket': self.config.get('gcs_bucket')
            }
        }

    def reset_pipeline(self):
        """Reset the pipeline (for testing)."""
        self.feedback_queue = []
        self.processing_status = "idle"
        self.last_retraining = None
        logger.info("Pipeline reset")

    def update_config(self, new_config: Dict[str, Any]):
        """Update pipeline configuration."""
        self.config.update(new_config)
        self.retraining_threshold = self.config.get('retraining_threshold', 10)
        self.quality_threshold = self.config.get('quality_threshold', 4)
        self.retraining_cooldown = self.config.get('retraining_cooldown', 3600)
        logger.info("Pipeline configuration updated")