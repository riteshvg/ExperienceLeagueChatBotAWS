#!/usr/bin/env python3
"""
Test AWS Bedrock Integration

This script tests the Bedrock client functionality with different models.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.utils.bedrock_client import BedrockClient, get_bedrock_client

def test_bedrock_models():
    """Test different Bedrock models."""
    print("🧪 Testing AWS Bedrock Models")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Test available models
    print("\n📋 Available Bedrock Models:")
    models = BedrockClient.get_available_models()
    for name, model_id in models.items():
        print(f"  {name}: {model_id}")
    
    # Test Haiku model
    print("\n🚀 Testing Claude Haiku...")
    try:
        haiku_client = get_bedrock_client("haiku")
        
        if haiku_client.test_connection():
            print("✅ Haiku connection successful")
            
            # Test text generation
            response = haiku_client.generate_text(
                prompt="What is Adobe Analytics?",
                max_tokens=100,
                temperature=0.7
            )
            print(f"✅ Haiku response: {response[:100]}...")
        else:
            print("❌ Haiku connection failed")
            
    except Exception as e:
        print(f"❌ Haiku test failed: {e}")
    
    # Test Sonnet model
    print("\n🚀 Testing Claude Sonnet...")
    try:
        sonnet_client = get_bedrock_client("sonnet")
        
        if sonnet_client.test_connection():
            print("✅ Sonnet connection successful")
            
            # Test chat completion
            messages = [
                {"role": "user", "content": "Explain Adobe Analytics in one sentence."}
            ]
            
            response = sonnet_client.chat_completion(messages, max_tokens=50)
            print(f"✅ Sonnet response: {response['choices'][0]['message']['content']}")
        else:
            print("❌ Sonnet connection failed")
            
    except Exception as e:
        print(f"❌ Sonnet test failed: {e}")
    
    # Test embeddings
    print("\n🚀 Testing Titan Embeddings...")
    try:
        haiku_client = get_bedrock_client("haiku")
        embeddings = haiku_client.generate_embeddings("Adobe Analytics is a web analytics platform")
        print(f"✅ Embeddings generated: {len(embeddings)} dimensions")
        print(f"   First 5 values: {embeddings[:5]}")
        
    except Exception as e:
        print(f"❌ Embeddings test failed: {e}")

def test_model_comparison():
    """Compare different models on the same prompt."""
    print("\n🔍 Model Comparison Test")
    print("=" * 40)
    
    prompt = "What are the key features of Adobe Analytics?"
    
    models_to_test = ["haiku", "sonnet"]
    
    for model_name in models_to_test:
        print(f"\n🤖 Testing {model_name.upper()}:")
        try:
            client = get_bedrock_client(model_name)
            
            if client.test_connection():
                response = client.generate_text(
                    prompt=prompt,
                    max_tokens=150,
                    temperature=0.7
                )
                print(f"✅ {model_name.upper()} Response:")
                print(f"   {response}")
            else:
                print(f"❌ {model_name.upper()} connection failed")
                
        except Exception as e:
            print(f"❌ {model_name.upper()} test failed: {e}")

def main():
    """Main test function."""
    try:
        test_bedrock_models()
        test_model_comparison()
        
        print("\n🎉 Bedrock testing completed!")
        print("\nNext steps:")
        print("1. Run: python test_config.py")
        print("2. Run: python scripts/setup_aws_infrastructure.py")
        print("3. Start the application: streamlit run src/app.py")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
