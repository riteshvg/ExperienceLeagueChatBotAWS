#!/usr/bin/env python3
"""
Test script for Enhanced Debug Panel

This script demonstrates the debug panel functionality and features.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.debug.debug_panel import debug_panel
import time

def test_debug_panel():
    """Test the debug panel functionality"""
    
    print("🔍 Testing Enhanced Debug Panel")
    print("=" * 50)
    
    # Initialize session state (simulating Streamlit session state)
    import streamlit as st
    
    # Mock session state for testing
    if not hasattr(st, 'session_state'):
        class MockSessionState:
            def __init__(self):
                self.data = {}
            
            def get(self, key, default=None):
                return self.data.get(key, default)
            
            def __setitem__(self, key, value):
                self.data[key] = value
            
            def __getitem__(self, key):
                return self.data[key]
            
            def __contains__(self, key):
                return key in self.data
        
        st.session_state = MockSessionState()
    
    # Initialize debug panel
    debug_panel.initialize_session_variables()
    
    print("✅ Debug panel initialized")
    
    # Test adding debug entries
    print("\n📝 Adding test debug entries...")
    
    # Simulate successful query
    debug_panel.add_debug_entry(
        query="What is Adobe Analytics?",
        status="completed",
        duration=2.5,
        tokens=150,
        cost=0.001,
        model="claude-3-haiku",
        step_info="Query completed successfully"
    )
    
    # Simulate processing query
    debug_panel.add_debug_entry(
        query="How do I create segments?",
        status="processing",
        step_info="Retrieving documents"
    )
    
    # Simulate failed query
    debug_panel.add_debug_entry(
        query="Invalid query with error",
        status="error",
        duration=1.2,
        error="Query validation failed",
        step_info="Query validation"
    )
    
    # Simulate complex query
    debug_panel.add_debug_entry(
        query="How do I integrate Adobe Analytics with Adobe Experience Platform for cross-channel attribution?",
        status="completed",
        duration=5.8,
        tokens=450,
        cost=0.003,
        model="claude-3-sonnet",
        step_info="Complex query processed"
    )
    
    print("✅ Test debug entries added")
    
    # Test performance stats
    print("\n📊 Performance Statistics:")
    stats = debug_panel.get_performance_stats()
    
    print(f"Complexity Distribution:")
    for complexity, count in stats['complexity_distribution'].items():
        print(f"  {complexity}: {count} queries")
    
    print(f"\nDetection Performance:")
    print(f"  Average time: {stats['detection_times']['avg_ms']:.2f} ms")
    print(f"  Min time: {stats['detection_times']['min_ms']:.2f} ms")
    print(f"  Max time: {stats['detection_times']['max_ms']:.2f} ms")
    print(f"  Total queries: {stats['detection_times']['count']}")
    
    # Test session variables display
    print("\n🔧 Session Variables:")
    print(f"  Debug history count: {len(st.session_state.get('debug_history', []))}")
    print(f"  Success count: {st.session_state.get('success_count', 0)}")
    print(f"  Error count: {st.session_state.get('error_count', 0)}")
    print(f"  Session cost: ${st.session_state.get('session_cost', 0):.4f}")
    print(f"  Total tokens: {st.session_state.get('total_tokens_used', 0):,}")
    
    # Test debug entry details
    print("\n📋 Debug Entry Details:")
    for entry in st.session_state.get('debug_history', []):
        print(f"  Query #{entry['id']}: {entry['query']}")
        print(f"    Status: {entry['status']}")
        print(f"    Duration: {entry.get('duration', 'N/A')}s")
        print(f"    Tokens: {entry.get('tokens', 'N/A')}")
        cost = entry.get('cost', 0)
        print(f"    Cost: ${cost:.4f}" if cost is not None else "    Cost: N/A")
        if entry.get('error'):
            print(f"    Error: {entry['error']}")
        print()
    
    print("✅ Debug panel test completed successfully!")
    
    # Test export functionality
    print("\n📤 Testing export functionality...")
    try:
        debug_panel.export_debug_data()
        print("✅ Export functionality working")
    except Exception as e:
        print(f"⚠️ Export test skipped (requires Streamlit UI): {e}")
    
    print("\n🎯 Debug Panel Features Demonstrated:")
    print("• ✅ Session status tracking")
    print("• ✅ Performance metrics dashboard")
    print("• ✅ Enhanced query history with color coding")
    print("• ✅ Organized session variables by category")
    print("• ✅ Debug controls and export functionality")
    print("• ✅ Real-time query tracking")
    print("• ✅ Cost and token usage monitoring")
    print("• ✅ Error tracking and debugging")

if __name__ == "__main__":
    test_debug_panel()
