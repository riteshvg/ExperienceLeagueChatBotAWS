#!/usr/bin/env python3
"""
Test script for Smart Context Management System

This script demonstrates how the smart context manager adapts context length
based on query complexity, optimizing costs while maintaining quality.
"""

from smart_context_manager import smart_context_manager, QueryComplexity
import time

def test_query_complexity_detection():
    """Test query complexity detection with various query types"""
    
    test_queries = [
        # Simple queries
        "What is Adobe Analytics?",
        "How to create a segment?",
        "Define conversion rate",
        "What are dimensions?",
        
        # Medium queries
        "How do I create custom events in Adobe Analytics?",
        "What is the difference between segments and calculated metrics?",
        "How to set up data collection for mobile apps?",
        
        # Complex queries
        "How do I integrate Adobe Analytics with Adobe Experience Platform for cross-channel attribution and customer journey analysis?",
        "What are the best practices for implementing Adobe Analytics in a multi-domain e-commerce environment with custom tracking requirements?",
        "How can I configure Adobe Analytics to track user behavior across web and mobile applications while maintaining data privacy compliance?",
        "What is the step-by-step process for migrating from Google Analytics to Adobe Analytics with custom dimension mapping?",
        "How do I troubleshoot Adobe Analytics data discrepancies between different reporting interfaces and ensure data accuracy?",
        "What are the security considerations and implementation requirements for Adobe Analytics in a healthcare organization with HIPAA compliance?",
        "How to optimize Adobe Analytics performance for high-traffic websites with complex data collection requirements?",
        "What are the prerequisites and configuration steps for implementing Adobe Analytics with Adobe Target for personalization?",
        "How do I set up Adobe Analytics data feeds and integrate them with external data warehouses for advanced analytics?",
        "What are the limitations and workarounds for Adobe Analytics when tracking single-page applications with dynamic content loading?"
    ]
    
    print("🧠 Smart Context Management - Query Complexity Detection Test")
    print("=" * 70)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i:2d}. Query: {query}")
        print("-" * 50)
        
        # Detect complexity
        complexity, details = smart_context_manager.detect_query_complexity(query)
        
        # Get context config
        config = smart_context_manager.get_context_config(complexity)
        
        # Display results
        complexity_emoji = {
            QueryComplexity.SIMPLE: '🟢',
            QueryComplexity.MEDIUM: '🟡',
            QueryComplexity.COMPLEX: '🔴'
        }
        
        print(f"   Complexity: {complexity_emoji[complexity]} {complexity.value.title()}")
        print(f"   Score: {details['complexity_score']}")
        print(f"   Length: {details['query_length']} chars")
        print(f"   Technical terms: {len(details['technical_indicators'])}")
        print(f"   Context config: {config.max_chars_per_doc:,} chars/doc, {config.max_docs} docs")
        
        if details['technical_indicators']:
            print(f"   Technical indicators: {', '.join(details['technical_indicators'][:3])}")
        
        if details['matched_patterns']:
            print(f"   Matched patterns: {len(details['matched_patterns'])}")

def test_context_preparation():
    """Test context preparation with mock documents"""
    
    # Mock documents with different lengths
    mock_documents = [
        {
            'content': {'text': 'Short document content about basic concepts. ' * 10},
            'score': 0.8
        },
        {
            'content': {'text': 'Medium length document with more detailed information about implementation and configuration. ' * 50},
            'score': 0.7
        },
        {
            'content': {'text': 'Very long document with comprehensive information about advanced topics, best practices, troubleshooting, and detailed implementation guides. ' * 100},
            'score': 0.9
        }
    ]
    
    test_queries = [
        "What is Adobe Analytics?",  # Simple
        "How do I implement Adobe Analytics?",  # Medium
        "What are the best practices for implementing Adobe Analytics in a multi-domain environment with custom tracking requirements?"  # Complex
    ]
    
    print("\n\n📄 Smart Context Preparation Test")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        
        # Prepare context
        context, metadata = smart_context_manager.prepare_smart_context(mock_documents, query)
        
        print(f"Complexity: {metadata['complexity']}")
        print(f"Context length: {metadata['context_length']:,} characters")
        print(f"Documents used: {metadata['documents_used']}")
        print(f"Max chars per doc: {metadata['max_chars_per_doc']:,}")
        print(f"Processing time: {metadata['processing_time_ms']:.2f} ms")
        print(f"Context preview: {context[:200]}...")

def test_cost_optimization():
    """Test cost optimization with different query types"""
    
    print("\n\n💰 Cost Optimization Analysis")
    print("=" * 70)
    
    # Simulate different usage patterns
    usage_scenarios = [
        {"simple": 70, "medium": 25, "complex": 5, "name": "Typical Usage (70% simple, 25% medium, 5% complex)"},
        {"simple": 50, "medium": 35, "complex": 15, "name": "Balanced Usage (50% simple, 35% medium, 15% complex)"},
        {"simple": 30, "medium": 40, "complex": 30, "name": "Complex Usage (30% simple, 40% medium, 30% complex)"}
    ]
    
    # Cost per query (approximate tokens)
    costs = {
        QueryComplexity.SIMPLE: 125,  # ~500 chars = 125 tokens
        QueryComplexity.MEDIUM: 375,  # ~1500 chars = 375 tokens  
        QueryComplexity.COMPLEX: 750  # ~3000 chars = 750 tokens
    }
    
    # Old fixed cost (always 2000 chars = 500 tokens)
    old_cost_per_query = 500
    
    for scenario in usage_scenarios:
        print(f"\n{scenario['name']}:")
        print("-" * 40)
        
        # Calculate average cost per query
        total_queries = 100
        simple_queries = int(total_queries * scenario['simple'] / 100)
        medium_queries = int(total_queries * scenario['medium'] / 100)
        complex_queries = int(total_queries * scenario['complex'] / 100)
        
        # Smart context costs
        smart_cost = (
            simple_queries * costs[QueryComplexity.SIMPLE] +
            medium_queries * costs[QueryComplexity.MEDIUM] +
            complex_queries * costs[QueryComplexity.COMPLEX]
        )
        
        # Old fixed cost
        old_cost = total_queries * old_cost_per_query
        
        # Calculate savings
        savings = old_cost - smart_cost
        savings_percent = (savings / old_cost) * 100
        
        print(f"  Smart context cost: {smart_cost:,} tokens")
        print(f"  Fixed context cost: {old_cost:,} tokens")
        print(f"  Cost savings: {savings:,} tokens ({savings_percent:.1f}%)")
        print(f"  Cost per query: {smart_cost/total_queries:.0f} tokens (vs {old_cost_per_query} fixed)")

def test_performance_stats():
    """Test performance statistics"""
    
    print("\n\n📊 Performance Statistics")
    print("=" * 70)
    
    # Run some queries to generate stats
    test_queries = [
        "What is Adobe Analytics?",
        "How do I implement Adobe Analytics?",
        "What are the best practices for implementing Adobe Analytics in a multi-domain environment?"
    ]
    
    for query in test_queries:
        smart_context_manager.detect_query_complexity(query)
    
    # Get performance stats
    stats = smart_context_manager.get_performance_stats()
    
    print("Complexity Distribution:")
    for complexity, count in stats['complexity_distribution'].items():
        print(f"  {complexity}: {count} queries")
    
    print(f"\nDetection Performance:")
    print(f"  Average time: {stats['detection_times']['avg_ms']:.2f} ms")
    print(f"  Min time: {stats['detection_times']['min_ms']:.2f} ms")
    print(f"  Max time: {stats['detection_times']['max_ms']:.2f} ms")
    print(f"  Total queries: {stats['detection_times']['count']}")
    
    print(f"\nContext Configurations:")
    for complexity, config in stats['context_configs'].items():
        print(f"  {complexity}: {config['max_chars_per_doc']:,} chars/doc, {config['max_docs']} docs")

if __name__ == "__main__":
    print("🚀 Starting Smart Context Management Tests")
    print("=" * 70)
    
    # Run all tests
    test_query_complexity_detection()
    test_context_preparation()
    test_cost_optimization()
    test_performance_stats()
    
    print("\n✅ All tests completed!")
    print("\nKey Benefits:")
    print("• 🎯 Adaptive context length based on query complexity")
    print("• 💰 Cost optimization (up to 50% savings for typical usage)")
    print("• ⚡ Fast complexity detection (< 1ms)")
    print("• 📊 Detailed performance monitoring")
    print("• 🔧 Configurable context settings")
