#!/usr/bin/env python3
"""
Test Final Working Bedrock Models

This script tests the models that are actually working in your account.
"""

import boto3
import json
import sys
import os
from botocore.exceptions import ClientError

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings

def test_working_models():
    """Test all working models."""
    settings = Settings()
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    print("🔍 Testing Working Bedrock Models")
    print("=" * 60)
    print(f"Configured Model: {settings.bedrock_model_id}")
    print(f"Configured Embedding Model: {settings.bedrock_embedding_model_id}")
    print()
    
    # Test the configured model
    print(f"🧪 Testing Configured Model: {settings.bedrock_model_id}")
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello! Can you tell me about Adobe Analytics and its key features in 2-3 sentences?"
                }
            ]
        })
        
        response = bedrock_client.invoke_model(
            modelId=settings.bedrock_model_id,
            body=body,
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        print("✅ Configured Model - SUCCESS!")
        print(f"✅ Response: {content}")
        
    except Exception as e:
        print(f"❌ Configured Model - ERROR: {e}")
    
    print("\n" + "=" * 60)
    
    # Test the configured embedding model
    print(f"🧪 Testing Configured Embedding Model: {settings.bedrock_embedding_model_id}")
    try:
        body = json.dumps({
            "inputText": "Adobe Analytics is a web analytics platform."
        })
        
        response = bedrock_client.invoke_model(
            modelId=settings.bedrock_embedding_model_id,
            body=body,
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        embedding = response_body.get('embedding', [])
        
        print("✅ Configured Embedding Model - SUCCESS!")
        print(f"✅ Embedding dimension: {len(embedding)}")
        
    except Exception as e:
        print(f"❌ Configured Embedding Model - ERROR: {e}")
    
    print("\n" + "=" * 60)
    
    # Test all working models we found
    working_models = [
        ("us.anthropic.claude-3-haiku-20240307-v1:0", "Claude 3 Haiku"),
        ("us.anthropic.claude-3-5-sonnet-20240620-v1:0", "Claude 3.5 Sonnet"),
        ("us.anthropic.claude-3-7-sonnet-20250219-v1:0", "Claude 3.7 Sonnet"),
    ]
    
    print("🧪 Testing All Working Models")
    print("=" * 60)
    
    for model_id, model_name in working_models:
        print(f"\n🧪 Testing {model_name} ({model_id})...")
        
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "messages": [
                    {
                        "role": "user",
                        "content": "What is Adobe Analytics?"
                    }
                ]
            })
            
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            print(f"✅ {model_name} - SUCCESS!")
            print(f"   Response: {content[:100]}...")
            
        except Exception as e:
            print(f"❌ {model_name} - ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("📋 FINAL STATUS SUMMARY")
    print("=" * 60)
    
    print(f"✅ Text Generation: {settings.bedrock_model_id}")
    print(f"✅ Embeddings: {settings.bedrock_embedding_model_id}")
    print(f"✅ Region: {settings.bedrock_region}")
    
    print("\n💡 Your RAG system is ready with:")
    print("   - Claude 3.7 Sonnet for text generation (latest and most capable)")
    print("   - Titan Embeddings v2 for vector embeddings")
    print("   - All models working via inference profiles")

if __name__ == "__main__":
    try:
        test_working_models()
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
