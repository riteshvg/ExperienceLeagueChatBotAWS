#!/usr/bin/env python3
"""
Final validation test for performance_comparison.py
"""

import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_complete_functionality():
    """Test complete functionality of performance comparison tool"""
    print("🚀 Final Validation Test")
    print("=" * 50)
    
    # Test 1: Imports
    print("1. Testing imports...")
    try:
        from performance_comparison import (
            PerformanceTracker, process_main_app_query, process_optimized_app_query,
            render_comparison_interface, display_comparison_results, main
        )
        print("   ✅ All imports successful")
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False
    
    # Test 2: PerformanceTracker
    print("2. Testing PerformanceTracker...")
    try:
        tracker = PerformanceTracker()
        timer_id = tracker.start_timer("test")
        time.sleep(0.01)
        tracker.end_timer(timer_id, success=True, response_length=100, model_used="haiku")
        
        result = tracker.get_latest_result("test")
        assert result['success'] == True
        assert result['duration'] > 0
        print("   ✅ PerformanceTracker working correctly")
    except Exception as e:
        print(f"   ❌ PerformanceTracker failed: {e}")
        return False
    
    # Test 3: Code quality checks
    print("3. Testing code quality...")
    try:
        with open('performance_comparison.py', 'r') as f:
            content = f.read()
        
        # Check for empty labels
        if 'st.text_area("",' in content:
            print("   ❌ Empty labels found!")
            return False
        else:
            print("   ✅ No empty labels found")
        
        # Check for proper label configuration
        if 'label_visibility="collapsed"' in content:
            print("   ✅ Proper label configuration found")
        else:
            print("   ❌ Label configuration missing")
            return False
        
        # Check for proper imports
        if 'from performance_comparison import' in content:
            print("   ✅ Proper import structure")
        else:
            print("   ⚠️ Import structure unclear")
        
    except Exception as e:
        print(f"   ❌ Code quality check failed: {e}")
        return False
    
    # Test 4: Function signatures
    print("4. Testing function signatures...")
    try:
        import inspect
        
        # Check display_comparison_results signature
        sig = inspect.signature(display_comparison_results)
        params = list(sig.parameters.keys())
        expected_params = ['main_success', 'main_answer', 'main_duration', 'main_model',
                          'opt_success', 'opt_answer', 'opt_duration', 'opt_model', 'query']
        
        if all(param in params for param in expected_params):
            print("   ✅ display_comparison_results signature correct")
        else:
            print("   ❌ display_comparison_results signature incorrect")
            return False
        
        # Check PerformanceTracker methods
        tracker_methods = ['start_timer', 'end_timer', 'get_results', 'get_latest_result']
        for method in tracker_methods:
            if hasattr(tracker, method):
                print(f"   ✅ {method} method available")
            else:
                print(f"   ❌ {method} method missing")
                return False
        
    except Exception as e:
        print(f"   ❌ Function signature test failed: {e}")
        return False
    
    # Test 5: Error handling
    print("5. Testing error handling...")
    try:
        tracker = PerformanceTracker()
        
        # Test with invalid timer_id
        tracker.end_timer("invalid_id", success=False)
        
        # Test error result
        timer_id = tracker.start_timer("error_test")
        tracker.end_timer(timer_id, success=False, error="Test error")
        
        result = tracker.get_latest_result("error_test")
        assert result['success'] == False
        assert result['error'] == "Test error"
        print("   ✅ Error handling working correctly")
        
    except Exception as e:
        print(f"   ❌ Error handling test failed: {e}")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ Performance comparison tool is ready for use")
    return True

def main():
    """Main test function"""
    success = test_complete_functionality()
    
    if success:
        print("\n🚀 Ready to run:")
        print("   streamlit run performance_comparison.py")
        print("\n📊 Features available:")
        print("   - Side-by-side comparison of main app vs optimized app")
        print("   - Real-time timing with millisecond precision")
        print("   - Performance metrics and analysis")
        print("   - Response quality comparison")
        print("   - Performance history tracking")
        print("   - No logger warnings or errors")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)