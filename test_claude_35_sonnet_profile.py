#!/usr/bin/env python3
"""
Test Claude 3.5 Sonnet v2 via Inference Profile

This script tests Claude 3.5 Sonnet v2 using the correct inference profile.
"""

import boto3
import json
from botocore.exceptions import ClientError

def test_claude_35_sonnet_profile():
    """Test Claude 3.5 Sonnet v2 via inference profile."""
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Use the inference profile ID instead of direct model ID
    inference_profile_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    print("🧪 Testing Claude 3.5 Sonnet v2 via Inference Profile")
    print("=" * 60)
    print(f"Inference Profile ID: {inference_profile_id}")
    print(f"Region: us-east-1")
    print()
    
    try:
        # Test with correct Claude 3.5 format
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
        
        print("🚀 Sending request to Claude 3.5 Sonnet v2...")
        response = bedrock_client.invoke_model(
            modelId=inference_profile_id,  # Use inference profile ID
            body=body,
            contentType="application/json"
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        print("✅ Claude 3.5 Sonnet v2 - SUCCESS!")
        print(f"✅ Response: {content}")
        print()
        print("🎉 Claude 3.5 Sonnet v2 is working perfectly via inference profile!")
        
        return True, inference_profile_id
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        print(f"❌ Claude 3.5 Sonnet v2 - ERROR!")
        print(f"Error Code: {error_code}")
        print(f"Error Message: {error_message}")
        
        if error_code == "AccessDeniedException":
            print("\n💡 This means the inference profile is not accessible.")
            print("   Please check the AWS Bedrock console to ensure the inference profile is enabled.")
        elif error_code == "ValidationException":
            print("\n💡 This might be a request format issue.")
            print("   The inference profile might be available but with different parameters.")
        else:
            print(f"\n💡 Unexpected error: {error_code}")
        
        return False, None
        
    except Exception as e:
        print(f"❌ Claude 3.5 Sonnet v2 - UNEXPECTED ERROR!")
        print(f"Error: {str(e)}")
        return False, None

def test_other_sonnet_profiles():
    """Test other available Sonnet inference profiles."""
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Other Sonnet profiles to test
    sonnet_profiles = [
        ("us.anthropic.claude-3-sonnet-20240229-v1:0", "Claude 3 Sonnet"),
        ("us.anthropic.claude-3-5-sonnet-20240620-v1:0", "Claude 3.5 Sonnet"),
        ("us.anthropic.claude-3-7-sonnet-20250219-v1:0", "Claude 3.7 Sonnet"),
        ("us.anthropic.claude-sonnet-4-20250514-v1:0", "Claude Sonnet 4"),
    ]
    
    print("\n🔍 Testing Other Sonnet Inference Profiles")
    print("=" * 60)
    
    working_profiles = []
    
    for profile_id, profile_name in sonnet_profiles:
        print(f"\n🧪 Testing {profile_name} ({profile_id})...")
        
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "Test"}]
            })
            
            response = bedrock_client.invoke_model(
                modelId=profile_id,
                body=body,
                contentType="application/json"
            )
            
            print(f"✅ {profile_name} - WORKING!")
            working_profiles.append((profile_id, profile_name))
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == "AccessDeniedException":
                print(f"❌ {profile_name} - NOT ACCESSIBLE")
            else:
                print(f"⚠️  {profile_name} - ERROR: {error_code}")
        except Exception as e:
            print(f"⚠️  {profile_name} - ERROR: {str(e)}")
    
    return working_profiles

if __name__ == "__main__":
    print("🔍 Claude 3.5 Sonnet v2 Inference Profile Test")
    print("=" * 70)
    
    # Test Claude 3.5 Sonnet v2
    success, profile_id = test_claude_35_sonnet_profile()
    
    if success:
        print(f"\n🎉 Claude 3.5 Sonnet v2 is working!")
        print(f"💡 Use this inference profile ID: {profile_id}")
        print("💡 You can now update your configuration to use this model.")
    else:
        # Test other Sonnet profiles
        working_profiles = test_other_sonnet_profiles()
        
        if working_profiles:
            print(f"\n🎉 Found {len(working_profiles)} working Sonnet profiles:")
            for profile_id, profile_name in working_profiles:
                print(f"   ✅ {profile_name} ({profile_id})")
        else:
            print("\n⚠️  No Sonnet profiles are accessible.")
            print("💡 Please check the model enablement in AWS Bedrock console.")
