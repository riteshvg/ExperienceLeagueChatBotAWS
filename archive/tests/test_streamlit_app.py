#!/usr/bin/env python3
"""
Test that the Streamlit app can be imported and initialized without errors
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_streamlit_import():
    """Test that the Streamlit app can be imported"""
    print("🧪 Testing Streamlit app import...")
    
    try:
        # Test importing the app module
        import src.performance.simple_optimized_app as app_module
        print("✅ Successfully imported app module")
        
        # Test that the main classes exist
        assert hasattr(app_module, 'SimpleLRUCache')
        assert hasattr(app_module, 'SimplePerformanceMonitor')
        assert hasattr(app_module, 'OptimizedStreamlitApp')
        print("✅ All required classes are available")
        
        # Test that the main function exists
        assert hasattr(app_module, 'main')
        print("✅ Main function is available")
        
        return True
        
    except Exception as e:
        print(f"❌ Streamlit app import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_creation():
    """Test that the app can be created"""
    print("\n🧪 Testing app creation...")
    
    try:
        from src.performance.simple_optimized_app import OptimizedStreamlitApp
        
        # Create app instance
        app = OptimizedStreamlitApp()
        assert app is not None
        print("✅ App instance created successfully")
        
        # Test that main methods exist
        assert hasattr(app, 'process_query_optimized')
        assert hasattr(app, 'render_optimized_chat_interface')
        assert hasattr(app, 'render_admin_dashboard')
        assert hasattr(app, 'run')
        print("✅ All required methods are available")
        
        return True
        
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_global_instances():
    """Test that global instances work"""
    print("\n🧪 Testing global instances...")
    
    try:
        from src.performance.simple_optimized_app import query_cache, performance_monitor
        
        # Test cache
        assert query_cache is not None
        query_cache.set("test", "value")
        assert query_cache.get("test") == "value"
        print("✅ Global cache instance works")
        
        # Test performance monitor
        assert performance_monitor is not None
        op_id = performance_monitor.start_operation("test")
        duration = performance_monitor.finish_operation(op_id)
        assert duration >= 0
        print("✅ Global performance monitor works")
        
        return True
        
    except Exception as e:
        print(f"❌ Global instances test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all Streamlit app tests"""
    print("🚀 Testing Streamlit App Components")
    print("=" * 50)
    
    tests = [
        test_streamlit_import,
        test_app_creation,
        test_global_instances
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Streamlit app tests passed!")
        print("\n✅ The app is ready to run with:")
        print("streamlit run src/performance/simple_optimized_app.py")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
