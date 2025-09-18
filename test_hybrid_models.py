"""
Test script for hybrid model architecture.
Tests both Gemini and Claude integration.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

from src.models.model_provider import ModelProvider

def test_model_provider():
    """Test the ModelProvider with both models."""
    print("🚀 Testing Hybrid Model Architecture")
    print("=" * 50)
    
    try:
        # Initialize model provider
        print("📡 Initializing ModelProvider...")
        provider = ModelProvider()
        
        # Test connections
        print("\n🔍 Testing API connections...")
        connection_results = provider.test_connections()
        
        for model, result in connection_results.items():
            status = "✅ Connected" if result['success'] else "❌ Failed"
            print(f"  {model.upper()}: {status}")
            if not result['success']:
                print(f"    Error: {result.get('error', 'Unknown error')}")
        
        # Test individual model queries
        test_prompt = "What is Adobe Analytics and how does it work?"
        
        print(f"\n🧪 Testing individual model queries...")
        print(f"Query: {test_prompt}")
        
        # Test Gemini
        if provider.gemini_client:
            print("\n📊 Testing Gemini...")
            gemini_result = provider.query_gemini(test_prompt, max_tokens=100)
            if gemini_result['success']:
                print(f"  ✅ Success: {gemini_result['response'][:100]}...")
                print(f"  ⏱️  Time: {gemini_result['response_time']:.2f}s")
                print(f"  💰 Cost: ${gemini_result['cost']:.4f}")
                print(f"  🔤 Tokens: {gemini_result['total_tokens']}")
            else:
                print(f"  ❌ Failed: {gemini_result['error']}")
        
        # Test Claude
        if provider.claude_client:
            print("\n🤖 Testing Claude...")
            claude_result = provider.query_claude_bedrock(test_prompt, max_tokens=100)
            if claude_result['success']:
                print(f"  ✅ Success: {claude_result['response'][:100]}...")
                print(f"  ⏱️  Time: {claude_result['response_time']:.2f}s")
                print(f"  💰 Cost: ${claude_result['cost']:.4f}")
                print(f"  🔤 Tokens: {claude_result['total_tokens']}")
            else:
                print(f"  ❌ Failed: {claude_result['error']}")
        
        # Test both models simultaneously
        if provider.gemini_client and provider.claude_client:
            print("\n🔄 Testing both models simultaneously...")
            both_result = provider.query_both_models(test_prompt)
            
            if both_result['success']:
                print(f"  ✅ Both models completed in {both_result['total_time']:.2f}s")
                
                comparison = both_result['comparison']
                print(f"  🏆 Speed winner: {comparison['winner'].get('speed', 'N/A')}")
                print(f"  💰 Cost winner: {comparison['winner'].get('cost', 'N/A')}")
                
                if 'cost_difference_percentage' in comparison['winner']:
                    cost_diff = comparison['winner']['cost_difference_percentage']
                    print(f"  📊 Cost difference: {cost_diff:.1f}%")
            else:
                print(f"  ❌ Parallel query failed")
        
        # Get usage statistics
        print("\n📈 Usage Statistics:")
        stats = provider.get_usage_stats()
        
        cost_summary = stats['cost_summary']
        print(f"  Total queries: {cost_summary['total_queries']}")
        print(f"  Total cost: ${cost_summary['total_cost']:.4f}")
        print(f"  Total tokens: {cost_summary['total_tokens']:,}")
        
        performance = stats['performance_summary']
        for model, data in performance.items():
            if data['total_requests'] > 0:
                print(f"  {model.upper()}:")
                print(f"    Success rate: {data['success_rate']:.1%}")
                print(f"    Avg response time: {data['response_time_stats']['avg']:.2f}s")
                print(f"    Health status: {data['health_status']}")
        
        print("\n✅ Hybrid model architecture test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_model_provider()
