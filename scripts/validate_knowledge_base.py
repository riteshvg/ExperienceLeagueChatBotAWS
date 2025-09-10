#!/usr/bin/env python3
"""
Validate Knowledge Base Setup

This script validates that the Knowledge Base was created correctly and is working.
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

class KnowledgeBaseValidator:
    """Validates Knowledge Base setup and functionality."""
    
    def __init__(self):
        self.settings = Settings()
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.settings.bedrock_region)
        self.bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=self.settings.bedrock_region)
        self.kb_id = None
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
    
    def find_knowledge_base(self):
        """Find and validate Knowledge Base."""
        logger.info("🔍 Looking for Knowledge Base...")
        
        try:
            response = self.bedrock_agent_client.list_knowledge_bases()
            
            knowledge_bases = response['knowledgeBaseSummaries']
            logger.info(f"📊 Found {len(knowledge_bases)} Knowledge Base(s)")
            
            # Look for our specific Knowledge Base
            for kb in knowledge_bases:
                if 'adobe-analytics' in kb['name'].lower():
                    self.kb_id = kb['knowledgeBaseId']
                    self.kb_arn = kb['knowledgeBaseArn']
                    logger.info(f"✅ Found Knowledge Base: {kb['name']}")
                    logger.info(f"✅ Knowledge Base ID: {self.kb_id}")
                    logger.info(f"✅ Status: {kb['status']}")
                    logger.info(f"✅ Created: {kb['createdAt']}")
                    return True
            
            logger.error("❌ Adobe Analytics Knowledge Base not found")
            logger.info("Available Knowledge Bases:")
            for kb in knowledge_bases:
                logger.info(f"   - {kb['name']} ({kb['status']})")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to find Knowledge Base: {e}")
            return False
    
    def validate_knowledge_base_details(self):
        """Get detailed Knowledge Base information."""
        logger.info("📋 Getting Knowledge Base details...")
        
        try:
            response = self.bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=self.kb_id
            )
            
            kb = response['knowledgeBase']
            logger.info(f"✅ Name: {kb['name']}")
            logger.info(f"✅ Description: {kb['description']}")
            logger.info(f"✅ Status: {kb['status']}")
            logger.info(f"✅ Role ARN: {kb['roleArn']}")
            
            # Check vector configuration
            if 'vectorKnowledgeBaseConfiguration' in kb['knowledgeBaseConfiguration']:
                vector_config = kb['knowledgeBaseConfiguration']['vectorKnowledgeBaseConfiguration']
                logger.info(f"✅ Embedding Model: {vector_config['embeddingModelArn']}")
            
            # Check storage configuration
            storage_config = kb['storageConfiguration']
            logger.info(f"✅ Storage Type: {storage_config['type']}")
            
            return kb['status'] == 'ACTIVE'
            
        except Exception as e:
            logger.error(f"❌ Failed to get Knowledge Base details: {e}")
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
                logger.info(f"   Status: {ds['status']}")
                logger.info(f"   Type: {ds['dataSourceConfiguration']['type']}")
                logger.info(f"   Updated: {ds['updatedAt']}")
                
                if ds['status'] == 'ACTIVE':
                    logger.info("   ✅ Data source is active")
                else:
                    logger.warning(f"   ⚠️  Data source status: {ds['status']}")
            
            return len(data_sources) > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to validate data sources: {e}")
            return False
    
    def test_retrieval(self, query="What is Adobe Analytics?"):
        """Test retrieval functionality."""
        logger.info(f"🧪 Testing retrieval with query: '{query}'")
        
        try:
            response = self.bedrock_agent_client.retrieve(
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
                    content = result['content']['text'][:150] + "..."
                    logger.info(f"   Result {i} (Score: {score}): {content}")
                
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
            retrieval_response = self.bedrock_agent_client.retrieve(
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
            
            # Generate answer
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
            logger.info(f"   {answer[:200]}...")
            
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
        
        # Test 2: Find Knowledge Base
        tests.append(("Knowledge Base Found", self.find_knowledge_base()))
        
        if self.kb_id:
            # Test 3: Knowledge Base Details
            tests.append(("Knowledge Base Details", self.validate_knowledge_base_details()))
            
            # Test 4: Data Sources
            tests.append(("Data Sources", self.validate_data_sources()))
            
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
        validator = KnowledgeBaseValidator()
        success = validator.run_validation_tests()
        
        if success:
            print("\n🎉 Knowledge Base validation completed successfully!")
            print("\nYour RAG system is ready to use!")
            print("\nNext steps:")
            print("1. Create a user interface for querying")
            print("2. Deploy to production")
            print("3. Monitor performance and usage")
        else:
            print("\n❌ Knowledge Base validation failed!")
            print("Please check the issues above and fix them.")
            
    except Exception as e:
        logger.error(f"❌ Error during validation: {e}")

if __name__ == "__main__":
    main()
