#!/usr/bin/env python3
"""
Test Titan Embedding Models

This script tests which Titan embedding models you have access to.
"""

import boto3
import json
from botocore.exceptions import ClientError

def test_embedding_models():
    """Test access to Titan embedding models."""
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Titan embedding models to test
    embedding_models = [
        'amazon.titan-embed-text-v1',
        'amazon.titan-embed-text-v1:2:8k',
        'amazon.titan-embed-text-v2:0',
        'amazon.titan-embed-text-v2:0:8k',
        'amazon.titan-embed-g1-text-02'
    ]
    
    accessible_models = []
    
    print("🔍 Testing Titan Embedding Models...")
    print("=" * 50)
    
    for model_id in embedding_models:
        print(f"\n🧪 Testing {model_id}...")
        
        try:
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "inputText": "Hello, this is a test."
                }),
                contentType="application/json"
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding', [])
            
            print(f"✅ {model_id} - ACCESSIBLE (embedding size: {len(embedding)})")
            accessible_models.append(model_id)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                print(f"❌ {model_id} - NO ACCESS")
            else:
                print(f"⚠️  {model_id} - ERROR: {error_code}")
        except Exception as e:
            print(f"⚠️  {model_id} - ERROR: {str(e)}")
    
    print("\n" + "=" * 50)
    print("📋 ACCESSIBLE EMBEDDING MODELS:")
    print("=" * 50)
    
    if accessible_models:
        for model in accessible_models:
            print(f"✅ {model}")
    else:
        print("❌ No embedding models accessible")
    
    return accessible_models

if __name__ == "__main__":
    try:
        accessible_models = test_embedding_models()
        
        if accessible_models:
            print(f"\n🎉 Found {len(accessible_models)} accessible embedding models!")
            print(f"\n💡 Recommended: {accessible_models[0]}")
        else:
            print("\n⚠️  No embedding models accessible. Please check your Bedrock model access in AWS console.")
            
    except Exception as e:
        print(f"\n❌ Error testing embedding models: {e}")
