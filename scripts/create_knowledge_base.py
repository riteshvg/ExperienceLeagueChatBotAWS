#!/usr/bin/env python3
"""
Create Bedrock Knowledge Base

This script creates a Bedrock Knowledge Base for the Adobe Analytics RAG system.
"""

import boto3
import json
import time
import logging
from botocore.exceptions import ClientError
from config.settings import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeBaseCreator:
    """Creates and manages Bedrock Knowledge Base."""
    
    def __init__(self):
        self.settings = Settings()
        self.bedrock_client = boto3.client('bedrock', region_name=self.settings.bedrock_region)
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.settings.bedrock_region)
        
        # Knowledge Base configuration
        self.kb_name = "adobe-analytics-rag-kb"
        self.kb_description = "Knowledge Base for Adobe Analytics and Customer Journey Analytics documentation"
        self.kb_role_arn = None
        self.kb_id = None
        
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
    
    def create_knowledge_base(self):
        """Create the Knowledge Base."""
        logger.info("🤖 Creating Bedrock Knowledge Base...")
        
        try:
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
                    "type": "OPENSEARCH_SERVERLESS",
                    "opensearchServerlessConfiguration": {
                        "collectionArn": f"arn:aws:aoss:{self.settings.bedrock_region}:{self.get_account_id()}:collection/adobe-analytics-rag",
                        "vectorIndexName": "adobe-analytics-rag-index",
                        "fieldMapping": {
                            "vectorField": "bedrock-knowledge-base-default-vector",
                            "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
                            "metadataField": "AMAZON_BEDROCK_METADATA"
                        }
                    }
                }
            )
            
            self.kb_id = response['knowledgeBase']['knowledgeBaseId']
            logger.info(f"✅ Knowledge Base created: {self.kb_id}")
            logger.info(f"✅ Knowledge Base ARN: {response['knowledgeBase']['knowledgeBaseArn']}")
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConflictException':
                logger.info("✅ Knowledge Base already exists, getting existing ID...")
                return self.get_existing_knowledge_base()
            else:
                logger.error(f"❌ Failed to create Knowledge Base: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected error creating Knowledge Base: {e}")
            return False
    
    def get_existing_knowledge_base(self):
        """Get existing Knowledge Base ID."""
        try:
            response = self.bedrock_agent_client.list_knowledge_bases()
            
            for kb in response['knowledgeBaseSummaries']:
                if kb['name'] == self.kb_name:
                    self.kb_id = kb['knowledgeBaseId']
                    logger.info(f"✅ Found existing Knowledge Base: {self.kb_id}")
                    return True
            
            logger.error("❌ Knowledge Base not found")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to get existing Knowledge Base: {e}")
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
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.get_data_source_id()
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
    
    def get_account_id(self):
        """Get AWS account ID."""
        try:
            sts_client = boto3.client('sts')
            response = sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            logger.error(f"❌ Failed to get account ID: {e}")
            return None
    
    def create_knowledge_base_workflow(self):
        """Run the complete Knowledge Base creation workflow."""
        logger.info("🚀 Starting Knowledge Base creation workflow...")
        logger.info("=" * 60)
        
        # Step 1: Create IAM role
        if not self.create_iam_role():
            logger.error("❌ Failed to create IAM role. Exiting.")
            return False
        
        # Step 2: Create Knowledge Base
        if not self.create_knowledge_base():
            logger.error("❌ Failed to create Knowledge Base. Exiting.")
            return False
        
        # Step 3: Create data source
        if not self.create_data_source():
            logger.error("❌ Failed to create data source. Exiting.")
            return False
        
        # Step 4: Start ingestion job
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
        creator = KnowledgeBaseCreator()
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
