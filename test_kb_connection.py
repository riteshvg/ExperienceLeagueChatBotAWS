#!/usr/bin/env python3
"""
Test Knowledge Base connection and identify issues.
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

def test_knowledge_base_connection():
    """Test Knowledge Base connection and retrieval."""
    print("🤖 Testing Knowledge Base Connection")
    print("=" * 50)
    
    # Check environment variables
    kb_id = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
    region = os.getenv("BEDROCK_REGION", "us-east-1")
    
    if not kb_id:
        print("❌ BEDROCK_KNOWLEDGE_BASE_ID not set")
        return False
    
    print(f"✅ Knowledge Base ID: {kb_id}")
    print(f"✅ Region: {region}")
    
    try:
        # Initialize Bedrock Agent client
        bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
        print("✅ Bedrock Agent client created")
        
        # Test Knowledge Base retrieval
        print("🔍 Testing Knowledge Base retrieval...")
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': 'What is Adobe Analytics?'
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 3
                }
            }
        )
        
        print("✅ Knowledge Base retrieval successful!")
        print(f"   - Retrieved {len(response.get('retrievalResults', []))} results")
        
        # Show sample results
        for i, result in enumerate(response.get('retrievalResults', [])[:2]):
            print(f"   - Result {i+1}: {result.get('content', {}).get('text', 'No text')[:100]}...")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        print(f"❌ Knowledge Base error: {error_code}")
        print(f"   Message: {error_message}")
        
        if error_code == "ResourceNotFoundException":
            print("🔧 Fix: Knowledge Base ID is incorrect or doesn't exist")
        elif error_code == "AccessDeniedException":
            print("🔧 Fix: IAM permissions issue - check Bedrock access")
        elif error_code == "ValidationException":
            print("🔧 Fix: Invalid Knowledge Base configuration")
        elif error_code == "ThrottlingException":
            print("🔧 Fix: Rate limit exceeded - try again later")
        else:
            print(f"🔧 Fix: Check AWS Bedrock console for details")
        
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_aws_credentials():
    """Test AWS credentials and permissions."""
    print("\n🔑 Testing AWS Credentials")
    print("=" * 50)
    
    try:
        # Test STS
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ AWS Identity: {identity.get('Arn', 'Unknown')}")
        
        # Test Bedrock permissions
        bedrock_client = boto3.client('bedrock', region_name='us-east-1')
        
        # List foundation models (basic permission test)
        try:
            models = bedrock_client.list_foundation_models()
            print("✅ Bedrock access confirmed")
        except ClientError as e:
            print(f"⚠️ Bedrock access issue: {e.response['Error']['Message']}")
        
        # Test Bedrock Agent permissions
        try:
            bedrock_agent_client = boto3.client('bedrock-agent', region_name='us-east-1')
            # Try to list knowledge bases
            kb_list = bedrock_agent_client.list_knowledge_bases()
            print("✅ Bedrock Agent access confirmed")
            print(f"   - Found {len(kb_list.get('knowledgeBaseSummaries', []))} knowledge bases")
        except ClientError as e:
            print(f"❌ Bedrock Agent access denied: {e.response['Error']['Message']}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ AWS credentials error: {e}")
        return False

def test_knowledge_base_status():
    """Check Knowledge Base status and configuration."""
    print("\n📊 Testing Knowledge Base Status")
    print("=" * 50)
    
    kb_id = os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")
    region = os.getenv("BEDROCK_REGION", "us-east-1")
    
    try:
        bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
        
        # Get Knowledge Base details
        kb_details = bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
        kb_info = kb_details['knowledgeBase']
        
        print(f"✅ Knowledge Base found: {kb_info['name']}")
        print(f"   - Status: {kb_info['status']}")
        print(f"   - Description: {kb_info.get('description', 'No description')}")
        
        if kb_info['status'] != 'ACTIVE':
            print(f"❌ Knowledge Base is not active! Status: {kb_info['status']}")
            return False
        
        # Check data sources
        data_sources = bedrock_agent_client.list_data_sources(knowledgeBaseId=kb_id)
        print(f"   - Data sources: {len(data_sources.get('dataSourceSummaries', []))}")
        
        if not data_sources.get('dataSourceSummaries'):
            print("❌ No data sources found! Knowledge Base is empty.")
            return False
        
        # Check data source status
        for ds in data_sources.get('dataSourceSummaries', []):
            print(f"   - Data source: {ds['name']} (Status: {ds['status']})")
            if ds['status'] != 'ACTIVE':
                print(f"❌ Data source not active: {ds['name']}")
                return False
        
        print("✅ Knowledge Base is properly configured and active")
        return True
        
    except ClientError as e:
        print(f"❌ Knowledge Base status check failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Knowledge Base Diagnostic Tool")
    print("=" * 50)
    
    # Test AWS credentials
    aws_ok = test_aws_credentials()
    if not aws_ok:
        print("\n❌ AWS credentials test failed. Fix this first.")
        return 1
    
    # Test Knowledge Base status
    kb_status_ok = test_knowledge_base_status()
    if not kb_status_ok:
        print("\n❌ Knowledge Base status check failed.")
        return 1
    
    # Test Knowledge Base retrieval
    kb_retrieval_ok = test_knowledge_base_connection()
    if not kb_retrieval_ok:
        print("\n❌ Knowledge Base retrieval failed.")
        return 1
    
    print("\n🎉 All tests passed! Knowledge Base should work.")
    return 0

if __name__ == "__main__":
    exit(main())
