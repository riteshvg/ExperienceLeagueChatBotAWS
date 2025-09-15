#!/usr/bin/env python3
"""
Quick Knowledge Base Test Script
Simple script to test a few key questions and verify Knowledge Base functionality.
"""

import boto3
import json
from datetime import datetime

def test_knowledge_base(kb_id: str, region: str = 'us-east-1'):
    """Test the Knowledge Base with key questions."""
    
    # Initialize AWS clients
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
    
    # Key test questions
    test_questions = [
        {
            "category": "Analytics",
            "question": "How do I set up Adobe Analytics tracking on my website?",
            "expected_keywords": ["tracking", "analytics", "website"]
        },
        {
            "category": "CJA", 
            "question": "How do I create a connection in Customer Journey Analytics?",
            "expected_keywords": ["connection", "customer journey", "cja"]
        },
        {
            "category": "AEP",
            "question": "How do I create a schema in Adobe Experience Platform?",
            "expected_keywords": ["schema", "experience platform", "aep"]
        },
        {
            "category": "Analytics + AEP",
            "question": "How do I connect Adobe Analytics data to Adobe Experience Platform?",
            "expected_keywords": ["analytics", "experience platform", "connect", "data"]
        },
        {
            "category": "Analytics + CJA",
            "question": "What's the difference between Adobe Analytics and Customer Journey Analytics?",
            "expected_keywords": ["analytics", "customer journey", "difference", "cja"]
        }
    ]
    
    print(f"🧪 Testing Knowledge Base: {kb_id}")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = []
    
    for i, test in enumerate(test_questions, 1):
        print(f"\n{i}. Testing {test['category']}: {test['question']}")
        print("-" * 60)
        
        try:
            # Query the Knowledge Base
            response = bedrock_agent_runtime.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={'text': test['question']},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {'numberOfResults': 3}
                }
            )
            
            # Analyze results
            retrieval_results = response.get('retrievalResults', [])
            if not retrieval_results:
                print("❌ No results found")
                results.append({
                    'category': test['category'],
                    'question': test['question'],
                    'status': 'FAIL',
                    'reason': 'No results found',
                    'score': 0
                })
                continue
            
            # Check for expected keywords
            content_text = ' '.join([
                result.get('content', {}).get('text', '') 
                for result in retrieval_results
            ]).lower()
            
            found_keywords = [
                keyword for keyword in test['expected_keywords'] 
                if keyword.lower() in content_text
            ]
            
            # Calculate score
            keyword_score = len(found_keywords) / len(test['expected_keywords'])
            avg_relevance = sum([
                result.get('score', 0) for result in retrieval_results
            ]) / len(retrieval_results)
            
            total_score = (keyword_score * 0.6) + (avg_relevance * 0.4)
            
            # Determine status
            status = "✅ PASS" if total_score >= 0.6 else "❌ FAIL"
            
            print(f"{status} | Score: {total_score:.2f}")
            print(f"   Found keywords: {', '.join(found_keywords)}")
            print(f"   Missing keywords: {', '.join(set(test['expected_keywords']) - set(found_keywords))}")
            print(f"   Avg relevance: {avg_relevance:.3f}")
            print(f"   Documents found: {len(retrieval_results)}")
            
            # Show sample content
            if retrieval_results:
                sample_content = retrieval_results[0].get('content', {}).get('text', '')[:200]
                print(f"   Sample content: {sample_content}...")
            
            results.append({
                'category': test['category'],
                'question': test['question'],
                'status': 'PASS' if total_score >= 0.6 else 'FAIL',
                'score': total_score,
                'found_keywords': found_keywords,
                'missing_keywords': list(set(test['expected_keywords']) - set(found_keywords)),
                'documents_found': len(retrieval_results),
                'avg_relevance': avg_relevance
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'category': test['category'],
                'question': test['question'],
                'status': 'ERROR',
                'error': str(e),
                'score': 0
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    passed_tests = len([r for r in results if r['status'] == 'PASS'])
    failed_tests = len([r for r in results if r['status'] == 'FAIL'])
    error_tests = len([r for r in results if r['status'] == 'ERROR'])
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {failed_tests} ❌")
    print(f"Errors: {error_tests} ⚠️")
    print(f"Pass Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Category breakdown
    print(f"\n📈 Category Breakdown:")
    categories = {}
    for result in results:
        cat = result['category']
        if cat not in categories:
            categories[cat] = {'total': 0, 'passed': 0}
        categories[cat]['total'] += 1
        if result['status'] == 'PASS':
            categories[cat]['passed'] += 1
    
    for cat, stats in categories.items():
        pass_rate = (stats['passed'] / stats['total']) * 100
        print(f"   {cat}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"quick_test_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'error_tests': error_tests,
                'pass_rate': (passed_tests/total_tests)*100
            },
            'category_breakdown': categories,
            'detailed_results': results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {filename}")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Quick Knowledge Base test')
    parser.add_argument('--kb-id', required=True, help='Knowledge Base ID')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    test_knowledge_base(args.kb_id, args.region)
