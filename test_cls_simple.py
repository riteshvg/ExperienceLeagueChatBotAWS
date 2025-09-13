#!/usr/bin/env python3
"""
Simple CLS Analysis Test for app.py
"""

import sys
import os
sys.path.insert(0, '.')

def test_status_messages_in_main_functions():
    """Test that main page functions don't have status messages."""
    print("🧪 Testing status messages in main functions...")
    
    try:
        # Read the app.py file and check for status messages in main functions
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Find render_main_page_minimal function
        start = content.find('def render_main_page_minimal():')
        if start == -1:
            print("❌ render_main_page_minimal function not found")
            return False
        
        # Find the end of the function (next def or end of file)
        next_def = content.find('\ndef ', start + 1)
        if next_def == -1:
            next_def = len(content)
        
        function_content = content[start:next_def]
        
        # Check for status messages
        status_patterns = [
            'st.success(',
            'st.warning(',
            'st.error(',
            'st.info('
        ]
        
        found_messages = []
        for pattern in status_patterns:
            if pattern in function_content:
                # Find the line numbers
                lines = function_content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        found_messages.append(f"Line {i+1}: {line.strip()}")
        
        if found_messages:
            print(f"❌ Found {len(found_messages)} status messages in render_main_page_minimal:")
            for msg in found_messages:
                print(f"  - {msg}")
            return False
        else:
            print("✅ No status messages found in render_main_page_minimal")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_query_processing_status_messages():
    """Test query processing function for status messages."""
    print("🧪 Testing query processing status messages...")
    
    try:
        # Read the app.py file and check for status messages in query processing
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Find process_query_with_full_initialization function
        start = content.find('def process_query_with_full_initialization(')
        if start == -1:
            print("❌ process_query_with_full_initialization function not found")
            return False
        
        # Find the end of the function (next def or end of file)
        next_def = content.find('\ndef ', start + 1)
        if next_def == -1:
            next_def = len(content)
        
        function_content = content[start:next_def]
        
        # Check for status messages
        status_patterns = [
            'st.success(',
            'st.warning(',
            'st.error(',
            'st.info('
        ]
        
        found_messages = []
        for pattern in status_patterns:
            if pattern in function_content:
                # Find the line numbers
                lines = function_content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        found_messages.append(f"Line {i+1}: {line.strip()}")
        
        if found_messages:
            print(f"❌ Found {len(found_messages)} status messages in process_query_with_full_initialization:")
            for msg in found_messages:
                print(f"  - {msg}")
            return False
        else:
            print("✅ No status messages found in process_query_with_full_initialization")
            return True
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_main_function_uses_minimal():
    """Test that main function uses render_main_page_minimal."""
    print("🧪 Testing main function uses minimal render...")
    
    try:
        # Read the app.py file and check main function
        with open('app.py', 'r') as f:
            content = f.read()
        
        # Find main function
        start = content.find('def main():')
        if start == -1:
            print("❌ main function not found")
            return False
        
        # Find the end of the function (next def or end of file)
        next_def = content.find('\ndef ', start + 1)
        if next_def == -1:
            next_def = len(content)
        
        function_content = content[start:next_def]
        
        # Check for render_main_page_minimal call
        if 'render_main_page_minimal()' in function_content:
            print("✅ main function calls render_main_page_minimal()")
            return True
        else:
            print("❌ main function does not call render_main_page_minimal()")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run all CLS analysis tests."""
    print("🔍 Simple CLS Analysis Test Suite")
    print("=" * 50)
    
    tests = [
        ("Status Messages in Main Functions", test_status_messages_in_main_functions),
        ("Query Processing Status Messages", test_query_processing_status_messages),
        ("Main Function Uses Minimal", test_main_function_uses_minimal)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
        print(f"Result: {'✅ PASS' if result else '❌ FAIL'}")
    
    print("\n📊 Test Summary")
    print("=" * 50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! CLS should be optimized.")
    else:
        print("⚠️ Some tests failed. CLS issues may still exist.")
    
    return passed == total

if __name__ == "__main__":
    main()
