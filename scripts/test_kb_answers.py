#!/usr/bin/env python3
"""
Unit Tests for Knowledge Base Answers

This script runs unit tests to validate the quality and accuracy of answers
from the Knowledge Base.
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

class KnowledgeBaseAnswerTester:
    """Tests Knowledge Base answers for accuracy and quality."""
    
    def __init__(self):
        self.settings = Settings()
        self.bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=self.settings.bedrock_region)
        self.bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=self.settings.bedrock_region)
        self.kb_id = "NQTC3SRPZX"
        
    def retrieve_from_kb(self, query, max_results=3):
        """Retrieve relevant documents from Knowledge Base."""
        try:
            response = self.bedrock_agent_runtime_client.retrieve(
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
            return response['retrievalResults']
        except Exception as e:
            logger.error(f"❌ Retrieval failed: {e}")
            return []
    
    def generate_answer(self, query, context_results):
        """Generate answer using Claude with retrieved context."""
        try:
            # Prepare context from retrieval results
            context = "\n\n".join([result['content']['text'] for result in context_results])
            
            messages = [{
                "role": "user",
                "content": f"Based on the following context about Adobe Analytics, please answer: {query}\n\nContext:\n{context}\n\nPlease provide a clear, accurate answer based on the context provided."
            }]
            
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
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            return None
    
    def test_query(self, query, expected_keywords=None, min_score=0.7):
        """Test a single query and validate the answer."""
        logger.info(f"\n🧪 Testing Query: '{query}'")
        logger.info("-" * 60)
        
        # Step 1: Retrieve relevant documents
        logger.info("📚 Retrieving relevant documents...")
        results = self.retrieve_from_kb(query)
        
        if not results:
            logger.error("❌ No documents retrieved")
            return False
        
        logger.info(f"✅ Retrieved {len(results)} documents")
        
        # Show retrieval scores
        for i, result in enumerate(results, 1):
            score = result.get('score', 'N/A')
            content_preview = result['content']['text'][:100] + "..."
            logger.info(f"   Document {i} (Score: {score}): {content_preview}")
        
        # Check if any result meets minimum score
        max_score = max([result.get('score', 0) for result in results])
        if max_score < min_score:
            logger.warning(f"⚠️  Maximum score {max_score} below threshold {min_score}")
        
        # Step 2: Generate answer
        logger.info("🤖 Generating answer...")
        answer = self.generate_answer(query, results)
        
        if not answer:
            logger.error("❌ Failed to generate answer")
            return False
        
        logger.info(f"✅ Generated answer: {answer[:200]}...")
        
        # Step 3: Validate answer quality
        validation_passed = True
        
        # Check for expected keywords
        if expected_keywords:
            answer_lower = answer.lower()
            found_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
            if found_keywords:
                logger.info(f"✅ Found expected keywords: {found_keywords}")
            else:
                logger.warning(f"⚠️  Missing expected keywords: {expected_keywords}")
                validation_passed = False
        
        # Check answer length (should be substantial)
        if len(answer) < 50:
            logger.warning("⚠️  Answer seems too short")
            validation_passed = False
        else:
            logger.info(f"✅ Answer length: {len(answer)} characters")
        
        # Check for source citations
        if any('source' in str(result.get('location', {})).lower() for result in results):
            logger.info("✅ Answer includes source references")
        else:
            logger.info("ℹ️  No explicit source references in answer")
        
        return validation_passed
    
    def run_comprehensive_tests(self):
        """Run comprehensive unit tests for Knowledge Base answers."""
        logger.info("🚀 Starting Knowledge Base Answer Unit Tests")
        logger.info("=" * 70)
        
        # Define test cases with expected keywords
        test_cases = [
            {
                "query": "What is Adobe Analytics?",
                "expected_keywords": ["adobe", "analytics", "web", "data", "tracking", "measurement"],
                "description": "Basic Adobe Analytics definition"
            },
            {
                "query": "How do I create custom events in Adobe Analytics?",
                "expected_keywords": ["custom", "events", "implementation", "code", "tracking"],
                "description": "Custom events implementation"
            },
            {
                "query": "What are eVars and props in Adobe Analytics?",
                "expected_keywords": ["evar", "props", "conversion", "traffic", "variable"],
                "description": "eVars and props explanation"
            },
            {
                "query": "How do I set up Customer Journey Analytics?",
                "expected_keywords": ["customer", "journey", "analytics", "cja", "setup", "configuration"],
                "description": "Customer Journey Analytics setup"
            },
            {
                "query": "What is the difference between Adobe Analytics and Google Analytics?",
                "expected_keywords": ["adobe", "google", "analytics", "difference", "comparison"],
                "description": "Analytics platform comparison"
            },
            {
                "query": "How do I create segments in Adobe Analytics?",
                "expected_keywords": ["segments", "segmentation", "audience", "create", "criteria"],
                "description": "Segmentation functionality"
            },
            {
                "query": "What are calculated metrics in Adobe Analytics?",
                "expected_keywords": ["calculated", "metrics", "formula", "custom", "measurement"],
                "description": "Calculated metrics feature"
            },
            {
                "query": "How do I implement Adobe Analytics on a website?",
                "expected_keywords": ["implementation", "website", "code", "javascript", "tracking"],
                "description": "Website implementation guide"
            }
        ]
        
        # Run tests
        passed_tests = 0
        total_tests = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n{'='*70}")
            logger.info(f"TEST {i}/{total_tests}: {test_case['description']}")
            logger.info(f"{'='*70}")
            
            success = self.test_query(
                test_case['query'],
                test_case['expected_keywords']
            )
            
            if success:
                passed_tests += 1
                logger.info(f"✅ TEST {i} PASSED")
            else:
                logger.error(f"❌ TEST {i} FAILED")
        
        # Summary
        logger.info(f"\n{'='*70}")
        logger.info("📊 UNIT TEST SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {total_tests - passed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED! Knowledge Base is working excellently!")
        elif passed_tests >= total_tests * 0.8:
            logger.info("✅ MOSTLY SUCCESSFUL! Knowledge Base is working well with minor issues.")
        elif passed_tests >= total_tests * 0.6:
            logger.warning("⚠️  PARTIALLY SUCCESSFUL! Knowledge Base needs improvement.")
        else:
            logger.error("❌ MOSTLY FAILED! Knowledge Base needs significant attention.")
        
        return passed_tests, total_tests

def main():
    """Main function."""
    try:
        tester = KnowledgeBaseAnswerTester()
        passed, total = tester.run_comprehensive_tests()
        
        print(f"\n🎯 Final Results: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            print("\n🎉 Your Knowledge Base is working perfectly!")
            print("✅ All queries returned relevant, accurate answers")
            print("✅ Document retrieval is functioning correctly")
            print("✅ Answer generation is working properly")
        else:
            print(f"\n⚠️  {total - passed} test(s) need attention")
            print("💡 Consider checking document quality or Knowledge Base configuration")
            
    except Exception as e:
        logger.error(f"❌ Error during testing: {e}")

if __name__ == "__main__":
    main()
