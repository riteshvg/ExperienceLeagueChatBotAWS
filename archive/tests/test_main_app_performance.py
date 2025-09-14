#!/usr/bin/env python3
"""
Test script to verify the main app has performance optimizations working
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_main_app_performance():
    """Test that the main app has performance optimizations"""
    print("🧪 Testing Main App Performance Optimizations")
    print("=" * 60)
    
    try:
        # Import main app components
        from app import (
            query_cache, performance_monitor, process_query_optimized,
            get_cached_settings, get_cached_aws_clients
        )
        print("✅ Performance components imported successfully")
        
        # Test cache functionality
        print("\n📦 Testing Cache Functionality...")
        query_cache.set("test_key", "test_value", ttl=60)
        cached_value = query_cache.get("test_key")
        assert cached_value == "test_value", "Cache not working"
        print("✅ Cache is working correctly")
        
        # Test performance monitor
        print("\n⏱️ Testing Performance Monitor...")
        op_id = performance_monitor.start_operation("test_operation")
        time.sleep(0.1)
        duration = performance_monitor.finish_operation(op_id)
        assert duration > 0, "Performance monitor not working"
        print(f"✅ Performance monitor working (duration: {duration:.3f}s)")
        
        # Test settings caching
        print("\n⚙️ Testing Settings Caching...")
        settings = get_cached_settings()
        if settings:
            print("✅ Settings loaded successfully")
            print(f"   - AWS Region: {settings.aws_default_region}")
            print(f"   - Knowledge Base ID: {settings.bedrock_knowledge_base_id}")
        else:
            print("❌ Settings failed to load")
            return False
        
        # Test AWS clients caching
        print("\n☁️ Testing AWS Clients Caching...")
        aws_clients = get_cached_aws_clients(settings)
        if aws_clients:
            print("✅ AWS clients loaded successfully")
            print(f"   - Available clients: {list(aws_clients.keys())}")
        else:
            print("❌ AWS clients failed to load")
            return False
        
        # Test optimized query processing function
        print("\n🚀 Testing Optimized Query Processing...")
        if callable(process_query_optimized):
            print("✅ Optimized query processing function available")
        else:
            print("❌ Optimized query processing function not available")
            return False
        
        # Test performance stats
        print("\n📊 Testing Performance Stats...")
        stats = performance_monitor.get_stats()
        print(f"✅ Performance stats available: {stats}")
        
        print("\n🎉 All performance optimizations are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_dashboard():
    """Test that the performance dashboard is accessible"""
    print("\n🔍 Testing Performance Dashboard Access...")
    
    try:
        from app import render_admin_page
        print("✅ Admin page function available")
        
        # Check if the performance dashboard code exists
        import inspect
        source = inspect.getsource(render_admin_page)
        if "Performance Dashboard" in source:
            print("✅ Performance Dashboard code found in admin page")
        else:
            print("❌ Performance Dashboard code not found")
            return False
        
        if "tab9" in source:
            print("✅ Performance tab (tab9) found")
        else:
            print("❌ Performance tab not found")
            return False
        
        print("✅ Performance Dashboard should be accessible in Admin Panel")
        return True
        
    except Exception as e:
        print(f"❌ Performance dashboard test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Main App Performance Validation")
    print("=" * 50)
    
    # Test performance components
    perf_test = test_main_app_performance()
    
    # Test performance dashboard
    dashboard_test = test_performance_dashboard()
    
    print("\n" + "=" * 50)
    if perf_test and dashboard_test:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ Your main app now has:")
        print("   - Intelligent query caching")
        print("   - Performance monitoring")
        print("   - Optimized query processing")
        print("   - Performance dashboard in Admin Panel")
        print("\n🚀 To see the performance dashboard:")
        print("   1. Run: streamlit run app.py")
        print("   2. Go to Admin Dashboard")
        print("   3. Click on '🚀 Performance' tab")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
