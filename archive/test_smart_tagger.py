#!/usr/bin/env python3
"""
Test script for the Smart Tagger system
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.tagging.smart_tagger import SmartTagger, TaggingResult

def test_smart_tagger():
    """Test the smart tagger with various question types."""
    
    print("🧪 Testing Smart Tagger System")
    print("=" * 60)
    
    # Initialize the tagger
    tagger = SmartTagger()
    
    # Test questions covering different scenarios
    test_questions = [
        {
            "question": "How do I implement Adobe Analytics tracking on my website?",
            "expected_products": ["adobe_analytics"],
            "expected_type": "implementation"
        },
        {
            "question": "I'm getting an error with my AppMeasurement code, can you help?",
            "expected_products": ["appmeasurement"],
            "expected_type": "troubleshooting"
        },
        {
            "question": "What's the difference between Adobe Analytics and Customer Journey Analytics?",
            "expected_products": ["adobe_analytics", "customer_journey_analytics"],
            "expected_type": "general"
        },
        {
            "question": "How to configure cross-device tracking in CJA?",
            "expected_products": ["customer_journey_analytics"],
            "expected_type": "configuration"
        },
        {
            "question": "I need help with Adobe Experience Platform data collection setup",
            "expected_products": ["adobe_experience_platform", "data_collection"],
            "expected_type": "implementation"
        },
        {
            "question": "How do I create custom segments in Adobe Analytics?",
            "expected_products": ["adobe_analytics"],
            "expected_type": "configuration"
        },
        {
            "question": "My Adobe Launch rules are not firing correctly",
            "expected_products": ["adobe_launch"],
            "expected_type": "troubleshooting"
        },
        {
            "question": "What are the best practices for GDPR compliance in Adobe Analytics?",
            "expected_products": ["adobe_analytics"],
            "expected_type": "privacy"
        },
        {
            "question": "How to integrate Adobe Analytics with mobile apps?",
            "expected_products": ["adobe_analytics"],
            "expected_type": "mobile"
        },
        {
            "question": "Can you help me with Adobe Analytics API authentication?",
            "expected_products": ["adobe_analytics"],
            "expected_type": "api"
        }
    ]
    
    # Run tests
    passed_tests = 0
    total_tests = len(test_questions)
    
    for i, test_case in enumerate(test_questions, 1):
        question = test_case["question"]
        expected_products = test_case["expected_products"]
        expected_type = test_case["expected_type"]
        
        print(f"\n📝 Test {i}: {question}")
        print("-" * 40)
        
        # Tag the question
        result = tagger.tag_question(question)
        
        # Display results
        print(f"✅ Products detected: {result.products}")
        print(f"✅ Question type: {result.question_type.value}")
        print(f"✅ Technical level: {result.technical_level.value}")
        print(f"✅ Topics: {result.topics[:3]}")  # Show top 3 topics
        print(f"✅ Confidence: {result.confidence_score:.2f}")
        print(f"✅ Urgency: {result.urgency}")
        print(f"✅ Bedrock enhancement needed: {tagger.should_use_bedrock_enhancement(result)}")
        
        # Check if expected products are detected
        products_found = any(product in result.products for product in expected_products)
        type_correct = result.question_type.value == expected_type
        
        if products_found and type_correct:
            print("✅ Test PASSED")
            passed_tests += 1
        else:
            print("❌ Test FAILED")
            if not products_found:
                print(f"   Expected products: {expected_products}")
            if not type_correct:
                print(f"   Expected type: {expected_type}")
    
    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 60)
    print(f"Passed: {passed_tests}/{total_tests}")
    print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed. Review the patterns and keywords.")

def test_edge_cases():
    """Test edge cases and error handling."""
    
    print(f"\n🔍 Testing Edge Cases")
    print("=" * 60)
    
    tagger = SmartTagger()
    
    edge_cases = [
        "",  # Empty string
        "Hello world",  # No Adobe-related content
        "Adobe",  # Just the word Adobe
        "How to use Adobe Analytics, CJA, AEP, and Launch together?",  # Multiple products
        "What is the difference between Adobe Analytics and Google Analytics?",  # Mixed products
    ]
    
    for i, question in enumerate(edge_cases, 1):
        print(f"\nEdge Case {i}: '{question}'")
        result = tagger.tag_question(question)
        summary = tagger.get_tagging_summary(result)
        print(f"Result: {summary}")

if __name__ == "__main__":
    test_smart_tagger()
    test_edge_cases()
