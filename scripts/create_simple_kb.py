#!/usr/bin/env python3
"""
Create Simple Bedrock Knowledge Base

This script creates a Bedrock Knowledge Base using a simpler approach.
"""

import boto3
import json
import time
import logging
from botocore.exceptions import ClientError
from config.settings import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleKnowledgeBaseCreator:
    """Creates a simple Bedrock Knowledge Base."""
    
    def __init__(self):
        self.settings = Settings()
        self.bedrock_client = boto3.client('bedrock', region_name=self.settings.bedrock_region)
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.settings.bedrock_region)
        
        # Knowledge Base configuration
        self.kb_name = "adobe-analytics-rag-kb"
        self.kb_description = "Knowledge Base for Adobe Analytics and Customer Journey Analytics documentation"
        self.kb_role_arn = None
        self.kb_id = None
        
    def get_account_id(self):
        """Get AWS account ID."""
        try:
            sts_client = boto3.client('sts')
            response = sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            logger.error(f"❌ Failed to get account ID: {e}")
            return None
    
    def create_iam_role(self):
        """Create IAM role for Knowledge Base."""
        logger.info("🔧 Creating IAM role for Knowledge Base...")
        
        iam_client = boto3.client('iam')
        role_name = "BedrockKnowledgeBaseRole"
        
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
        
        # Permissions for S3 and Bedrock
        permissions_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{self.settings.aws_s3_bucket_name}",
                        f"arn:aws:s3:::{self.settings.aws_s3_bucket_name}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel"
                    ],
                    "Resource": [
                        f"arn:aws:bedrock:{self.settings.bedrock_region}::foundation-model/{self.settings.bedrock_embedding_model_id}"
                    ]
                }
            ]
        }
        
        try:
            # Create role
            try:
                response = iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description="Role for Bedrock Knowledge Base to access S3 and Bedrock models"
                )
                logger.info(f"✅ Created IAM role: {role_name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityAlreadyExists':
                    logger.info(f"✅ IAM role already exists: {role_name}")
                else:
                    raise
            
            # Attach permissions policy
            try:
                iam_client.put_role_policy(
                    RoleName=role_name,
                    PolicyName="BedrockKnowledgeBasePolicy",
                    PolicyDocument=json.dumps(permissions_policy)
                )
                logger.info("✅ Attached permissions policy to role")
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityAlreadyExists':
                    logger.info("✅ Permissions policy already attached")
                else:
                    raise
            
            # Get role ARN
            response = iam_client.get_role(RoleName=role_name)
            self.kb_role_arn = response['Role']['Arn']
            logger.info(f"✅ IAM role ARN: {self.kb_role_arn}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create IAM role: {e}")
            return False
    
    def check_existing_knowledge_base(self):
        """Check if Knowledge Base already exists."""
        logger.info("🔍 Checking for existing Knowledge Base...")
        
        try:
            response = self.bedrock_agent_client.list_knowledge_bases()
            
            for kb in response['knowledgeBaseSummaries']:
                if kb['name'] == self.kb_name:
                    self.kb_id = kb['knowledgeBaseId']
                    logger.info(f"✅ Found existing Knowledge Base: {self.kb_id}")
                    return True
            
            logger.info("ℹ️  No existing Knowledge Base found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to check existing Knowledge Base: {e}")
            return False
    
    def create_knowledge_base(self):
        """Create the Knowledge Base."""
        logger.info("🤖 Creating Bedrock Knowledge Base...")
        
        try:
            # Use Pinecone as vector store (simpler than OpenSearch)
            response = self.bedrock_agent_client.create_knowledge_base(
                name=self.kb_name,
                description=self.kb_description,
                roleArn=self.kb_role_arn,
                knowledgeBaseConfiguration={
                    "type": "VECTOR",
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": f"arn:aws:bedrock:{self.settings.bedrock_region}::foundation-model/{self.settings.bedrock_embedding_model_id}"
                    }
                },
                storageConfiguration={
                    "type": "PINECONE",
                    "pineconeConfiguration": {
                        "connectionString": "https://adobe-analytics-rag-123456.svc.us-east-1.pinecone.io",
                        "credentialsSecretArn": f"arn:aws:secretsmanager:{self.settings.bedrock_region}:{self.get_account_id()}:secret:pinecone-credentials",
                        "fieldMapping": {
                            "vectorField": "values",
                            "textField": "text",
                            "metadataField": "metadata"
                        },
                        "namespace": "adobe-analytics"
                    }
                }
            )
            
            self.kb_id = response['knowledgeBase']['knowledgeBaseId']
            logger.info(f"✅ Knowledge Base created: {self.kb_id}")
            logger.info(f"✅ Knowledge Base ARN: {response['knowledgeBase']['knowledgeBaseArn']}")
            
            return True
            
        except ClientError as e:
            logger.error(f"❌ Failed to create Knowledge Base: {e}")
            logger.error(f"Error details: {e.response}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error creating Knowledge Base: {e}")
            return False
    
    def create_data_source(self):
        """Create data source for the Knowledge Base."""
        logger.info("📚 Creating data source for Knowledge Base...")
        
        data_source_name = "adobe-analytics-docs"
        
        try:
            response = self.bedrock_agent_client.create_data_source(
                knowledgeBaseId=self.kb_id,
                name=data_source_name,
                description="Adobe Analytics and Customer Journey Analytics documentation",
                dataSourceConfiguration={
                    "type": "S3",
                    "s3Configuration": {
                        "bucketArn": f"arn:aws:s3:::{self.settings.aws_s3_bucket_name}",
                        "inclusionPrefixes": ["adobe-docs/"]
                    }
                },
                vectorIngestionConfiguration={
                    "chunkingConfiguration": {
                        "chunkingStrategy": "FIXED_SIZE",
                        "fixedSizeChunkingConfiguration": {
                            "maxTokens": 1000,
                            "overlapPercentage": 20
                        }
                    }
                }
            )
            
            data_source_id = response['dataSource']['dataSourceId']
            logger.info(f"✅ Data source created: {data_source_id}")
            logger.info(f"✅ Data source ARN: {response['dataSource']['dataSourceArn']}")
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConflictException':
                logger.info("✅ Data source already exists")
                return True
            else:
                logger.error(f"❌ Failed to create data source: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected error creating data source: {e}")
            return False
    
    def start_ingestion_job(self):
        """Start ingestion job to process documents."""
        logger.info("🚀 Starting document ingestion job...")
        
        try:
            data_source_id = self.get_data_source_id()
            if not data_source_id:
                logger.error("❌ Could not find data source ID")
                return None
            
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=data_source_id
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"✅ Ingestion job started: {job_id}")
            logger.info("⏳ Processing documents... This may take 10-30 minutes.")
            
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start ingestion job: {e}")
            return None
    
    def get_data_source_id(self):
        """Get data source ID."""
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            for ds in response['dataSourceSummaries']:
                if ds['name'] == "adobe-analytics-docs":
                    return ds['dataSourceId']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get data source ID: {e}")
            return None
    
    def create_knowledge_base_workflow(self):
        """Run the complete Knowledge Base creation workflow."""
        logger.info("🚀 Starting Knowledge Base creation workflow...")
        logger.info("=" * 60)
        
        # Step 1: Check for existing Knowledge Base
        if self.check_existing_knowledge_base():
            logger.info("✅ Using existing Knowledge Base")
        else:
            # Step 2: Create IAM role
            if not self.create_iam_role():
                logger.error("❌ Failed to create IAM role. Exiting.")
                return False
            
            # Step 3: Create Knowledge Base
            if not self.create_knowledge_base():
                logger.error("❌ Failed to create Knowledge Base. Exiting.")
                return False
        
        # Step 4: Create data source
        if not self.create_data_source():
            logger.error("❌ Failed to create data source. Exiting.")
            return False
        
        # Step 5: Start ingestion job
        job_id = self.start_ingestion_job()
        if not job_id:
            logger.error("❌ Failed to start ingestion job. Exiting.")
            return False
        
        logger.info("=" * 60)
        logger.info("🎉 Knowledge Base creation workflow completed!")
        logger.info(f"📋 Knowledge Base ID: {self.kb_id}")
        logger.info(f"📋 Ingestion Job ID: {job_id}")
        logger.info("⏳ Documents are being processed. Check status in AWS console.")
        
        return True

def main():
    """Main function."""
    try:
        creator = SimpleKnowledgeBaseCreator()
        success = creator.create_knowledge_base_workflow()
        
        if success:
            print("\n🎉 Knowledge Base creation workflow completed successfully!")
            print("\nNext steps:")
            print("1. Wait for ingestion job to complete (10-30 minutes)")
            print("2. Test the Knowledge Base with sample queries")
            print("3. Create RAG interface for querying")
        else:
            print("\n❌ Knowledge Base creation workflow failed!")
            
    except Exception as e:
        logger.error(f"❌ Error in Knowledge Base creation: {e}")

if __name__ == "__main__":
    main()
