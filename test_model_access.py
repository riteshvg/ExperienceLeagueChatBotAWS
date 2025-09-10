#!/usr/bin/env python3
"""
Test Bedrock Model Access

This script tests which Bedrock models you actually have access to.
"""

import boto3
import json
from botocore.exceptions import ClientError

def test_model_access():
    """Test access to different Bedrock models."""
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Models to test
    models_to_test = [
        {
            'id': 'anthropic.claude-3-haiku-20240307-v1:0',
            'name': 'Claude 3 Haiku',
            'type': 'text'
        },
        {
            'id': 'anthropic.claude-3-sonnet-20240229-v1:0',
            'name': 'Claude 3 Sonnet',
            'type': 'text'
        },
        {
            'id': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'name': 'Claude 3.5 Sonnet v2',
            'type': 'text'
        },
        {
            'id': 'anthropic.claude-3-7-sonnet-20250219-v1:0',
            'name': 'Claude 3.7 Sonnet',
            'type': 'text'
        },
        {
            'id': 'amazon.titan-embed-text-v1',
            'name': 'Titan Embeddings v1',
            'type': 'embedding'
        },
        {
            'id': 'amazon.titan-embed-text-v2',
            'name': 'Titan Embeddings v2',
            'type': 'embedding'
        }
    ]
    
    accessible_models = []
    
    print("🔍 Testing Bedrock Model Access...")
    print("=" * 50)
    
    for model in models_to_test:
        print(f"\n🧪 Testing {model['name']} ({model['id']})...")
        
        try:
            if model['type'] == 'text':
                # Test text generation with correct format for Claude models
                if 'claude' in model['id']:
                    body = json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 10,
                        "messages": [
                            {
                                "role": "user",
                                "content": "Hello, this is a test."
                            }
                        ]
                    })
                else:
                    body = json.dumps({
                        "prompt": "Hello, this is a test.",
                        "max_tokens_to_sample": 10
                    })
                
                response = bedrock_client.invoke_model(
                    modelId=model['id'],
                    body=body,
                    contentType="application/json"
                )
                print(f"✅ {model['name']} - ACCESSIBLE")
                accessible_models.append(model)
                
            elif model['type'] == 'embedding':
                # Test embeddings with correct format
                body = json.dumps({
                    "inputText": "Hello, this is a test."
                })
                
                response = bedrock_client.invoke_model(
                    modelId=model['id'],
                    body=body,
                    contentType="application/json"
                )
                print(f"✅ {model['name']} - ACCESSIBLE")
                accessible_models.append(model)
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                print(f"❌ {model['name']} - NO ACCESS")
            else:
                print(f"⚠️  {model['name']} - ERROR: {error_code}")
        except Exception as e:
            print(f"⚠️  {model['name']} - ERROR: {str(e)}")
    
    print("\n" + "=" * 50)
    print("📋 ACCESSIBLE MODELS SUMMARY:")
    print("=" * 50)
    
    if accessible_models:
        for model in accessible_models:
            print(f"✅ {model['name']} ({model['id']})")
    else:
        print("❌ No models accessible")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    print("=" * 50)
    
    text_models = [m for m in accessible_models if m['type'] == 'text']
    embedding_models = [m for m in accessible_models if m['type'] == 'embedding']
    
    if text_models:
        # Find the best text model
        best_text = None
        for model in text_models:
            if '3.5' in model['id'] or '3.7' in model['id']:
                best_text = model
                break
        if not best_text:
            best_text = text_models[0]
        
        print(f"🎯 Recommended Text Model: {best_text['name']} ({best_text['id']})")
    else:
        print("❌ No text models accessible - check model access in AWS console")
    
    if embedding_models:
        best_embedding = embedding_models[0]
        print(f"🎯 Recommended Embedding Model: {best_embedding['name']} ({best_embedding['id']})")
    else:
        print("❌ No embedding models accessible - check model access in AWS console")
    
    return accessible_models

if __name__ == "__main__":
    try:
        accessible_models = test_model_access()
        
        if accessible_models:
            print(f"\n🎉 Found {len(accessible_models)} accessible models!")
        else:
            print("\n⚠️  No models accessible. Please check your Bedrock model access in AWS console.")
            
    except Exception as e:
        print(f"\n❌ Error testing model access: {e}")
