"""
Auto-retraining pipeline configuration.
Uses environment variables for real cloud integration.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AUTO_RETRAINING_CONFIG = {
    'retraining_threshold': 3,   # Minimum feedback count (TESTING MODE)
    'quality_threshold': 3,      # Minimum quality score (TESTING MODE)
    'retraining_cooldown': 60,   # 1 minute cooldown (TESTING MODE)
    
    # AWS Configuration from environment
    'aws_region': os.getenv('AWS_DEFAULT_REGION', 'us-east-1'),
    's3_bucket': os.getenv('RETRAINING_S3_BUCKET', 'your-retraining-bucket'),
    'bedrock_role_arn': os.getenv('BEDROCK_ROLE_ARN', 'arn:aws:iam::YOUR_ACCOUNT:role/BedrockCustomModelRole'),
    'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
    'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
    
    # GCP Configuration from environment
    'gcp_project_id': os.getenv('GCP_PROJECT_ID', 'your-gcp-project'),
    'gcs_bucket': os.getenv('RETRAINING_GCS_BUCKET', 'your-retraining-bucket'),
    'google_application_credentials': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
    
    # Feature flags
    'enable_claude_retraining': os.getenv('ENABLE_CLAUDE_RETRAINING', 'true').lower() == 'true',
    'enable_gemini_retraining': os.getenv('ENABLE_GEMINI_RETRAINING', 'true').lower() == 'true',
    
    # Monitoring and logging
    'enable_detailed_logging': True,
    'save_training_data_locally': True,
    'local_data_path': './training_data'
}
