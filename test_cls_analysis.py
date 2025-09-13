#!/usr/bin/env python3
"""
CLS Analysis Test for app.py
Tests for status messages and layout shifts that could cause CLS issues.
"""

import sys
import os
sys.path.insert(0, '.')

import streamlit as st
from unittest.mock import Mock, patch
import time

def test_status_messages_removed():
    """Test that status messages are removed from main page functions."""
    print("🧪 Testing status messages removal...")
    
    try:
        from app import render_main_page_minimal, render_main_page
        
        # Mock streamlit components
        with patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.header'), \
             patch('streamlit.text_input'), \
             patch('streamlit.button'), \
             patch('streamlit.container'), \
             patch('streamlit.columns'), \
             patch('streamlit.empty'), \
             patch('streamlit.progress'), \
             patch('streamlit.spinner'), \
             patch('streamlit.metric'), \
             patch('streamlit.success'), \
             patch('streamlit.warning'), \
             patch('streamlit.error'), \
             patch('streamlit.info'), \
             patch('streamlit.expander'), \
             patch('streamlit.caption'), \
             patch('streamlit.subheader'), \
             patch('streamlit.session_state', {}):
            
            # Track status messages
            status_messages = []
            
            def mock_success(message):
                status_messages.append(('success', message))
                print(f"  ❌ Found success message: {message}")
            
            def mock_warning(message):
                status_messages.append(('warning', message))
                print(f"  ❌ Found warning message: {message}")
            
            def mock_error(message):
                status_messages.append(('error', message))
                print(f"  ❌ Found error message: {message}")
            
            def mock_info(message):
                status_messages.append(('info', message))
                print(f"  ❌ Found info message: {message}")
            
            # Mock the status message functions
            with patch('streamlit.success', side_effect=mock_success), \
                 patch('streamlit.warning', side_effect=mock_warning), \
                 patch('streamlit.error', side_effect=mock_error), \
                 patch('streamlit.info', side_effect=mock_info):
                
                # Test render_main_page_minimal
                print("  Testing render_main_page_minimal...")
                try:
                    render_main_page_minimal()
                    print(f"  ✅ render_main_page_minimal completed - {len(status_messages)} status messages found")
                except Exception as e:
                    print(f"  ❌ render_main_page_minimal failed: {e}")
                
                # Reset for next test
                status_messages.clear()
                
                # Test render_main_page with mocked parameters
                print("  Testing render_main_page...")
                try:
                    mock_settings = Mock()
                    mock_aws_clients = {'bedrock': Mock()}
                    render_main_page(mock_settings, mock_aws_clients, None, True, None, Mock())
                    print(f"  ✅ render_main_page completed - {len(status_messages)} status messages found")
                except Exception as e:
                    print(f"  ❌ render_main_page failed: {e}")
                
                return len(status_messages) == 0
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_query_processing_status_messages():
    """Test query processing function for status messages."""
    print("🧪 Testing query processing status messages...")
    
    try:
        from app import process_query_with_full_initialization
        
        # Mock dependencies
        with patch('streamlit.container'), \
             patch('streamlit.columns'), \
             patch('streamlit.empty'), \
             patch('streamlit.progress'), \
             patch('streamlit.spinner'), \
             patch('streamlit.metric'), \
             patch('streamlit.success'), \
             patch('streamlit.warning'), \
             patch('streamlit.error'), \
             patch('streamlit.info'), \
             patch('streamlit.expander'), \
             patch('streamlit.session_state', {}), \
             patch('app.save_chat_message'), \
             patch('app.process_query_optimized', return_value={'success': True, 'answer': 'Test answer'}):
            
            # Track status messages
            status_messages = []
            
            def mock_success(message):
                status_messages.append(('success', message))
                print(f"  ❌ Found success message: {message}")
            
            def mock_warning(message):
                status_messages.append(('warning', message))
                print(f"  ❌ Found warning message: {message}")
            
            def mock_error(message):
                status_messages.append(('error', message))
                print(f"  ❌ Found error message: {message}")
            
            def mock_info(message):
                status_messages.append(('info', message))
                print(f"  ❌ Found info message: {message}")
            
            # Mock the status message functions
            with patch('streamlit.success', side_effect=mock_success), \
                 patch('streamlit.warning', side_effect=mock_warning), \
                 patch('streamlit.error', side_effect=mock_error), \
                 patch('streamlit.info', side_effect=mock_info):
                
                # Test process_query_with_full_initialization
                print("  Testing process_query_with_full_initialization...")
                try:
                    mock_settings = Mock()
                    mock_aws_clients = {'bedrock': Mock()}
                    mock_smart_router = Mock()
                    mock_analytics_service = Mock()
                    
                    process_query_with_full_initialization(
                        "test query", 
                        mock_settings, 
                        mock_aws_clients, 
                        mock_smart_router, 
                        mock_analytics_service
                    )
                    print(f"  ✅ process_query_with_full_initialization completed - {len(status_messages)} status messages found")
                except Exception as e:
                    print(f"  ❌ process_query_with_full_initialization failed: {e}")
                
                return len(status_messages) == 0
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_function_flow():
    """Test main function flow to ensure minimal path is used."""
    print("🧪 Testing main function flow...")
    
    try:
        from app import main
        
        # Mock streamlit components
        with patch('streamlit.sidebar.selectbox', return_value="🏠 Main Chat"), \
             patch('streamlit.title'), \
             patch('streamlit.markdown'), \
             patch('streamlit.header'), \
             patch('streamlit.text_input'), \
             patch('streamlit.button'), \
             patch('streamlit.container'), \
             patch('streamlit.columns'), \
             patch('streamlit.empty'), \
             patch('streamlit.progress'), \
             patch('streamlit.spinner'), \
             patch('streamlit.metric'), \
             patch('streamlit.success'), \
             patch('streamlit.warning'), \
             patch('streamlit.error'), \
             patch('streamlit.info'), \
             patch('streamlit.expander'), \
             patch('streamlit.caption'), \
             patch('streamlit.subheader'), \
             patch('streamlit.session_state', {}):
            
            # Track which function is called
            called_functions = []
            
            def mock_render_main_page_minimal():
                called_functions.append('render_main_page_minimal')
                print("  ✅ render_main_page_minimal called")
            
            def mock_render_admin_page():
                called_functions.append('render_admin_page')
                print("  ❌ render_admin_page called (should not be called for main chat)")
            
            # Mock the render functions
            with patch('app.render_main_page_minimal', side_effect=mock_render_main_page_minimal), \
                 patch('app.render_admin_page', side_effect=mock_render_admin_page):
                
                # Test main function
                print("  Testing main function with Main Chat selection...")
                try:
                    main()
                    print(f"  ✅ main function completed - called functions: {called_functions}")
                    return 'render_main_page_minimal' in called_functions and 'render_admin_page' not in called_functions
                except Exception as e:
                    print(f"  ❌ main function failed: {e}")
                    return False
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all CLS analysis tests."""
    print("🔍 CLS Analysis Test Suite")
    print("=" * 50)
    
    tests = [
        ("Status Messages Removed", test_status_messages_removed),
        ("Query Processing Status Messages", test_query_processing_status_messages),
        ("Main Function Flow", test_main_function_flow)
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
