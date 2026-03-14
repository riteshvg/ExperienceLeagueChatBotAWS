"""
Dependency injection for FastAPI routes.
Provides reusable dependencies for AWS clients, settings, etc.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from app.core.config import settings
from config.settings import Settings as AppSettings
from src.utils.aws_utils import (
    get_sts_client,
    get_bedrock_client,
    get_bedrock_agent_client,
    get_s3_client,
    get_cost_explorer_client
)
# BedrockClient will be imported from the existing module
try:
    from src.utils.bedrock_client import BedrockClient
except ImportError:
    try:
        # Alternative import path
        from utils.bedrock_client import BedrockClient
    except ImportError:
        # Fallback if import path is different
        BedrockClient = None


def get_settings() -> AppSettings:
    """Dependency to get application settings"""
    return AppSettings()


def get_aws_clients(settings: AppSettings = Depends(get_settings)):
    """Dependency to get AWS clients"""
    try:
        clients = {
            "sts": get_sts_client(settings.aws_default_region),
            "bedrock": get_bedrock_client(settings.bedrock_region),
            "bedrock_agent": get_bedrock_agent_client(settings.bedrock_region),
            "s3": get_s3_client(settings.aws_default_region),
            "cost_explorer": get_cost_explorer_client(settings.aws_default_region),
        }
        
        # Add BedrockClient if available
        if BedrockClient:
            clients["bedrock_client"] = BedrockClient(
                model_id=settings.bedrock_model_id,
                region=settings.bedrock_region
            )
        
        return clients
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize AWS clients: {str(e)}"
        )


def verify_aws_connection(aws_clients: dict = Depends(get_aws_clients)):
    """Dependency to verify AWS connection is working"""
    try:
        identity = aws_clients["sts"].get_caller_identity()
        return {
            "account_id": identity.get("Account"),
            "arn": identity.get("Arn"),
            "clients": aws_clients
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AWS connection failed: {str(e)}"
        )

