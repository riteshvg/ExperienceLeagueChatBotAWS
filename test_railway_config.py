#!/usr/bin/env python3
"""
Test Railway configuration and identify issues.
"""

import os
import sys
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

def test_environment_variables():
    """Test if all required environment variables are set."""
    print("🔍 Testing Environment Variables")
    print("=" * 50)
    
    required_vars = {
        "AWS_ACCESS_KEY_ID": "AWS Access Key ID",
        "AWS_SECRET_ACCESS_KEY": "AWS Secret Access Key",
        "AWS_DEFAULT_REGION": "AWS Region",
        "AWS_S3_BUCKET": "S3 Bucket Name",
        "BEDROCK_KNOWLEDGE_BASE_ID": "Bedrock Knowledge Base ID",
        "BEDROCK_REGION": "Bedrock Region",
        "ADOBE_CLIENT_ID": "Adobe Client ID",
        "ADOBE_CLIENT_SECRET": "Adobe Client Secret",
        "ADOBE_ORGANIZATION_ID": "Adobe Organization ID",
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            if "SECRET" in var or "KEY" in var:
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET - {description}")
            missing_vars.append(var)
    
    return missing_vars

def test_configuration_loading():
    """Test if configuration can be loaded."""
    print("\n🔧 Testing Configuration Loading")
    print("=" * 50)
    
    try:
        from config.settings import Settings
        settings = Settings()
        print("✅ Settings class loaded successfully")
        
        # Test specific attributes
        if hasattr(settings, 'aws_default_region'):
            print(f"✅ aws_default_region: {settings.aws_default_region}")
        else:
            print("❌ aws_default_region attribute not found")
            
        if hasattr(settings, 'bedrock_knowledge_base_id'):
            print(f"✅ bedrock_knowledge_base_id: {settings.bedrock_knowledge_base_id}")
        else:
            print("❌ bedrock_knowledge_base_id attribute not found")
            
        return True, settings
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False, None

def test_aws_connection():
    """Test AWS connection."""
    print("\n☁️ Testing AWS Connection")
    print("=" * 50)
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Test STS connection
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ AWS Identity: {identity.get('Arn', 'Unknown')}")
        
        # Test Bedrock connection
        bedrock_client = boto3.client('bedrock', region_name='us-east-1')
        print("✅ Bedrock client created successfully")
        
        return True
        
    except ClientError as e:
        print(f"❌ AWS connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ AWS connection error: {e}")
        return False

def test_database_connection():
    """Test database connection."""
    print("\n🗄️ Testing Database Connection")
    print("=" * 50)
    
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            print(f"✅ DATABASE_URL found: {database_url[:20]}...")
            
            import psycopg2
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print("✅ Database connection successful")
            cursor.close()
            conn.close()
            return True
        else:
            print("❌ DATABASE_URL not found")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Railway Configuration Test")
    print("=" * 50)
    
    # Test environment variables
    missing_vars = test_environment_variables()
    
    # Test configuration loading
    config_ok, settings = test_configuration_loading()
    
    # Test AWS connection
    aws_ok = test_aws_connection()
    
    # Test database connection
    db_ok = test_database_connection()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    if missing_vars:
        print(f"❌ Missing {len(missing_vars)} environment variables")
        print("🔧 Add these to Railway Variables:")
        for var in missing_vars:
            print(f"   - {var}")
    else:
        print("✅ All environment variables present")
    
    if config_ok:
        print("✅ Configuration loading works")
    else:
        print("❌ Configuration loading failed")
    
    if aws_ok:
        print("✅ AWS connection works")
    else:
        print("❌ AWS connection failed")
    
    if db_ok:
        print("✅ Database connection works")
    else:
        print("❌ Database connection failed")
    
    if not missing_vars and config_ok and aws_ok:
        print("\n🎉 All tests passed! Your app should work.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
