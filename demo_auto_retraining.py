#!/usr/bin/env python3
"""
Demo script for auto-retraining pipeline workflow.
Shows how to use the auto-retraining pipeline in practice.
"""

import asyncio
import time
from datetime import datetime
from src.retraining.auto_retraining_pipeline import AutoRetrainingPipeline
from config.auto_retraining_config import AUTO_RETRAINING_CONFIG

def print_separator(title):
    """Print a formatted separator."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_pipeline_status(pipeline):
    """Print current pipeline status."""
    status = pipeline.get_pipeline_status()
    print(f"\n📊 Pipeline Status:")
    print(f"   Status: {status['status']}")
    print(f"   Queue Size: {status['queue_size']}/{status['retraining_threshold']}")
    print(f"   Last Retraining: {status['last_retraining'] or 'Never'}")
    print(f"   Cooldown Remaining: {status['cooldown_remaining']:.0f}s")

async def demo_feedback_processing():
    """Demonstrate feedback processing workflow."""
    print_separator("AUTO-RETRAINING PIPELINE DEMO")
    
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
    
    # Sample feedback data
    sample_feedbacks = [
        {
            'query': 'How do I set up Adobe Analytics tracking?',
            'gemini_response': 'To set up Adobe Analytics tracking, you need to implement the Adobe Analytics extension in Adobe Launch...',
            'claude_response': 'Setting up Adobe Analytics tracking involves configuring the Adobe Analytics extension, setting up data elements, and creating rules...',
            'selected_model': 'claude',
            'user_rating': 4,
            'response_quality': {
                'accuracy': 4,
                'relevance': 5,
                'clarity': 4,
                'completeness': 5
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
                'accuracy': 5,
                'relevance': 5,
                'clarity': 5,
                'completeness': 5
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
                'accuracy': 3,
                'relevance': 4,
                'clarity': 3,
                'completeness': 4
            },
            'timestamp': datetime.now().isoformat()
        }
    ]
    
    print_separator("PROCESSING FEEDBACK")
    
    # Process each feedback
    for i, feedback in enumerate(sample_feedbacks, 1):
        print(f"\n📝 Processing Feedback {i}:")
        print(f"   Query: {feedback['query'][:50]}...")
        print(f"   Selected Model: {feedback['selected_model']}")
        print(f"   User Rating: {feedback['user_rating']}/5")
        
        # Process feedback through pipeline
        result = await pipeline.process_feedback_async(feedback)
        
        print(f"   Result: {result['status']}")
        print(f"   Message: {result['message']}")
        
        if result['status'] == 'retraining_started':
            print(f"   🚀 Training Data Size: {result['training_data_size']} examples")
            print(f"   Jobs Started: {len(result['jobs'])}")
        
        print_pipeline_status(pipeline)
        
        # Small delay between feedback submissions
        if i < len(sample_feedbacks):
            print("\n⏳ Waiting 2 seconds before next feedback...")
            await asyncio.sleep(2)
    
    print_separator("DEMO COMPLETE")
    print("✅ Auto-retraining pipeline demo completed successfully!")
    print("\nTo integrate with your Streamlit app:")
    print("1. Import the pipeline in your app.py")
    print("2. Initialize it in your session state")
    print("3. Use the AutoRetrainingUI for the interface")
    print("4. Connect it to your existing feedback system")

async def demo_manual_controls():
    """Demonstrate manual pipeline controls."""
    print_separator("MANUAL CONTROLS DEMO")
    
    # Initialize pipeline
    pipeline = AutoRetrainingPipeline(AUTO_RETRAINING_CONFIG)
    
    # Add some feedback manually
    feedback = {
        'query': 'Test query for manual demo',
        'gemini_response': 'Test gemini response',
        'claude_response': 'Test claude response',
        'selected_model': 'claude',
        'user_rating': 4,
        'response_quality': {'accuracy': 4, 'relevance': 4, 'clarity': 4, 'completeness': 4},
        'timestamp': datetime.now().isoformat()
    }
    
    pipeline.feedback_queue.append(feedback)
    print("✅ Added feedback to queue manually")
    print_pipeline_status(pipeline)
    
    # Update configuration
    print("\n⚙️ Updating configuration...")
    pipeline.update_config({
        'retraining_threshold': 5,
        'quality_threshold': 4,
        'retraining_cooldown': 3600
    })
    print("✅ Configuration updated")
    print_pipeline_status(pipeline)
    
    # Reset pipeline
    print("\n🗑️ Resetting pipeline...")
    pipeline.reset_pipeline()
    print("✅ Pipeline reset")
    print_pipeline_status(pipeline)

def main():
    """Main demo function."""
    print("🚀 Auto-Retraining Pipeline Demo")
    print("This demo shows how to use the auto-retraining pipeline workflow.")
    
    try:
        # Run the main demo
        asyncio.run(demo_feedback_processing())
        
        # Run manual controls demo
        asyncio.run(demo_manual_controls())
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        print("Make sure you're running this from the project root directory")

if __name__ == "__main__":
    main()

