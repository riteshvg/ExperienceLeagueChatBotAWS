#!/usr/bin/env python3
"""
Test Advanced Capabilities of the Chatbot

This script tests the chatbot with questions of varying complexity
to verify smart routing, knowledge base retrieval, and response quality.
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

API_BASE_URL = "http://localhost:8000"


def test_question(question: str, expected_model: str = None) -> Dict:
    """Test a single question."""
    print(f"\n{'='*80}")
    print(f"❓ Question: {question}")
    if expected_model:
        print(f"🎯 Expected Model: {expected_model}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat",
            json={
                "query": question,
                "user_id": "test_user"
            },
            timeout=120
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ Status: Success")
            print(f"⏱️  Response Time: {elapsed:.2f}s")
            print(f"🤖 Model Used: {data.get('model_used', 'Unknown')}")
            
            if expected_model and data.get('model_used') != expected_model:
                print(f"⚠️  Model Mismatch: Expected {expected_model}, got {data.get('model_used')}")
            
            if data.get('routing_decision'):
                routing = data['routing_decision']
                print(f"🧠 Complexity: {routing.get('complexity', 'Unknown')}")
                print(f"💭 Reasoning: {routing.get('reasoning', 'N/A')}")
            
            print(f"📄 Documents Retrieved: {len(data.get('documents', []))}")
            
            if data.get('answer'):
                answer_preview = data['answer'][:200] + "..." if len(data['answer']) > 200 else data['answer']
                print(f"📝 Answer Preview: {answer_preview}")
            else:
                print(f"❌ No answer provided")
                print(f"   Error: {data.get('error', 'Unknown error')}")
            
            return {
                "success": data.get('success', False),
                "model_used": data.get('model_used'),
                "expected_model": expected_model,
                "response_time": elapsed,
                "documents_count": len(data.get('documents', [])),
                "has_answer": bool(data.get('answer')),
                "answer_length": len(data.get('answer', ''))
            }
        else:
            print(f"❌ Status: Failed ({response.status_code})")
            print(f"   Error: {response.text}")
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"❌ Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "response_time": elapsed
        }


def run_test_suite():
    """Run comprehensive test suite."""
    print("🧪 Advanced Capabilities Test Suite")
    print("=" * 80)
    print(f"API Endpoint: {API_BASE_URL}")
    print()
    
    # Test questions organized by complexity
    test_cases = [
        # Simple (Haiku)
        {
            "question": "What is Adobe Analytics?",
            "expected_model": "haiku",
            "category": "Simple"
        },
        {
            "question": "How do I create a segment in Adobe Analytics?",
            "expected_model": "haiku",
            "category": "Simple"
        },
        # Complex (Sonnet)
        {
            "question": "How do I implement cross-domain tracking in Adobe Analytics, and what are the common pitfalls to avoid?",
            "expected_model": "sonnet",
            "category": "Complex"
        },
        {
            "question": "What are the differences between Adobe Analytics and Customer Journey Analytics, and when should I use each?",
            "expected_model": "sonnet",
            "category": "Complex"
        },
        # Very Complex (Opus)
        {
            "question": "Design a complete data architecture that integrates Adobe Analytics, Customer Journey Analytics, and Adobe Experience Platform to provide a unified view of customer journeys across web, mobile, email, and offline channels.",
            "expected_model": "opus",
            "category": "Very Complex"
        },
        # Troubleshooting
        {
            "question": "Why is my Adobe Analytics data showing zero visitors even though I can see hits being sent?",
            "expected_model": "sonnet",
            "category": "Troubleshooting"
        },
        # Integration
        {
            "question": "How do I integrate Adobe Analytics with Salesforce to track marketing campaign performance?",
            "expected_model": "sonnet",
            "category": "Integration"
        },
        # Business
        {
            "question": "What are the key metrics I should track for an e-commerce business in Adobe Analytics?",
            "expected_model": "sonnet",
            "category": "Business"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}/{len(test_cases)} - {test_case['category']}")
        result = test_question(
            test_case['question'],
            test_case.get('expected_model')
        )
        result['category'] = test_case['category']
        result['question'] = test_case['question']
        results.append(result)
        
        # Small delay between tests
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for r in results if r.get('success'))
    total = len(results)
    
    print(f"\n✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")
    
    # Model selection accuracy
    correct_model = sum(
        1 for r in results 
        if r.get('expected_model') and r.get('model_used') == r.get('expected_model')
    )
    model_tests = sum(1 for r in results if r.get('expected_model'))
    
    if model_tests > 0:
        print(f"\n🎯 Model Selection Accuracy: {correct_model}/{model_tests}")
    
    # Average response times
    response_times = [r.get('response_time', 0) for r in results if r.get('response_time')]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"⏱️  Average Response Time: {avg_time:.2f}s")
        print(f"⏱️  Fastest: {min(response_times):.2f}s")
        print(f"⏱️  Slowest: {max(response_times):.2f}s")
    
    # Documents retrieved
    doc_counts = [r.get('documents_count', 0) for r in results if r.get('documents_count', 0) > 0]
    if doc_counts:
        avg_docs = sum(doc_counts) / len(doc_counts)
        print(f"📄 Average Documents Retrieved: {avg_docs:.1f}")
    
    # Category breakdown
    print(f"\n📊 Results by Category:")
    categories = {}
    for r in results:
        cat = r.get('category', 'Unknown')
        if cat not in categories:
            categories[cat] = {'success': 0, 'total': 0}
        categories[cat]['total'] += 1
        if r.get('success'):
            categories[cat]['success'] += 1
    
    for cat, stats in categories.items():
        print(f"   {cat}: {stats['success']}/{stats['total']} passed")
    
    print("\n" + "=" * 80)
    print("✅ Test suite completed!")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    try:
        # Check if API is running
        try:
            response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=5)
            if response.status_code != 200:
                print(f"❌ API health check failed: {response.status_code}")
                sys.exit(1)
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to API at {API_BASE_URL}")
            print("   Make sure the backend is running:")
            print("   cd backend && source ../venv/bin/activate && uvicorn app.main:app --reload")
            sys.exit(1)
        
        results = run_test_suite()
        
        # Save results
        output_file = project_root / "test_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {output_file}")
        
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

