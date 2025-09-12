#!/usr/bin/env python3
"""
Simple health check for Railway deployment.
"""

import os
import sys
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

def check_health():
    """Check if the app is healthy."""
    print("🏥 Health Check for Railway App")
    print("=" * 40)
    
    # Check environment variables
    required_vars = [
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION",
        "AWS_S3_BUCKET", "BEDROCK_KNOWLEDGE_BASE_ID", "BEDROCK_REGION",
        "ADOBE_CLIENT_ID", "ADOBE_CLIENT_SECRET", "ADOBE_ORGANIZATION_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required environment variables present")
    
    # Check configuration loading
    try:
        from config.settings import Settings
        settings = Settings()
        print("✅ Configuration loaded successfully")
        print(f"   - AWS Region: {settings.aws_default_region}")
        print(f"   - S3 Bucket: {settings.aws_s3_bucket}")
        print(f"   - KB ID: {settings.bedrock_knowledge_base_id}")
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    # Check AWS connection
    try:
        import boto3
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        print(f"✅ AWS connection successful: {identity.get('Arn', 'Unknown')}")
    except Exception as e:
        print(f"❌ AWS connection failed: {e}")
        return False
    
    # Check database
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            import psycopg2
            conn = psycopg2.connect(database_url)
            conn.close()
            print("✅ Database connection successful")
        else:
            print("⚠️ No DATABASE_URL found")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    print("\n🎉 Health check passed! App should be working.")
    return True

if __name__ == "__main__":
    if check_health():
        exit(0)
    else:
        exit(1)
