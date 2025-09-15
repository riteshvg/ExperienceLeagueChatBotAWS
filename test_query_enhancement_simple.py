#!/usr/bin/env python3
"""
Simple test script for Query Enhancement System

This script tests the query enhancement functionality without requiring
the full Streamlit application or AWS services.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

try:
    from query_enhancer import AdobeQueryEnhancer
    print("✅ Query enhancer imported successfully")
except ImportError as e:
    print(f"❌ Failed to import query enhancer: {e}")
    sys.exit(1)


def test_query_enhancement():
    """Test the query enhancement system"""
    print("\n🧪 Testing Adobe Query Enhancement System")
    print("=" * 50)
    
    # Initialize enhancer
    enhancer = AdobeQueryEnhancer()
    
    # Test queries
    test_queries = [
        "How to track custom events?",
        "AA implementation steps", 
        "AEP data ingestion",
        "Target personalization setup",
        "Campaign email automation",
        "AEM content management",
        "CJA journey analytics",
        "AJO journey optimization"
    ]
    
    print(f"\n📝 Testing {len(test_queries)} queries...")
    
    total_time = 0
    successful_tests = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        
        try:
            start_time = time.time()
            result = enhancer.enhance_query(query)
            processing_time = (time.time() - start_time) * 1000
            total_time += processing_time
            
            print(f"   ✅ Enhanced queries: {len(result['enhanced_queries'])}")
            print(f"   📊 Detected products: {result['detected_products']}")
            print(f"   ⏱️  Processing time: {processing_time:.2f}ms")
            
            # Show enhanced queries
            for j, eq in enumerate(result['enhanced_queries'], 1):
                print(f"      {j}. {eq}")
            
            # Check performance requirement
            if processing_time < 400:
                successful_tests += 1
                print(f"   ✅ Performance: PASS (<400ms)")
            else:
                print(f"   ❌ Performance: FAIL ({processing_time:.2f}ms >= 400ms)")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 30)
    print(f"Total queries tested: {len(test_queries)}")
    print(f"Successful tests: {successful_tests}")
    print(f"Success rate: {successful_tests/len(test_queries)*100:.1f}%")
    print(f"Average processing time: {total_time/len(test_queries):.2f}ms")
    print(f"Total processing time: {total_time:.2f}ms")
    
    if successful_tests == len(test_queries):
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed")
        return False


def test_specific_adobe_queries():
    """Test specific Adobe product queries"""
    print("\n🎯 Testing Specific Adobe Product Queries")
    print("=" * 50)
    
    enhancer = AdobeQueryEnhancer()
    
    # Test cases with expected products
    test_cases = [
        ("How to setup Adobe Analytics?", ["Adobe Analytics"]),
        ("AEP data ingestion guide", ["Adobe Experience Platform"]),
        ("Target personalization", ["Adobe Target"]),
        ("Campaign email marketing", ["Adobe Campaign"]),
        ("AEM content management", ["Adobe Experience Manager"]),
        ("CJA journey analytics", ["Customer Journey Analytics"]),
        ("AJO journey optimization", ["Adobe Journey Optimizer"]),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for query, expected_products in test_cases:
        print(f"\nTesting: '{query}'")
        result = enhancer.enhance_query(query)
        detected_products = result['detected_products']
        
        # Check if expected products are detected
        found_expected = any(product in detected_products for product in expected_products)
        
        if found_expected:
            print(f"   ✅ Detected: {detected_products}")
            passed += 1
        else:
            print(f"   ❌ Expected: {expected_products}, Got: {detected_products}")
    
    print(f"\n📊 Product Detection Summary: {passed}/{total} passed ({passed/total*100:.1f}%)")
    return passed == total


if __name__ == "__main__":
    print("🚀 Adobe Experience League RAG Query Enhancement Test")
    print("=" * 60)
    
    # Test basic functionality
    basic_test_passed = test_query_enhancement()
    
    # Test specific Adobe queries
    adobe_test_passed = test_specific_adobe_queries()
    
    # Overall result
    print(f"\n🏁 Overall Result")
    print("=" * 20)
    if basic_test_passed and adobe_test_passed:
        print("🎉 All tests passed! Query enhancement system is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
