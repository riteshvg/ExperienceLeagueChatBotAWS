#!/usr/bin/env python3
"""
Test script for real retraining functionality with AWS/GCP integration.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from src.retraining.auto_retraining_pipeline import AutoRetrainingPipeline
from config.auto_retraining_config import AUTO_RETRAINING_CONFIG

def test_real_retraining_setup():
    """Test the real retraining setup with environment variables."""
    print("🧪 TESTING: Real Retraining Setup")
    print("=" * 60)
    
    # Check environment variables
    print("1. 📋 Checking Environment Variables")
    print("-" * 40)
    
    required_vars = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY', 
        'RETRAINING_S3_BUCKET',
        'BEDROCK_ROLE_ARN',
        'GCP_PROJECT_ID',
        'RETRAINING_GCS_BUCKET'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'*' * 10}{value[-4:] if len(value) > 4 else '****'}")
        else:
            print(f"   ❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set these in your .env file or environment")
        return False
    
    print("\n✅ All required environment variables are set!")
    
    # Test configuration loading
    print("\n2. ⚙️ Testing Configuration Loading")
    print("-" * 40)
    
    print(f"   AWS Region: {AUTO_RETRAINING_CONFIG['aws_region']}")
    print(f"   S3 Bucket: {AUTO_RETRAINING_CONFIG['s3_bucket']}")
    print(f"   GCP Project: {AUTO_RETRAINING_CONFIG['gcp_project_id']}")
    print(f"   GCS Bucket: {AUTO_RETRAINING_CONFIG['gcs_bucket']}")
    print(f"   Claude Retraining: {AUTO_RETRAINING_CONFIG['enable_claude_retraining']}")
    print(f"   Gemini Retraining: {AUTO_RETRAINING_CONFIG['enable_gemini_retraining']}")
    
    # Test pipeline initialization
    print("\n3. 🚀 Testing Pipeline Initialization")
    print("-" * 40)
    
    try:
        pipeline = AutoRetrainingPipeline(AUTO_RETRAINING_CONFIG)
        print("   ✅ Pipeline initialized successfully")
        
        # Check cloud client status
        creds_status = pipeline.get_cloud_credentials_status()
        
        print(f"   AWS Available: {'✅' if creds_status['aws']['available'] else '❌'}")
        print(f"   S3 Available: {'✅' if creds_status['aws']['s3_available'] else '❌'}")
        print(f"   GCP Available: {'✅' if creds_status['gcp']['available'] else '❌'}")
        print(f"   GCS Available: {'✅' if creds_status['gcp']['gcs_available'] else '❌'}")
        
        if not (creds_status['aws']['available'] or creds_status['gcp']['available']):
            print("   ⚠️  No cloud services available. Check credentials.")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Pipeline initialization failed: {e}")
        return False

async def test_real_retraining_workflow():
    """Test the complete real retraining workflow."""
    print("\n4. 🔄 Testing Real Retraining Workflow")
    print("-" * 40)
    
    try:
        pipeline = AutoRetrainingPipeline(AUTO_RETRAINING_CONFIG)
        
        # Create sample feedback data
        sample_feedback = {
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
        }
        
        print("   📝 Processing sample feedback...")
        result = await pipeline.process_feedback_async(sample_feedback)
        
        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message']}")
        
        if result['status'] == 'queued':
            print("   ✅ Feedback queued successfully")
            
            # Check pipeline status
            status = pipeline.get_pipeline_status()
            print(f"   Queue Size: {status['queue_size']}/{status['retraining_threshold']}")
            print(f"   AWS Available: {status['aws_available']}")
            print(f"   GCP Available: {status['gcp_available']}")
            
            return True
        else:
            print(f"   ❌ Feedback processing failed: {result['message']}")
            return False
            
    except Exception as e:
        print(f"   ❌ Workflow test failed: {e}")
        return False

def test_monitoring_features():
    """Test monitoring and tracking features."""
    print("\n5. 📊 Testing Monitoring Features")
    print("-" * 40)
    
    try:
        pipeline = AutoRetrainingPipeline(AUTO_RETRAINING_CONFIG)
        
        # Test retraining history
        history = pipeline.get_retraining_history()
        print(f"   Retraining History: {len(history)} jobs")
        
        # Test training data history
        data_history = pipeline.get_training_data_history()
        print(f"   Training Data History: {len(data_history)} uploads")
        
        # Test cloud credentials status
        creds_status = pipeline.get_cloud_credentials_status()
        print(f"   AWS Status: {creds_status['aws']['available']}")
        print(f"   GCP Status: {creds_status['gcp']['available']}")
        
        print("   ✅ Monitoring features working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Monitoring test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 REAL RETRAINING FUNCTIONALITY - TEST SUITE")
    print("=" * 60)
    
    # Test 1: Environment setup
    if not test_real_retraining_setup():
        print("\n❌ Environment setup failed. Please check your credentials.")
        return False
    
    # Test 2: Real retraining workflow
    if not asyncio.run(test_real_retraining_workflow()):
        print("\n❌ Real retraining workflow failed.")
        return False
    
    # Test 3: Monitoring features
    if not test_monitoring_features():
        print("\n❌ Monitoring features failed.")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED - Real Retraining Ready!")
    print("=" * 60)
    
    print("\n🚀 Ready to test in Streamlit:")
    print("   1. Go to http://localhost:1503")
    print("   2. Navigate to '🚀 Auto-Retraining'")
    print("   3. Check the '🔍 Monitoring' tab for real-time tracking")
    print("   4. Submit feedback to trigger real retraining jobs")
    print("   5. Monitor job progress and data uploads in real-time")
    
    print("\n📋 Environment Setup Instructions:")
    print("   1. Copy retraining_env_template.txt to .env")
    print("   2. Fill in your AWS and GCP credentials")
    print("   3. Set up S3 and GCS buckets for training data")
    print("   4. Configure IAM roles for Bedrock access")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)




