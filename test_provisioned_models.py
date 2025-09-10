#!/usr/bin/env python3
"""
Test Provisioned Bedrock Models

This script tests which Bedrock models are actually provisioned and accessible.
"""

import boto3
import json
from botocore.exceptions import ClientError

def test_model_access(model_id, model_name, model_type="text"):
    """Test if a specific model is accessible."""
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    try:
        if model_type == "text":
            if 'claude' in model_id:
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Test"}]
                })
            else:
                body = json.dumps({
                    "prompt": "Test",
                    "max_tokens_to_sample": 10
                })
        elif model_type == "embedding":
            body = json.dumps({
                "inputText": "Test"
            })
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json"
        )
        return True, "Success"
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        return False, error_code
    except Exception as e:
        return False, str(e)

def main():
    """Test provisioned models."""
    print("🔍 Testing Provisioned Bedrock Models")
    print("=" * 60)
    
    # Key models to test
    models_to_test = [
        # Claude Models
        ("anthropic.claude-3-haiku-20240307-v1:0", "Claude 3 Haiku", "text"),
        ("anthropic.claude-3-sonnet-20240229-v1:0", "Claude 3 Sonnet", "text"),
        ("anthropic.claude-3-opus-20240229-v1:0", "Claude 3 Opus", "text"),
        ("anthropic.claude-3-5-sonnet-20241022-v2:0", "Claude 3.5 Sonnet v2", "text"),
        ("anthropic.claude-3-7-sonnet-20250219-v1:0", "Claude 3.7 Sonnet", "text"),
        ("anthropic.claude-3-5-haiku-20241022-v1:0", "Claude 3.5 Haiku", "text"),
        ("anthropic.claude-sonnet-4-20250514-v1:0", "Claude Sonnet 4", "text"),
        ("anthropic.claude-opus-4-20250514-v1:0", "Claude Opus 4", "text"),
        
        # Titan Models
        ("amazon.titan-text-express-v1", "Titan Text Express", "text"),
        ("amazon.titan-embed-text-v1", "Titan Embeddings v1", "embedding"),
        ("amazon.titan-embed-text-v2:0", "Titan Embeddings v2", "embedding"),
        ("amazon.titan-embed-g1-text-02", "Titan Embeddings G1", "embedding"),
        
        # Llama Models
        ("meta.llama3-8b-instruct-v1:0", "Llama 3 8B", "text"),
        ("meta.llama3-70b-instruct-v1:0", "Llama 3 70B", "text"),
        ("meta.llama3-1-8b-instruct-v1:0", "Llama 3.1 8B", "text"),
        ("meta.llama3-1-70b-instruct-v1:0", "Llama 3.1 70B", "text"),
    ]
    
    accessible_models = []
    text_models = []
    embedding_models = []
    
    for model_id, model_name, model_type in models_to_test:
        print(f"\n🧪 Testing {model_name} ({model_id})...")
        
        accessible, error = test_model_access(model_id, model_name, model_type)
        
        if accessible:
            print(f"✅ {model_name} - PROVISIONED")
            accessible_models.append((model_id, model_name, model_type))
            if model_type == "text":
                text_models.append((model_id, model_name))
            elif model_type == "embedding":
                embedding_models.append((model_id, model_name))
        else:
            if error == "AccessDeniedException":
                print(f"❌ {model_name} - NOT PROVISIONED")
            else:
                print(f"⚠️  {model_name} - ERROR: {error}")
    
    print("\n" + "=" * 60)
    print("📋 PROVISIONED MODELS SUMMARY")
    print("=" * 60)
    
    if accessible_models:
        print(f"\n✅ Total Provisioned Models: {len(accessible_models)}")
        
        if text_models:
            print(f"\n🤖 Text Generation Models ({len(text_models)}):")
            for model_id, model_name in text_models:
                print(f"   ✅ {model_name}")
        
        if embedding_models:
            print(f"\n🔗 Embedding Models ({len(embedding_models)}):")
            for model_id, model_name in embedding_models:
                print(f"   ✅ {model_name}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        print("=" * 30)
        
        if text_models:
            # Find the best text model
            best_text = None
            for model_id, model_name in text_models:
                if '3.5' in model_id or '3.7' in model_id or '4' in model_id:
                    best_text = (model_id, model_name)
                    break
            if not best_text and text_models:
                best_text = text_models[0]
            
            if best_text:
                print(f"🎯 Best Text Model: {best_text[1]} ({best_text[0]})")
        
        if embedding_models:
            best_embedding = embedding_models[0]
            print(f"🎯 Best Embedding Model: {best_embedding[1]} ({best_embedding[0]})")
        
    else:
        print("❌ No models provisioned")
    
    return accessible_models

if __name__ == "__main__":
    try:
        accessible_models = main()
        
        if accessible_models:
            print(f"\n🎉 Found {len(accessible_models)} provisioned models!")
        else:
            print("\n⚠️  No models provisioned. Please enable models in AWS Bedrock console.")
            
    except Exception as e:
        print(f"\n❌ Error testing models: {e}")
