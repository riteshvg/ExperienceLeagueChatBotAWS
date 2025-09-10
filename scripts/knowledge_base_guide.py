#!/usr/bin/env python3
"""
Knowledge Base Creation Guide

This script provides step-by-step instructions for creating a Bedrock Knowledge Base
through the AWS console, which is more reliable than programmatic creation.
"""

import json
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings

def print_knowledge_base_guide():
    """Print comprehensive guide for creating Knowledge Base."""
    
    settings = Settings()
    
    print("🚀 BEDROCK KNOWLEDGE BASE CREATION GUIDE")
    print("=" * 60)
    print()
    
    print("📋 PREREQUISITES CHECK:")
    print("✅ AWS Account with Bedrock access")
    print("✅ S3 bucket with Adobe documentation")
    print("✅ IAM permissions for Bedrock")
    print("✅ Bedrock models enabled")
    print()
    
    print(f"📊 YOUR CONFIGURATION:")
    print(f"   S3 Bucket: {settings.aws_s3_bucket}")
    print(f"   Region: {settings.bedrock_region}")
    print(f"   Embedding Model: {settings.bedrock_embedding_model_id}")
    print(f"   Text Model: {settings.bedrock_model_id}")
    print()
    
    print("🎯 STEP-BY-STEP INSTRUCTIONS:")
    print("=" * 60)
    print()
    
    print("1️⃣  OPEN AWS BEDROCK CONSOLE")
    print("   • Go to: https://console.aws.amazon.com/bedrock/")
    print("   • Select region: us-east-1")
    print("   • Click 'Knowledge bases' in the left menu")
    print()
    
    print("2️⃣  CREATE KNOWLEDGE BASE")
    print("   • Click 'Create knowledge base'")
    print("   • Name: adobe-analytics-rag-kb")
    print("   • Description: Knowledge Base for Adobe Analytics documentation")
    print()
    
    print("3️⃣  CONFIGURE VECTOR DATABASE")
    print("   • Select 'Create and use a new vector store'")
    print("   • Choose 'Pinecone' (recommended for simplicity)")
    print("   • Or choose 'Amazon OpenSearch Serverless' (if you prefer AWS native)")
    print()
    
    print("4️⃣  CONFIGURE EMBEDDING MODEL")
    print(f"   • Embedding model: {settings.bedrock_embedding_model_id}")
    print("   • Chunking strategy: Fixed size")
    print("   • Max tokens: 1000")
    print("   • Overlap percentage: 20%")
    print()
    
    print("5️⃣  CONFIGURE DATA SOURCE")
    print(f"   • Data source name: adobe-analytics-docs")
    print(f"   • S3 bucket: {settings.aws_s3_bucket}")
    print("   • Prefix: adobe-docs/")
    print("   • File types: All supported types")
    print()
    
    print("6️⃣  CREATE IAM ROLE")
    print("   • Click 'Create and use a new service role'")
    print("   • Role name: BedrockKnowledgeBaseRole")
    print("   • The role will be created automatically")
    print()
    
    print("7️⃣  REVIEW AND CREATE")
    print("   • Review all settings")
    print("   • Click 'Create knowledge base'")
    print("   • Wait for creation to complete (5-10 minutes)")
    print()
    
    print("8️⃣  START INGESTION")
    print("   • Once created, click on your Knowledge Base")
    print("   • Go to 'Data sources' tab")
    print("   • Click 'Sync' to start document processing")
    print("   • Wait for ingestion to complete (10-30 minutes)")
    print()
    
    print("🔧 ALTERNATIVE: PROGRAMMATIC CREATION")
    print("=" * 60)
    print()
    print("If you prefer to create programmatically, run:")
    print("   python scripts/create_simple_kb.py")
    print()
    print("Note: This requires additional setup for vector stores.")
    print()
    
    print("📊 EXPECTED RESULTS:")
    print("=" * 60)
    print()
    print("✅ Knowledge Base created with ID")
    print("✅ Data source configured")
    print("✅ Documents processed and embedded")
    print("✅ Ready for querying")
    print()
    
    print("🧪 TESTING YOUR KNOWLEDGE BASE:")
    print("=" * 60)
    print()
    print("Once created, test with these queries:")
    print("   • 'What is Adobe Analytics?'")
    print("   • 'How do I create custom events?'")
    print("   • 'What are eVars and props?'")
    print("   • 'How do I set up Customer Journey Analytics?'")
    print()
    
    print("📚 NEXT STEPS:")
    print("=" * 60)
    print()
    print("1. Create Knowledge Base (follow steps above)")
    print("2. Wait for ingestion to complete")
    print("3. Test with sample queries")
    print("4. Create RAG interface")
    print("5. Deploy to production")
    print()
    
    print("💡 TROUBLESHOOTING:")
    print("=" * 60)
    print()
    print("• If creation fails: Check IAM permissions")
    print("• If ingestion fails: Check S3 bucket access")
    print("• If queries fail: Check model access")
    print("• For help: Check AWS Bedrock documentation")
    print()

def create_iam_role_script():
    """Create IAM role for Knowledge Base."""
    settings = Settings()
    
    print("🔧 IAM ROLE CREATION SCRIPT")
    print("=" * 60)
    print()
    print("Run this AWS CLI command to create the IAM role:")
    print()
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{settings.aws_s3_bucket}",
                    f"arn:aws:s3:::{settings.aws_s3_bucket}/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": [
                    f"arn:aws:bedrock:{settings.bedrock_region}::foundation-model/{settings.bedrock_embedding_model_id}"
                ]
            }
        ]
    }
    
    print("1. Create trust policy file:")
    print(f"   echo '{json.dumps(trust_policy, indent=2)}' > trust-policy.json")
    print()
    
    print("2. Create permissions policy file:")
    print(f"   echo '{json.dumps(permissions_policy, indent=2)}' > permissions-policy.json")
    print()
    
    print("3. Create IAM role:")
    print("   aws iam create-role \\")
    print("     --role-name BedrockKnowledgeBaseRole \\")
    print("     --assume-role-policy-document file://trust-policy.json")
    print()
    
    print("4. Attach permissions policy:")
    print("   aws iam put-role-policy \\")
    print("     --role-name BedrockKnowledgeBaseRole \\")
    print("     --policy-name BedrockKnowledgeBasePolicy \\")
    print("     --policy-document file://permissions-policy.json")
    print()
    
    print("5. Get role ARN:")
    print("   aws iam get-role --role-name BedrockKnowledgeBaseRole")
    print()

def main():
    """Main function."""
    print_knowledge_base_guide()
    print()
    create_iam_role_script()

if __name__ == "__main__":
    main()
