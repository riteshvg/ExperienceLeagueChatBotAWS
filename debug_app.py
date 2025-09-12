#!/usr/bin/env python3
"""
Debug version of the app to identify issues.
"""

import streamlit as st
import os
import sys
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

st.set_page_config(
    page_title="Debug - Adobe Analytics Chatbot",
    page_icon="🐛",
    layout="wide"
)

def main():
    st.title("🐛 Debug Information")
    
    st.header("Environment Variables")
    
    required_vars = [
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION",
        "AWS_S3_BUCKET", "BEDROCK_KNOWLEDGE_BASE_ID", "BEDROCK_REGION",
        "ADOBE_CLIENT_ID", "ADOBE_CLIENT_SECRET", "ADOBE_ORGANIZATION_ID",
        "DATABASE_URL"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if "SECRET" in var or "KEY" in var or "PASSWORD" in var:
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "*" * len(value)
                st.success(f"✅ {var}: {masked_value}")
            else:
                st.success(f"✅ {var}: {value}")
        else:
            st.error(f"❌ {var}: NOT SET")
    
    st.header("Configuration Loading")
    
    try:
        from config.settings import Settings
        settings = Settings()
        st.success("✅ Settings loaded successfully")
        
        st.subheader("Settings Details:")
        st.write(f"- AWS Region: {settings.aws_default_region}")
        st.write(f"- S3 Bucket: {settings.aws_s3_bucket}")
        st.write(f"- KB ID: {settings.bedrock_knowledge_base_id}")
        st.write(f"- Bedrock Region: {settings.bedrock_region}")
        
    except Exception as e:
        st.error(f"❌ Configuration loading failed: {e}")
        st.exception(e)
    
    st.header("AWS Connection Test")
    
    try:
        import boto3
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        st.success(f"✅ AWS connection successful: {identity.get('Arn', 'Unknown')}")
    except Exception as e:
        st.error(f"❌ AWS connection failed: {e}")
        st.exception(e)
    
    st.header("Database Connection Test")
    
    try:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            import psycopg2
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            st.success("✅ Database connection successful")
            cursor.close()
            conn.close()
        else:
            st.warning("⚠️ No DATABASE_URL found")
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        st.exception(e)

if __name__ == "__main__":
    main()
