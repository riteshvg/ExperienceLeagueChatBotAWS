#!/usr/bin/env python3
"""
List available AWS Bedrock Knowledge Bases
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Load .env
load_dotenv()

def list_knowledge_bases(region: str = "us-east-1"):
    """List all Bedrock Knowledge Bases in the specified region."""
    try:
        bedrock_agent_client = boto3.client('bedrock-agent', region_name=region)
        
        print(f"🔍 Searching for Knowledge Bases in region: {region}")
        print("=" * 60)
        
        # List all knowledge bases
        response = bedrock_agent_client.list_knowledge_bases()
        
        knowledge_bases = response.get('knowledgeBaseSummaries', [])
        
        if not knowledge_bases:
            print("❌ No Knowledge Bases found in this region.")
            print("\n💡 To create a Knowledge Base:")
            print("   1. Go to AWS Bedrock Console → Knowledge Bases")
            print("   2. Click 'Create knowledge base'")
            print("   3. Follow the setup wizard")
            print("   4. Copy the Knowledge Base ID to your .env file")
            return []
        
        print(f"\n✅ Found {len(knowledge_bases)} Knowledge Base(s):\n")
        
        for kb in knowledge_bases:
            kb_id = kb.get('knowledgeBaseId', 'N/A')
            kb_name = kb.get('name', 'N/A')
            kb_status = kb.get('status', 'N/A')
            kb_description = kb.get('description', 'No description')
            
            print(f"📚 Knowledge Base: {kb_name}")
            print(f"   ID: {kb_id}")
            print(f"   Status: {kb_status}")
            print(f"   Description: {kb_description}")
            print()
        
        # Show how to add to .env
        if knowledge_bases:
            print("=" * 60)
            print("💡 To use a Knowledge Base, add this to your .env file:")
            print(f"   BEDROCK_KNOWLEDGE_BASE_ID={knowledge_bases[0].get('knowledgeBaseId', 'your_kb_id_here')}")
            print()
        
        return knowledge_bases
        
    except NoCredentialsError:
        print("❌ No AWS credentials found. Please configure your AWS credentials.")
        print("   Run: python scripts/get_aws_env_vars.py --source cli --save")
        return []
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            print(f"❌ Access denied. Your AWS credentials don't have permission to list Knowledge Bases.")
            print("   Required IAM permission: bedrock:ListKnowledgeBases")
        else:
            print(f"❌ Error: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    list_knowledge_bases(region)

