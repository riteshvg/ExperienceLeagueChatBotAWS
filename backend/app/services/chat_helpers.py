"""
Helper functions extracted from app.py for chat service
These are standalone functions that don't depend on Streamlit
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

logger = logging.getLogger(__name__)


def check_query_relevance(query: str) -> bool:
    """Check if the query is relevant to Adobe Analytics, CJA, AEP, or related topics."""
    query_lower = query.lower()
    
    relevant_keywords = [
        'adobe analytics', 'aa', 'analytics', 'workspace', 'reports', 'segments',
        'customer journey analytics', 'cja', 'cross-channel', 'journey',
        'adobe experience platform', 'aep', 'experience platform', 'xdm',
        'adobe experience cloud', 'experience cloud', 'adobe',
        'implementation', 'tracking', 'sdk', 'api',
        'marketing', 'digital marketing', 'web analytics'
    ]
    
    return any(keyword in query_lower for keyword in relevant_keywords)


def select_best_documents(documents: List[Dict], max_docs: int = 3) -> List[Dict]:
    """Select the best documents, prioritizing main documentation."""
    if not documents:
        return []
    
    # Simple selection: take top max_docs by score
    sorted_docs = sorted(
        documents,
        key=lambda x: x.get('score', 0),
        reverse=True
    )
    
    return sorted_docs[:max_docs]


def process_document_content(doc: Dict) -> str:
    """Process document content."""
    content = doc.get('content', {}).get('text', '')
    if not content:
        # Try alternative content paths
        content = doc.get('text', '')
    return content


def extract_source_url(doc: Dict) -> Optional[str]:
    """
    Extract Experience League URL from document metadata.
    
    Since GitHub repo file paths don't reliably map to published Experience League URLs,
    we use search links based on article titles/content, which are more reliable.
    """
    try:
        # Get document content to extract title
        content = doc.get('content', {}).get('text', '')
        if not content:
            return None
        
        # Extract title from document content
        title = None
        lines = content.split('\n')
        
        # Look for main heading (H1 or H2)
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if line.startswith('# '):
                title = line[2:].strip()
                # Clean up common markdown artifacts
                title = title.replace('**', '').replace('*', '').strip()
                break
            elif line.startswith('## ') and not title:
                title = line[3:].strip()
                title = title.replace('**', '').replace('*', '').strip()
        
        # If no title found, try to extract from first meaningful line
        if not title:
            for line in lines[:30]:
                line = line.strip()
                # Skip empty lines, metadata, and common markdown patterns
                if (line and 
                    len(line) > 10 and 
                    not line.startswith('<!--') and
                    not line.startswith('---') and
                    not line.startswith('[') and
                    '|' not in line[:20]):  # Skip tables
                    title = line[:100]  # Limit length
                    break
        
        # If still no title, use a generic search
        if not title:
            # Try to determine product from S3 path
            location = doc.get('location', {})
            s3_uri = location.get('s3Location', {}).get('uri', '')
            
            if 'adobe-analytics' in s3_uri:
                return "https://experienceleague.adobe.com/docs/analytics.html"
            elif 'customer-journey-analytics' in s3_uri:
                return "https://experienceleague.adobe.com/docs/customer-journey-analytics.html"
            elif 'experience-platform' in s3_uri:
                return "https://experienceleague.adobe.com/docs/experience-platform.html"
            elif 'analytics-apis' in s3_uri:
                return "https://experienceleague.adobe.com/docs/analytics/2.0.html"
            else:
                return "https://experienceleague.adobe.com/docs.html"
        
        # Create search URL with the article title
        # Experience League search format
        base_url = "https://experienceleague.adobe.com"
        
        # Clean title for search query
        search_query = title.replace(' ', '+').replace('&', '%26').replace('#', '%23')
        # URL encode common special characters
        search_query = search_query.replace(':', '%3A').replace('/', '%2F')
        
        # Use Experience League search
        return f"{base_url}/search.html?q={search_query}"
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug(f"Error extracting source URL: {e}")
        # Fallback to main docs page
        return "https://experienceleague.adobe.com/docs.html"


def extract_video_url(content: str) -> Optional[str]:
    """
    Extract video URL from document content.
    Looks for YouTube, Vimeo, Adobe video links, and other common video platforms.
    """
    import re
    
    if not content:
        return None
    
    # First, try to find full video URLs directly
    full_url_patterns = [
        # Full YouTube URLs
        r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        # Full Vimeo URLs
        r'https?://(?:www\.)?vimeo\.com/(\d+)',
        r'https?://(?:www\.)?vimeo\.com/embed/(\d+)',
        # Adobe video URLs
        r'https?://(?:www\.)?experienceleague\.adobe\.com/[^\s)]*video[^\s)]*',
        r'https?://(?:www\.)?video\.adobe\.com/[^\s)]+',
        # Direct video file URLs
        r'https?://[^\s)]+\.(?:mp4|mov|avi|webm|mkv)(?:\?[^\s)]*)?',
    ]
    
    for pattern in full_url_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            match = matches[0]
            if isinstance(match, tuple):
                match = match[0] if match else None
            
            if match:
                # Reconstruct YouTube URL from video ID
                if 'youtube' in pattern or 'youtu.be' in pattern:
                    if isinstance(match, str) and len(match) == 11:
                        return f"https://www.youtube.com/watch?v={match}"
                # Reconstruct Vimeo URL from video ID
                elif 'vimeo' in pattern:
                    if isinstance(match, str) and match.isdigit():
                        return f"https://vimeo.com/{match}"
                # Return full URL as-is
                elif isinstance(match, str) and match.startswith('http'):
                    return match
    
    # Check for iframe embeds
    iframe_pattern = r'<iframe[^>]+src=["\']([^"\']*(?:youtube|vimeo|video)[^"\']*)["\']'
    iframe_matches = re.findall(iframe_pattern, content, re.IGNORECASE)
    if iframe_matches:
        url = iframe_matches[0]
        # Extract YouTube video ID from embed URL
        youtube_embed_match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]{11})', url, re.IGNORECASE)
        if youtube_embed_match:
            return f"https://www.youtube.com/watch?v={youtube_embed_match.group(1)}"
        # Return Vimeo or other URLs as-is
        if url.startswith('http'):
            return url
    
    # Check for markdown video links: [text](video_url)
    markdown_video_pattern = r'\[([^\]]*video[^\]]*)\]\(([^)]+)\)'
    markdown_matches = re.findall(markdown_video_pattern, content, re.IGNORECASE)
    if markdown_matches:
        for text, url in markdown_matches:
            url_lower = url.lower()
            if any(platform in url_lower for platform in ['youtube', 'vimeo', 'video', '.mp4', '.mov', 'watch?v=']):
                # Normalize YouTube short URLs
                if 'youtu.be' in url_lower:
                    video_id_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url, re.IGNORECASE)
                    if video_id_match:
                        return f"https://www.youtube.com/watch?v={video_id_match.group(1)}"
                return url
    
    return None


def extract_source_links(documents: List[Dict]) -> List[Dict[str, str]]:
    """
    Extract source links from multiple documents.
    Returns list of dicts with 'title', 'url', and optionally 'video_url'.
    """
    links = []
    seen_urls = set()
    
    for doc in documents:
        url = extract_source_url(doc)
        if url and url not in seen_urls:
            # Try to extract a title from document content or location
            content = doc.get('content', {}).get('text', '')
            title = None
            
            # Try to extract title from content (first heading or first line)
            if content:
                lines = content.split('\n')
                for line in lines[:10]:  # Check first 10 lines
                    line = line.strip()
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break
                    elif line.startswith('## '):
                        title = line[3:].strip()
                        break
                
                # Fallback: use first non-empty line
                if not title:
                    for line in lines:
                        if line.strip() and len(line.strip()) > 10:
                            title = line.strip()[:100]  # Limit length
                            break
            
            # Fallback: use S3 path
            if not title:
                location = doc.get('location', {})
                s3_uri = location.get('s3Location', {}).get('uri', '')
                if s3_uri:
                    # Extract filename or last part of path
                    parts = s3_uri.split('/')
                    title = parts[-1] if parts else "Experience League Article"
                    if title.endswith(('.md', '.html', '.txt')):
                        title = title.rsplit('.', 1)[0]
                    title = title.replace('-', ' ').replace('_', ' ').title()
            
            if not title:
                title = "Experience League Article"
            
            # Extract video URL from content
            video_url = extract_video_url(content) if content else None
            
            link_data = {
                'title': title,
                'url': url
            }
            
            # Only add video_url if found
            if video_url:
                link_data['video_url'] = video_url
            
            links.append(link_data)
            seen_urls.add(url)
    
    return links


def invoke_bedrock_model(
    model_id: str,
    query: str,
    bedrock_client,
    context: str = ""
) -> Tuple[str, Optional[str]]:
    """Invoke Bedrock model."""
    try:
        from src.utils.bedrock_client import BedrockClient
        
        prompt = f"{context}\n\nQuery: {query}" if context else query
        
        # Create BedrockClient with the specific model_id
        region = getattr(bedrock_client, 'region', 'us-east-1')
        temp_client = BedrockClient(model_id=model_id, region=region)
        
        answer = temp_client.generate_text(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9
        )
        
        return answer, None
        
    except Exception as e:
        # Fallback to Haiku
        try:
            from src.utils.bedrock_client import BedrockClient
            region = getattr(bedrock_client, 'region', 'us-east-1')
            fallback_client = BedrockClient(
                model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
                region=region
            )
            answer = fallback_client.generate_text(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.7,
                top_p=0.9
            )
            return answer, None
        except Exception as fallback_error:
            return "", f"Model error: {str(e)}. Fallback failed: {str(fallback_error)}"


def invoke_bedrock_model_stream(
    model_id: str,
    query: str,
    bedrock_client,
    context: str = ""
):
    """Invoke Bedrock model with streaming response."""
    try:
        from src.utils.bedrock_client import BedrockClient
        
        prompt = f"{context}\n\nQuery: {query}" if context else query
        
        region = getattr(bedrock_client, 'region', 'us-east-1')
        temp_client = BedrockClient(model_id=model_id, region=region)
        
        for chunk in temp_client.generate_text_stream(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9
        ):
            yield chunk, None
            
    except Exception as e:
        # Fallback to Haiku
        try:
            from src.utils.bedrock_client import BedrockClient
            region = getattr(bedrock_client, 'region', 'us-east-1')
            fallback_client = BedrockClient(
                model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
                region=region
            )
            for chunk in fallback_client.generate_text_stream(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.7,
                top_p=0.9
            ):
                yield chunk, None
        except Exception as fallback_error:
            yield "", f"Model error: {str(e)}. Fallback failed: {str(fallback_error)}"


class SmartRouter:
    """Smart router for selecting appropriate Bedrock models based on query analysis."""
    
    def __init__(self, haiku_only_mode=False):
        self.models = {
            "haiku": "us.anthropic.claude-3-haiku-20240307-v1:0",
            "sonnet": "us.anthropic.claude-3-7-sonnet-20250219-v1:0", 
            "opus": "us.anthropic.claude-3-opus-20240229-v1:0"
        }
        
        self.haiku_only_mode = haiku_only_mode
        
        # Query complexity indicators
        self.simple_keywords = ["what", "define", "explain", "how to", "tutorial", "guide"]
        self.complex_keywords = ["analyze", "compare", "difference", "troubleshoot", "debug", "optimize", "implement"]
        self.creative_keywords = ["best", "recommend", "suggest", "trends", "future", "strategy", "design"]
        
        # Knowledge Base relevance thresholds
        self.high_relevance_threshold = 0.7
        self.medium_relevance_threshold = 0.3
    
    def analyze_query_complexity(self, query: str) -> str:
        """Analyze query complexity based on keywords and structure."""
        query_lower = query.lower()
        word_count = len(query.split())
        
        # Check for creative/open-ended queries
        if any(keyword in query_lower for keyword in self.creative_keywords):
            return "extremely_complex"
        
        # Check for analytical queries
        if any(keyword in query_lower for keyword in self.complex_keywords):
            return "complex"
        
        # Check query length and structure
        if word_count < 5:
            return "simple"
        elif word_count > 15:
            return "complex"
        elif "?" in query and word_count > 8:
            return "complex"
        else:
            return "simple"
    
    def check_kb_relevance(self, query: str, documents: list) -> float:
        """Check Knowledge Base relevance based on retrieved documents."""
        if not documents:
            return 0.0
        
        # Calculate average relevance score
        scores = [doc.get('score', 0) for doc in documents]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return avg_score
    
    def select_model(self, query: str, documents: list = None) -> dict:
        """Select appropriate model based on query analysis."""
        complexity = self.analyze_query_complexity(query)
        relevance = self.check_kb_relevance(query, documents or [])
        
        # HAIKU-ONLY MODE: Force all queries to use Haiku for cost optimization
        if self.haiku_only_mode:
            selected_model = "haiku"
            reasoning = f"HAIKU-ONLY MODE: Using Haiku for all queries (cost optimization test - 92% cost reduction)"
        else:
            # Original model selection logic with fallback for unavailable models
            if relevance < self.medium_relevance_threshold:
                # Low KB relevance - prefer Opus, fallback to Sonnet
                selected_model = "opus"
                reasoning = f"Low KB relevance ({relevance:.2f}) - using Opus for general knowledge"
            elif complexity == "simple":
                # Simple queries - use fast, cost-effective model
                selected_model = "haiku"
                reasoning = f"Simple query - using Haiku for fast response"
            elif complexity == "complex":
                # Complex queries - use balanced model
                selected_model = "sonnet"
                reasoning = f"Complex query - using Sonnet for detailed analysis"
            else:  # extremely_complex
                # Extremely complex queries - prefer Opus, fallback to Sonnet
                selected_model = "opus"
                reasoning = f"Extremely complex query - using Opus for maximum capability"
        
        return {
            "model": selected_model,
            "model_id": self.models[selected_model],
            "complexity": complexity,
            "relevance": relevance,
            "reasoning": reasoning
        }
    
    def select_available_model(self, query: str, documents: list = None, available_models: list = None) -> dict:
        """Select appropriate model with fallback to available models."""
        if available_models is None:
            available_models = ["haiku", "sonnet"]  # Default available models
        
        # HAIKU-ONLY MODE: Override available models to only include Haiku
        if self.haiku_only_mode:
            available_models = ["haiku"]
        
        # Get initial selection
        selection = self.select_model(query, documents)
        
        # Check if selected model is available, fallback if not
        if selection["model"] not in available_models:
            if "sonnet" in available_models:
                selection["model"] = "sonnet"
                selection["model_id"] = self.models["sonnet"]
                selection["reasoning"] += " (fallback to Sonnet - Opus not available)"
            elif "haiku" in available_models:
                selection["model"] = "haiku"
                selection["model_id"] = self.models["haiku"]
                selection["reasoning"] += " (fallback to Haiku - preferred model not available)"
        
        return selection


def retrieve_documents_from_kb(
    query: str,
    knowledge_base_id: str,
    bedrock_agent_client,
    max_results: int = 3
) -> Tuple[List[Dict], Optional[str]]:
    """
    Retrieve relevant documents from Knowledge Base.
    FastAPI-compatible version without Streamlit dependencies.
    """
    try:
        # Optional security validation (if available, but don't fail if not)
        try:
            from src.security.input_validator import security_validator
            from src.security.security_monitor import security_monitor
            
            # Comprehensive security validation
            is_valid, sanitized_query, threats_detected = security_validator.validate_chat_query(query)
            
            # Monitor the validation attempt
            security_monitor.monitor_input_validation(
                user_input=query,
                threats_detected=threats_detected,
                blocked=not is_valid
            )
            
            # Block malicious queries
            if not is_valid:
                error_msg = f"Security validation failed. Detected threats: {', '.join(threats_detected)}"
                logger.warning(f"Blocked malicious query: {error_msg}")
                return [], "Invalid query detected. Please provide a legitimate question about Adobe Analytics, Customer Journey Analytics, or Adobe Experience Platform."
            
            # Use sanitized query for processing
            query = sanitized_query
        except ImportError:
            # Security modules not available - continue without validation
            logger.debug("Security validation modules not available, skipping validation")
        except Exception as e:
            # Security validation failed but don't block the request
            logger.warning(f"Security validation error (non-blocking): {e}")
        
        # Additional validation for AWS Bedrock limits
        MAX_QUERY_LENGTH = 20000
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH - 100] + "... [truncated]"
            logger.info(f"Query truncated to {len(query)} characters for AWS Bedrock compatibility")
        
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )
        return response.get('retrievalResults', []), None
    except Exception as e:
        # Enhanced error handling for specific AWS errors
        error_msg = str(e)
        if "ValidationException" in error_msg and "length less than or equal to 20000" in error_msg:
            return [], f"Query too long for processing. Maximum allowed: {MAX_QUERY_LENGTH} characters. Please provide a more specific question."
        elif "ValidationException" in error_msg:
            return [], f"Invalid query format: {error_msg}"
        else:
            return [], f"Retrieval error: {error_msg}"

