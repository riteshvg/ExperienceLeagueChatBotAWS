#!/usr/bin/env python3
"""
Test script to demonstrate auto-retraining with just 3 responses.
Shows the complete workflow from feedback submission to retraining trigger.
"""

import asyncio
import time
from datetime import datetime
from src.retraining.auto_retraining_pipeline import AutoRetrainingPipeline
from config.auto_retraining_config import AUTO_RETRAINING_CONFIG

def print_test_header():
    """Print test header."""
    print("🧪 TESTING: Auto-Retraining with 3 Responses")
    print("=" * 60)
    print("Configuration:")
    print(f"   - Retraining threshold: {AUTO_RETRAINING_CONFIG['retraining_threshold']} responses")
    print(f"   - Quality threshold: {AUTO_RETRAINING_CONFIG['quality_threshold']}/5")
    print(f"   - Cooldown: {AUTO_RETRAINING_CONFIG['retraining_cooldown']} seconds")
    print("=" * 60)

def print_feedback_submission(feedback_num, feedback):
    """Print feedback submission details."""
    print(f"\n📝 FEEDBACK #{feedback_num} SUBMISSION")
    print("-" * 40)
    print(f"Query: {feedback['query'][:60]}...")
    print(f"Selected Model: {feedback['selected_model']}")
    print(f"User Rating: {'⭐' * feedback['user_rating']} ({feedback['user_rating']}/5)")
    print(f"Quality: Accuracy={feedback['response_quality']['accuracy']}, "
          f"Relevance={feedback['response_quality']['relevance']}")

def print_processing_result(result, pipeline):
    """Print the processing result."""
    print(f"\n🔄 PROCESSING RESULT")
    print("-" * 40)
    
    if result['status'] == 'queued':
        print("✅ STATUS: FEEDBACK QUEUED")
        print(f"📝 Message: {result['message']}")
        
        # Show queue progress
        status = pipeline.get_pipeline_status()
        progress = min(status['queue_size'] / status['retraining_threshold'], 1.0)
        progress_bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
        print(f"📊 Queue Progress: [{progress_bar}] {status['queue_size']}/{status['retraining_threshold']} items")
        
        remaining = status['retraining_threshold'] - status['queue_size']
        if remaining > 0:
            print(f"🎯 Next: {remaining} more responses needed to trigger retraining")
        else:
            print("🚀 Ready to trigger retraining on next submission!")
            
    elif result['status'] == 'retraining_started':
        print("🚀 STATUS: AUTO-RETRAINING STARTED!")
        print(f"📊 Training Data Size: {result['training_data_size']} examples")
        print(f"🔧 Jobs Started: {len(result['jobs'])} models")
        
        for job in result['jobs']:
            if job.get('status') == 'started':
                print(f"✅ {job['model_type'].title()} job: {job.get('job_name', 'N/A')}")
        
        print("🔄 Models are being trained with your feedback...")
        
    else:
        print("❌ STATUS: ERROR")
        print(f"Error: {result['message']}")

async def test_3_response_retraining():
    """Test the 3-response retraining workflow."""
    print_test_header()
    
    # Initialize pipeline
    pipeline = AutoRetrainingPipeline(AUTO_RETRAINING_CONFIG)
    print("✅ Pipeline initialized with TESTING configuration")
    
    # Sample feedback data
    sample_feedbacks = [
        {
            'query': 'How do I set up Adobe Analytics tracking?',
            'gemini_response': 'To set up Adobe Analytics tracking, you need to implement the Adobe Analytics extension in Adobe Launch...',
            'claude_response': 'Setting up Adobe Analytics tracking involves configuring the Adobe Analytics extension, setting up data elements, and creating rules...',
            'selected_model': 'claude',
            'user_rating': 4,
            'response_quality': {
                'accuracy': 4, 'relevance': 5, 'clarity': 4, 'completeness': 5
            },
            'timestamp': datetime.now().isoformat()
        },
        {
            'query': 'What is Customer Journey Analytics?',
            'gemini_response': 'Customer Journey Analytics (CJA) is a next-generation analytics workspace that allows you to analyze customer journeys across channels...',
            'claude_response': 'Customer Journey Analytics is Adobe\'s cross-channel analytics solution that provides a unified view of customer interactions...',
            'selected_model': 'both',
            'user_rating': 5,
            'response_quality': {
                'accuracy': 5, 'relevance': 5, 'clarity': 5, 'completeness': 5
            },
            'timestamp': datetime.now().isoformat()
        },
        {
            'query': 'How to create segments in Adobe Analytics?',
            'gemini_response': 'Creating segments in Adobe Analytics involves using the Segment Builder to define criteria based on dimensions and metrics...',
            'claude_response': 'To create segments in Adobe Analytics, navigate to the Segment Builder and use the drag-and-drop interface to define your criteria...',
            'selected_model': 'gemini',
            'user_rating': 3,
            'response_quality': {
                'accuracy': 3, 'relevance': 4, 'clarity': 3, 'completeness': 4
            },
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    # Process each feedback
    for i, feedback in enumerate(sample_feedbacks, 1):
        print_feedback_submission(i, feedback)
        
        # Process feedback
        print("🔄 Processing feedback...")
        await asyncio.sleep(1)  # Simulate processing time
        
        result = await pipeline.process_feedback_async(feedback)
        print_processing_result(result, pipeline)
        
        # Show current status
        status = pipeline.get_pipeline_status()
        print(f"📊 Current Status: {status['queue_size']}/{status['retraining_threshold']} items in queue")
        
        if i < len(sample_feedbacks):
            print(f"\n⏳ Waiting 2 seconds before next feedback...")
            await asyncio.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ 3-RESPONSE RETRAINING TEST COMPLETED!")
    print("=" * 60)
    print("\nTo test in Streamlit:")
    print("1. Run: streamlit run app.py")
    print("2. Navigate to '🚀 Auto-Retraining' page")
    print("3. Submit 3 feedback items to trigger retraining")
    print("4. Watch the automatic retraining process!")
    
    print("\nTo switch to production mode later:")
    print("1. Run: python switch_retraining_config.py")
    print("2. Choose option 2 (Production mode)")
    print("3. Restart the Streamlit app")

def main():
    """Main test function."""
    try:
        asyncio.run(test_3_response_retraining())
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running test: {e}")

if __name__ == "__main__":
    main()




