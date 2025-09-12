"""
Streaming AWS Bedrock Client for Real-time AI Responses

This module provides streaming capabilities for AWS Bedrock models,
allowing responses to be generated and displayed progressively.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Generator
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class StreamingBedrockClient:
    """AWS Bedrock client with streaming capabilities."""
    
    # Available Bedrock models
    MODELS = {
        "haiku": "us.anthropic.claude-3-haiku-20240307-v1:0",
        "sonnet": "us.anthropic.claude-3-sonnet-20240229-v1:0",
        "opus": "us.anthropic.claude-3-opus-20240229-v1:0",
        "claude-3-5-sonnet": "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        "claude-3-7-sonnet": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    }
    
    def __init__(self, model_id: str = None, region: str = "us-east-1"):
        """Initialize streaming Bedrock client."""
        self.model_id = model_id or self.MODELS["haiku"]
        self.region = region
        
        try:
            self.client = boto3.client('bedrock-runtime', region_name=region)
            logger.info(f"Streaming Bedrock client initialized for model: {self.model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    def generate_streaming_text(self, 
                              prompt: str, 
                              max_tokens: int = 1000,
                              temperature: float = 0.7,
                              top_p: float = 0.9,
                              system_prompt: str = None) -> Generator[str, None, None]:
        """
        Generate streaming text using Bedrock model.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Top-p sampling parameter
            system_prompt: Optional system prompt
            
        Yields:
            Text chunks as they are generated
        """
        try:
            if "claude" in self.model_id.lower():
                yield from self._generate_claude_streaming_text(prompt, max_tokens, temperature, top_p, system_prompt)
            else:
                # For non-Claude models, fall back to regular generation with simulated streaming
                yield from self._simulate_streaming(prompt, max_tokens, temperature, top_p)
                
        except Exception as e:
            logger.error(f"Streaming text generation failed: {e}")
            yield f"Error: {str(e)}"
    
    def _generate_claude_streaming_text(self, prompt: str, max_tokens: int, temperature: float, top_p: float, system_prompt: str = None) -> Generator[str, None, None]:
        """Generate streaming text using Claude models."""
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
        
        try:
            # Use invoke_model_with_response_stream for streaming
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json"
            )
            
            # Process streaming response
            for event in response['body']:
                if event:
                    chunk = json.loads(event['chunk']['bytes'])
                    if chunk['type'] == 'content_block_delta':
                        if 'text' in chunk['delta']:
                            yield chunk['delta']['text']
                            
        except Exception as e:
            logger.error(f"Claude streaming failed: {e}")
            # Fallback to regular generation with simulated streaming
            yield from self._simulate_streaming(prompt, max_tokens, temperature, top_p)
    
    def _simulate_streaming(self, prompt: str, max_tokens: int, temperature: float, top_p: float) -> Generator[str, None, None]:
        """Simulate streaming by generating text and yielding it in chunks."""
        try:
            # Generate full text first
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            full_text = response_body['content'][0]['text']
            
            # Split into words and yield progressively
            words = full_text.split()
            current_text = ""
            
            for i, word in enumerate(words):
                current_text += word + " "
                
                # Yield every 3-5 words or at punctuation
                if (i + 1) % 4 == 0 or word.endswith(('.', '!', '?', ':', ';')):
                    yield current_text
                    current_text = ""
                    time.sleep(0.05)  # Small delay for realistic streaming effect
            
            # Yield any remaining text
            if current_text.strip():
                yield current_text
                
        except Exception as e:
            logger.error(f"Simulated streaming failed: {e}")
            yield f"Error generating response: {str(e)}"
    
    def generate_text(self, 
                     prompt: str, 
                     max_tokens: int = 1000,
                     temperature: float = 0.7,
                     top_p: float = 0.9,
                     system_prompt: str = None) -> str:
        """
        Generate complete text (non-streaming) using Bedrock model.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Top-p sampling parameter
            system_prompt: Optional system prompt
            
        Returns:
            Complete generated text
        """
        try:
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
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise


def get_streaming_bedrock_client(model_name: str = "haiku", region: str = "us-east-1") -> StreamingBedrockClient:
    """
    Create a streaming Bedrock client for the specified model.
    
    Args:
        model_name: Model name (haiku, sonnet, opus, etc.)
        region: AWS region
        
    Returns:
        Configured StreamingBedrockClient instance
    """
    models = StreamingBedrockClient.MODELS
    
    if model_name not in models:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(models.keys())}")
    
    return StreamingBedrockClient(model_id=models[model_name], region=region)
