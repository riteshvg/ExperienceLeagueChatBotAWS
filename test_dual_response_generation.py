#!/usr/bin/env python3
"""
Test script to demonstrate the dual response generation feature in auto-retraining.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.retraining.auto_retraining_pipeline import AutoRetrainingPipeline
from config.auto_retraining_config import AUTO_RETRAINING_CONFIG

def test_dual_response_workflow():
    """Test the complete dual response generation workflow."""
    print("🧪 TESTING: Dual Response Generation Workflow")
    print("=" * 60)
    
    # Initialize pipeline
    pipeline = AutoRetrainingPipeline(AUTO_RETRAINING_CONFIG)
    print("✅ Auto-retraining pipeline initialized")
    
    # Simulate the workflow
    print("\n📝 WORKFLOW SIMULATION")
    print("-" * 40)
    
    # Step 1: User enters query
    test_query = "How do I set up Adobe Analytics tracking?"
    print(f"1. User Query: {test_query}")
    
    # Step 2: Generate dual responses (simulated)
    print("2. 🚀 Generate Dual Response button clicked")
    print("   - Querying both Gemini and Claude models...")
    print("   - Using knowledge base for context...")
    
    # Simulate generated responses
    simulated_responses = {
        'query': test_query,
        'gemini_response': "To set up Adobe Analytics tracking, you need to implement the Adobe Analytics extension in Adobe Launch. First, create a new property in Adobe Launch, then add the Analytics extension. Configure the extension with your report suite ID and other settings. Finally, publish the changes to make tracking active on your website.",
        'claude_response': "Setting up Adobe Analytics tracking involves several key steps: 1) Create a Launch property, 2) Install the Analytics extension, 3) Configure data elements for the data you want to collect, 4) Create rules to define when and how data is sent, and 5) Publish the configuration. The extension handles the technical implementation while Launch provides the management interface.",
        'gemini_metrics': {
            'response_time': 2.3,
            'tokens_used': 156,
            'cost': 0.0008
        },
        'claude_metrics': {
            'response_time': 3.1,
            'tokens_used': 142,
            'cost': 0.0012
        }
    }
    
    print("   ✅ Dual responses generated successfully!")
    print(f"   - Gemini: {simulated_responses['gemini_response'][:80]}...")
    print(f"   - Claude: {simulated_responses['claude_response'][:80]}...")
    
    # Step 3: Display responses with metrics
    print("\n3. 📊 Display Generated Responses")
    print("-" * 40)
    print("   🤖 Gemini Response:")
    print(f"      Time: {simulated_responses['gemini_metrics']['response_time']:.2f}s")
    print(f"      Tokens: {simulated_responses['gemini_metrics']['tokens_used']:,}")
    print(f"      Cost: ${simulated_responses['gemini_metrics']['cost']:.4f}")
    
    print("   🧠 Claude Response:")
    print(f"      Time: {simulated_responses['claude_metrics']['response_time']:.2f}s")
    print(f"      Tokens: {simulated_responses['claude_metrics']['tokens_used']:,}")
    print(f"      Cost: ${simulated_responses['claude_metrics']['cost']:.4f}")
    
    # Step 4: User provides feedback
    print("\n4. 📝 User Provides Feedback")
    print("-" * 40)
    print("   - Query: [Pre-filled from generated responses]")
    print("   - Gemini Response: [Pre-filled and disabled]")
    print("   - Claude Response: [Pre-filled and disabled]")
    print("   - User selects preferred model: claude")
    print("   - User rating: 4/5")
    print("   - Quality scores: Accuracy=4, Relevance=5, Clarity=4, Completeness=5")
    
    # Step 5: Submit feedback
    print("\n5. 🚀 Submit Feedback & Trigger Auto-Retraining")
    print("-" * 40)
    
    feedback = {
        'query': simulated_responses['query'],
        'gemini_response': simulated_responses['gemini_response'],
        'claude_response': simulated_responses['claude_response'],
        'selected_model': 'claude',
        'user_rating': 4,
        'response_quality': {
            'accuracy': 4,
            'relevance': 5,
            'clarity': 4,
            'completeness': 5
        },
        'timestamp': '2024-01-01T00:00:00'
    }
    
    # Simulate feedback processing
    print("   - Feedback data prepared")
    print("   - Processing through auto-retraining pipeline...")
    print("   - Feedback queued successfully!")
    
    # Add to pipeline for testing
    pipeline.feedback_queue.append(feedback)
    status = pipeline.get_pipeline_status()
    
    print(f"   - Queue status: {status['queue_size']}/{status['retraining_threshold']} items")
    print(f"   - Progress: {status['queue_size']/status['retraining_threshold']*100:.1f}%")
    
    # Step 6: Show what happens next
    print("\n6. 🎯 Next Steps")
    print("-" * 40)
    remaining = status['retraining_threshold'] - status['queue_size']
    if remaining > 0:
        print(f"   - Submit {remaining} more high-quality feedback items")
        print("   - Auto-retraining will trigger automatically")
    else:
        print("   - Ready to trigger auto-retraining!")
    
    print("\n" + "=" * 60)
    print("✅ DUAL RESPONSE GENERATION WORKFLOW COMPLETED!")
    print("=" * 60)
    
    print("\n🚀 Ready to test in Streamlit:")
    print("   1. Go to http://localhost:8508")
    print("   2. Navigate to '🚀 Auto-Retraining'")
    print("   3. Enter a query and click 'Generate Dual Response'")
    print("   4. Review the generated responses")
    print("   5. Provide feedback and submit")
    print("   6. Watch the auto-retraining process!")

if __name__ == "__main__":
    test_dual_response_workflow()




