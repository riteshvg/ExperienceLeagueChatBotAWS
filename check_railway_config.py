#!/usr/bin/env python3
"""
Railway Configuration Checker

This script checks if all required environment variables are set for Railway deployment.
"""

import os
import sys
from typing import List, Dict

def check_environment_variables() -> Dict[str, bool]:
    """Check if all required environment variables are set."""
    
    required_vars = {
        # AWS Configuration
        "AWS_ACCESS_KEY_ID": "AWS Access Key ID",
        "AWS_SECRET_ACCESS_KEY": "AWS Secret Access Key", 
        "AWS_DEFAULT_REGION": "AWS Region (default: us-east-1)",
        "AWS_S3_BUCKET": "S3 Bucket Name",
        
        # Bedrock Configuration
        "BEDROCK_KNOWLEDGE_BASE_ID": "Bedrock Knowledge Base ID",
        "BEDROCK_REGION": "Bedrock Region (default: us-east-1)",
        "BEDROCK_MODEL_ID": "Bedrock Model ID (optional)",
        "BEDROCK_EMBEDDING_MODEL_ID": "Bedrock Embedding Model ID (optional)",
        
        # Adobe Analytics API
        "ADOBE_CLIENT_ID": "Adobe Client ID",
        "ADOBE_CLIENT_SECRET": "Adobe Client Secret",
        "ADOBE_ORGANIZATION_ID": "Adobe Organization ID",
        
        # Database (Railway sets this automatically)
        "DATABASE_URL": "Database URL (Railway sets this automatically)",
    }
    
    results = {}
    missing_vars = []
    
    print("🔍 Checking Railway Environment Variables")
    print("=" * 50)
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "SECRET" in var or "KEY" in var or "PASSWORD" in var:
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
            results[var] = True
        else:
            print(f"❌ {var}: NOT SET - {description}")
            results[var] = False
            missing_vars.append(var)
    
    print("\n" + "=" * 50)
    
    if missing_vars:
        print(f"❌ Missing {len(missing_vars)} required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n🔧 To fix this:")
        print("1. Go to Railway Dashboard")
        print("2. Select your project")
        print("3. Go to 'Variables' tab")
        print("4. Add the missing environment variables")
        print("5. Redeploy your application")
        return False
    else:
        print("🎉 All required environment variables are set!")
        print("✅ Your Railway deployment should work correctly")
        return True

def check_optional_variables():
    """Check optional environment variables."""
    
    optional_vars = {
        "ENVIRONMENT": "Environment (default: development)",
        "LOG_LEVEL": "Log Level (default: INFO)",
        "DEBUG": "Debug Mode (default: false)",
        "STREAMLIT_SERVER_PORT": "Streamlit Port (default: 8501)",
        "STREAMLIT_SERVER_ADDRESS": "Streamlit Address (default: 0.0.0.0)",
    }
    
    print("\n🔍 Checking Optional Environment Variables")
    print("=" * 50)
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚪ {var}: Not set (using default) - {description}")

def main():
    """Main function."""
    print("🚀 Railway Configuration Checker")
    print("=" * 50)
    
    # Check required variables
    required_ok = check_environment_variables()
    
    # Check optional variables
    check_optional_variables()
    
    print("\n" + "=" * 50)
    
    if required_ok:
        print("🎉 Configuration check passed!")
        print("✅ Your app should deploy successfully on Railway")
        return 0
    else:
        print("❌ Configuration check failed!")
        print("🔧 Please set the missing environment variables and try again")
        return 1

if __name__ == "__main__":
    exit(main())
