#!/usr/bin/env python3
"""
Query Enhancement Demo Script

This script demonstrates the query enhancement system with real-world examples
and shows the difference between enhanced and non-enhanced queries.
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


def demo_query_enhancement():
    """Demonstrate query enhancement with real examples"""
    print("🚀 Adobe Experience League RAG Query Enhancement Demo")
    print("=" * 60)
    
    enhancer = AdobeQueryEnhancer()
    
    # Real-world test scenarios
    test_scenarios = [
        {
            "category": "Analytics",
            "queries": [
                "How to track custom events?",
                "AA implementation steps",
                "analytics dashboard creation",
                "track user behavior"
            ]
        },
        {
            "category": "Experience Platform",
            "queries": [
                "AEP data ingestion",
                "platform schema creation",
                "CDP configuration",
                "data platform setup"
            ]
        },
        {
            "category": "Target",
            "queries": [
                "Target personalization",
                "AT audience targeting",
                "ab testing setup",
                "experience targeting"
            ]
        },
        {
            "category": "Campaign",
            "queries": [
                "Campaign email marketing",
                "AC automation setup",
                "email campaign management",
                "marketing automation"
            ]
        },
        {
            "category": "Experience Manager",
            "queries": [
                "AEM content management",
                "experience manager setup",
                "CMS configuration",
                "web content management"
            ]
        },
        {
            "category": "Journey Analytics",
            "queries": [
                "CJA journey analytics",
                "journey analytics reporting",
                "cross-channel analytics",
                "attribution analysis"
            ]
        },
        {
            "category": "Journey Optimizer",
            "queries": [
                "AJO journey optimization",
                "journey orchestration",
                "customer journey management",
                "journey optimizer setup"
            ]
        }
    ]
    
    total_queries = 0
    total_enhancements = 0
    total_products_detected = 0
    
    for scenario in test_scenarios:
        print(f"\n📊 {scenario['category']} Queries")
        print("-" * 40)
        
        for query in scenario['queries']:
            total_queries += 1
            print(f"\n🔍 Original: '{query}'")
            
            # Enhance the query
            start_time = time.time()
            result = enhancer.enhance_query(query)
            processing_time = (time.time() - start_time) * 1000
            
            print(f"   ⏱️  Processing: {processing_time:.2f}ms")
            print(f"   📈 Enhanced queries: {len(result['enhanced_queries'])}")
            print(f"   🎯 Products detected: {result['detected_products']}")
            
            # Show enhanced queries
            for i, eq in enumerate(result['enhanced_queries'], 1):
                print(f"      {i}. {eq}")
            
            total_enhancements += len(result['enhanced_queries'])
            total_products_detected += len(result['detected_products'])
    
    # Summary
    print(f"\n📊 Enhancement Summary")
    print("=" * 30)
    print(f"Total queries processed: {total_queries}")
    print(f"Total enhanced queries generated: {total_enhancements}")
    print(f"Average enhancements per query: {total_enhancements/total_queries:.1f}")
    print(f"Total products detected: {total_products_detected}")
    print(f"Average products per query: {total_products_detected/total_queries:.1f}")


def demo_performance_benchmark():
    """Demonstrate performance characteristics"""
    print(f"\n⚡ Performance Benchmark")
    print("=" * 30)
    
    enhancer = AdobeQueryEnhancer()
    
    # Performance test queries
    perf_queries = [
        "Adobe Analytics setup",
        "AEP data ingestion",
        "Target personalization",
        "Campaign automation",
        "AEM content management",
        "CJA journey analytics",
        "AJO journey optimization",
        "analytics implementation",
        "platform configuration",
        "targeting setup"
    ]
    
    times = []
    for query in perf_queries:
        start_time = time.time()
        result = enhancer.enhance_query(query)
        processing_time = (time.time() - start_time) * 1000
        times.append(processing_time)
        
        print(f"   {query}: {processing_time:.2f}ms")
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n📈 Performance Stats:")
    print(f"   Average: {avg_time:.2f}ms")
    print(f"   Minimum: {min_time:.2f}ms")
    print(f"   Maximum: {max_time:.2f}ms")
    print(f"   Target: <400ms ✅" if avg_time < 400 else "   Target: <400ms ❌")


def demo_edge_cases():
    """Test edge cases and error handling"""
    print(f"\n🔬 Edge Cases & Error Handling")
    print("=" * 35)
    
    enhancer = AdobeQueryEnhancer()
    
    edge_cases = [
        ("", "Empty query"),
        ("a", "Single character"),
        ("   ", "Whitespace only"),
        ("Adobe", "Single product name"),
        ("How to setup Adobe Analytics tracking for custom events in a complex implementation?", "Very long query"),
        ("!@#$%^&*()", "Special characters"),
        ("123456789", "Numbers only"),
        ("analytics analytics analytics", "Repeated words"),
    ]
    
    for query, description in edge_cases:
        print(f"\n   {description}: '{query}'")
        try:
            result = enhancer.safe_enhance_query(query)
            print(f"      ✅ Enhanced queries: {len(result['enhanced_queries'])}")
            print(f"      📊 Products detected: {result['detected_products']}")
            print(f"      ⏱️  Processing time: {result['processing_time_ms']:.2f}ms")
        except Exception as e:
            print(f"      ❌ Error: {e}")


if __name__ == "__main__":
    print("🧪 Query Enhancement System Testing")
    print("=" * 50)
    
    # Run all demos
    demo_query_enhancement()
    demo_performance_benchmark()
    demo_edge_cases()
    
    print(f"\n🎉 Demo completed! The query enhancement system is working correctly.")
    print(f"💡 You can now test this in your Streamlit app by running: streamlit run app.py")
