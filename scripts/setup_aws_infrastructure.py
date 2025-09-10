#!/usr/bin/env python3
"""
AWS Infrastructure Setup Script for Adobe Analytics RAG System

This script sets up the necessary AWS infrastructure including:
- S3 bucket for Adobe documentation storage
- Proper folder structure for different Adobe services
- Bucket policies for Bedrock access
- Lifecycle policies for cost optimization
- IAM roles and policies for cross-service access

Usage:
    python scripts/setup_aws_infrastructure.py

Environment Variables:
    AWS_REGION: AWS region (default: us-east-1)
    S3_BUCKET_NAME: S3 bucket name (default: adobe-analytics-rag-docs-{random})
    BEDROCK_KNOWLEDGE_BASE_ROLE_NAME: IAM role name for Bedrock (default: AdobeAnalyticsRAGBedrockRole)
    S3_ACCESS_ROLE_NAME: IAM role name for S3 access (default: AdobeAnalyticsRAGS3Role)
"""

import os
import sys
import json
import logging
import random
import string
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config


class AWSInfrastructureSetup:
    """Handles AWS infrastructure setup for Adobe Analytics RAG system."""
    
    def __init__(self):
        """Initialize the AWS infrastructure setup."""
        self.setup_logging()
        self.load_configuration()
        self.initialize_aws_clients()
        
    def setup_logging(self):
        """Configure logging for the script."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('aws_setup.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_configuration(self):
        """Load configuration from environment variables."""
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.bedrock_role_name = os.getenv('BEDROCK_KNOWLEDGE_BASE_ROLE_NAME', 'AdobeAnalyticsRAGBedrockRole')
        self.s3_access_role_name = os.getenv('S3_ACCESS_ROLE_NAME', 'AdobeAnalyticsRAGS3Role')
        
        # Generate bucket name if not provided
        if not self.bucket_name:
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            self.bucket_name = f"adobe-analytics-rag-docs-{random_suffix}"
            
        self.logger.info(f"Configuration loaded - Region: {self.region}, Bucket: {self.bucket_name}")
        
    def initialize_aws_clients(self):
        """Initialize AWS service clients."""
        try:
            config = Config(region_name=self.region)
            self.s3_client = boto3.client('s3', config=config)
            self.iam_client = boto3.client('iam', config=config)
            self.bedrock_client = boto3.client('bedrock', config=config)
            self.sts_client = boto3.client('sts', config=config)
            
            # Verify AWS credentials
            self.sts_client.get_caller_identity()
            self.logger.info("AWS clients initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS clients: {e}")
            raise
            
    def create_s3_bucket(self) -> bool:
        """Create S3 bucket for Adobe documentation storage."""
        try:
            # Check if bucket already exists
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                self.logger.info(f"S3 bucket '{self.bucket_name}' already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != '404':
                    raise
                    
            # Create bucket
            if self.region == 'us-east-1':
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
                
            self.logger.info(f"S3 bucket '{self.bucket_name}' created successfully")
            
            # Enable versioning
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Block public access
            self.s3_client.put_public_access_block(
                Bucket=self.bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            self.logger.info("S3 bucket configured with versioning and public access blocking")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create S3 bucket: {e}")
            return False
            
    def create_folder_structure(self) -> bool:
        """Create the required folder structure in S3 bucket."""
        try:
            folders = [
                'adobe-docs/adobe-analytics/',
                'adobe-docs/customer-journey-analytics/',
                'adobe-docs/analytics-apis/',
                'adobe-docs/cja-apis/'
            ]
            
            for folder in folders:
                # Create folder by uploading an empty object
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=folder,
                    Body=b'',
                    ContentType='application/x-directory'
                )
                self.logger.info(f"Created folder: {folder}")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create folder structure: {e}")
            return False
            
    def create_iam_roles(self) -> Tuple[bool, bool]:
        """Create IAM roles for S3 and Bedrock access."""
        s3_role_created = self._create_s3_access_role()
        bedrock_role_created = self._create_bedrock_role()
        return s3_role_created, bedrock_role_created
        
    def _create_s3_access_role(self) -> bool:
        """Create IAM role for S3 access."""
        try:
            # Check if role already exists
            try:
                self.iam_client.get_role(RoleName=self.s3_access_role_name)
                self.logger.info(f"IAM role '{self.s3_access_role_name}' already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise
                    
            # Trust policy for the role
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "bedrock.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # Create the role
            self.iam_client.create_role(
                RoleName=self.s3_access_role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for Adobe Analytics RAG S3 access"
            )
            
            # Attach S3 policy
            s3_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{self.bucket_name}",
                            f"arn:aws:s3:::{self.bucket_name}/*"
                        ]
                    }
                ]
            }
            
            policy_name = f"{self.s3_access_role_name}Policy"
            self.iam_client.put_role_policy(
                RoleName=self.s3_access_role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(s3_policy)
            )
            
            self.logger.info(f"IAM role '{self.s3_access_role_name}' created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create S3 access role: {e}")
            return False
            
    def _create_bedrock_role(self) -> bool:
        """Create IAM role for Bedrock Knowledge Base access."""
        try:
            # Check if role already exists
            try:
                self.iam_client.get_role(RoleName=self.bedrock_role_name)
                self.logger.info(f"IAM role '{self.bedrock_role_name}' already exists")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise
                    
            # Trust policy for Bedrock
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "bedrock.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # Create the role
            self.iam_client.create_role(
                RoleName=self.bedrock_role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Role for Adobe Analytics RAG Bedrock Knowledge Base"
            )
            
            # Attach Bedrock and S3 policies
            bedrock_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "bedrock:CreateKnowledgeBase",
                            "bedrock:GetKnowledgeBase",
                            "bedrock:UpdateKnowledgeBase",
                            "bedrock:DeleteKnowledgeBase",
                            "bedrock:ListKnowledgeBases",
                            "bedrock:CreateDataSource",
                            "bedrock:GetDataSource",
                            "bedrock:UpdateDataSource",
                            "bedrock:DeleteDataSource",
                            "bedrock:ListDataSources",
                            "bedrock:CreateVectorIndex",
                            "bedrock:GetVectorIndex",
                            "bedrock:UpdateVectorIndex",
                            "bedrock:DeleteVectorIndex",
                            "bedrock:ListVectorIndexes"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{self.bucket_name}",
                            f"arn:aws:s3:::{self.bucket_name}/*"
                        ]
                    }
                ]
            }
            
            policy_name = f"{self.bedrock_role_name}Policy"
            self.iam_client.put_role_policy(
                RoleName=self.bedrock_role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(bedrock_policy)
            )
            
            self.logger.info(f"IAM role '{self.bedrock_role_name}' created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create Bedrock role: {e}")
            return False
            
    def configure_bucket_policies(self) -> bool:
        """Configure bucket policies for Bedrock access."""
        try:
            # Get account ID
            account_id = self.sts_client.get_caller_identity()['Account']
            
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "BedrockAccess",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": f"arn:aws:iam::{account_id}:role/{self.bedrock_role_name}"
                        },
                        "Action": [
                            "s3:GetObject",
                            "s3:ListBucket"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{self.bucket_name}",
                            f"arn:aws:s3:::{self.bucket_name}/*"
                        ]
                    }
                ]
            }
            
            self.s3_client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            
            self.logger.info("Bucket policy configured for Bedrock access")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure bucket policies: {e}")
            return False
            
    def setup_lifecycle_policies(self) -> bool:
        """Set up S3 lifecycle policies for cost optimization."""
        try:
            lifecycle_configuration = {
                'Rules': [
                    {
                        'ID': 'AdobeDocsLifecycle',
                        'Status': 'Enabled',
                        'Filter': {
                            'Prefix': 'adobe-docs/'
                        },
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': 90,
                                'StorageClass': 'GLACIER'
                            },
                            {
                                'Days': 365,
                                'StorageClass': 'DEEP_ARCHIVE'
                            }
                        ],
                        'NoncurrentVersionTransitions': [
                            {
                                'NoncurrentDays': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'NoncurrentDays': 60,
                                'StorageClass': 'GLACIER'
                            }
                        ],
                        'NoncurrentVersionExpiration': {
                            'NoncurrentDays': 90
                        }
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_configuration
            )
            
            self.logger.info("Lifecycle policies configured for cost optimization")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to setup lifecycle policies: {e}")
            return False
            
    def verify_setup(self) -> bool:
        """Verify that all components were set up correctly."""
        try:
            # Verify S3 bucket
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            # Verify folder structure
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='adobe-docs/',
                Delimiter='/'
            )
            
            expected_folders = [
                'adobe-docs/adobe-analytics/',
                'adobe-docs/customer-journey-analytics/',
                'adobe-docs/analytics-apis/',
                'adobe-docs/cja-apis/'
            ]
            
            created_folders = [obj['Prefix'] for obj in response.get('CommonPrefixes', [])]
            missing_folders = set(expected_folders) - set(created_folders)
            
            if missing_folders:
                self.logger.warning(f"Missing folders: {missing_folders}")
                return False
                
            # Verify IAM roles
            self.iam_client.get_role(RoleName=self.s3_access_role_name)
            self.iam_client.get_role(RoleName=self.bedrock_role_name)
            
            self.logger.info("All components verified successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return False
            
    def run_setup(self) -> bool:
        """Run the complete AWS infrastructure setup."""
        self.logger.info("Starting AWS infrastructure setup...")
        
        try:
            # Create S3 bucket
            if not self.create_s3_bucket():
                return False
                
            # Create folder structure
            if not self.create_folder_structure():
                return False
                
            # Create IAM roles
            s3_role_created, bedrock_role_created = self.create_iam_roles()
            if not (s3_role_created and bedrock_role_created):
                return False
                
            # Configure bucket policies (optional - can be done later)
            try:
                if not self.configure_bucket_policies():
                    self.logger.warning("Bucket policy configuration failed, but continuing...")
            except Exception as e:
                self.logger.warning(f"Bucket policy configuration failed: {e}, but continuing...")
                
            # Setup lifecycle policies
            if not self.setup_lifecycle_policies():
                return False
                
            # Verify setup
            if not self.verify_setup():
                return False
                
            self.logger.info("AWS infrastructure setup completed successfully!")
            self._print_summary()
            return True
            
        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            return False
            
    def _print_summary(self):
        """Print a summary of the created resources."""
        account_id = self.sts_client.get_caller_identity()['Account']
        
        print("\n" + "="*60)
        print("AWS INFRASTRUCTURE SETUP SUMMARY")
        print("="*60)
        print(f"S3 Bucket: {self.bucket_name}")
        print(f"Region: {self.region}")
        print(f"Account ID: {account_id}")
        print("\nCreated Resources:")
        print(f"  - S3 Bucket: {self.bucket_name}")
        print(f"  - IAM Role (S3): {self.s3_access_role_name}")
        print(f"  - IAM Role (Bedrock): {self.bedrock_role_name}")
        print("\nFolder Structure:")
        print("  - adobe-docs/adobe-analytics/")
        print("  - adobe-docs/customer-journey-analytics/")
        print("  - adobe-docs/analytics-apis/")
        print("  - adobe-docs/cja-apis/")
        print("\nNext Steps:")
        print("1. Upload your Adobe documentation to the appropriate folders")
        print("2. Create a Bedrock Knowledge Base using the S3 data source")
        print("3. Configure your RAG application to use the Knowledge Base")
        print("="*60)


def main():
    """Main function to run the AWS infrastructure setup."""
    try:
        setup = AWSInfrastructureSetup()
        success = setup.run_setup()
        
        if success:
            print("\n✅ AWS infrastructure setup completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ AWS infrastructure setup failed!")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
