"""
Adobe Analytics OAuth Server-to-Server Authentication

This module handles OAuth2 authentication for Adobe Analytics API using the
modern Server-to-Server credentials (replacing deprecated JWT).
"""

import os
import time
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AdobeOAuth2Auth:
    """Handles OAuth2 Server-to-Server authentication for Adobe Analytics API."""
    
    def __init__(self, client_id: str, client_secret: str, organization_id: str):
        """
        Initialize Adobe OAuth2 authentication.
        
        Args:
            client_id: Adobe Client ID
            client_secret: Adobe Client Secret
            organization_id: Adobe Organization ID
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.organization_id = organization_id
        self.access_token = None
        self.token_expires_at = None
        self.base_url = "https://ims-na1.adobelogin.com"
        
    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token string
            
        Raises:
            Exception: If authentication fails
        """
        if self._is_token_valid():
            return self.access_token
            
        return self._refresh_access_token()
    
    def _is_token_valid(self) -> bool:
        """Check if current token is still valid."""
        if not self.access_token or not self.token_expires_at:
            return False
            
        # Add 5-minute buffer to avoid edge cases
        buffer_time = timedelta(minutes=5)
        return datetime.now() < (self.token_expires_at - buffer_time)
    
    def _refresh_access_token(self) -> str:
        """
        Refresh the access token using OAuth2 client credentials flow.
        
        Returns:
            New access token string
            
        Raises:
            Exception: If token refresh fails
        """
        logger.info("Refreshing Adobe OAuth2 access token...")
        
        token_url = f"{self.base_url}/ims/token/v3"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache"
        }
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "openid,AdobeID,read_organizations,additional_info.projectedProductContext,read_analytics"
        }
        
        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            logger.info(f"Successfully refreshed Adobe OAuth2 token (expires in {expires_in}s)")
            return self.access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to refresh Adobe OAuth2 token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Adobe OAuth2 authentication failed: {e}")
        except KeyError as e:
            logger.error(f"Invalid response format from Adobe OAuth2: {e}")
            raise Exception(f"Invalid Adobe OAuth2 response: {e}")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get headers with valid authorization token.
        
        Returns:
            Dictionary with authorization headers
        """
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-api-key": self.client_id
        }
    
    def test_connection(self) -> bool:
        """
        Test the OAuth2 connection by making a simple API call.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test with a simple Adobe Analytics API call
            test_url = f"https://analytics.adobe.io/api/{self.organization_id}/reports"
            headers = self.get_auth_headers()
            
            # Make a simple request to test authentication
            response = requests.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("Adobe OAuth2 connection test successful")
                return True
            elif response.status_code == 401:
                logger.error("Adobe OAuth2 authentication failed - invalid credentials")
                return False
            else:
                logger.warning(f"Adobe OAuth2 test returned status {response.status_code}")
                return True  # Authentication worked, but API call failed for other reasons
                
        except Exception as e:
            logger.error(f"Adobe OAuth2 connection test failed: {e}")
            return False


def create_adobe_auth(client_id: str, client_secret: str, organization_id: str) -> AdobeOAuth2Auth:
    """
    Create an Adobe OAuth2 authentication instance.
    
    Args:
        client_id: Adobe Client ID
        client_secret: Adobe Client Secret
        organization_id: Adobe Organization ID
        
    Returns:
        Configured AdobeOAuth2Auth instance
    """
    return AdobeOAuth2Auth(client_id, client_secret, organization_id)


def get_adobe_auth_from_config() -> AdobeOAuth2Auth:
    """
    Create Adobe OAuth2 authentication from environment configuration.
    
    Returns:
        Configured AdobeOAuth2Auth instance
        
    Raises:
        Exception: If required configuration is missing
    """
    from config.settings import get_settings
    
    settings = get_settings()
    
    if not settings.adobe_client_id:
        raise Exception("ADOBE_CLIENT_ID not configured")
    if not settings.adobe_client_secret:
        raise Exception("ADOBE_CLIENT_SECRET not configured")
    if not settings.adobe_organization_id:
        raise Exception("ADOBE_ORGANIZATION_ID not configured")
    
    return create_adobe_auth(
        settings.adobe_client_id,
        settings.adobe_client_secret,
        settings.adobe_organization_id
    )
