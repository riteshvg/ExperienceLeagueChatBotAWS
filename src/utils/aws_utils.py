"""
AWS utility functions for Adobe Analytics RAG Chatbot.
"""

import boto3
from typing import Optional
from config.settings import Settings


def get_s3_client(region: str = "us-east-1") -> boto3.client:
    """Get S3 client for the specified region."""
    return boto3.client('s3', region_name=region)


def get_sts_client(region: str = "us-east-1") -> boto3.client:
    """Get STS client for the specified region."""
    return boto3.client('sts', region_name=region)


def get_bedrock_client(region: str = "us-east-1") -> boto3.client:
    """Get Bedrock client for the specified region."""
    return boto3.client('bedrock-runtime', region_name=region)


def get_bedrock_agent_client(region: str = "us-east-1") -> boto3.client:
    """Get Bedrock Agent Runtime client for the specified region."""
    return boto3.client('bedrock-agent-runtime', region_name=region)


def get_aws_identity() -> dict:
    """Get AWS caller identity information."""
    sts_client = get_sts_client()
    return sts_client.get_caller_identity()


def test_s3_bucket_access(bucket_name: str, region: str = "us-east-1") -> bool:
    """Test if S3 bucket is accessible."""
    try:
        s3_client = get_s3_client(region)
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except Exception:
        return False


def list_s3_objects(bucket_name: str, prefix: str = "", region: str = "us-east-1") -> list:
    """List objects in S3 bucket with optional prefix."""
    try:
        s3_client = get_s3_client(region)
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        return response.get('Contents', [])
    except Exception:
        return []


def get_s3_object(bucket_name: str, key: str, region: str = "us-east-1") -> Optional[bytes]:
    """Get S3 object content."""
    try:
        s3_client = get_s3_client(region)
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read()
    except Exception:
        return None
