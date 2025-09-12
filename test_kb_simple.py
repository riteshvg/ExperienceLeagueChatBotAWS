#!/usr/bin/env python3
"""
Simple Knowledge Base test with your actual KB ID.
"""

import boto3
from botocore.exceptions import ClientError

def test_your_kb():
    """Test your specific Knowledge Base."""
    
    # Your Knowledge Base ID from earlier
    KB_ID = "THHVE7ALMA"  # This was your KB ID from earlier
    REGION = "us-east-1"
    
    print(f"🤖 Testing Knowledge Base: {KB_ID}")
    print("=" * 50)
    
    try:
        # Initialize client
        bedrock_agent_client = boto3.client('bedrock-agent', region_name=REGION)
        
        # Test Knowledge Base status first
        print("🔍 Checking Knowledge Base status...")
        kb_details = bedrock_agent_client.get_knowledge_base(knowledgeBaseId=KB_ID)
        kb_info = kb_details['knowledgeBase']
        
        print(f"✅ Knowledge Base found: {kb_info['name']}")
        print(f"   - Status: {kb_info['status']}")
        
        if kb_info['status'] != 'ACTIVE':
            print(f"❌ Knowledge Base is not active! Status: {kb_info['status']}")
            return False
        
        # Test data sources
        data_sources = bedrock_agent_client.list_data_sources(knowledgeBaseId=KB_ID)
        print(f"   - Data sources: {len(data_sources.get('dataSourceSummaries', []))}")
        
        if not data_sources.get('dataSourceSummaries'):
            print("❌ No data sources found! Knowledge Base is empty.")
            return False
        
        print("✅ Knowledge Base is properly configured")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        print(f"❌ ERROR: {error_code}")
        print(f"   Message: {error_message}")
        
        if error_code == "ResourceNotFoundException":
            print("🔧 The Knowledge Base ID 'THHVE7ALMA' doesn't exist or is wrong")
            print("   Check your AWS Bedrock console for the correct ID")
        elif error_code == "AccessDeniedException":
            print("🔧 Permission denied - check your AWS credentials")
        else:
            print(f"🔧 Check AWS Bedrock console for details")
        
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_your_kb()
