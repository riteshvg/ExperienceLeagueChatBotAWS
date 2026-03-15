#!/usr/bin/env python3
"""
Knowledge Base Test Script
Tests the Knowledge Base with questions across all data sources and combinations.
"""

import boto3
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeBaseTester:
    def __init__(self, knowledge_base_id: str, region: str = 'us-east-1'):
        """Initialize the Knowledge Base tester."""
        self.knowledge_base_id = knowledge_base_id
        self.region = region
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=region)
        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
        
        # Test questions organized by category
        self.test_questions = {
            "Analytics": [
                "How do I set up Adobe Analytics tracking on my website?",
                "What are the different types of variables in Adobe Analytics and how do I use them?"
            ],
            "CJA": [
                "How do I create a connection in Customer Journey Analytics?",
                "What is the difference between Adobe Analytics and Customer Journey Analytics?"
            ],
            "AEP": [
                "How do I create a schema in Adobe Experience Platform?",
                "What are datasets in AEP and how do I create them?"
            ],
            "Analytics + AEP": [
                "How do I connect Adobe Analytics data to Adobe Experience Platform for customer journey analysis?",
                "What is the best way to send Analytics data to AEP for real-time personalization?"
            ],
            "Analytics + CJA": [
                "How do I use Adobe Analytics data in Customer Journey Analytics for cross-device analysis?",
                "What's the process to migrate from Adobe Analytics to Customer Journey Analytics?"
            ]
        }
        
        # Expected keywords for each category
        self.expected_keywords = {
            "Analytics": ["tracking", "variables", "reports", "analytics", "adobe analytics"],
            "CJA": ["connection", "customer journey", "cja", "cross-device", "data view"],
            "AEP": ["schema", "dataset", "xdm", "experience platform", "aep"],
            "Analytics + AEP": ["analytics", "experience platform", "aep", "integration", "data flow"],
            "Analytics + CJA": ["analytics", "customer journey", "cja", "migration", "cross-device"]
        }

    def test_knowledge_base_status(self) -> bool:
        """Check if the Knowledge Base is available and ready."""
        try:
            response = self.bedrock_agent.get_knowledge_base(knowledgeBaseId=self.knowledge_base_id)
            status = response['knowledgeBase']['status']
            logger.info(f"Knowledge Base Status: {status}")
            return status == 'ACTIVE'
        except Exception as e:
            logger.error(f"Error checking Knowledge Base status: {e}")
            return False

    def query_knowledge_base(self, question: str) -> Dict:
        """Query the Knowledge Base with a question."""
        try:
            # Use the retrieve API to get relevant documents
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    'text': question
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': 5
                    }
                }
            )
            
            # Extract relevant content
            relevant_docs = []
            for result in response.get('retrievalResults', []):
                relevant_docs.append({
                    'content': result.get('content', {}).get('text', ''),
                    'score': result.get('score', 0),
                    'location': result.get('location', {})
                })
            
            return {
                'success': True,
                'relevant_docs': relevant_docs,
                'total_results': len(relevant_docs)
            }
            
        except Exception as e:
            logger.error(f"Error querying Knowledge Base: {e}")
            return {
                'success': False,
                'error': str(e),
                'relevant_docs': [],
                'total_results': 0
            }

    def evaluate_response(self, question: str, response: Dict, category: str) -> Dict:
        """Evaluate the response quality and relevance."""
        if not response['success']:
            return {
                'score': 0,
                'issues': [f"Query failed: {response.get('error', 'Unknown error')}"],
                'relevant_content_found': False
            }
        
        relevant_docs = response['relevant_docs']
        if not relevant_docs:
            return {
                'score': 0,
                'issues': ["No relevant documents found"],
                'relevant_content_found': False
            }
        
        # Check for expected keywords
        expected_keywords = self.expected_keywords.get(category, [])
        content_text = ' '.join([doc['content'] for doc in relevant_docs]).lower()
        
        found_keywords = []
        missing_keywords = []
        
        for keyword in expected_keywords:
            if keyword.lower() in content_text:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        # Calculate score based on keyword matches and document relevance
        keyword_score = len(found_keywords) / len(expected_keywords) if expected_keywords else 1
        relevance_score = sum([doc['score'] for doc in relevant_docs]) / len(relevant_docs)
        total_score = (keyword_score * 0.6) + (relevance_score * 0.4)
        
        issues = []
        if missing_keywords:
            issues.append(f"Missing expected keywords: {', '.join(missing_keywords)}")
        if relevance_score < 0.3:
            issues.append("Low relevance scores for retrieved documents")
        
        return {
            'score': total_score,
            'issues': issues,
            'relevant_content_found': True,
            'found_keywords': found_keywords,
            'missing_keywords': missing_keywords,
            'avg_relevance_score': relevance_score,
            'total_documents': len(relevant_docs)
        }

    def run_single_test(self, category: str, question: str) -> Dict:
        """Run a single test question."""
        logger.info(f"Testing {category}: {question}")
        
        # Query the Knowledge Base
        response = self.query_knowledge_base(question)
        
        # Evaluate the response
        evaluation = self.evaluate_response(question, response, category)
        
        return {
            'category': category,
            'question': question,
            'response': response,
            'evaluation': evaluation,
            'timestamp': datetime.now().isoformat()
        }

    def run_all_tests(self) -> Dict:
        """Run all test questions and return comprehensive results."""
        logger.info("Starting comprehensive Knowledge Base testing...")
        
        if not self.test_knowledge_base_status():
            logger.error("Knowledge Base is not active. Cannot run tests.")
            return {'error': 'Knowledge Base not active'}
        
        results = {
            'test_summary': {
                'total_questions': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'categories_tested': list(self.test_questions.keys())
            },
            'category_results': {},
            'detailed_results': [],
            'timestamp': datetime.now().isoformat()
        }
        
        for category, questions in self.test_questions.items():
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing Category: {category}")
            logger.info(f"{'='*50}")
            
            category_results = {
                'total_questions': len(questions),
                'passed_tests': 0,
                'failed_tests': 0,
                'avg_score': 0,
                'questions': []
            }
            
            total_score = 0
            
            for question in questions:
                test_result = self.run_single_test(category, question)
                results['detailed_results'].append(test_result)
                
                # Update category results
                evaluation = test_result['evaluation']
                if evaluation['score'] >= 0.6:  # 60% threshold for passing
                    category_results['passed_tests'] += 1
                    results['test_summary']['passed_tests'] += 1
                else:
                    category_results['failed_tests'] += 1
                    results['test_summary']['failed_tests'] += 1
                
                total_score += evaluation['score']
                category_results['questions'].append({
                    'question': question,
                    'score': evaluation['score'],
                    'passed': evaluation['score'] >= 0.6,
                    'issues': evaluation['issues']
                })
                
                # Log result
                status = "✅ PASS" if evaluation['score'] >= 0.6 else "❌ FAIL"
                logger.info(f"{status} | Score: {evaluation['score']:.2f} | {question}")
                if evaluation['issues']:
                    logger.info(f"    Issues: {'; '.join(evaluation['issues'])}")
            
            # Calculate category average
            category_results['avg_score'] = total_score / len(questions)
            results['category_results'][category] = category_results
            results['test_summary']['total_questions'] += len(questions)
            
            logger.info(f"\nCategory {category} Results:")
            logger.info(f"  Passed: {category_results['passed_tests']}/{category_results['total_questions']}")
            logger.info(f"  Average Score: {category_results['avg_score']:.2f}")
        
        # Calculate overall results
        total_questions = results['test_summary']['total_questions']
        passed_tests = results['test_summary']['passed_tests']
        results['test_summary']['pass_rate'] = (passed_tests / total_questions) * 100 if total_questions > 0 else 0
        
        logger.info(f"\n{'='*60}")
        logger.info("OVERALL TEST RESULTS")
        logger.info(f"{'='*60}")
        logger.info(f"Total Questions: {total_questions}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {results['test_summary']['failed_tests']}")
        logger.info(f"Pass Rate: {results['test_summary']['pass_rate']:.1f}%")
        
        return results

    def save_results(self, results: Dict, filename: str = None) -> str:
        """Save test results to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"knowledge_base_test_results_{timestamp}.json"
        
        filepath = f"test_results/{filename}"
        
        # Create directory if it doesn't exist
        import os
        os.makedirs("test_results", exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test results saved to: {filepath}")
        return filepath

def main():
    """Main function to run the Knowledge Base tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Knowledge Base with programmatic questions')
    parser.add_argument('--kb-id', required=True, help='Knowledge Base ID')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--save-results', action='store_true', help='Save results to JSON file')
    parser.add_argument('--output-file', help='Output filename for results')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = KnowledgeBaseTester(args.kb_id, args.region)
    
    # Run tests
    results = tester.run_all_tests()
    
    # Save results if requested
    if args.save_results:
        output_file = args.output_file
        filepath = tester.save_results(results, output_file)
        print(f"\n📁 Results saved to: {filepath}")
    
    # Print summary
    if 'error' not in results:
        print(f"\n🎯 Test Summary:")
        print(f"   Total Questions: {results['test_summary']['total_questions']}")
        print(f"   Passed: {results['test_summary']['passed_tests']}")
        print(f"   Failed: {results['test_summary']['failed_tests']}")
        print(f"   Pass Rate: {results['test_summary']['pass_rate']:.1f}%")
        
        print(f"\n📊 Category Breakdown:")
        for category, cat_results in results['category_results'].items():
            print(f"   {category}: {cat_results['passed_tests']}/{cat_results['total_questions']} passed ({cat_results['avg_score']:.2f} avg score)")

if __name__ == "__main__":
    main()
