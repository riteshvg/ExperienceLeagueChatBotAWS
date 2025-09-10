#!/usr/bin/env python3
"""
Validate Existing Knowledge Base

This script validates the existing Knowledge Base with ID NQTC3SRPZX.
"""

import boto3
import json
import logging
import sys
import os
from botocore.exceptions import ClientError

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExistingKnowledgeBaseValidator:
    """Validates the existing Knowledge Base."""
    
    def __init__(self):
        self.settings = Settings()
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.settings.bedrock_region)
        self.bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=self.settings.bedrock_region)
        self.kb_id = "NQTC3SRPZX"
        self.kb_arn = None
        
    def validate_iam_user(self):
        """Validate IAM user access."""
        logger.info("🔐 Validating IAM user access...")
        
        try:
            sts_client = boto3.client('sts')
            response = sts_client.get_caller_identity()
            
            user_arn = response['Arn']
            if 'user/' in user_arn:
                username = user_arn.split('user/')[-1]
                logger.info(f"✅ Using IAM user: {username}")
                logger.info(f"✅ Account ID: {response['Account']}")
                return True
            else:
                logger.warning(f"⚠️  Not using IAM user: {user_arn}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to validate IAM user: {e}")
            return False
    
    def validate_knowledge_base(self):
        """Validate Knowledge Base details."""
        logger.info(f"🔍 Validating Knowledge Base: {self.kb_id}")
        
        try:
            response = self.bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=self.kb_id
            )
            
            kb = response['knowledgeBase']
            self.kb_arn = kb['knowledgeBaseArn']
            
            logger.info(f"✅ Name: {kb['name']}")
            logger.info(f"✅ Description: {kb['description']}")
            logger.info(f"✅ Status: {kb['status']}")
            logger.info(f"✅ Created: {kb['createdAt']}")
            logger.info(f"✅ Updated: {kb['updatedAt']}")
            logger.info(f"✅ ARN: {self.kb_arn}")
            
            # Check vector configuration
            if 'vectorKnowledgeBaseConfiguration' in kb['knowledgeBaseConfiguration']:
                vector_config = kb['knowledgeBaseConfiguration']['vectorKnowledgeBaseConfiguration']
                logger.info(f"✅ Embedding Model: {vector_config['embeddingModelArn']}")
                
                if 'embeddingModelConfiguration' in vector_config:
                    embedding_config = vector_config['embeddingModelConfiguration']['bedrockEmbeddingModelConfiguration']
                    logger.info(f"✅ Embedding Dimensions: {embedding_config['dimensions']}")
                    logger.info(f"✅ Embedding Data Type: {embedding_config['embeddingDataType']}")
            
            # Check storage configuration
            storage_config = kb['storageConfiguration']
            logger.info(f"✅ Storage Type: {storage_config['type']}")
            
            if storage_config['type'] == 'S3_VECTORS':
                s3_config = storage_config['s3VectorsConfiguration']
                logger.info(f"✅ Index ARN: {s3_config['indexArn']}")
            
            return kb['status'] == 'ACTIVE'
            
        except Exception as e:
            logger.error(f"❌ Failed to validate Knowledge Base: {e}")
            return False
    
    def validate_data_sources(self):
        """Validate data sources."""
        logger.info("📚 Validating data sources...")
        
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            data_sources = response['dataSourceSummaries']
            logger.info(f"📊 Found {len(data_sources)} data source(s)")
            
            for ds in data_sources:
                logger.info(f"✅ Data Source: {ds['name']}")
                logger.info(f"   ID: {ds['dataSourceId']}")
                logger.info(f"   Status: {ds['status']}")
                logger.info(f"   Updated: {ds['updatedAt']}")
                
                if ds['status'] == 'AVAILABLE':
                    logger.info("   ✅ Data source is available")
                else:
                    logger.warning(f"   ⚠️  Data source status: {ds['status']}")
            
            return len(data_sources) > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to validate data sources: {e}")
            return False
    
    def get_data_source_details(self):
        """Get detailed data source information."""
        logger.info("📋 Getting data source details...")
        
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            if response['dataSourceSummaries']:
                data_source_id = response['dataSourceSummaries'][0]['dataSourceId']
                
                ds_response = self.bedrock_agent_client.get_data_source(
                    knowledgeBaseId=self.kb_id,
                    dataSourceId=data_source_id
                )
                
                ds = ds_response['dataSource']
                logger.info(f"✅ Data Source Name: {ds['name']}")
                logger.info(f"✅ Data Source Type: {ds['dataSourceConfiguration']['type']}")
                
                if ds['dataSourceConfiguration']['type'] == 'S3':
                    s3_config = ds['dataSourceConfiguration']['s3Configuration']
                    logger.info(f"✅ S3 Bucket: {s3_config['bucketArn']}")
                    if 'inclusionPrefixes' in s3_config:
                        logger.info(f"✅ Inclusion Prefixes: {s3_config['inclusionPrefixes']}")
                
                # Check vector ingestion configuration
                if 'vectorIngestionConfiguration' in ds:
                    vector_config = ds['vectorIngestionConfiguration']
                    if 'chunkingConfiguration' in vector_config:
                        chunking = vector_config['chunkingConfiguration']
                        logger.info(f"✅ Chunking Strategy: {chunking['chunkingStrategy']}")
                        
                        if chunking['chunkingStrategy'] == 'FIXED_SIZE':
                            fixed_size = chunking['fixedSizeChunkingConfiguration']
                            logger.info(f"✅ Max Tokens: {fixed_size['maxTokens']}")
                            logger.info(f"✅ Overlap Percentage: {fixed_size['overlapPercentage']}")
                
                return True
            else:
                logger.warning("⚠️  No data sources found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to get data source details: {e}")
            return False
    
    def test_retrieval(self, query="What is Adobe Analytics?"):
        """Test retrieval functionality using bedrock-runtime."""
        logger.info(f"🧪 Testing retrieval with query: '{query}'")
        
        try:
            # Use the retrieve API from bedrock-runtime
            response = self.bedrock_runtime_client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={
                    "text": query
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": 3
                    }
                }
            )
            
            results = response['retrievalResults']
            logger.info(f"✅ Retrieved {len(results)} results")
            
            if results:
                for i, result in enumerate(results, 1):
                    score = result.get('score', 'N/A')
                    content = result['content']['text'][:200] + "..."
                    logger.info(f"   Result {i} (Score: {score}): {content}")
                    
                    if 'location' in result:
                        location = result['location']
                        if 's3Location' in location:
                            s3_location = location['s3Location']
                            logger.info(f"   Source: {s3_location.get('uri', 'N/A')}")
                
                return True
            else:
                logger.warning("⚠️  No results retrieved")
                return False
                
        except Exception as e:
            logger.error(f"❌ Retrieval test failed: {e}")
            return False
    
    def test_generation(self, query="What is Adobe Analytics?"):
        """Test generation with retrieved context."""
        logger.info(f"🤖 Testing generation with query: '{query}'")
        
        try:
            # First retrieve context
            retrieval_response = self.bedrock_runtime_client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {"numberOfResults": 2}
                }
            )
            
            if not retrieval_response['retrievalResults']:
                logger.warning("⚠️  No context retrieved for generation test")
                return False
            
            # Prepare context
            context = "\n\n".join([
                result['content']['text'] for result in retrieval_response['retrievalResults']
            ])
            
            # Generate answer using Claude
            messages = [{
                "role": "user",
                "content": f"Based on the following context about Adobe Analytics, please answer: {query}\n\nContext:\n{context}"
            }]
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "messages": messages
            })
            
            response = self.bedrock_runtime_client.invoke_model(
                modelId=self.settings.bedrock_model_id,
                body=body,
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            answer = response_body['content'][0]['text']
            
            logger.info("✅ Generated answer:")
            logger.info(f"   {answer[:300]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Generation test failed: {e}")
            return False
    
    def run_validation_tests(self):
        """Run comprehensive validation tests."""
        logger.info("🚀 Starting Knowledge Base validation...")
        logger.info("=" * 60)
        
        tests = []
        
        # Test 1: IAM User
        tests.append(("IAM User Access", self.validate_iam_user()))
        
        # Test 2: Knowledge Base Details
        tests.append(("Knowledge Base Details", self.validate_knowledge_base()))
        
        # Test 3: Data Sources
        tests.append(("Data Sources", self.validate_data_sources()))
        
        # Test 4: Data Source Details
        tests.append(("Data Source Details", self.get_data_source_details()))
        
        # Test 5: Retrieval
        tests.append(("Retrieval Test", self.test_retrieval()))
        
        # Test 6: Generation
        tests.append(("Generation Test", self.test_generation()))
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 VALIDATION SUMMARY")
        logger.info("=" * 60)
        
        passed = 0
        total = len(tests)
        
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} {test_name}")
            if result:
                passed += 1
        
        logger.info(f"\n📈 Results: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All validation tests passed! Knowledge Base is working correctly.")
        else:
            logger.warning(f"⚠️  {total - passed} test(s) failed. Please check the issues above.")
        
        return passed == total

def main():
    """Main function."""
    try:
        validator = ExistingKnowledgeBaseValidator()
        success = validator.run_validation_tests()
        
        if success:
            print("\n🎉 Knowledge Base validation completed successfully!")
            print(f"\n📋 Knowledge Base Details:")
            print(f"   ID: NQTC3SRPZX")
            print(f"   Name: knowledge-base-experienceleagechatbot")
            print(f"   Status: ACTIVE")
            print(f"   Region: us-east-1")
            print("\nYour RAG system is ready to use!")
        else:
            print("\n❌ Knowledge Base validation failed!")
            print("Please check the issues above and fix them.")
            
    except Exception as e:
        logger.error(f"❌ Error during validation: {e}")

if __name__ == "__main__":
    main()
