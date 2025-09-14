#!/usr/bin/env python3
"""
Basic test for the simplified optimized Streamlit app
"""

import sys
import os
import time

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work"""
    print("🧪 Testing imports...")
    
    try:
        from src.performance.simple_optimized_app import (
            SimpleLRUCache, 
            SimplePerformanceMonitor, 
            OptimizedStreamlitApp
        )
        print("✅ Successfully imported optimized app components")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_cache_functionality():
    """Test cache functionality"""
    print("\n🧪 Testing cache functionality...")
    
    try:
        from src.performance.simple_optimized_app import SimpleLRUCache
        
        # Test basic operations
        cache = SimpleLRUCache(max_size=3, default_ttl=1)
        
        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        print("✅ Basic cache operations work")
        
        # Test TTL
        cache.set("ttl_key", "ttl_value", ttl=0.1)
        assert cache.get("ttl_key") == "ttl_value"
        time.sleep(0.2)
        assert cache.get("ttl_key") is None
        print("✅ Cache TTL works")
        
        # Test LRU eviction
        for i in range(4):
            cache.set(f"key_{i}", f"value_{i}")
        assert cache.get("key_0") is None  # Should be evicted
        assert cache.get("key_3") == "value_3"  # Should still be there
        print("✅ Cache LRU eviction works")
        
        # Test clear
        cache.clear()
        assert cache.get("key_3") is None
        print("✅ Cache clear works")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_monitor():
    """Test performance monitor"""
    print("\n🧪 Testing performance monitor...")
    
    try:
        from src.performance.simple_optimized_app import SimplePerformanceMonitor
        
        monitor = SimplePerformanceMonitor()
        
        # Test single operation
        op_id = monitor.start_operation("test")
        time.sleep(0.1)
        duration = monitor.finish_operation(op_id)
        assert duration > 0.09 and duration < 0.2
        print("✅ Single operation timing works")
        
        # Test multiple operations
        for i in range(5):
            op_id = monitor.start_operation("test")
            time.sleep(0.01)
            monitor.finish_operation(op_id)
        
        stats = monitor.get_stats()
        assert "test" in stats
        assert stats["test"]["count"] == 6  # 1 + 5
        print("✅ Multiple operations tracking works")
        
        # Test invalid operation
        duration = monitor.finish_operation("nonexistent")
        assert duration == 0.0
        print("✅ Invalid operation handling works")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_initialization():
    """Test app initialization without external dependencies"""
    print("\n🧪 Testing app initialization...")
    
    try:
        from src.performance.simple_optimized_app import OptimizedStreamlitApp
        
        # This should work even if external dependencies are missing
        app = OptimizedStreamlitApp()
        assert app is not None
        print("✅ App initialization works")
        
        # Test that components are None when dependencies are missing
        # (This is expected behavior)
        print(f"Settings available: {app.settings is not None}")
        print(f"AWS clients available: {app.aws_clients is not None}")
        print(f"Smart router available: {app.smart_router is not None}")
        print(f"Analytics service available: {app.analytics_service is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ App initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_query_processing_without_dependencies():
    """Test query processing when dependencies are missing"""
    print("\n🧪 Testing query processing without dependencies...")
    
    try:
        from src.performance.simple_optimized_app import OptimizedStreamlitApp
        
        app = OptimizedStreamlitApp()
        
        # Test query processing when smart router is not available
        result = app.process_query_optimized("test query")
        
        # Should return error result
        assert "success" in result
        assert result["success"] == False
        assert "error" in result
        print("✅ Query processing error handling works")
        
        return True
        
    except Exception as e:
        print(f"❌ Query processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all basic tests"""
    print("🚀 Running Basic Tests for Simple Optimized App")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_cache_functionality,
        test_performance_monitor,
        test_app_initialization,
        test_query_processing_without_dependencies
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The optimized app is ready to use.")
        print("\n🚀 To run the app:")
        print("streamlit run src/performance/simple_optimized_app.py")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
