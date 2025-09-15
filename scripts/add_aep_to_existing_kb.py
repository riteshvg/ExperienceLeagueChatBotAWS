#!/usr/bin/env python3
"""
Add Adobe Experience Platform to Existing Knowledge Base

This script adds AEP documentation as a new data source to your existing
knowledge-base-experienceleagechatbot knowledge base.
"""

import boto3
import json
import time
import logging
from botocore.exceptions import ClientError
from config.settings import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AEPDataSourceAdder:
    """Adds AEP data source to existing knowledge base."""
    
    def __init__(self):
        self.settings = Settings()
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.settings.bedrock_region)
        
        # Use your existing knowledge base
        self.kb_id = self.settings.bedrock_knowledge_base_id
        
        if not self.kb_id:
            raise ValueError("BEDROCK_KNOWLEDGE_BASE_ID not found in settings")
        
        logger.info(f"Using existing Knowledge Base: {self.kb_id}")
    
    def get_existing_data_sources(self):
        """Get list of existing data sources."""
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            existing_sources = []
            for ds in response['dataSourceSummaries']:
                existing_sources.append({
                    'name': ds['name'],
                    'id': ds['dataSourceId'],
                    'status': ds['status']
                })
            
            logger.info(f"Found {len(existing_sources)} existing data sources:")
            for source in existing_sources:
                logger.info(f"  - {source['name']} ({source['status']})")
            
            return existing_sources
            
        except Exception as e:
            logger.error(f"Failed to get existing data sources: {e}")
            return []
    
    def add_aep_data_source(self):
        """Add AEP data source to existing knowledge base."""
        logger.info("📚 Adding Adobe Experience Platform data source...")
        
        data_source_name = "adobe-experience-platform-docs"
        
        try:
            response = self.bedrock_agent_client.create_data_source(
                knowledgeBaseId=self.kb_id,
                name=data_source_name,
                description="Adobe Experience Platform documentation",
                dataSourceConfiguration={
                    "type": "S3",
                    "s3Configuration": {
                        "bucketArn": f"arn:aws:s3:::{self.settings.aws_s3_bucket}",
                        "inclusionPrefixes": ["adobe-docs/experience-platform/"]
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
            logger.info(f"✅ AEP data source created: {data_source_id}")
            
            # Check if dataSourceArn exists in response
            if 'dataSourceArn' in response['dataSource']:
                logger.info(f"✅ Data source ARN: {response['dataSource']['dataSourceArn']}")
            else:
                logger.info("✅ Data source created successfully")
            
            return data_source_id
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConflictException':
                logger.info("✅ AEP data source already exists")
                return self.get_data_source_id(data_source_name)
            else:
                logger.error(f"❌ Failed to create AEP data source: {e}")
                return None
        except Exception as e:
            logger.error(f"❌ Unexpected error creating AEP data source: {e}")
            return None
    
    def get_data_source_id(self, data_source_name):
        """Get data source ID by name."""
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            for ds in response['dataSourceSummaries']:
                if ds['name'] == data_source_name:
                    return ds['dataSourceId']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get data source ID for {data_source_name}: {e}")
            return None
    
    def start_ingestion_job(self, data_source_id):
        """Start ingestion job for AEP data source."""
        logger.info("🚀 Starting AEP document ingestion job...")
        
        try:
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=data_source_id
            )
            
            job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"✅ AEP ingestion job started: {job_id}")
            logger.info("⏳ Processing AEP documents... This may take 10-30 minutes.")
            
            return job_id
            
        except Exception as e:
            logger.error(f"❌ Failed to start AEP ingestion job: {e}")
            return None
    
    def add_aep_to_existing_kb(self):
        """Add AEP to existing knowledge base workflow."""
        logger.info("🚀 Adding Adobe Experience Platform to existing Knowledge Base")
        logger.info("=" * 70)
        
        # Step 1: Show existing data sources
        logger.info("📋 Current data sources:")
        existing_sources = self.get_existing_data_sources()
        
        # Step 2: Add AEP data source
        logger.info("📚 Adding AEP data source...")
        data_source_id = self.add_aep_data_source()
        
        if not data_source_id:
            logger.error("❌ Failed to add AEP data source")
            return False
        
        # Step 3: Start ingestion job
        logger.info("🚀 Starting AEP document ingestion...")
        job_id = self.start_ingestion_job(data_source_id)
        
        if not job_id:
            logger.error("❌ Failed to start AEP ingestion job")
            return False
        
        logger.info("=" * 70)
        logger.info("🎉 AEP successfully added to existing Knowledge Base!")
        logger.info(f"📋 Knowledge Base ID: {self.kb_id}")
        logger.info(f"📋 AEP Data Source ID: {data_source_id}")
        logger.info(f"📋 Ingestion Job ID: {job_id}")
        logger.info("")
        logger.info("📚 Your Knowledge Base now includes:")
        logger.info("  • Adobe Analytics documentation")
        logger.info("  • Customer Journey Analytics documentation")
        logger.info("  • Adobe Experience Platform documentation")
        logger.info("")
        logger.info("⏳ AEP documents are being processed. Check status in AWS console.")
        logger.info("🧪 Test AEP queries once ingestion completes!")
        
        return True

def main():
    """Main function."""
    try:
        adder = AEPDataSourceAdder()
        success = adder.add_aep_to_existing_kb()
        
        if success:
            print("\n🎉 AEP successfully added to your existing Knowledge Base!")
            print("\nYour chatbot now supports:")
            print("• Adobe Analytics")
            print("• Customer Journey Analytics") 
            print("• Adobe Experience Platform")
            print("\nNo new infrastructure needed - using your existing setup!")
        else:
            print("\n❌ Failed to add AEP to existing Knowledge Base!")
            print("Please check the logs above for error details.")
            
    except Exception as e:
        logger.error(f"❌ Error adding AEP to existing KB: {e}")

if __name__ == "__main__":
    main()
