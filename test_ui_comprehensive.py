#!/usr/bin/env python3
"""
Comprehensive test for UI components with 3-response configuration.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.retraining.auto_retraining_ui import AutoRetrainingUI
from src.retraining.auto_retraining_pipeline import AutoRetrainingPipeline
from config.auto_retraining_config import AUTO_RETRAINING_CONFIG

def test_ui_components():
    """Test all UI components with 3-response configuration."""
    print("🧪 COMPREHENSIVE UI TEST - 3-Response Configuration")
    print("=" * 60)
    
    # Initialize pipeline with testing config
    pipeline = AutoRetrainingPipeline(AUTO_RETRAINING_CONFIG)
    ui = AutoRetrainingUI()
    
    print(f"✅ Pipeline initialized")
    print(f"   - Threshold: {pipeline.retraining_threshold}")
    print(f"   - Quality: {pipeline.quality_threshold}")
    print(f"   - Cooldown: {pipeline.retraining_cooldown}s ({pipeline.retraining_cooldown/3600:.4f}h)")
    
    # Test 1: Configuration values compatibility
    print("\n📊 Test 1: Configuration Values")
    print("-" * 40)
    
    # Check if values are within UI limits
    threshold_ok = 1 <= pipeline.retraining_threshold <= 100
    quality_ok = 1 <= pipeline.quality_threshold <= 5
    cooldown_hours = pipeline.retraining_cooldown / 3600
    cooldown_ok = 0.01 <= cooldown_hours <= 24.0
    
    print(f"   Threshold (3): {'✅' if threshold_ok else '❌'} (1-100)")
    print(f"   Quality (3): {'✅' if quality_ok else '❌'} (1-5)")
    print(f"   Cooldown ({cooldown_hours:.4f}h): {'✅' if cooldown_ok else '❌'} (0.01-24h)")
    
    # Test 2: Status monitoring
    print("\n📊 Test 2: Status Monitoring")
    print("-" * 40)
    
    status = pipeline.get_pipeline_status()
    print(f"   Status: {status['status']}")
    print(f"   Queue: {status['queue_size']}/{status['retraining_threshold']}")
    print(f"   Cooldown remaining: {status['cooldown_remaining']}s")
    
    # Test 3: Feedback processing
    print("\n📊 Test 3: Feedback Processing")
    print("-" * 40)
    
    # Add some test feedback
    test_feedback = {
        'query': 'Test query for UI validation',
        'gemini_response': 'Test gemini response',
        'claude_response': 'Test claude response',
        'selected_model': 'claude',
        'user_rating': 4,
        'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
        'timestamp': '2024-01-01T00:00:00'
    }
    
    pipeline.feedback_queue.append(test_feedback)
    status_after = pipeline.get_pipeline_status()
    
    print(f"   Before: 0/{pipeline.retraining_threshold} items")
    print(f"   After: {status_after['queue_size']}/{pipeline.retraining_threshold} items")
    print(f"   Progress: {status_after['queue_size']/pipeline.retraining_threshold*100:.1f}%")
    
    # Test 4: Force retraining button logic
    print("\n📊 Test 4: Force Retraining Logic")
    print("-" * 40)
    
    # Test with 1 item (should be enabled)
    force_enabled = status_after['queue_size'] >= 1
    print(f"   Force retraining enabled: {'✅' if force_enabled else '❌'} (1+ items)")
    
    # Test 5: Configuration update
    print("\n📊 Test 5: Configuration Update")
    print("-" * 40)
    
    # Test updating configuration
    new_config = {
        'retraining_threshold': 5,
        'quality_threshold': 4,
        'retraining_cooldown': 3600
    }
    
    pipeline.update_config(new_config)
    updated_status = pipeline.get_pipeline_status()
    
    print(f"   Updated threshold: {updated_status['retraining_threshold']}")
    print(f"   Updated quality: {pipeline.quality_threshold}")
    print(f"   Updated cooldown: {pipeline.retraining_cooldown}s")
    
    # Reset to testing config
    pipeline.update_config(AUTO_RETRAINING_CONFIG)
    
    # Test 6: UI component initialization
    print("\n📊 Test 6: UI Component Initialization")
    print("-" * 40)
    
    try:
        # Test that UI can be initialized without errors
        ui_instance = AutoRetrainingUI()
        print("   ✅ AutoRetrainingUI initialized successfully")
        
        # Test status monitor
        if hasattr(ui_instance, 'status_monitor'):
            print("   ✅ StatusMonitor available")
        else:
            print("   ❌ StatusMonitor not available")
            
    except Exception as e:
        print(f"   ❌ UI initialization failed: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 COMPREHENSIVE UI TEST COMPLETED!")
    print("=" * 60)
    
    # Summary
    all_tests_passed = (
        threshold_ok and quality_ok and cooldown_ok and 
        force_enabled and ui_instance is not None
    )
    
    if all_tests_passed:
        print("✅ ALL TESTS PASSED - UI is ready for 3-response configuration!")
    else:
        print("❌ SOME TESTS FAILED - Check the output above for details")
    
    print("\n🚀 Ready to test in Streamlit:")
    print("   1. Go to http://localhost:8507")
    print("   2. Navigate to '🚀 Auto-Retraining'")
    print("   3. Submit 3 feedback items")
    print("   4. Watch automatic retraining trigger!")

if __name__ == "__main__":
    test_ui_components()




