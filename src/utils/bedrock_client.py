"""
AWS Bedrock Client for AI/LLM Operations

This module provides a unified interface for using AWS Bedrock models
including Claude Haiku, Sonnet, and other available models.
"""

import json
import logging
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class BedrockClient:
    """AWS Bedrock client for AI/LLM operations."""
    
    # Available Bedrock models (using inference profiles where applicable)
    MODELS = {
        "haiku": "us.anthropic.claude-3-haiku-20240307-v1:0",
        "sonnet": "us.anthropic.claude-3-sonnet-20240229-v1:0",
        "opus": "us.anthropic.claude-3-opus-20240229-v1:0",
        "claude-3-5-sonnet": "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        "claude-3-7-sonnet": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "claude-sonnet-4": "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "titan-text": "amazon.titan-text-express-v1",
        "titan-embed": "amazon.titan-embed-text-v2:0",
        "llama2": "meta.llama2-13b-chat-v1",
        "llama3": "meta.llama3-8b-instruct-v1:0"
    }
    
    def __init__(self, model_id: str = None, region: str = "us-east-1"):
        """
        Initialize Bedrock client.
        
        Args:
            model_id: Bedrock model ID (defaults to Haiku)
            region: AWS region
        """
        self.model_id = model_id or self.MODELS["haiku"]
        self.region = region
        
        try:
            self.client = boto3.client('bedrock-runtime', region_name=region)
            logger.info(f"Bedrock client initialized for model: {self.model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     top_p: float = 0.9,
                     system_prompt: str = None) -> str:
        """
        Generate text using Bedrock model.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Top-p sampling parameter
            system_prompt: Optional system prompt
            
        Returns:
            Generated text
            
        Raises:
            Exception: If generation fails
        """
        try:
            # Prepare the request body based on model type
            if "claude" in self.model_id.lower():
                return self._generate_claude_text(prompt, max_tokens, temperature, top_p, system_prompt)
            elif "titan" in self.model_id.lower():
                return self._generate_titan_text(prompt, max_tokens, temperature, top_p)
            elif "llama" in self.model_id.lower():
                return self._generate_llama_text(prompt, max_tokens, temperature, top_p)
            else:
                raise ValueError(f"Unsupported model: {self.model_id}")
                
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise
    
    def _generate_claude_text(self, prompt: str, max_tokens: int, temperature: float, top_p: float, system_prompt: str = None) -> str:
        """Generate text using Claude models."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "user", "content": f"System: {system_prompt}\n\nUser: {prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "messages": messages
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def _generate_titan_text(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> str:
        """Generate text using Titan models."""
        body = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": max_tokens,
                "temperature": temperature,
                "topP": top_p
            }
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['results'][0]['outputText']
    
    def _generate_llama_text(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> str:
        """Generate text using Llama models."""
        body = {
            "prompt": prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['generation']
    
    def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text using Titan Embeddings.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
            
        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Use Titan Embeddings model
            embedding_model_id = self.MODELS["titan-embed"]
            
            body = {
                "inputText": text
            }
            
            response = self.client.invoke_model(
                modelId=embedding_model_id,
                body=json.dumps(body),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       max_tokens: int = 1000,
                       temperature: float = 0.7) -> Dict[str, Any]:
        """
        Chat completion interface compatible with OpenAI format.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Response in OpenAI-compatible format
        """
        try:
            # Convert messages to Claude format
            claude_messages = []
            system_prompt = None
            
            for message in messages:
                if message["role"] == "system":
                    system_prompt = message["content"]
                else:
                    claude_messages.append({
                        "role": message["role"],
                        "content": message["content"]
                    })
            
            # Generate response
            if claude_messages:
                prompt = claude_messages[-1]["content"]
                response_text = self.generate_text(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt=system_prompt
                )
                
                return {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": response_text
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(response_text.split()),
                        "total_tokens": len(prompt.split()) + len(response_text.split())
                    }
                }
            else:
                raise ValueError("No messages provided")
                
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test Bedrock connection and model availability.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to list available models
            bedrock_client = boto3.client('bedrock', region_name=self.region)
            response = bedrock_client.list_foundation_models()
            
            # Check if our model is available
            available_models = [model['modelId'] for model in response['modelSummaries']]
            if self.model_id in available_models:
                logger.info(f"Bedrock model {self.model_id} is available")
                return True
            else:
                logger.warning(f"Bedrock model {self.model_id} not found in available models")
                return False
                
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {e}")
            return False
    
    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """Get available Bedrock models."""
        return cls.MODELS.copy()
    
    @classmethod
    def create_from_config(cls):
        """Create Bedrock client from configuration."""
        from config.settings import get_settings
        
        settings = get_settings()
        return cls(
            model_id=settings.bedrock_model_id,
            region=settings.bedrock_region
        )


def get_bedrock_client(model_name: str = "haiku", region: str = "us-east-1") -> BedrockClient:
    """
    Create a Bedrock client for the specified model.
    
    Args:
        model_name: Model name (haiku, sonnet, opus, etc.)
        region: AWS region
        
    Returns:
        Configured BedrockClient instance
    """
    models = BedrockClient.get_available_models()
    
    if model_name not in models:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(models.keys())}")
    
    return BedrockClient(model_id=models[model_name], region=region)
