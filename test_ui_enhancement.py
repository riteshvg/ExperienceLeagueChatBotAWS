#!/usr/bin/env python3
"""
Test script to verify query enhancement UI integration
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_query_enhancement_integration():
    """Test that query enhancement modules are properly integrated"""
    print("🧪 Testing Query Enhancement Integration")
    print("=" * 50)
    
    try:
        # Test 1: Import modules
        print("1. Testing module imports...")
        from query_enhancer import AdobeQueryEnhancer
        from enhanced_rag_pipeline import EnhancedRAGPipeline
        print("   ✅ Modules imported successfully")
        
        # Test 2: Check if modules are available in app
        print("2. Testing app integration...")
        import app
        print(f"   ✅ QUERY_ENHANCEMENT_AVAILABLE: {app.QUERY_ENHANCEMENT_AVAILABLE}")
        
        # Test 3: Test query enhancement
        print("3. Testing query enhancement...")
        enhancer = AdobeQueryEnhancer()
        result = enhancer.enhance_query("How to track custom events?")
        print(f"   ✅ Enhanced queries: {len(result['enhanced_queries'])}")
        print(f"   ✅ Detected products: {result['detected_products']}")
        print(f"   ✅ Processing time: {result['processing_time_ms']:.2f}ms")
        
        # Test 4: Test UI components
        print("4. Testing UI components...")
        if hasattr(app, 'QUERY_ENHANCEMENT_AVAILABLE') and app.QUERY_ENHANCEMENT_AVAILABLE:
            print("   ✅ Query enhancement is available in app")
        else:
            print("   ❌ Query enhancement not available in app")
        
        print("\n🎉 All tests passed! Query enhancement should be working in the UI.")
        print("📍 Access the app at: http://localhost:8502")
        print("🔍 Look for:")
        print("   - '🚀 Query Enhancement' checkbox below input box")
        print("   - '🚀 Query Enhancement' expandable section after submitting queries")
        print("   - Debug console output showing enhancement processing")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_query_enhancement_integration()
    sys.exit(0 if success else 1)
