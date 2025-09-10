#!/usr/bin/env python3
"""
Configuration Test Script

This script validates your .env configuration and tests connectivity to various services.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    from config.settings import get_settings
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)


def test_env_file():
    """Test if .env file exists and is readable."""
    print("🔍 Testing .env file...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        print("Run: python scripts/setup_env.py")
        return False
    
    print("✅ .env file found")
    return True


def test_basic_config():
    """Test basic configuration loading."""
    print("\n🔧 Testing basic configuration...")
    
    try:
        settings = get_settings()
        print("✅ Configuration loaded successfully")
        print(f"   Environment: {settings.environment}")
        print(f"   Log Level: {settings.log_level}")
        print(f"   Debug Mode: {settings.debug}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def test_aws_config():
    """Test AWS configuration."""
    print("\n☁️ Testing AWS configuration...")
    
    try:
        settings = get_settings()
        
        # Check required AWS settings
        if not settings.aws_s3_bucket:
            print("❌ AWS_S3_BUCKET not set")
            return False
        
        print(f"✅ AWS Region: {settings.aws_default_region}")
        print(f"✅ S3 Bucket: {settings.aws_s3_bucket}")
        
        # Test AWS connectivity
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError
            
            # Try to create a client
            if hasattr(settings, 'aws_profile') and settings.aws_profile:
                session = boto3.Session(profile_name=settings.aws_profile)
                s3_client = session.client('s3')
            else:
                s3_client = boto3.client('s3')
            
            # Test credentials by getting caller identity
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            print(f"✅ AWS credentials valid (Account: {identity['Account']})")
            
        except NoCredentialsError:
            print("❌ AWS credentials not found")
            return False
        except ClientError as e:
            print(f"❌ AWS credentials invalid: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ AWS configuration error: {e}")
        return False


def test_adobe_config():
    """Test Adobe Analytics configuration (OAuth Server-to-Server)."""
    print("\n🎨 Testing Adobe Analytics configuration...")
    
    try:
        settings = get_settings()
        
        # Check required Adobe settings (OAuth Server-to-Server)
        required_fields = [
            'adobe_client_id',
            'adobe_client_secret', 
            'adobe_organization_id'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(settings, field, None):
                missing_fields.append(field.upper())
        
        if missing_fields:
            print(f"❌ Missing Adobe fields: {', '.join(missing_fields)}")
            print("Note: JWT authentication is deprecated. Use OAuth Server-to-Server credentials.")
            return False
        
        print("✅ Adobe OAuth Server-to-Server configuration complete")
        print(f"   Organization ID: {settings.adobe_organization_id}")
        print(f"   Client ID: {settings.adobe_client_id}")
        
        # Test OAuth2 connection
        try:
            from src.utils.adobe_auth import get_adobe_auth_from_config
            adobe_auth = get_adobe_auth_from_config()
            
            if adobe_auth.test_connection():
                print("✅ Adobe OAuth2 connection test successful")
            else:
                print("⚠️  Adobe OAuth2 connection test failed - check credentials")
                
        except ImportError:
            print("⚠️  Adobe OAuth2 module not available - skipping connection test")
        except Exception as e:
            print(f"⚠️  Adobe OAuth2 test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Adobe configuration error: {e}")
        return False


def test_ai_config():
    """Test AI/LLM configuration."""
    print("\n🤖 Testing AI/LLM configuration...")
    
    try:
        settings = get_settings()
        
        # Check for different AI providers
        has_openai = bool(settings.openai_api_key)
        has_bedrock = bool(getattr(settings, 'bedrock_model_id', None))
        has_azure = bool(getattr(settings, 'azure_openai_endpoint', None))
        
        if not (has_openai or has_bedrock or has_azure):
            print("❌ No AI provider configured (OpenAI, Bedrock, or Azure OpenAI)")
            return False
        
        if has_bedrock:
            print("✅ AWS Bedrock configuration found")
            print(f"   Model: {settings.bedrock_model_id}")
            print(f"   Region: {settings.bedrock_region}")
            
            # Test Bedrock connection
            try:
                from src.utils.bedrock_client import BedrockClient
                bedrock_client = BedrockClient.create_from_config()
                
                if bedrock_client.test_connection():
                    print("✅ Bedrock connection test successful")
                else:
                    print("⚠️  Bedrock connection test failed - check permissions")
                    
            except ImportError:
                print("⚠️  Bedrock client module not available - skipping connection test")
            except Exception as e:
                print(f"⚠️  Bedrock test failed: {e}")
        
        if has_openai:
            print("✅ OpenAI configuration found")
            # Test OpenAI API key format
            if not settings.openai_api_key.startswith('sk-'):
                print("⚠️  OpenAI API key format looks incorrect (should start with 'sk-')")
        
        if has_azure:
            print("✅ Azure OpenAI configuration found")
            print(f"   Endpoint: {getattr(settings, 'azure_openai_endpoint', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI configuration error: {e}")
        return False


def test_database_config():
    """Test database configuration."""
    print("\n🗄️ Testing database configuration...")
    
    try:
        settings = get_settings()
        
        db_url = settings.database_url
        print(f"✅ Database URL: {db_url}")
        
        if db_url.startswith('sqlite'):
            print("✅ SQLite database (no additional setup required)")
        elif db_url.startswith('postgresql'):
            print("⚠️  PostgreSQL database - ensure PostgreSQL is running")
        else:
            print("⚠️  Unknown database type")
        
        return True
        
    except Exception as e:
        print(f"❌ Database configuration error: {e}")
        return False


def test_rag_config():
    """Test RAG configuration."""
    print("\n🔍 Testing RAG configuration...")
    
    try:
        settings = get_settings()
        
        print(f"✅ Chunk Size: {settings.chunk_size}")
        print(f"✅ Chunk Overlap: {settings.chunk_overlap}")
        print(f"✅ Embedding Model: {settings.embedding_model}")
        print(f"✅ Vector Store Path: {settings.vector_store_path}")
        
        # Create vector store directory if it doesn't exist
        vector_store_path = Path(settings.vector_store_path)
        vector_store_path.mkdir(parents=True, exist_ok=True)
        print("✅ Vector store directory ready")
        
        return True
        
    except Exception as e:
        print(f"❌ RAG configuration error: {e}")
        return False


def main():
    """Run all configuration tests."""
    print("🧪 Adobe Analytics RAG - Configuration Test")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    tests = [
        ("Environment File", test_env_file),
        ("Basic Configuration", test_basic_config),
        ("AWS Configuration", test_aws_config),
        ("Adobe Analytics", test_adobe_config),
        ("AI/LLM Configuration", test_ai_config),
        ("Database Configuration", test_database_config),
        ("RAG Configuration", test_rag_config),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your configuration is ready.")
        print("\nNext steps:")
        print("1. Run AWS infrastructure setup: python scripts/setup_aws_infrastructure.py")
        print("2. Start the application: streamlit run src/app.py")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues above.")
        print("\nFor help, see: scripts/setup_env_guide.md")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
