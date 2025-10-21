#!/usr/bin/env python3
"""
Test script to demonstrate auto-retraining pipeline feedback processing.
Shows clear visual indicators and progress tracking.
"""

import asyncio
import time
from datetime import datetime
from src.retraining.auto_retraining_pipeline import AutoRetrainingPipeline
from config.auto_retraining_config import AUTO_RETRAINING_CONFIG

def print_status_header():
    """Print a formatted status header."""
    print("=" * 80)
    print("🚀 AUTO-RETRAINING PIPELINE - FEEDBACK PROCESSING TEST")
    print("=" * 80)

def print_feedback_submission(feedback_num, feedback):
    """Print feedback submission details."""
    print(f"\n📝 FEEDBACK #{feedback_num} SUBMISSION")
    print("-" * 40)
    print(f"Query: {feedback['query'][:60]}...")
    print(f"Selected Model: {feedback['selected_model']}")
    print(f"User Rating: {'⭐' * feedback['user_rating']} ({feedback['user_rating']}/5)")
    print(f"Quality Scores: Accuracy={feedback['response_quality']['accuracy']}, "
          f"Relevance={feedback['response_quality']['relevance']}, "
          f"Clarity={feedback['response_quality']['clarity']}, "
          f"Completeness={feedback['response_quality']['completeness']}")

def print_processing_result(result, pipeline):
    """Print the processing result with visual indicators."""
    print(f"\n🔄 PROCESSING RESULT")
    print("-" * 40)
    
    if result['status'] == 'queued':
        print("✅ STATUS: FEEDBACK QUEUED SUCCESSFULLY")
        print(f"📝 Message: {result['message']}")
        
        # Show queue progress
        status = pipeline.get_pipeline_status()
        progress = min(status['queue_size'] / status['retraining_threshold'], 1.0)
        progress_bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
        print(f"📊 Queue Progress: [{progress_bar}] {status['queue_size']}/{status['retraining_threshold']} items")
        
        # Show what's needed next
        remaining = status['retraining_threshold'] - status['queue_size']
        if remaining > 0:
            print(f"🎯 Next Steps: Submit {remaining} more high-quality feedback items to trigger retraining!")
        else:
            print("⚠️  Queue is full! Retraining may be triggered on next submission.")
            
    elif result['status'] == 'retraining_started':
        print("🚀 STATUS: AUTO-RETRAINING STARTED!")
        print(f"📊 Training Data Size: {result['training_data_size']} examples")
        print(f"🔧 Jobs Started: {len(result['jobs'])} models")
        
        for job in result['jobs']:
            if job.get('status') == 'started':
                print(f"✅ {job['model_type'].title()} retraining job: {job.get('job_name', 'N/A')}")
        
        print("🔄 What's happening: Models are being trained with collected feedback...")
        
    else:
        print("❌ STATUS: ERROR PROCESSING FEEDBACK")
        print(f"Error: {result['message']}")

def print_pipeline_status(pipeline):
    """Print detailed pipeline status."""
    status = pipeline.get_pipeline_status()
    print(f"\n📊 PIPELINE STATUS")
    print("-" * 40)
    print(f"Status: {status['status'].upper()}")
    print(f"Queue Size: {status['queue_size']}/{status['retraining_threshold']}")
    print(f"Quality Threshold: {pipeline.quality_threshold}/5")
    print(f"Cooldown Period: {pipeline.retraining_cooldown/3600:.1f} hours")
    
    if status['last_retraining']:
        last_time = datetime.fromtimestamp(status['last_retraining'])
        print(f"Last Retraining: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("Last Retraining: Never")
    
    if status['cooldown_remaining'] > 0:
        print(f"Cooldown Remaining: {status['cooldown_remaining']:.0f} seconds")
    else:
        print("Cooldown: Ready")

async def test_feedback_processing():
    """Test the feedback processing workflow with enhanced visual feedback."""
    print_status_header()
    
    # Initialize pipeline with demo configuration
    demo_config = AUTO_RETRAINING_CONFIG.copy()
    demo_config.update({
        'retraining_threshold': 3,  # Lower threshold for demo
        'quality_threshold': 3,     # Lower quality threshold for demo
        'retraining_cooldown': 5,   # 5 seconds for demo
    })
    
    pipeline = AutoRetrainingPipeline(demo_config)
    print("✅ Auto-retraining pipeline initialized")
    print_pipeline_status(pipeline)
    
    # Sample feedback data with different quality levels
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
    
    # Process each feedback with enhanced visual feedback
    for i, feedback in enumerate(sample_feedbacks, 1):
        print_feedback_submission(i, feedback)
        
        # Simulate processing delay
        print("🔄 Processing feedback...")
        await asyncio.sleep(1)
        
        # Process feedback through pipeline
        result = await pipeline.process_feedback_async(feedback)
        print_processing_result(result, pipeline)
        
        # Show updated pipeline status
        print_pipeline_status(pipeline)
        
        # Wait between submissions
        if i < len(sample_feedbacks):
            print(f"\n⏳ Waiting 2 seconds before next feedback...")
            await asyncio.sleep(2)
    
    print("\n" + "=" * 80)
    print("✅ FEEDBACK PROCESSING TEST COMPLETED!")
    print("=" * 80)
    print("\nTo see this in action in your Streamlit app:")
    print("1. Run: streamlit run app.py")
    print("2. Navigate to '🚀 Auto-Retraining' page")
    print("3. Submit feedback using the form")
    print("4. Watch the real-time progress indicators!")

def main():
    """Main test function."""
    try:
        asyncio.run(test_feedback_processing())
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running test: {e}")

if __name__ == "__main__":
    main()

