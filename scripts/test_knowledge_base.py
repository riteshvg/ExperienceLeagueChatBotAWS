#!/usr/bin/env python3
"""
Test Bedrock Knowledge Base

This script tests the Knowledge Base with sample queries once it's created.
"""

import boto3
import json
import logging
from botocore.exceptions import ClientError
from config.settings import Settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeBaseTester:
    """Tests Bedrock Knowledge Base functionality."""
    
    def __init__(self):
        self.settings = Settings()
        self.bedrock_agent_client = boto3.client('bedrock-agent', region_name=self.settings.bedrock_region)
        self.bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=self.settings.bedrock_region)
        self.kb_id = None
        self.kb_arn = None
        
    def find_knowledge_base(self):
        """Find the Knowledge Base by name."""
        logger.info("🔍 Looking for Knowledge Base...")
        
        try:
            response = self.bedrock_agent_client.list_knowledge_bases()
            
            for kb in response['knowledgeBaseSummaries']:
                if kb['name'] == 'adobe-analytics-rag-kb':
                    self.kb_id = kb['knowledgeBaseId']
                    self.kb_arn = kb['knowledgeBaseArn']
                    logger.info(f"✅ Found Knowledge Base: {self.kb_id}")
                    return True
            
            logger.error("❌ Knowledge Base not found. Please create it first.")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to find Knowledge Base: {e}")
            return False
    
    def get_knowledge_base_status(self):
        """Get Knowledge Base status and details."""
        logger.info("📊 Getting Knowledge Base status...")
        
        try:
            response = self.bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=self.kb_id
            )
            
            kb = response['knowledgeBase']
            logger.info(f"✅ Knowledge Base Name: {kb['name']}")
            logger.info(f"✅ Knowledge Base Status: {kb['status']}")
            logger.info(f"✅ Created: {kb['createdAt']}")
            logger.info(f"✅ Updated: {kb['updatedAt']}")
            
            return kb['status'] == 'ACTIVE'
            
        except Exception as e:
            logger.error(f"❌ Failed to get Knowledge Base status: {e}")
            return False
    
    def get_data_sources(self):
        """Get data sources for the Knowledge Base."""
        logger.info("📚 Getting data sources...")
        
        try:
            response = self.bedrock_agent_client.list_data_sources(
                knowledgeBaseId=self.kb_id
            )
            
            for ds in response['dataSourceSummaries']:
                logger.info(f"✅ Data Source: {ds['name']}")
                logger.info(f"   Status: {ds['status']}")
                logger.info(f"   Updated: {ds['updatedAt']}")
                
                # Check ingestion status
                if ds['status'] == 'ACTIVE':
                    logger.info("   ✅ Data source is active and ready")
                else:
                    logger.warning(f"   ⚠️  Data source status: {ds['status']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to get data sources: {e}")
            return False
    
    def test_retrieval(self, query, max_results=3):
        """Test retrieval from Knowledge Base."""
        logger.info(f"🧪 Testing retrieval with query: '{query}'")
        
        try:
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={
                    "text": query
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": max_results
                    }
                }
            )
            
            results = response['retrievalResults']
            logger.info(f"✅ Retrieved {len(results)} results")
            
            for i, result in enumerate(results, 1):
                logger.info(f"   Result {i}:")
                logger.info(f"   Score: {result.get('score', 'N/A')}")
                logger.info(f"   Content: {result['content']['text'][:200]}...")
                if 'location' in result:
                    logger.info(f"   Source: {result['location']['s3Location']['uri']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve from Knowledge Base: {e}")
            return []
    
    def test_generation(self, query, context_results):
        """Test generation with retrieved context."""
        logger.info(f"🤖 Testing generation with query: '{query}'")
        
        try:
            # Prepare context from retrieval results
            context = "\n\n".join([result['content']['text'] for result in context_results])
            
            # Prepare messages for Claude
            messages = [
                {
                    "role": "user",
                    "content": f"Based on the following context about Adobe Analytics, please answer the question: {query}\n\nContext:\n{context}"
                }
            ]
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
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
            logger.info(f"   {answer}")
            
            return answer
            
        except Exception as e:
            logger.error(f"❌ Failed to generate answer: {e}")
            return None
    
    def run_test_queries(self):
        """Run a series of test queries."""
        logger.info("🧪 Running test queries...")
        
        test_queries = [
            "What is Adobe Analytics?",
            "How do I create custom events in Adobe Analytics?",
            "What are eVars and props?",
            "How do I set up Customer Journey Analytics?",
            "What is the difference between Adobe Analytics and Google Analytics?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"TEST QUERY {i}: {query}")
            logger.info(f"{'='*60}")
            
            # Test retrieval
            results = self.test_retrieval(query)
            
            if results:
                # Test generation
                answer = self.test_generation(query, results)
                
                if answer:
                    logger.info("✅ Query test completed successfully")
                else:
                    logger.error("❌ Generation failed")
            else:
                logger.error("❌ Retrieval failed")
    
    def run_complete_test(self):
        """Run complete Knowledge Base test."""
        logger.info("🚀 Starting Knowledge Base test...")
        logger.info("=" * 60)
        
        # Step 1: Find Knowledge Base
        if not self.find_knowledge_base():
            return False
        
        # Step 2: Check status
        if not self.get_knowledge_base_status():
            logger.error("❌ Knowledge Base is not active")
            return False
        
        # Step 3: Check data sources
        if not self.get_data_sources():
            return False
        
        # Step 4: Run test queries
        self.run_test_queries()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 Knowledge Base test completed!")
        
        return True

def main():
    """Main function."""
    try:
        tester = KnowledgeBaseTester()
        success = tester.run_complete_test()
        
        if success:
            print("\n🎉 Knowledge Base is working correctly!")
            print("\nNext steps:")
            print("1. Create RAG interface for production use")
            print("2. Deploy to your application")
            print("3. Monitor performance and usage")
        else:
            print("\n❌ Knowledge Base test failed!")
            print("Please check the Knowledge Base status in AWS console.")
            
    except Exception as e:
        logger.error(f"❌ Error testing Knowledge Base: {e}")

if __name__ == "__main__":
    main()
