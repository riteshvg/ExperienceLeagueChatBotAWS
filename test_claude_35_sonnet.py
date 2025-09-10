#!/usr/bin/env python3
"""
Test Claude 3.5 Sonnet Model

This script specifically tests Claude 3.5 Sonnet model access.
"""

import boto3
import json
from botocore.exceptions import ClientError

def test_claude_35_sonnet():
    """Test Claude 3.5 Sonnet model access."""
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    print("🧪 Testing Claude 3.5 Sonnet Model")
    print("=" * 50)
    print(f"Model ID: {model_id}")
    print(f"Region: us-east-1")
    print()
    
    try:
        # Test with correct Claude 3.5 format
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello! Can you tell me about Adobe Analytics in one sentence?"
                }
            ]
        })
        
        print("🚀 Sending request to Claude 3.5 Sonnet...")
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=body,
            contentType="application/json"
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        print("✅ Claude 3.5 Sonnet - SUCCESS!")
        print(f"✅ Response: {content}")
        print()
        print("🎉 Claude 3.5 Sonnet is working perfectly!")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        print(f"❌ Claude 3.5 Sonnet - ERROR!")
        print(f"Error Code: {error_code}")
        print(f"Error Message: {error_message}")
        
        if error_code == "AccessDeniedException":
            print("\n💡 This means the model is not provisioned in your account.")
            print("   Please check the AWS Bedrock console to ensure Claude 3.5 Sonnet is enabled.")
        elif error_code == "ValidationException":
            print("\n💡 This might be a request format issue.")
            print("   The model might be available but with different parameters.")
        else:
            print(f"\n💡 Unexpected error: {error_code}")
        
        return False
        
    except Exception as e:
        print(f"❌ Claude 3.5 Sonnet - UNEXPECTED ERROR!")
        print(f"Error: {str(e)}")
        return False

def test_alternative_formats():
    """Test alternative request formats for Claude 3.5 Sonnet."""
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    print("\n🔍 Testing Alternative Request Formats")
    print("=" * 50)
    
    # Test different formats
    test_cases = [
        {
            "name": "Standard Claude 3.5 Format",
            "body": {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "Test"}]
            }
        },
        {
            "name": "Legacy Claude Format",
            "body": {
                "prompt": "Test",
                "max_tokens_to_sample": 50
            }
        },
        {
            "name": "Minimal Format",
            "body": {
                "messages": [{"role": "user", "content": "Test"}]
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing {test_case['name']}...")
        
        try:
            response = bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(test_case['body']),
                contentType="application/json"
            )
            print(f"✅ {test_case['name']} - SUCCESS!")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"❌ {test_case['name']} - {error_code}")
        except Exception as e:
            print(f"❌ {test_case['name']} - {str(e)}")
    
    return False

if __name__ == "__main__":
    print("🔍 Claude 3.5 Sonnet Connection Test")
    print("=" * 60)
    
    # Test main format
    success = test_claude_35_sonnet()
    
    if not success:
        # Test alternative formats
        success = test_alternative_formats()
    
    if success:
        print("\n🎉 Claude 3.5 Sonnet is working!")
        print("💡 You can now update your configuration to use this model.")
    else:
        print("\n⚠️  Claude 3.5 Sonnet is not accessible.")
        print("💡 Please double-check the model enablement in AWS Bedrock console.")
