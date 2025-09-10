"""
Utilities Module

This module contains utility functions and helper classes used throughout
the Adobe Analytics RAG chatbot application.
"""

# Import available modules
try:
    from .bedrock_client import BedrockClient, get_bedrock_client
    __all__ = ["BedrockClient", "get_bedrock_client"]
except ImportError:
    __all__ = []
