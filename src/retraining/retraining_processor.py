"""
Retraining processor for hybrid model feedback data.
Handles data preparation, model training, and evaluation.
"""

import json
import os
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class RetrainingProcessor:
    """Processes feedback data for model retraining."""
    
    def __init__(self, feedback_data_path: str = "./feedback_data"):
        """Initialize retraining processor."""
        self.feedback_data_path = Path(feedback_data_path)
        self.training_data_path = self.feedback_data_path / "training_data"
        self.training_data_path.mkdir(exist_ok=True)
        
    def prepare_training_data(self, min_rating: int = 4, min_quality: int = 4) -> Dict[str, Any]:
        """
        Prepare training data from feedback.
        
        Args:
            min_rating: Minimum user rating to include
            min_quality: Minimum quality score to include
            
        Returns:
            Prepared training data
        """
        feedback_file = self.feedback_data_path / "feedback.json"
        
        if not feedback_file.exists():
            logger.error("No feedback data found")
            return {}
        
        with open(feedback_file, 'r') as f:
            feedback_data = json.load(f)
        
        # Filter high-quality examples
        high_quality_examples = []
        for feedback in feedback_data:
            if (feedback.get('user_rating', 0) >= min_rating and
                feedback.get('response_quality', {}).get('accuracy', 0) >= min_quality):
                high_quality_examples.append(feedback)
        
        logger.info(f"Found {len(high_quality_examples)} high-quality examples out of {len(feedback_data)} total")
        
        # Prepare training data for each model
        training_data = {
            'gemini': [],
            'claude': [],
            'preference_data': [],
            'metadata': {
                'total_examples': len(high_quality_examples),
                'filtered_at': datetime.now().isoformat(),
                'min_rating': min_rating,
                'min_quality': min_quality
            }
        }
        
        for feedback in high_quality_examples:
            query = feedback['query']
            gemini_response = feedback.get('gemini_response', '')
            claude_response = feedback.get('claude_response', '')
            selected_model = feedback.get('selected_model', '')
            rating = feedback.get('user_rating', 0)
            quality_scores = feedback.get('response_quality', {})
            
            # Add to model-specific training data
            if gemini_response and selected_model in ['gemini', 'both']:
                training_data['gemini'].append({
                    'prompt': f"Question: {query}\n\nAnswer:",
                    'completion': gemini_response,
                    'rating': rating,
                    'quality_scores': quality_scores,
                    'feedback_id': feedback['feedback_id']
                })
            
            if claude_response and selected_model in ['claude', 'both']:
                training_data['claude'].append({
                    'prompt': f"Question: {query}\n\nAnswer:",
                    'completion': claude_response,
                    'rating': rating,
                    'quality_scores': quality_scores,
                    'feedback_id': feedback['feedback_id']
                })
            
            # Add preference data if both responses available
            if gemini_response and claude_response:
                preferred_model = selected_model if selected_model in ['gemini', 'claude'] else 'both'
                if preferred_model == 'gemini':
                    preferred_response = gemini_response
                    rejected_response = claude_response
                elif preferred_model == 'claude':
                    preferred_response = claude_response
                    rejected_response = gemini_response
                else:
                    # If both are good, use the higher-rated one
                    if rating >= 4:
                        preferred_response = gemini_response if len(gemini_response) > len(claude_response) else claude_response
                        rejected_response = claude_response if preferred_response == gemini_response else gemini_response
                    else:
                        continue
                
                training_data['preference_data'].append({
                    'prompt': f"Question: {query}\n\nAnswer:",
                    'chosen': preferred_response,
                    'rejected': rejected_response,
                    'preference_strength': rating / 5.0,
                    'feedback_id': feedback['feedback_id']
                })
        
        # Save training data
        self._save_training_data(training_data)
        
        return training_data
    
    def _save_training_data(self, training_data: Dict[str, Any]):
        """Save training data to files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save complete training data
        training_file = self.training_data_path / f"training_data_{timestamp}.json"
        with open(training_file, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        # Save model-specific data
        for model in ['gemini', 'claude']:
            if training_data[model]:
                model_file = self.training_data_path / f"{model}_training_{timestamp}.jsonl"
                with open(model_file, 'w') as f:
                    for example in training_data[model]:
                        f.write(json.dumps(example) + '\n')
        
        # Save preference data
        if training_data['preference_data']:
            pref_file = self.training_data_path / f"preference_data_{timestamp}.jsonl"
            with open(pref_file, 'w') as f:
                for example in training_data['preference_data']:
                    f.write(json.dumps(example) + '\n')
        
        logger.info(f"Training data saved to {self.training_data_path}")
    
    def generate_retraining_script(self, model_type: str = 'claude') -> str:
        """
        Generate retraining script for specific model.
        
        Args:
            model_type: 'claude' or 'gemini'
            
        Returns:
            Path to generated script
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        script_path = self.training_data_path / f"retrain_{model_type}_{timestamp}.py"
        
        if model_type == 'claude':
            script_content = self._generate_claude_script()
        elif model_type == 'gemini':
            script_content = self._generate_gemini_script()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        logger.info(f"Retraining script generated: {script_path}")
        return str(script_path)
    
    def _generate_claude_script(self) -> str:
        """Generate Claude retraining script."""
        return '''#!/usr/bin/env python3
"""
Claude model retraining script using AWS Bedrock.
Generated automatically from feedback data.
"""

import boto3
import json
import time
from pathlib import Path

def retrain_claude_model():
    """Retrain Claude model using feedback data."""
    
    # Initialize Bedrock client
    bedrock = boto3.client('bedrock')
    
    # Configuration
    job_name = f"claude-feedback-retrain-{int(time.time())}"
    base_model = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    custom_model_name = "claude-analytics-expert"
    
    # Training data (you'll need to upload this to S3)
    training_data_s3_uri = "s3://your-bucket/training-data.jsonl"
    validation_data_s3_uri = "s3://your-bucket/validation-data.jsonl"
    
    try:
        # Create model customization job
        response = bedrock.create_model_customization_job(
            jobName=job_name,
            customModelName=custom_model_name,
            baseModelIdentifier=base_model,
            trainingDataConfig={
                's3Uri': training_data_s3_uri
            },
            validationDataConfig={
                's3Uri': validation_data_s3_uri
            },
            roleArn="arn:aws:iam::YOUR_ACCOUNT:role/BedrockCustomModelRole",
            outputDataConfig={
                's3Uri': "s3://your-bucket/output/"
            }
        )
        
        print(f"Retraining job started: {response['jobArn']}")
        print(f"Job name: {job_name}")
        
        # Monitor job status
        while True:
            status = bedrock.get_model_customization_job(jobIdentifier=job_name)
            job_status = status['status']
            
            print(f"Job status: {job_status}")
            
            if job_status in ['Completed', 'Failed', 'Stopped']:
                break
            
            time.sleep(60)  # Check every minute
        
        if job_status == 'Completed':
            print("✅ Model retraining completed successfully!")
            print(f"Custom model ARN: {status['customModelArn']}")
        else:
            print(f"❌ Model retraining failed: {job_status}")
            
    except Exception as e:
        print(f"❌ Error during retraining: {e}")

if __name__ == "__main__":
    retrain_claude_model()
'''
    
    def _generate_gemini_script(self) -> str:
        """Generate Gemini retraining script."""
        return '''#!/usr/bin/env python3
"""
Gemini model retraining script using Google AI Platform.
Generated automatically from feedback data.
"""

import json
import os
from google.cloud import aiplatform
from google.cloud.aiplatform import gapic as aip

def retrain_gemini_model():
    """Retrain Gemini model using feedback data."""
    
    # Configuration
    project_id = "your-gcp-project"
    location = "us-central1"
    model_display_name = "gemini-analytics-expert"
    
    # Initialize AI Platform
    aiplatform.init(project=project_id, location=location)
    
    # Training data configuration
    training_data_uri = "gs://your-bucket/training-data.jsonl"
    
    try:
        # Create training job
        job = aiplatform.CustomTrainingJob(
            display_name=model_display_name,
            script_path="training_script.py",  # You'll need to create this
            container_uri="gcr.io/cloud-aiplatform/training/tf-cpu.2-8:latest",
            requirements=["google-cloud-aiplatform"],
            model_serving_container_image_uri="gcr.io/cloud-aiplatform/prediction/tf-cpu.2-8:latest"
        )
        
        # Run training job
        model = job.run(
            dataset=training_data_uri,
            model_display_name=model_display_name,
            args=["--training-data", training_data_uri]
        )
        
        print(f"✅ Model retraining completed successfully!")
        print(f"Model resource name: {model.resource_name}")
        
    except Exception as e:
        print(f"❌ Error during retraining: {e}")

if __name__ == "__main__":
    retrain_gemini_model()
'''
    
    def create_evaluation_dataset(self, test_ratio: float = 0.2) -> Dict[str, Any]:
        """
        Create evaluation dataset from feedback data.
        
        Args:
            test_ratio: Ratio of data to use for testing
            
        Returns:
            Train/test split data
        """
        feedback_file = self.feedback_data_path / "feedback.json"
        
        if not feedback_file.exists():
            logger.error("No feedback data found")
            return {}
        
        with open(feedback_file, 'r') as f:
            feedback_data = json.load(f)
        
        # Filter and prepare data
        examples = []
        for feedback in feedback_data:
            if feedback.get('user_rating', 0) >= 3:  # Include moderate quality for evaluation
                examples.append({
                    'query': feedback['query'],
                    'gemini_response': feedback.get('gemini_response', ''),
                    'claude_response': feedback.get('claude_response', ''),
                    'selected_model': feedback.get('selected_model', ''),
                    'rating': feedback.get('user_rating', 0),
                    'quality_scores': feedback.get('response_quality', {})
                })
        
        # Split data
        import random
        random.shuffle(examples)
        split_idx = int(len(examples) * (1 - test_ratio))
        
        train_data = examples[:split_idx]
        test_data = examples[split_idx:]
        
        evaluation_data = {
            'train': train_data,
            'test': test_data,
            'metadata': {
                'total_examples': len(examples),
                'train_count': len(train_data),
                'test_count': len(test_data),
                'created_at': datetime.now().isoformat()
            }
        }
        
        # Save evaluation data
        eval_file = self.training_data_path / "evaluation_data.json"
        with open(eval_file, 'w') as f:
            json.dump(evaluation_data, f, indent=2)
        
        logger.info(f"Evaluation dataset created: {len(train_data)} train, {len(test_data)} test")
        return evaluation_data
    
    def analyze_feedback_trends(self) -> Dict[str, Any]:
        """Analyze feedback trends and patterns."""
        feedback_file = self.feedback_data_path / "feedback.json"
        
        if not feedback_file.exists():
            return {"error": "No feedback data found"}
        
        with open(feedback_file, 'r') as f:
            feedback_data = json.load(f)
        
        if not feedback_data:
            return {"error": "No feedback data available"}
        
        # Convert to DataFrame for analysis
        df = pd.DataFrame(feedback_data)
        
        # Basic statistics
        stats = {
            'total_feedback': len(df),
            'average_rating': df['user_rating'].mean(),
            'model_preferences': df['selected_model'].value_counts().to_dict(),
            'rating_distribution': df['user_rating'].value_counts().sort_index().to_dict()
        }
        
        # Quality score analysis
        quality_cols = ['accuracy', 'relevance', 'clarity', 'completeness']
        quality_stats = {}
        for col in quality_cols:
            if col in df.columns:
                quality_stats[col] = {
                    'mean': df[col].mean(),
                    'std': df[col].std(),
                    'min': df[col].min(),
                    'max': df[col].max()
                }
        
        stats['quality_scores'] = quality_stats
        
        # Time-based trends
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            
            daily_stats = df.groupby('date').agg({
                'user_rating': 'mean',
                'selected_model': lambda x: x.value_counts().to_dict()
            }).to_dict()
            
            stats['daily_trends'] = daily_stats
        
        return stats
