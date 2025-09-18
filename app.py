import streamlit as st
import os
import sys
import time
import logging
import threading
import hashlib
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from collections import OrderedDict
from typing import Dict, Any, Optional, List, Tuple

# Add project root and src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Import query enhancement modules
try:
    from query_enhancer import query_enhancer
    from enhanced_rag_pipeline import enhanced_rag_pipeline
    QUERY_ENHANCEMENT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Query enhancement modules not available: {e}")
    QUERY_ENHANCEMENT_AVAILABLE = False

# Import smart context manager
try:
    from smart_context_manager import smart_context_manager
    SMART_CONTEXT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Smart context manager not available: {e}")
    SMART_CONTEXT_AVAILABLE = False

# Import debug panel
try:
    from src.debug.debug_panel import debug_panel
    DEBUG_PANEL_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Debug panel not available: {e}")
    DEBUG_PANEL_AVAILABLE = False

# Import hybrid model components
try:
    from src.models.model_provider import ModelProvider
    from src.config.hybrid_config import HybridConfigManager
    from src.routing.query_router import QueryRouter
    from src.ui.comparison_ui import ComparisonUI
    from src.feedback.feedback_ui import FeedbackUI
    from src.retraining.retraining_ui import RetrainingUI
    HYBRID_MODELS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Hybrid model components not available: {e}")
    HYBRID_MODELS_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Performance Optimization Classes
class SimpleLRUCache:
    """Simple LRU Cache without external dependencies"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
    
    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired"""
        if key not in self.timestamps:
            return True
        return time.time() > self.timestamps[key]
    
    def _evict_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if current_time > timestamp
        ]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            elif key in self.cache:
                # Remove expired entry
                self.cache.pop(key, None)
                self.timestamps.pop(key, None)
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        with self.lock:
            # Remove if exists
            self.cache.pop(key, None)
            
            # Add new entry
            self.cache[key] = value
            self.timestamps[key] = time.time() + (ttl or self.default_ttl)
            
            # Evict if necessary
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

class SimplePerformanceMonitor:
    """Simple performance monitoring without external dependencies"""
    
    def __init__(self):
        self.operation_times = {}
        self.operation_counts = {}
        self.lock = threading.Lock()
    
    def start_operation(self, operation: str) -> str:
        """Start timing an operation"""
        operation_id = f"{operation}_{int(time.time() * 1000)}"
        with self.lock:
            self.operation_times[operation_id] = time.time()
        return operation_id
    
    def finish_operation(self, operation_id: str) -> float:
        """Finish timing an operation and return duration"""
        with self.lock:
            if operation_id in self.operation_times:
                duration = time.time() - self.operation_times.pop(operation_id)
                operation = operation_id.split('_')[0]
                if operation not in self.operation_counts:
                    self.operation_counts[operation] = []
                self.operation_counts[operation].append(duration)
                return duration
        return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self.lock:
            stats = {}
            for operation, times in self.operation_counts.items():
                if times:
                    stats[operation] = {
                        'count': len(times),
                        'avg_duration': sum(times) / len(times),
                        'min_duration': min(times),
                        'max_duration': max(times)
                    }
            return stats

# Global performance instances
query_cache = SimpleLRUCache(max_size=500, default_ttl=600)
performance_monitor = SimplePerformanceMonitor()

# Cached helper functions for performance optimization
def get_cached_settings():
    """Get settings with caching"""
    cache_key = "settings"
    cached = query_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        settings = Settings()
        if settings:
            query_cache.set(cache_key, settings, ttl=1800)  # 30 minutes
        return settings
    except Exception as e:
        logger.error(f"❌ Failed to get settings: {e}")
        return None

def get_cached_aws_clients(settings):
    """Get AWS clients with caching"""
    if not settings:
        return None
        
    cache_key = "aws_clients"
    cached = query_cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # Initialize all AWS clients
        s3_client = get_s3_client(settings.aws_default_region)
        sts_client = get_sts_client(settings.aws_default_region)
        bedrock_client = BedrockClient(
            model_id=settings.bedrock_model_id,
            region=settings.bedrock_region
        )
        bedrock_agent_client = get_bedrock_agent_client(settings.bedrock_region)
        cost_explorer_client = get_cost_explorer_client(settings.aws_default_region)
        
        # Get AWS account information
        try:
            identity = sts_client.get_caller_identity()
            account_id = identity.get('Account', 'Unknown')
            user_arn = identity.get('Arn', 'Unknown')
        except Exception as e:
            logger.warning(f"⚠️ Could not get AWS identity: {e}")
            account_id = 'Unknown'
            user_arn = 'Unknown'
        
        # Test S3 bucket access
        s3_status = "Unknown"
        try:
            s3_client.head_bucket(Bucket=settings.aws_s3_bucket)
            s3_status = "✅ Accessible"
        except Exception as e:
            s3_status = f"❌ Error: {str(e)[:50]}..."
        
        clients = {
            "s3": s3_client,
            "sts": sts_client,
            "bedrock": bedrock_client,
            "bedrock_agent_client": bedrock_agent_client,
            "cost_explorer": cost_explorer_client,
            "account_id": account_id,
            "user_arn": user_arn,
            "s3_status": s3_status
        }
        query_cache.set(cache_key, clients, ttl=1800)  # 30 minutes
        return clients
    except Exception as e:
        logger.error(f"❌ Failed to initialize AWS clients: {e}")
        return None

# Import configuration
from config.settings import Settings

# Import AWS utilities
from src.utils.aws_utils import (
    get_s3_client, get_sts_client, get_bedrock_agent_client, get_cost_explorer_client,
    get_cost_and_usage, get_cost_by_service, get_bedrock_costs, get_s3_costs
)
from src.utils.bedrock_client import BedrockClient

# Import analytics components with error handling
try:
    from src.integrations.streamlit_analytics_simple import (
        initialize_analytics_service, StreamlitAnalyticsIntegration
    )
    ANALYTICS_AVAILABLE = True
    print("✅ Analytics integration loaded successfully")
except ImportError as e:
    print(f"⚠️  Analytics components not available: {e}")
    ANALYTICS_AVAILABLE = False
    # Create dummy classes for compatibility
    def initialize_analytics_service(): return None
    class StreamlitAnalyticsIntegration: 
        def __init__(self, *args, **kwargs): pass
        def track_query(self, *args, **kwargs): return None
        def track_response(self, *args, **kwargs): return None
        def track_feedback(self, *args, **kwargs): return None
        def render_analytics_dashboard(self): 
            st.error("Analytics not available - database configuration error")

# Import admin panel components
try:
    from src.admin.admin_panel import render_admin_page, display_aws_cost_data, display_bedrock_cost_data, display_s3_cost_data
    ADMIN_PANEL_AVAILABLE = True
    print("✅ Admin panel loaded successfully")
except ImportError as e:
    print(f"⚠️  Admin panel not available: {e}")
    ADMIN_PANEL_AVAILABLE = False
    def render_admin_page(*args, **kwargs):
        st.error("Admin panel not available - import error")

# Tagging functionality removed for now - keeping simple query_analytics table

# Import database query components
try:
    from src.integrations.database_query import render_database_query_interface
    DATABASE_QUERY_AVAILABLE = True
    print("✅ Database query integration loaded successfully")
except ImportError as e:
    print(f"⚠️  Database query components not available: {e}")
    DATABASE_QUERY_AVAILABLE = False
    def render_database_query_interface():
        st.error("Database query interface not available - import error")

# Basic app configuration
st.set_page_config(
    page_title="Adobe Experience League Chatbot (Unofficial)",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_configuration():
    """Load and validate configuration settings."""
    try:
        settings = Settings()
        
        # Check for required environment variables
        missing_vars = []
        if not settings.aws_access_key_id:
            missing_vars.append("AWS_ACCESS_KEY_ID")
        if not settings.aws_secret_access_key:
            missing_vars.append("AWS_SECRET_ACCESS_KEY")
        if not settings.aws_s3_bucket:
            missing_vars.append("AWS_S3_BUCKET")
        if not settings.bedrock_knowledge_base_id:
            missing_vars.append("BEDROCK_KNOWLEDGE_BASE_ID")
        if not settings.adobe_client_id:
            missing_vars.append("ADOBE_CLIENT_ID")
        if not settings.adobe_client_secret:
            missing_vars.append("ADOBE_CLIENT_SECRET")
        if not settings.adobe_organization_id:
            missing_vars.append("ADOBE_ORGANIZATION_ID")
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            return None, error_msg
            
        return settings, None
    except Exception as e:
        return None, str(e)

def initialize_aws_clients(settings):
    """Initialize AWS clients and test connectivity."""
    try:
        # Initialize S3 client
        s3_client = get_s3_client(settings.aws_default_region)
        
        # Initialize STS client for identity verification
        sts_client = get_sts_client(settings.aws_default_region)
        
        # Initialize Bedrock client
        bedrock_client = BedrockClient(
            model_id=settings.bedrock_model_id,
            region=settings.bedrock_region
        )
        
        # Initialize Bedrock Agent Runtime client for Knowledge Base
        bedrock_agent_client = get_bedrock_agent_client(settings.bedrock_region)
        
        # Initialize Cost Explorer client
        cost_explorer_client = get_cost_explorer_client(settings.aws_default_region)
        
        # Test AWS connectivity
        identity = sts_client.get_caller_identity()
        account_id = identity.get('Account', 'Unknown')
        user_arn = identity.get('Arn', 'Unknown')
        
        # Test S3 bucket access
        try:
            s3_client.head_bucket(Bucket=settings.aws_s3_bucket)
            s3_status = "✅ Accessible"
        except Exception as e:
            s3_status = f"❌ Error: {str(e)[:50]}..."
        
        return {
            's3_client': s3_client,
            'sts_client': sts_client,
            'bedrock_client': bedrock_client,
            'bedrock_agent_client': bedrock_agent_client,
            'cost_explorer_client': cost_explorer_client,
            'account_id': account_id,
            'user_arn': user_arn,
            's3_status': s3_status
        }, None
        
    except Exception as e:
        return None, str(e)

def clean_adobe_dnl_text(text: str) -> str:
    """Clean Adobe DNL (Display Name Language) markup from text."""
    import re
    
    # Remove [!DNL ...] markup and replace with just the text
    text = re.sub(r'\[!DNL\s+([^\]]+)\]', r'\1', text)
    
    # Remove other common Adobe markup patterns
    text = re.sub(r'\[!UICONTROL\s+([^\]]+)\]', r'\1', text)
    text = re.sub(r'\[!BADGE\s+([^\]]+)\]', r'\1', text)
    text = re.sub(r'\[!NOTE\]', 'Note:', text)
    text = re.sub(r'\[!WARNING\]', 'Warning:', text)
    text = re.sub(r'\[!TIP\]', 'Tip:', text)
    
    return text

def extract_source_urls(documents: List[Dict]) -> List[str]:
    """Extract source URLs from documents for debug panel."""
    source_urls = []
    for doc in documents:
        location = doc.get('location', {})
        s3_uri = location.get('s3Location', {}).get('uri', '')
        if s3_uri:
            source_urls.append(s3_uri)
    return source_urls

def retrieve_documents_from_kb(query: str, knowledge_base_id: str, bedrock_agent_client, max_results: int = 3):
    """Retrieve relevant documents from Knowledge Base with comprehensive security validation."""
    try:
        # Import security validator
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
        
        # Additional legacy validation for AWS Bedrock limits
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

def generate_answer_from_kb(query: str, knowledge_base_id: str, model_id: str, bedrock_agent_client):
    """Generate answer using Knowledge Base."""
    try:
        response = bedrock_agent_client.retrieve_and_generate(
            input={
                'text': query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': knowledge_base_id,
                    'modelArn': model_id
                }
            }
        )
        return response.get('output', {}).get('text', ''), None
    except Exception as e:
        return '', str(e)

def test_knowledge_base_connection(knowledge_base_id: str, bedrock_agent_client):
    """Test Knowledge Base connection with a simple query."""
    try:
        # Test with a simple query
        test_query = "What is Adobe Analytics?"
        documents, error = retrieve_documents_from_kb(test_query, knowledge_base_id, bedrock_agent_client, max_results=1)
        
        if error:
            return False, f"Retrieval error: {error}"
        
        if not documents:
            return False, "No documents retrieved"
        
        return True, f"Successfully retrieved {len(documents)} document(s)"
        
    except Exception as e:
        return False, str(e)

class SmartRouter:
    """Smart router for selecting appropriate Bedrock models based on query analysis."""
    
    def __init__(self, haiku_only_mode=False):
        self.models = {
            "haiku": "us.anthropic.claude-3-haiku-20240307-v1:0",
            "sonnet": "us.anthropic.claude-3-7-sonnet-20250219-v1:0", 
            "opus": "us.anthropic.claude-3-opus-20240229-v1:0"
        }
        
        # HAIKU-ONLY MODE: Set to True for one week testing (cost optimization)
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
    
    def get_model_info(self, model_name: str) -> dict:
        """Get information about a specific model."""
        model_info = {
            "haiku": {
                "name": "Claude 3 Haiku",
                "description": "Fast, cost-effective for simple queries",
                "cost_per_1m_tokens": "$1.50",
                "use_cases": ["Definitions", "Simple how-to", "Quick answers"]
            },
            "sonnet": {
                "name": "Claude 3.7 Sonnet", 
                "description": "Balanced performance for complex queries",
                "cost_per_1m_tokens": "$18.00",
                "use_cases": ["Analysis", "Comparisons", "Detailed explanations"]
            },
            "opus": {
                "name": "Claude 3 Opus",
                "description": "Most capable for creative and complex tasks",
                "cost_per_1m_tokens": "$75.00", 
                "use_cases": ["Creative tasks", "Open-ended questions", "General knowledge"]
            }
        }
        return model_info.get(model_name, {})

def invoke_bedrock_model(model_id: str, query: str, bedrock_client, context: str = "") -> tuple:
    """Invoke Bedrock model with proper request format based on model type."""
    try:
        # Use the BedrockClient's generate_text method instead of direct invoke_model
        prompt = f"{context}\n\nQuery: {query}" if context else query
        
        # Create a temporary BedrockClient with the specific model_id
        from src.utils.bedrock_client import BedrockClient
        temp_client = BedrockClient(model_id=model_id, region=bedrock_client.region)
        
        # Generate text using the appropriate method
        answer = temp_client.generate_text(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9
        )
        
        return answer, None
            
    except Exception as e:
        # If the selected model fails, try fallback to Haiku
        if "AccessDeniedException" in str(e) or "don't have access" in str(e).lower():
            try:
                print(f"⚠️ Model {model_id} not accessible, falling back to Haiku...")
                fallback_client = BedrockClient(model_id="us.anthropic.claude-3-haiku-20240307-v1:0", region=bedrock_client.region)
                answer = fallback_client.generate_text(
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=0.7,
                    top_p=0.9
                )
                return answer, None
            except Exception as fallback_error:
                return "", f"Primary model failed: {str(e)}. Fallback also failed: {str(fallback_error)}"
        else:
            return "", str(e)

def invoke_bedrock_model_stream(model_id: str, query: str, bedrock_client, context: str = ""):
    """Invoke Bedrock model with streaming response."""
    try:
        # Use the BedrockClient's generate_text_stream method
        prompt = f"{context}\n\nQuery: {query}" if context else query
        
        # Create a temporary BedrockClient with the specific model_id
        from src.utils.bedrock_client import BedrockClient
        temp_client = BedrockClient(model_id=model_id, region=bedrock_client.region)
        
        # Generate text using streaming
        for chunk in temp_client.generate_text_stream(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9
        ):
            yield chunk, None
            
    except Exception as e:
        # If the selected model fails, try fallback to Haiku
        if "AccessDeniedException" in str(e) or "don't have access" in str(e).lower():
            try:
                print(f"⚠️ Model {model_id} not accessible, falling back to Haiku...")
                fallback_client = BedrockClient(model_id="us.anthropic.claude-3-haiku-20240307-v1:0", region=bedrock_client.region)
                for chunk in fallback_client.generate_text_stream(
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=0.7,
                    top_p=0.9
                ):
                    yield chunk, None
            except Exception as fallback_error:
                yield "", f"Primary model failed: {str(e)}. Fallback also failed: {str(fallback_error)}"
        else:
            yield "", str(e)

def process_query_optimized(query: str, knowledge_base_id: str, smart_router, aws_clients, user_id: str = "anonymous") -> dict:
    """Optimized query processing with caching and performance monitoring"""
    operation_id = performance_monitor.start_operation("query_processing")
    
    try:
        # Check cache first
        cache_key = f"query_{hashlib.md5(query.encode()).hexdigest()}"
        cached_result = query_cache.get(cache_key)
        if cached_result:
            duration = performance_monitor.finish_operation(operation_id)
            logger.info(f"✅ Query served from cache in {duration:.3f}s")
            return cached_result
        
        # Process query with smart routing
        result = process_query_with_smart_routing(query, knowledge_base_id, smart_router, aws_clients)
        
        # Cache the result
        query_cache.set(cache_key, result, ttl=600)  # 10 minutes
        
        duration = performance_monitor.finish_operation(operation_id)
        logger.info(f"✅ Query processed in {duration:.3f}s")
        
        return result
        
    except Exception as e:
        performance_monitor.finish_operation(operation_id)
        logger.error(f"❌ Query processing failed: {e}")
        return {"success": False, "error": str(e)}

def process_query_with_smart_routing(query: str, knowledge_base_id: str, smart_router, aws_clients) -> dict:
    """Process query using smart routing and return comprehensive results."""
    try:
        # Input validation before processing
        if not query or not query.strip():
            return {
                "success": False,
                "error": "Please enter a valid question about Adobe Analytics.",
                "documents": [],
                "routing_decision": None,
                "answer": "",
                "model_used": None
            }
        
        # Check for extremely long queries early
        MAX_QUERY_LENGTH = 20000
        if len(query) > MAX_QUERY_LENGTH * 2:  # More than 40,000 characters
            return {
                "success": False,
                "error": f"Query too long ({len(query)} characters). Maximum allowed: {MAX_QUERY_LENGTH} characters. Please provide a more specific question about Adobe Analytics.",
                "documents": [],
                "routing_decision": None,
                "answer": "",
                "model_used": None
            }
        
        # Step 1: Enhanced document retrieval with query enhancement
        if QUERY_ENHANCEMENT_AVAILABLE and st.session_state.get('query_enhancement_enabled', True):
            try:
                # Use enhanced RAG pipeline
                enhanced_results = asyncio.run(enhanced_rag_pipeline.enhanced_retrieve_documents(
                    query, 
                    top_k=10,
                    use_enhancement=True
                ))
                
                # Convert enhanced results to legacy format
                documents = []
                for result in enhanced_results:
                    documents.append({
                        'content': {'text': result.content},
                        'score': result.score,
                        'location': {'s3Location': {'uri': result.source}}
                    })
                
                # Store enhancement metadata in session state for UI display
                st.session_state['last_query_enhancement'] = {
                    'original_query': query,
                    'enhanced_queries': [r.enhanced_query for r in enhanced_results],
                    'detected_products': enhanced_results[0].product_context if enhanced_results else [],
                    'processing_time_ms': sum(r.processing_time_ms for r in enhanced_results) / len(enhanced_results) if enhanced_results else 0
                }
                
            except Exception as e:
                logger.warning(f"Enhanced retrieval failed, falling back to standard: {e}")
                # Fallback to standard retrieval
                documents, retrieval_error = retrieve_documents_from_kb(
                    query, 
                    knowledge_base_id, 
                    aws_clients['bedrock_agent_client']
                )
                
                if retrieval_error:
                    return {
                        "success": False,
                        "error": f"Retrieval error: {retrieval_error}",
                        "documents": [],
                        "routing_decision": None,
                        "answer": "",
                        "model_used": None
                    }
        else:
            # Standard retrieval without enhancement
            documents, retrieval_error = retrieve_documents_from_kb(
                query, 
                knowledge_base_id, 
                aws_clients['bedrock_agent_client']
            )
            
            if retrieval_error:
                return {
                    "success": False,
                    "error": f"Retrieval error: {retrieval_error}",
                    "documents": [],
                    "routing_decision": None,
                    "answer": "",
                    "model_used": None
                }
        
        # Step 2: Smart routing - select appropriate model with fallback
        # Use available models (Haiku and Sonnet are confirmed working)
        # Check current mode from session state for dynamic switching
        current_haiku_only_mode = st.session_state.get('haiku_only_mode', smart_router.haiku_only_mode)
        available_models = ["haiku"] if current_haiku_only_mode else ["haiku", "sonnet", "opus"]
        routing_decision = smart_router.select_available_model(query, documents, available_models)
        
        # Add debug entry for model selection
        if DEBUG_PANEL_AVAILABLE:
            debug_panel.add_debug_entry(
                query=query,
                status="processing",
                model=routing_decision['model'],
                step_info=f"Model selected: {routing_decision['model']} - {routing_decision.get('reasoning', 'No reasoning provided')}"
            )
        
        # Step 3: Prepare context from retrieved documents with smart context management
        context = ""
        context_metadata = {}
        if documents:
            if SMART_CONTEXT_AVAILABLE:
                # Use smart context manager for adaptive context length
                context, context_metadata = smart_context_manager.prepare_smart_context(documents, query)
                # Store context metadata in session state for UI display
                st.session_state['last_context_metadata'] = context_metadata
            else:
                # Fallback to standard context preparation
                selected_docs = select_best_documents(documents, max_docs=3)
                context_parts = []
                for i, doc in enumerate(selected_docs, 1):
                    processed_content = process_document_content(doc)
                    if processed_content:
                        score = doc.get('score', 0)
                        max_length = 3000 if score > 0.6 else 2000
                        content_to_use = processed_content[:max_length]
                        if len(processed_content) > max_length:
                            content_to_use += "..."
                        context_parts.append(f"Document {i} (Score: {score:.3f}): {content_to_use}")
                context = "\n\n".join(context_parts)
        
        # Step 4: Invoke selected model
        answer, generation_error = invoke_bedrock_model(
            routing_decision['model_id'],
            query,
            aws_clients['bedrock'],
            context
        )
        
        if generation_error:
            return {
                "success": False,
                "error": f"Generation error: {generation_error}",
                "documents": documents,
                "routing_decision": routing_decision,
                "answer": "",
                "model_used": routing_decision['model']
            }
        
        return {
            "success": True,
            "error": None,
            "documents": documents,
            "routing_decision": routing_decision,
            "answer": answer,
            "model_used": routing_decision['model']
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Processing error: {str(e)}",
            "documents": [],
            "routing_decision": None,
            "answer": "",
            "model_used": None
        }

def process_query_with_smart_routing_stream(query: str, knowledge_base_id: str, smart_router, aws_clients):
    """Process query using smart routing with streaming response."""
    try:
        # Input validation before processing
        if not query or not query.strip():
            yield {
                "success": False,
                "error": "Please enter a valid question about Adobe Analytics.",
                "documents": [],
                "routing_decision": None,
                "answer": "",
                "model_used": None
            }
            return
        
        # Check for extremely long queries early
        MAX_QUERY_LENGTH = 20000
        if len(query) > MAX_QUERY_LENGTH * 2:  # More than 40,000 characters
            yield {
                "success": False,
                "error": f"Query too long ({len(query)} characters). Maximum allowed: {MAX_QUERY_LENGTH} characters. Please provide a more specific question about Adobe Analytics.",
                "documents": [],
                "routing_decision": None,
                "answer": "",
                "model_used": None
            }
            return
        
        # Update processing step: Analyzing question
        st.session_state.processing_step = 0
        st.session_state.current_step_start = time.time()
        
        # Add debug entry for query start
        if DEBUG_PANEL_AVAILABLE:
            debug_panel.add_debug_entry(
                query=query,
                status="processing",
                step_info="Starting query analysis",
                source_urls=[]
            )
        
        # Step 1: Enhanced document retrieval with query enhancement
        if QUERY_ENHANCEMENT_AVAILABLE and st.session_state.get('query_enhancement_enabled', True):
            try:
                # Use enhanced RAG pipeline
                enhanced_results = asyncio.run(enhanced_rag_pipeline.enhanced_retrieve_documents(
                    query, 
                    top_k=10,
                    use_enhancement=True
                ))
                
                # Convert enhanced results to legacy format
                documents = []
                for result in enhanced_results:
                    documents.append({
                        'content': {'text': result.content},
                        'score': result.score,
                        'location': {'s3Location': {'uri': result.source}}
                    })
                
                # Store enhancement metadata in session state for UI display
                st.session_state['last_query_enhancement'] = {
                    'original_query': query,
                    'enhanced_queries': [r.enhanced_query for r in enhanced_results],
                    'detected_products': enhanced_results[0].product_context if enhanced_results else [],
                    'processing_time_ms': sum(r.processing_time_ms for r in enhanced_results) / len(enhanced_results) if enhanced_results else 0
                }
                
                print(f"🔍 [ENHANCEMENT] Query enhanced: {len(enhanced_results)} results, {len(st.session_state.get('last_query_enhancement', {}).get('enhanced_queries', []))} enhanced queries")
                
            except Exception as e:
                print(f"⚠️ [ENHANCEMENT] Enhanced retrieval failed, falling back to standard: {e}")
                # Fallback to standard retrieval
                documents, retrieval_error = retrieve_documents_from_kb(
                    query, 
                    knowledge_base_id, 
                    aws_clients['bedrock_agent_client']
                )
                
                if retrieval_error:
                    yield {
                        "success": False,
                        "error": f"Retrieval error: {retrieval_error}",
                        "documents": [],
                        "routing_decision": None,
                        "answer": "",
                        "model_used": None
                    }
                    return
        else:
            # Standard retrieval without enhancement
            documents, retrieval_error = retrieve_documents_from_kb(
                query, 
                knowledge_base_id, 
                aws_clients['bedrock_agent_client']
            )
            
            if retrieval_error:
                yield {
                    "success": False,
                    "error": f"Retrieval error: {retrieval_error}",
                    "documents": [],
                    "routing_decision": None,
                    "answer": "",
                    "model_used": None
                }
                return
        
        # Update processing step: Searching knowledge base
        st.session_state.processing_step = 1
        
        # Step 2: Smart routing - select appropriate model with fallback
        current_haiku_only_mode = st.session_state.get('haiku_only_mode', smart_router.haiku_only_mode)
        available_models = ["haiku"] if current_haiku_only_mode else ["haiku", "sonnet", "opus"]
        routing_decision = smart_router.select_available_model(query, documents, available_models)
        
        # Add debug entry for model selection
        if DEBUG_PANEL_AVAILABLE:
            debug_panel.add_debug_entry(
                query=query,
                status="processing",
                model=routing_decision['model'],
                step_info=f"Model selected: {routing_decision['model']} - {routing_decision.get('reasoning', 'No reasoning provided')}"
            )
        
        # Update processing step: Querying AI model
        st.session_state.processing_step = 2
        
        # Step 3: Prepare context from retrieved documents with smart context management
        context = ""
        context_metadata = {}
        if documents:
            if SMART_CONTEXT_AVAILABLE:
                # Use smart context manager for adaptive context length
                context, context_metadata = smart_context_manager.prepare_smart_context(documents, query)
                # Store context metadata in session state for UI display
                st.session_state['last_context_metadata'] = context_metadata
            else:
                # Fallback to standard context preparation
                selected_docs = select_best_documents(documents, max_docs=3)
                context_parts = []
                for i, doc in enumerate(selected_docs, 1):
                    processed_content = process_document_content(doc)
                    if processed_content:
                        score = doc.get('score', 0)
                        max_length = 3000 if score > 0.6 else 2000
                        content_to_use = processed_content[:max_length]
                        if len(processed_content) > max_length:
                            content_to_use += "..."
                        context_parts.append(f"Document {i} (Score: {score:.3f}): {content_to_use}")
                context = "\n\n".join(context_parts)
        
        # Update processing step: Synthesizing response
        st.session_state.processing_step = 3
        
        # Step 4: Invoke selected model with streaming
        full_answer = ""
        # Update processing step: Generating final answer
        st.session_state.processing_step = 4
        
        for chunk, generation_error in invoke_bedrock_model_stream(
            routing_decision['model_id'],
            query,
            aws_clients['bedrock'],
            context
        ):
            if generation_error:
                yield {
                    "success": False,
                    "error": f"Generation error: {generation_error}",
                    "documents": documents,
                    "routing_decision": routing_decision,
                    "answer": "",
                    "model_used": routing_decision['model']
                }
                return
            
            if chunk:
                full_answer += chunk
                # Yield streaming update with current full answer for display
                yield {
                    "success": True,
                    "error": None,
                    "documents": documents,
                    "routing_decision": routing_decision,
                    "answer": full_answer,  # Stream the accumulated answer so far
                    "model_used": routing_decision['model'],
                    "is_streaming": True
                }
        
        # Final result with complete answer (no duplication)
        yield {
            "success": True,
            "error": None,
            "documents": documents,
            "routing_decision": routing_decision,
            "answer": "",  # Empty since we already yielded the full answer
            "model_used": routing_decision['model'],
            "is_streaming": False
        }
        
    except Exception as e:
        yield {
            "success": False,
            "error": f"Processing error: {str(e)}",
            "documents": [],
            "routing_decision": None,
            "answer": "",
            "model_used": None
        }

def test_model_invocation(model_id: str, test_query: str, bedrock_client) -> tuple:
    """Test model invocation with a simple query."""
    try:
        answer, error = invoke_bedrock_model(model_id, test_query, bedrock_client, "")
        
        if error:
            return False, f"Model invocation error: {error}"
        
        if not answer or len(answer.strip()) < 10:
            return False, "Model returned empty or very short response"
        
        return True, f"Model responded successfully (length: {len(answer)} chars)"
        
    except Exception as e:
        return False, str(e)

def check_query_relevance(query: str) -> bool:
    """Check if the query is relevant to Adobe Analytics, CJA, AEP, or related topics."""
    # Convert query to lowercase for case-insensitive matching
    query_lower = query.lower()
    
    # Define relevant keywords and topics
    relevant_keywords = [
        # Adobe Analytics
        'adobe analytics', 'aa', 'analytics', 'workspace', 'reports', 'segments', 'calculated metrics',
        'virtual report suites', 'vrs', 'data warehouse', 'data feeds', 'attribution', 'conversion',
        'funnel', 'cohort', 'flow', 'fallout', 'pathing', 'real-time', 'realtime',
        'metrics', 'dimensions', 'breakdown', 'trend', 'overview', 'summary',
        
        # Customer Journey Analytics
        'customer journey analytics', 'cja', 'cross-channel', 'cross channel', 'journey',
        'customer journey', 'stitching', 'identity', 'person', 'person id',
        
        # Adobe Experience Platform
        'adobe experience platform', 'aep', 'experience platform', 'xdm', 'experience data model',
        'schemas', 'schema', 'datasets', 'dataset', 'data ingestion', 'data prep', 'query service', 'real-time customer profile',
        'rtcp', 'profile', 'identity graph', 'data lake', 'data science workspace', 'jupyter',
        'destinations', 'sources', 'connectors', 'workflows', 'data flows', 'segmentation',
        'audience', 'audiences', 'activation', 'data governance', 'privacy', 'consent',
        'sandbox', 'sandboxes', 'dev', 'stage', 'prod', 'production',
        
        # Adobe Experience Cloud
        'adobe experience cloud', 'experience cloud', 'adobe', 'marketing cloud',
        'campaign', 'target', 'audience manager', 'adobe io', 'adobe io',
        
        # Technical terms
        'implementation', 'tracking', 'sdk', 'api', 'javascript', 'mobile sdk',
        'server-side', 'client-side', 'data collection', 'beacon', 'hit',
        'visitor', 'visit', 'page view', 'event', 'custom events', 'props', 'evar',
        's.t', 's.tl', 's.clearVars', 's.link', 's.track', 's.visitorID',
        'code', 'script', 'tag', 'tagging', 'measurement', 'measure',
        
        # Business terms
        'marketing', 'digital marketing', 'web analytics', 'conversion tracking',
        'ecommerce', 'e-commerce', 'revenue', 'orders', 'products', 'cart',
        'checkout', 'purchase', 'transaction', 'bounce rate', 'time on site',
        'business', 'website', 'app', 'mobile', 'digital', 'online',
        
        # Adobe-specific tools
        'analysis workspace', 'report builder', 'ad hoc analysis', 'adobe connect',
        'adobe launch', 'dynamic tag manager', 'dtm', 'adobe tag manager',
        'adobe audience manager', 'adobe target', 'adobe campaign'
    ]
    
    # Check if query contains any relevant keywords
    for keyword in relevant_keywords:
        if keyword in query_lower:
            return True
    
    # Additional check for question patterns that might be relevant
    question_patterns = [
        'how to', 'how do i', 'what is', 'what are', 'how can', 'how does',
        'why', 'when', 'where', 'which', 'who', 'explain', 'tutorial',
        'guide', 'setup', 'configure', 'implement', 'track', 'measure',
        'analyze', 'report', 'dashboard', 'visualization'
    ]
    
    # If query contains question patterns, it might be relevant even without keywords
    for pattern in question_patterns:
        if pattern in query_lower:
            # Check if it's asking about analytics, data, or business topics
            business_terms = ['data', 'analytics', 'marketing', 'business', 'website', 'app', 'mobile', 'digital', 'online', 'web', 'ecommerce', 'e-commerce', 'revenue', 'conversion', 'tracking', 'measurement', 'report', 'dashboard', 'visualization']
            if any(term in query_lower for term in business_terms):
                return True
    
    return False

def get_irrelevant_question_response() -> str:
    """Return a standard response for irrelevant questions."""
    return """I'm sorry, but your question doesn't appear to be related to Adobe Analytics, Customer Journey Analytics, Adobe Experience Platform, or other Adobe Experience Cloud products.

I'm specifically designed to help with questions about:
• **Adobe Analytics** - Reports, segments, calculated metrics, implementation
• **Customer Journey Analytics (CJA)** - Cross-channel analysis, customer journeys
• **Adobe Experience Platform (AEP)** - Schemas, datasets, data ingestion, XDM
• **Adobe Experience Cloud** - Marketing automation, personalization, content management

Please ask questions about these topics, and I'll be happy to help! For example:
- "How do I create a segment in Adobe Analytics?"
- "What is Analysis Workspace?"
- "How do I create schemas in Adobe Experience Platform?"
- "What is Customer Journey Analytics?" """

def select_best_documents(documents, max_docs=3):
    """Select the best documents, prioritizing main documentation and high-relevance docs."""
    if not documents:
        return []
    
    # Separate documents by type and relevance
    main_docs = []
    high_relevance_docs = []
    release_notes = []
    other_docs = []
    
    for doc in documents:
        location = doc.get('location', {})
        s3_uri = location.get('s3Location', {}).get('uri', '')
        score = doc.get('score', 0)
        
        # Prioritize high-relevance documents (score > 0.6)
        if score > 0.6:
            high_relevance_docs.append(doc)
        elif 'release-notes' in s3_uri:
            release_notes.append(doc)
        elif any(keyword in s3_uri for keyword in ['/home.md', '/overview.md', '/getting-started.md']):
            main_docs.append(doc)
        else:
            other_docs.append(doc)
    
    # Sort each category by score (highest first)
    high_relevance_docs.sort(key=lambda x: x.get('score', 0), reverse=True)
    main_docs.sort(key=lambda x: x.get('score', 0), reverse=True)
    other_docs.sort(key=lambda x: x.get('score', 0), reverse=True)
    release_notes.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # Prioritize: high-relevance docs, then main docs, then other docs, then release notes
    selected = []
    
    # Add high-relevance documents first
    selected.extend(high_relevance_docs[:max_docs])
    
    # If we need more docs, add main documentation
    if len(selected) < max_docs:
        remaining = max_docs - len(selected)
        selected.extend(main_docs[:remaining])
    
    # If we still need more docs, add other documentation
    if len(selected) < max_docs:
        remaining = max_docs - len(selected)
        selected.extend(other_docs[:remaining])
    
    # If we still need more docs, add release notes
    if len(selected) < max_docs:
        remaining = max_docs - len(selected)
        selected.extend(release_notes[:remaining])
    
    return selected

def fix_markdown_links(content: str, base_url: str = "https://experienceleague.adobe.com") -> str:
    """Fix relative markdown links to point to correct Adobe Experience League URLs."""
    import re
    
    if not content:
        return content
    
    # Pattern to match markdown links: [text](relative/path)
    link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    
    def replace_link(match):
        link_text = match.group(1)
        link_path = match.group(2)
        
        # Skip if it's already an absolute URL
        if link_path.startswith(('http://', 'https://', 'mailto:')):
            return match.group(0)
        
        # Skip if it's an anchor link
        if link_path.startswith('#'):
            return match.group(0)
        
        # Handle different types of relative paths
        if link_path.startswith('./'):
            # Remove ./ prefix - this is a sibling directory
            clean_path = link_path[2:]
        elif link_path.startswith('../'):
            # Handle parent directory references - these are often broken in release notes
            # Map common broken paths to correct Experience League URLs
            if 'tags/home' in link_path:
                clean_path = 'tags/home'
            elif 'data-governance/home' in link_path:
                clean_path = 'data-governance/home'
            elif 'data-prep/home' in link_path:
                clean_path = 'data-prep/home'
            else:
                # For other parent references, try to clean them up
                clean_path = link_path.replace('../', '').replace('../../', '')
        else:
            # Use path as-is
            clean_path = link_path
        
        # Remove .md extension and convert to proper URL format
        if clean_path.endswith('.md'):
            clean_path = clean_path[:-3]
        
        # Construct the full URL
        full_url = f"{base_url}/docs/{clean_path}"
        
        return f"[{link_text}]({full_url})"
    
    # Replace all relative links
    fixed_content = re.sub(link_pattern, replace_link, content)
    
    return fixed_content

def process_document_content(doc: dict) -> str:
    """Process document content and fix links."""
    content = doc.get('content', {}).get('text', '')
    if not content:
        return content
    
    # Fix markdown links in the content
    fixed_content = fix_markdown_links(content)
    
    return fixed_content

def render_processing_loader(step: int = 0):
    """Render a thin processing loader with steps."""
    steps = [
        "🔍 Analyzing your question...",
        "📚 Searching knowledge base...",
        "🤖 Querying AI model...",
        "⚡ Synthesizing response...",
        "✨ Generating final answer..."
    ]
    
    # Create a thin progress bar
    progress = (step + 1) / len(steps)
    
    # Add CSS for the loader
    st.markdown("""
    <style>
    .processing-loader {
        background: linear-gradient(90deg, #e0e0e0 0%, #1f77b4 50%, #e0e0e0 100%);
        height: 3px;
        border-radius: 2px;
        margin: 10px 0;
        position: relative;
        overflow: hidden;
    }
    .processing-loader::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.8), transparent);
        animation: shimmer 2s infinite;
    }
    @keyframes shimmer {
        0% { left: -100%; }
        100% { left: 100%; }
    }
    .processing-step {
        text-align: center;
        font-size: 14px;
        color: #666;
        margin: 5px 0;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Render the loader
    st.markdown(f'<div class="processing-loader"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="processing-step">{steps[step]}</div>', unsafe_allow_html=True)
    
    return step + 1 if step < len(steps) - 1 else 0


def initialize_chat_history():
    """Initialize chat history in session state."""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = f"session_{int(time.time())}"

def check_admin_access():
    """Check if user has admin access."""
    # Check if already authenticated
    if st.session_state.get('admin_authenticated', False):
        return True
    
    # Show authentication form
    st.markdown("### 🔐 Admin Access Required")
    st.markdown("Please enter the admin password to access the dashboard.")
    
    # Create a form for password input
    with st.form("admin_auth_form"):
        password = st.text_input("Admin Password", type="password", placeholder="Enter admin password")
        submit_button = st.form_submit_button("🔓 Access Admin Panel")
        
        if submit_button:
            # Check password (you can change this to your preferred password)
            admin_password = st.secrets.get("ADMIN_PASSWORD", "admin123")  # Default password
            if password == admin_password:
                st.session_state.admin_authenticated = True
                st.success("✅ Access granted! Redirecting to admin panel...")
                st.rerun()
            else:
                st.error("❌ Invalid password. Please try again.")
    
    return False

def logout_admin():
    """Logout from admin panel."""
    if 'admin_authenticated' in st.session_state:
        del st.session_state.admin_authenticated
    st.success("👋 Logged out successfully!")
    st.rerun()

def check_hybrid_demo_access():
    """Check if user has access to hybrid demo."""
    # Check if already authenticated
    if st.session_state.get('hybrid_demo_authenticated', False):
        return True
    
    # Show authentication form
    st.markdown("### 🔐 Hybrid Demo Access Required")
    st.markdown("Please enter the password to access the Hybrid AI Model Demo.")
    
    # Create a form for password input
    with st.form("hybrid_demo_auth_form"):
        password = st.text_input("Password", type="password", placeholder="Enter password")
        submit_button = st.form_submit_button("🔓 Access Demo")
        
        if submit_button:
            # Check password (you can change this to your preferred password)
            demo_password = os.getenv("DEMO_PASSWORD", "demo123")  # Default password
            if password == demo_password:
                st.session_state.hybrid_demo_authenticated = True
                st.success("✅ Access granted! Loading demo...")
                st.rerun()
            else:
                st.error("❌ Invalid password. Please try again.")
    
    return False

def logout_hybrid_demo():
    """Logout from hybrid demo."""
    if 'hybrid_demo_authenticated' in st.session_state:
        del st.session_state.hybrid_demo_authenticated
    st.success("👋 Logged out successfully!")
    st.rerun()

def render_hybrid_smart_routing_interface():
    """Render smart routing interface for hybrid demo."""
    st.header("🧭 Smart Query Routing")
    st.markdown("Let the system automatically choose the best model for your query")
    
    # Query input
    query = st.text_area(
        "Enter your query:",
        placeholder="e.g., What is Adobe Analytics and how does it work?",
        height=100,
        key="hybrid_query_text_area"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        context_length = st.slider(
            "Context Length:",
            min_value=0,
            max_value=100000,
            value=0,
            step=1000,
            help="Estimated context length in characters",
            key="hybrid_context_length_slider"
        )
    
    with col2:
        if st.button("🎯 Analyze & Route", type="primary"):
            if query:
                with st.spinner("Analyzing query and routing to best model..."):
                    try:
                        # Analyze query
                        analysis = st.session_state.hybrid_query_router.analyze_query(query)
                        
                        # Display analysis
                        st.subheader("📊 Query Analysis")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Complexity", analysis['complexity'].title())
                        with col2:
                            st.metric("Query Type", analysis['query_type'].title())
                        with col3:
                            st.metric("Estimated Tokens", f"{analysis['estimated_tokens']:,}")
                        
                        # Route query
                        routing_decision = st.session_state.hybrid_query_router.route_query(
                            query, analysis, context_length
                        )
                        
                        st.subheader("🎯 Routing Decision")
                        st.info(f"**Selected Model:** {routing_decision['selected_model'].title()}")
                        st.write(f"**Reasoning:** {routing_decision['reasoning']}")
                        
                        # Execute query with selected model
                        st.subheader("🤖 Response")
                        with st.spinner(f"Generating response using {routing_decision['selected_model'].title()}..."):
                            try:
                                # Get knowledge base and AWS clients from main app
                                settings = get_cached_settings()
                                aws_clients = get_cached_aws_clients(settings) if settings else None
                                knowledge_base_id = settings.bedrock_knowledge_base_id if settings else None
                                
                                if routing_decision['selected_model'] == 'gemini':
                                    result = st.session_state.hybrid_model_provider.generate_response(
                                        query, 'gemini', knowledge_base_id, aws_clients
                                    )
                                else:
                                    result = st.session_state.hybrid_model_provider.generate_response(
                                        query, 'claude', knowledge_base_id, aws_clients
                                    )
                                
                                # Clean Adobe DNL markup from response
                                cleaned_response = clean_adobe_dnl_text(result['response'])
                                st.write(cleaned_response)
                                
                                # Display metrics
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Response Time", f"{result['response_time']:.2f}s")
                                with col2:
                                    st.metric("Tokens Used", f"{result['tokens_used']:,}")
                                with col3:
                                    st.metric("Cost", f"${result['cost']:.4f}")
                                
                            except Exception as e:
                                st.error(f"Error generating response: {e}")
                    
                    except Exception as e:
                        st.error(f"Error in smart routing: {e}")
            else:
                st.warning("Please enter a query first.")

def render_hybrid_test_suite_interface():
    """Render test suite interface for hybrid demo."""
    st.header("🧪 Test Suite")
    st.markdown("Run predefined test queries to evaluate model performance")
    
    # Test categories
    test_categories = {
        "Adobe Analytics": [
            "How do I set up Adobe Analytics tracking?",
            "What is the difference between eVars and props?",
            "How do I create custom segments in Adobe Analytics?"
        ],
        "Customer Journey Analytics": [
            "How do I connect data sources in CJA?",
            "What is the difference between CJA and Adobe Analytics?",
            "How do I create cross-channel reports in CJA?"
        ],
        "Adobe Experience Platform": [
            "How do I set up a schema in AEP?",
            "What is the difference between datasets and profiles?",
            "How do I create segments in AEP?"
        ]
    }
    
    selected_category = st.selectbox("Select Test Category:", list(test_categories.keys()), key="hybrid_test_category_selectbox")
    
    if selected_category:
        st.subheader(f"Test Queries - {selected_category}")
        
        for i, query in enumerate(test_categories[selected_category]):
            with st.expander(f"Query {i+1}: {query[:50]}...", expanded=False):
                st.write(f"**Full Query:** {query}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Test with Gemini", key=f"gemini_test_{i}"):
                        with st.spinner("Testing with Gemini..."):
                            try:
                                # Get knowledge base and AWS clients
                                settings = get_cached_settings()
                                aws_clients = get_cached_aws_clients(settings) if settings else None
                                knowledge_base_id = settings.bedrock_knowledge_base_id if settings else None
                                
                                result = st.session_state.hybrid_model_provider.generate_response(
                                    query, 'gemini', knowledge_base_id, aws_clients
                                )
                                st.write("**Gemini Response:**")
                                # Clean Adobe DNL markup from response
                                cleaned_response = clean_adobe_dnl_text(result['response'])
                                st.write(cleaned_response)
                                kb_status = "✅ Used KB" if result.get('used_knowledge_base') else "❌ No KB"
                                st.write(f"**Metrics:** {result['response_time']:.2f}s, {result['tokens_used']} tokens, ${result['cost']:.4f} | {kb_status}")
                            except Exception as e:
                                st.error(f"Gemini test failed: {e}")
                
                with col2:
                    if st.button(f"Test with Claude", key=f"claude_test_{i}"):
                        with st.spinner("Testing with Claude..."):
                            try:
                                # Get knowledge base and AWS clients
                                settings = get_cached_settings()
                                aws_clients = get_cached_aws_clients(settings) if settings else None
                                knowledge_base_id = settings.bedrock_knowledge_base_id if settings else None
                                
                                result = st.session_state.hybrid_model_provider.generate_response(
                                    query, 'claude', knowledge_base_id, aws_clients
                                )
                                st.write("**Claude Response:**")
                                # Clean Adobe DNL markup from response
                                cleaned_response = clean_adobe_dnl_text(result['response'])
                                st.write(cleaned_response)
                                kb_status = "✅ Used KB" if result.get('used_knowledge_base') else "❌ No KB"
                                st.write(f"**Metrics:** {result['response_time']:.2f}s, {result['tokens_used']} tokens, ${result['cost']:.4f} | {kb_status}")
                            except Exception as e:
                                st.error(f"Claude test failed: {e}")

def render_hybrid_analytics_interface():
    """Render analytics interface for hybrid demo."""
    st.header("📊 Analytics")
    st.markdown("View performance metrics and usage statistics")
    
    if st.session_state.hybrid_model_provider:
        # Get usage statistics
        usage_stats = st.session_state.hybrid_model_provider.get_usage_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Queries", usage_stats.get('total_queries', 0))
        with col2:
            st.metric("Total Cost", f"${usage_stats.get('total_cost', 0):.4f}")
        with col3:
            st.metric("Avg Response Time", f"{usage_stats.get('avg_response_time', 0):.2f}s")
        with col4:
            st.metric("Total Tokens", f"{usage_stats.get('total_tokens', 0):,}")
        
        # Model-specific metrics
        st.subheader("Model Performance")
        
        if 'model_stats' in usage_stats:
            for model, stats in usage_stats['model_stats'].items():
                with st.expander(f"{model.title()} Statistics", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Queries", stats.get('queries', 0))
                    with col2:
                        st.metric("Cost", f"${stats.get('cost', 0):.4f}")
                    with col3:
                        st.metric("Avg Time", f"{stats.get('avg_time', 0):.2f}s")
    else:
        st.info("Please initialize the models first to view analytics.")

def render_hybrid_feedback_interface():
    """Render feedback interface for hybrid demo."""
    st.header("📝 Feedback & Retraining")
    st.markdown("Rate model responses and prepare data for retraining")
    
    # Initialize feedback UI
    feedback_ui = FeedbackUI()
    
    # Feedback dashboard
    feedback_ui.render_feedback_dashboard()
    
    st.markdown("---")
    
    # Retraining interface
    feedback_ui.render_retraining_interface()

def render_hybrid_retraining_interface():
    """Render retraining interface for hybrid demo."""
    st.header("🔄 Model Retraining")
    st.markdown("Prepare feedback data for model retraining and improvement")
    
    # Initialize retraining UI
    retraining_ui = RetrainingUI()
    
    # Render retraining interface
    retraining_ui.render_retraining_interface()


def render_about_page():
    """Render the About page with application information."""
    st.title("ℹ️ About This Application")
    st.markdown("---")
    
    # Application Overview
    st.markdown("### 🎯 What is this application?")
    st.markdown("""
    This is an **intelligent chatbot** designed specifically to help you with Adobe Analytics 
    and Customer Journey Analytics (CJA) questions. 
    Think of it as your personal Adobe expert that's available 24/7!
    """)
    
    # Key Features
    st.markdown("### ✨ Key Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🤖 Smart AI Assistant**
        - Powered by advanced AI technology
        - Understands Adobe-specific terminology
        - Provides accurate, helpful answers
        
        **📚 Knowledge Base**
        - Access to comprehensive Adobe documentation
        - Up-to-date information and best practices
        - Real-world examples and use cases
        """)
    
    with col2:
        st.markdown("""
        **💬 Natural Conversations**
        - Ask questions in plain English
        - Get detailed, step-by-step guidance
        - Follow-up questions welcome
        
        **⚡ Fast & Reliable**
        - Quick response times
        - Always available when you need help
        - No need to search through documentation
        """)
    
    # What You Can Ask
    st.markdown("### 💡 What can you ask?")
    
    st.markdown("""
    **Adobe Analytics Questions:**
    - How do I create segments and calculated metrics?
    - What's the difference between eVars and props?
    - How do I set up conversion tracking?
    - How do I use Analysis Workspace?
    
    **Customer Journey Analytics (CJA) Questions:**
    - How do I analyze cross-channel customer journeys?
    - What's the difference between Analytics and CJA?
    - How do I create connections in CJA?
    - How do I use the CJA workspace?
    """)
    
    # How It Works
    st.markdown("### 🔧 How does it work?")
    
    st.markdown("""
    1. **Ask Your Question**: Type your Adobe-related question in the chat box
    2. **AI Processing**: Our smart AI searches through Adobe documentation and knowledge
    3. **Get Your Answer**: Receive a detailed, helpful response tailored to your question
    4. **Follow Up**: Ask follow-up questions or dive deeper into any topic
    """)
    
    # Technology Stack
    st.markdown("### 🛠️ Built With")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🤖 AI Technology**
        - AWS Bedrock
        - Claude AI Models
        - Smart Routing
        """)
    
    with col2:
        st.markdown("""
        **📊 Adobe Integration**
        - Adobe Analytics
        - Customer Journey Analytics
        """)
    
    with col3:
        st.markdown("""
        **💻 Modern Web Tech**
        - Streamlit
        - Python
        - Real-time Processing
        """)
    
    # Getting Started
    st.markdown("### 🚀 Getting Started")
    
    st.markdown("""
    **Ready to get help with Adobe? Here's how to start:**
    
    1. **Go to the Main Chat** page using the navigation menu
    2. **Type your question** in the chat box
    3. **Press Enter** or click the "Ask" button
    4. **Get your answer** and ask follow-up questions as needed
    
    **💡 Pro Tips:**
    - Be specific with your questions for better answers
    - Ask follow-up questions to dive deeper
    - Try different ways of asking the same question
    - The more context you provide, the better the answer
    """)
    
    # Support & Contact
    st.markdown("### 📞 Need Help?")
    
    st.markdown("""
    **📧 Contact Support:**
    - **Email**: ritesh@thelearningproject.in
    - **Website**: [www.thelearningproject.in](https://www.thelearningproject.in)
    """)
    
    # Legal Disclaimer
    st.markdown("---")
    st.markdown("### ⚖️ Legal Disclaimer")
    st.markdown("""
    This unofficial Experience League Documentation chatbot is powered by AWS Bedrock and public Adobe Analytics and Customer Journey Analytics documentation and guides. 
    Answers may be inaccurate, inefficient, or biased. Any use or decisions based on such answers should include 
    reasonable practices including human oversight to ensure they are safe, accurate, and suitable for your intended 
    purpose. This application or its developer(s) is not liable for any actions, losses, or damages resulting from 
    the use of the chatbot. Do not enter any private, sensitive, personal, or regulated data. By using this chatbot, 
    you acknowledge and agree that input you provide and answers you receive (collectively, "Content") may be used 
    by the developer to provide, maintain, develop, and improve their respective offerings.
    """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 14px;'>
        <p>🤖 <strong>Unofficial Adobe Experience League Chatbot</strong></p>
        <p>Powered by Adobe Experience League documentation and AWS Bedrock</p>
        <p>Built to answer questions about Adobe Analytics and CJA</p>
    </div>
    """, unsafe_allow_html=True)
    if 'saved_sessions' not in st.session_state:
        st.session_state.saved_sessions = {}
    if 'favorite_conversations' not in st.session_state:
        st.session_state.favorite_conversations = set()

def save_chat_message(role, content, metadata=None):
    """Save a chat message to history."""
    message = {
        'id': f"msg_{int(time.time() * 1000)}",
        'timestamp': datetime.now().isoformat(),
        'role': role,  # 'user' or 'assistant'
        'content': content,
        'metadata': metadata or {}
    }
    st.session_state.chat_history.append(message)

# Export functions removed - moved to future enhancements

def render_chat_history_sidebar():
    """Render chat history sidebar."""
    with st.sidebar:
        st.header("💬 Chat History")
        
        # Session management
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆕 New Chat", help="Start a new chat session", key="new_chat_button"):
                st.session_state.chat_history = []
                st.session_state.current_session_id = f"session_{int(time.time())}"
                st.rerun()
        
        with col2:
            if st.button("💾 Save Session", help="Save current chat session", key="save_session_button"):
                session_name = f"Chat_{datetime.now().strftime('%Y%m%d_%H%M')}"
                st.session_state.saved_sessions[session_name] = {
                    'id': st.session_state.current_session_id,
                    'history': st.session_state.chat_history.copy(),
                    'timestamp': datetime.now().isoformat()
                }
                st.success(f"Session saved as '{session_name}'")
        
        # Load saved sessions
        if st.session_state.saved_sessions:
            st.subheader("📁 Saved Sessions")
            for session_name, session_data in st.session_state.saved_sessions.items():
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.button(f"📂 {session_name}", key=f"load_{session_name}"):
                        st.session_state.chat_history = session_data['history'].copy()
                        st.session_state.current_session_id = session_data['id']
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"delete_{session_name}", help="Delete session"):
                        del st.session_state.saved_sessions[session_name]
                        st.rerun()
        
        # Example questions section
        st.markdown("---")
        st.subheader("💡 Example Questions")
        
        example_questions = [
            "What is Adobe Analytics?",
            "How do I create custom events?",
            "Compare Adobe Analytics vs Google Analytics",
            "What are the best practices for web analytics?",
            "How to implement tracking scripts?",
            "What is Customer Journey Analytics?"
        ]
        
        # Initialize selected question in session state
        if 'selected_example_question' not in st.session_state:
            st.session_state.selected_example_question = None
        
        for i, question in enumerate(example_questions):
            if st.button(f"💬 {question}", key=f"example_{i}", help="Click to use this example question", use_container_width=True):
                st.session_state.selected_example_question = question
                st.rerun()

def render_main_page_minimal():
    """Render main page with minimal initialization for fast LCP and low CLS."""
    # Initialize chat history
    initialize_chat_history()
    
    # Header section - render immediately
    st.title("📊 Adobe Experience League Chatbot - Unofficial")
    st.markdown("**Intelligent RAG Assistant for answering questions about Adobe Analytics and Customer Journey Analytics**")
    
    # Debug mode indicator (only visible when enabled)
    if st.session_state.get('debug_mode', False):
        st.info("🔍 **Debug Mode Active** - Debug information will be shown when processing queries")
    
    # No status messages to prevent CLS (matching optimized app)
    
    # Main content area
    st.markdown("---")
    
    # Query input and submit button in a row
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "Ask your question about Adobe Analytics, Customer Journey Analytics related topics",
            placeholder="e.g., How do I set up Adobe Analytics tracking?",
            key="query_input",
            help="Maximum 20,000 characters. Be specific and clear for best results.",
            on_change=lambda: st.session_state.update(enter_pressed=True)
        )
        
        # Add tip below the input box
        st.markdown("💡 **Tip:** Be precise and avoid anything that is not related. Ensure you put the name of the solution completely instead of abbreviations.")
        
        # Character counter
        if query:
            char_count = len(query)
            max_chars = 20000
            if char_count > max_chars:
                st.error(f"⚠️ Query too long: {char_count:,} characters (max: {max_chars:,})")
            elif char_count > max_chars * 0.8:  # 80% of limit
                st.warning(f"📝 Query length: {char_count:,} characters (approaching limit)")
            else:
                st.caption(f"📝 Query length: {char_count:,} characters")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add some vertical spacing
        submit_button = st.button("🚀 Ask", type="primary", key="ask_question_button")
    
    # Add custom CSS for question box border, hover glow effect, and larger label font
    st.markdown("""
    <style>
    .stTextInput > div > div > input {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        outline: none !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1f77b4;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        outline: none !important;
    }
    .stTextInput > div > div > input:hover {
        border-color: #1f77b4;
        box-shadow: 0 0 15px rgba(31, 119, 180, 0.3);
    }
    .stTextInput > label {
        font-size: 18px !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Processing loader (shown during query processing)
    if st.session_state.get('processing_query', False):
        render_processing_loader(st.session_state.get('processing_step', 0))
    
    # Reserve space for chat history to prevent CLS
    chat_container = st.container()
    with chat_container:
        if st.session_state.chat_history:
            st.markdown("---")
            st.subheader("💬 Chat History")
            
            # Display messages in reverse order (newest first) with proper grouping
            messages = list(reversed(st.session_state.chat_history))
            i = 0
            while i < len(messages):
                message = messages[i]
                
                if message['role'] == 'assistant':
                    # This is an assistant message, check if there's a user message after it
                    if i + 1 < len(messages) and messages[i + 1]['role'] == 'user':
                        # Found a user-assistant pair, display user first, then assistant
                        user_message = messages[i + 1]
                        st.markdown(f"**👤 You:** {user_message['content']}")
                        st.markdown(f"**🤖 Assistant:** {message['content']}")
                        
                        # Metadata display removed for cleaner interface
                        
                        # Skip both messages since we've displayed them
                        i += 2
                    else:
                        # Orphaned assistant message, display it
                        st.markdown(f"**🤖 Assistant:** {message['content']}")
                        
                        # Metadata display removed for cleaner interface
                        
                        i += 1
                else:
                    # This is an orphaned user message, display it
                    st.markdown(f"**👤 You:** {message['content']}")
                    i += 1
                
                st.markdown("---")
        else:
            # Reserve space even when no chat history to prevent CLS
            st.markdown("---")
            st.subheader("💬 Chat History")
            st.markdown("*No messages yet. Ask a question to start the conversation!*")
            st.markdown("---")
    
    # Process query when submitted (button click or Enter key)
    if submit_button or st.session_state.get('enter_pressed', False):
        # Basic validation only (no UI messages to prevent CLS)
        if query and len(query) >= 3:
            # Check if query is relevant to Adobe Analytics, CJA, AEP, etc.
            if not check_query_relevance(query):
                # Save user message
                save_chat_message('user', query)
                
                # Save irrelevant response
                irrelevant_response = get_irrelevant_question_response()
                save_chat_message('assistant', irrelevant_response)
                
                # Clear the query input and enter_pressed flag
                if 'query_input' in st.session_state:
                    del st.session_state.query_input
                if 'enter_pressed' in st.session_state:
                    del st.session_state.enter_pressed
                
                st.rerun()
                return
            # Lazy initialization - only when needed
            settings = get_cached_settings()
            if settings:
                aws_clients = get_cached_aws_clients(settings)
                if aws_clients:
                    # Quick KB test
                    kb_status, kb_error = test_knowledge_base_connection(
                        settings.bedrock_knowledge_base_id,
                        aws_clients['bedrock_agent_client']
                    )
                    
                    if kb_status:
                        # Initialize smart router
                        haiku_only_mode = st.session_state.get('haiku_only_mode', False)
                        smart_router = SmartRouter(haiku_only_mode=haiku_only_mode)
                        
                        # Initialize analytics service
                        analytics_service = None
                        if ANALYTICS_AVAILABLE:
                            try:
                                analytics_service = initialize_analytics_service()
                                st.session_state.analytics_available = analytics_service is not None
                            except Exception as e:
                                st.session_state.analytics_available = False
                        
                        # Debug analytics before processing
                        print(f"🔍 [MAIN] About to process query: {query[:50]}...")
                        print(f"🔍 [MAIN] Analytics available: {st.session_state.get('analytics_available', False)}")
                        print(f"🔍 [MAIN] Analytics service: {analytics_service is not None}")
                        
                        # Process the query
                        process_query_with_full_initialization(query, settings, aws_clients, smart_router, analytics_service)
    
    # Enhanced Debug Panel (always visible when debug mode is enabled)
    if st.session_state.get('debug_mode', False) and DEBUG_PANEL_AVAILABLE:
        debug_panel.render_debug_panel()
    elif st.session_state.get('debug_mode', False):
        # Fallback to basic debug info if debug panel is not available
        with st.expander("🔍 Basic Debug Info", expanded=True):
            st.write(f"**Debug mode status:** {st.session_state.get('debug_mode', False)}")
            st.write(f"**Session state keys:** {list(st.session_state.keys())}")
            if 'query_input' in st.session_state:
                st.write(f"**Query input:** '{st.session_state.get('query_input', 'NOT_SET')}'")
            if 'processing_query' in st.session_state:
                st.write(f"**Processing query:** {st.session_state.get('processing_query', False)}")
            if 'query_count' in st.session_state:
                st.write(f"**Query count:** {st.session_state.get('query_count', 0)}")
            if 'total_tokens_used' in st.session_state:
                st.write(f"**Total tokens used:** {st.session_state.get('total_tokens_used', 0)}")
            if 'cost_by_model' in st.session_state:
                st.write(f"**Cost by model:** {st.session_state.get('cost_by_model', {})}")
            if 'debug_history' in st.session_state:
                st.write(f"**Debug history entries:** {len(st.session_state.get('debug_history', []))}")
    
    # Query Enhancement Information (show when available)
    if QUERY_ENHANCEMENT_AVAILABLE and st.session_state.get('last_enhancement_metadata'):
        enhancement_data = st.session_state['last_enhancement_metadata']
        with st.expander("🚀 Query Enhancement Details", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Original Query:**")
                st.write(f"'{enhancement_data.get('original_query', 'N/A')}'")
                
                st.write("**Enhanced Queries:**")
                for i, enhanced_query in enumerate(enhancement_data.get('enhanced_queries', [])[:3], 1):
                    st.write(f"{i}. {enhanced_query}")
            
            with col2:
                st.write("**Detected Products:**")
                products = enhancement_data.get('detected_products', [])
                if products:
                    for product in products:
                        st.write(f"• {product}")
                else:
                    st.write("None detected")
                
                st.write("**Processing Time:**")
                st.write(f"{enhancement_data.get('processing_time_ms', 0):.2f} ms")
    
    # Smart Context Management Information (show when available)
    if SMART_CONTEXT_AVAILABLE:
        if st.session_state.get('last_context_metadata'):
            context_data = st.session_state['last_context_metadata']
            with st.expander("🧠 Smart Context Management", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Query Complexity:**")
                    complexity_emoji = {
                        'simple': '🟢',
                        'medium': '🟡', 
                        'complex': '🔴'
                    }
                    complexity = context_data['complexity']
                    st.write(f"{complexity_emoji.get(complexity, '⚪')} {complexity.title()}")
                    
                    st.write("**Context Configuration:**")
                    st.write(f"• Max chars per doc: {context_data['max_chars_per_doc']:,}")
                    st.write(f"• Max documents: {context_data['max_docs']}")
                    st.write(f"• Documents used: {context_data['documents_used']}")
                
                with col2:
                    st.write("**Context Statistics:**")
                    st.write(f"• Total context length: {context_data['context_length']:,} chars")
                    st.write(f"• Processing time: {context_data['processing_time_ms']:.2f} ms")
                    
                    if 'detection_details' in context_data:
                        details = context_data['detection_details']
                        st.write("**Detection Details:**")
                        st.write(f"• Query length: {details['query_length']} chars")
                        st.write(f"• Complexity score: {details['complexity_score']}")
                        if details['technical_indicators']:
                            st.write(f"• Technical terms: {len(details['technical_indicators'])}")
        else:
            # Show that smart context is available but not used yet
            st.info("🧠 Smart Context Management is available. Submit a query to see context optimization details.")

def process_query_with_full_initialization(query, settings, aws_clients, smart_router, analytics_service):
    """Process query with full initialization (called only when needed)."""
    print(f"🔍 [PROCESS] Function called with query: {query[:50]}...")
    print(f"🔍 [PROCESS] Analytics service: {analytics_service is not None}")
    print(f"🔍 [PROCESS] Analytics available: {st.session_state.get('analytics_available', False)}")
    
    # Initialize debug panel and cost tracking early
    if DEBUG_PANEL_AVAILABLE:
        debug_panel.initialize_session_variables()
    
    # Initialize cost tracking early to prevent KeyError
    if 'cost_by_model' not in st.session_state:
        st.session_state.cost_by_model = {'haiku': 0, 'sonnet': 0, 'opus': 0}
    if 'query_count' not in st.session_state:
        st.session_state.query_count = 0
    if 'total_tokens_used' not in st.session_state:
        st.session_state.total_tokens_used = 0
    
    # Save user message
    save_chat_message('user', query)
    print(f"🔍 [PROCESS] User message saved")
    
    # Set processing state
    st.session_state.processing_query = True
    st.session_state.processing_step = 0
    print(f"🔍 [PROCESS] Processing state set")
    
    # Track query start time
    st.session_state.query_start_time = time.time()
    print(f"🔍 [PROCESS] Query start time set")
    
    # Process query with streaming UI
    print(f"🔍 [PROCESS] About to call process_query_with_smart_routing_stream")
    start_time = time.time()
    
    # Reserve space for result messages to prevent CLS
    result_container = st.container()
    with result_container:
        
        # Create a placeholder for the streaming response
        response_placeholder = st.empty()
        full_response = ""
        model_used = None
        documents = []
        routing_decision = {}
        
        # Show initial processing message
        with st.spinner("🤖 Processing your question with AI..."):
            # Process query with streaming
            for result in process_query_with_smart_routing_stream(
                query,
                settings.bedrock_knowledge_base_id,
                smart_router,
                aws_clients
            ):
                if not result["success"]:
                    # Handle error
                    response_placeholder.error(f"❌ **Error:** {result['error']}")
                    save_chat_message('assistant', f"❌ Error: {result['error']}")
                    
                    # Add debug entry for error
                    if DEBUG_PANEL_AVAILABLE:
                        debug_panel.add_debug_entry(
                            query=query,
                            status="error",
                            duration=time.time() - start_time,
                            error=result['error'],
                            step_info="Query processing failed",
                            source_urls=[]
                        )
                    
                    st.rerun()
                    return
                
                # Update response variables
                if result.get('answer'):
                    # For streaming, replace the full response with the accumulated answer
                    if result.get('is_streaming', True):
                        full_response = result['answer']  # Replace with accumulated answer
                    else:
                        full_response += result['answer']  # Add final chunk if any
                    
                    model_used = result.get('model_used', 'haiku')
                    documents = result.get('documents', [])
                    routing_decision = result.get('routing_decision', {})
                    
                    # Display streaming response only during streaming
                    if result.get('is_streaming', True):
                        response_placeholder.markdown(f"**🤖 Assistant:** {full_response}")
                    # Don't display final response here - it will be shown in chat history after st.rerun()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Track cost and usage
        if full_response:
            # Increment query count
            st.session_state.query_count += 1
            
            # Estimate tokens and cost (rough estimation)
            answer_length = len(full_response)
            query_length = len(query)
            
            # Rough token estimation (1 token ≈ 4 characters)
            estimated_tokens = (query_length + answer_length) // 4
            st.session_state.total_tokens_used += estimated_tokens
            
            # Cost calculation based on model
            cost_per_1k_tokens = {
                'haiku': 0.00125,  # $1.25 per 1M tokens
                'sonnet': 0.015,   # $15 per 1M tokens  
                'opus': 0.075      # $75 per 1M tokens
            }
            
            # Ensure cost_by_model is initialized with all model keys
            if 'cost_by_model' not in st.session_state:
                st.session_state.cost_by_model = {'haiku': 0, 'sonnet': 0, 'opus': 0}
            
            # Ensure the specific model key exists
            if model_used not in st.session_state.cost_by_model:
                st.session_state.cost_by_model[model_used] = 0
            
            estimated_cost = (estimated_tokens / 1000) * cost_per_1k_tokens.get(model_used, 0.00125)
            st.session_state.cost_by_model[model_used] += estimated_cost
            
            # Add debug entry for query completion
            if DEBUG_PANEL_AVAILABLE:
                # Extract source URLs from documents
                source_urls = extract_source_urls(documents) if documents else []
                
                debug_panel.add_debug_entry(
                    query=query,
                    status="completed",
                    duration=processing_time,
                    tokens=estimated_tokens,
                    cost=estimated_cost,
                    model=model_used,
                    step_info="Query completed successfully",
                    source_urls=source_urls
                )
            
            # Save assistant response with metadata
            assistant_metadata = {
                'model_used': model_used,
                'documents_retrieved': len(documents),
                'cost': estimated_cost,
                'routing_decision': routing_decision,
                'processing_time': time.time() - st.session_state.get('query_start_time', time.time())
            }
            # Fix links in the response before saving
            fixed_response = fix_markdown_links(full_response)
            save_chat_message('assistant', fixed_response, assistant_metadata)
            
            # Clear the streaming response placeholder since it will be shown in chat history
            response_placeholder.empty()
            
            # Store analytics data directly (synchronous) - BEFORE st.rerun()
            query_id = None
            response_id = None
            
            # Debug analytics conditions
            analytics_available = st.session_state.get('analytics_available', False)
            print(f"🔍 [DEBUG] Analytics available: {analytics_available}")
            print(f"🔍 [DEBUG] Analytics service: {analytics_service is not None}")
            print(f"🔍 [DEBUG] Analytics service type: {type(analytics_service)}")
            
            if analytics_available and analytics_service:
                try:
                    print(f"🔍 [APP] About to track query: {query[:50]}...")
                    print(f"🔍 [APP] Analytics service available: {analytics_service is not None}")
                    print(f"🔍 [APP] Session ID: {st.session_state.get('current_session_id', 'default')}")
                    
                    # Calculate query processing time
                    query_processing_time = time.time() - st.session_state.get('query_start_time', time.time())
                    
                    # Track user query using the simplified integration with timing and model info
                    query_id = analytics_service.track_query(
                        session_id=st.session_state.get('current_session_id', 'default'),
                        query_text=query,
                        query_complexity=routing_decision.get('complexity', 'simple'),
                        query_time_seconds=query_processing_time,
                        model_used=model_used
                    )
                    
                    print(f"🔍 [APP] Query tracking result: {query_id}")
                    
                    if query_id:
                        # Track AI response using the simplified integration
                        response_id = analytics_service.track_response(
                            query_id=query_id,
                            response_text=full_response,
                            model_used=model_used
                        )
                        
                        if response_id:
                            st.session_state.last_query_id = query_id
                            st.session_state.last_response_id = response_id
                            print(f"✅ [APP] Analytics tracking successful - Query ID: {query_id}, Response ID: {response_id}")
                        else:
                            print(f"❌ [APP] Response tracking failed")
                    else:
                        print(f"❌ [APP] Query tracking failed")
                        
                except Exception as e:
                    print(f"❌ [APP] Analytics storage failed: {e}")
                    import traceback
                    print(f"❌ [APP] Traceback: {traceback.format_exc()}")
            else:
                print(f"❌ [APP] Analytics not available - available: {st.session_state.get('analytics_available', False)}, service: {analytics_service is not None}")
            
            # Add processing message with insertion ID to the response
            if query_id:
                processing_message = f"📊 **Query tracked successfully!** (ID: {query_id})"
                if response_id:
                    processing_message += f" | Response ID: {response_id}"
                st.info(processing_message)
            else:
                st.warning("⚠️ Query tracking failed - check logs for details")
            
            # Show success message
            st.success("✅ **Query processed successfully!**")
            
            # Clear processing state
            st.session_state.processing_query = False
            st.session_state.processing_step = 0
            
            # Clear the query input and enter_pressed flag after successful processing
            if 'query_input' in st.session_state:
                del st.session_state.query_input
            if 'enter_pressed' in st.session_state:
                del st.session_state.enter_pressed
            
            # Rerun to display the new message in chat history IMMEDIATELY
            st.rerun()

def render_main_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, analytics_service=None):
    """Render the clean main page focused on user experience."""
    # Initialize chat history
    initialize_chat_history()
    
    # Header section
    st.title("📊 Adobe Experience League Chatbot")
    st.markdown("**Intelligent RAG Assistant for Adobe Analytics Documentation**")
    
    # No status messages to prevent CLS (matching optimized app)
    
    # Main content area
    st.markdown("---")
    
    # Query input section
    # Handle selected example question
    if st.session_state.get('selected_example_question'):
        st.session_state.query_input = st.session_state.get('selected_example_question')
        st.session_state.selected_example_question = None
    
    # Handle clear button before creating the text input
    clear_button = st.button("🗑️ Clear", help="Clear the input field", use_container_width=True, key="clear_button")
    if clear_button:
        # Clear the query input by removing it from session state
        if 'query_input' in st.session_state:
            del st.session_state.query_input
        st.rerun()
    
    # Create the text input and submit button in a row
    col1, col2 = st.columns([4, 1])
    
    with col1:
        query = st.text_input(
            "Ask your question about Adobe Analytics, Customer Journey Analytics, or related topics:",
            value=st.session_state.get('query_input', ''),
            placeholder="e.g., How do I create custom events in Adobe Analytics?",
            help="Maximum 20,000 characters. Be specific and clear for best results.",
            key="query_input",
            on_change=lambda: st.session_state.update(enter_pressed=True)
        )
        
        # Query Enhancement Toggle (moved here for better visibility)
        if QUERY_ENHANCEMENT_AVAILABLE:
            st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
            query_enhancement_enabled = st.checkbox(
                "🚀 Query Enhancement", 
                value=st.session_state.get('query_enhancement_enabled', True),
                help="Enable query enhancement for better search results"
            )
            st.session_state['query_enhancement_enabled'] = query_enhancement_enabled
        
        # Character counter
        if query:
            char_count = len(query)
            max_chars = 20000
            if char_count > max_chars:
                st.error(f"⚠️ Query too long: {char_count:,} characters (max: {max_chars:,})")
            elif char_count > max_chars * 0.8:  # 80% of limit
                st.warning(f"📝 Query length: {char_count:,} characters (approaching limit)")
            else:
                st.caption(f"📝 Query length: {char_count:,} characters")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Add some vertical spacing
        submit_button = st.button("🚀 Ask", type="primary", key="ask_question_button")
    
    # Add custom CSS for question box border, hover glow effect, and larger label font
    st.markdown("""
    <style>
    .stTextInput > div > div > input {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        outline: none !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1f77b4;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        outline: none !important;
    }
    .stTextInput > div > div > input:hover {
        border-color: #1f77b4;
        box-shadow: 0 0 15px rgba(31, 119, 180, 0.3);
    }
    .stTextInput > label {
        font-size: 18px !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Processing loader (shown during query processing)
    if st.session_state.get('processing_query', False):
        render_processing_loader(st.session_state.get('processing_step', 0))
    
    # Display chat history (simplified for performance)
    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("💬 Chat History")
        
        # Display messages in reverse order (newest first) with proper grouping
        messages = list(reversed(st.session_state.chat_history))
        i = 0
        while i < len(messages):
            message = messages[i]
            
            if message['role'] == 'assistant':
                # This is an assistant message, check if there's a user message after it
                if i + 1 < len(messages) and messages[i + 1]['role'] == 'user':
                    # Found a user-assistant pair, display user first, then assistant
                    user_message = messages[i + 1]
                    st.markdown(f"**👤 You:** {user_message['content']}")
                    st.markdown(f"**🤖 Assistant:** {message['content']}")
                    
                    # Metadata display removed for cleaner interface
                    
                    # Skip both messages since we've displayed them
                    i += 2
                else:
                    # Orphaned assistant message, display it
                    st.markdown(f"**🤖 Assistant:** {message['content']}")
                    
                    # Metadata display removed for cleaner interface
                    
                    i += 1
            else:
                # This is an orphaned user message, display it
                st.markdown(f"**👤 You:** {message['content']}")
                i += 1
            
            st.markdown("---")
    
    # Enhanced Debug Panel (always visible when debug mode is enabled)
    if st.session_state.get('debug_mode', False) and DEBUG_PANEL_AVAILABLE:
        debug_panel.render_debug_panel()
    elif st.session_state.get('debug_mode', False):
        # Fallback to basic debug info if debug panel is not available
        with st.expander("🔍 Basic Debug Info", expanded=True):
            st.write(f"**Query value:** '{query if query else 'No query yet'}'")
            st.write(f"**Query length:** {len(query) if query else 0}")
            st.write(f"**Session state query_input:** '{st.session_state.get('query_input', 'NOT_SET')}'")
            st.write(f"**Submit button clicked:** {submit_button}")
            st.write(f"**AWS clients available:** {aws_clients is not None}")
            st.write(f"**AWS error:** {aws_error}")
            st.write(f"**KB status:** {kb_status}")
            st.write(f"**Smart router:** {smart_router is not None}")
            st.write(f"**Debug mode status:** {st.session_state.get('debug_mode', False)}")
            st.write(f"**Session state keys:** {list(st.session_state.keys())}")
    
    # Query Enhancement Information (show when available)
    if QUERY_ENHANCEMENT_AVAILABLE:
        if st.session_state.get('last_query_enhancement'):
            enhancement_data = st.session_state['last_query_enhancement']
            with st.expander("🚀 Query Enhancement", expanded=False):
                st.write(f"**Original Query:** {enhancement_data['original_query']}")
                st.write(f"**Enhanced Queries:** {len(enhancement_data['enhanced_queries'])}")
                for i, eq in enumerate(enhancement_data['enhanced_queries'], 1):
                    st.write(f"  {i}. {eq}")
                if enhancement_data['detected_products']:
                    st.write(f"**Detected Products:** {', '.join(enhancement_data['detected_products'])}")
                st.write(f"**Processing Time:** {enhancement_data['processing_time_ms']:.2f}ms")
        else:
            # Show that enhancement is available but not used yet
            st.info("🚀 Query Enhancement is available and enabled. Submit a query to see enhancement details.")
    
    # Smart Context Management Information (show when available)
    if SMART_CONTEXT_AVAILABLE:
        if st.session_state.get('last_context_metadata'):
            context_data = st.session_state['last_context_metadata']
            with st.expander("🧠 Smart Context Management", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Query Complexity:**")
                    complexity_emoji = {
                        'simple': '🟢',
                        'medium': '🟡', 
                        'complex': '🔴'
                    }
                    complexity = context_data['complexity']
                    st.write(f"{complexity_emoji.get(complexity, '⚪')} {complexity.title()}")
                    
                    st.write("**Context Configuration:**")
                    st.write(f"• Max chars per doc: {context_data['max_chars_per_doc']:,}")
                    st.write(f"• Max documents: {context_data['max_docs']}")
                    st.write(f"• Documents used: {context_data['documents_used']}")
                
                with col2:
                    st.write("**Context Statistics:**")
                    st.write(f"• Total context length: {context_data['context_length']:,} chars")
                    st.write(f"• Processing time: {context_data['processing_time_ms']:.2f} ms")
                    
                    if 'detection_details' in context_data:
                        details = context_data['detection_details']
                        st.write("**Detection Details:**")
                        st.write(f"• Query length: {details['query_length']} chars")
                        st.write(f"• Complexity score: {details['complexity_score']}")
                        if details['technical_indicators']:
                            st.write(f"• Technical terms: {len(details['technical_indicators'])}")
        else:
            # Show that smart context is available but not used yet
            st.info("🧠 Smart Context Management is available. Submit a query to see context optimization details.")
    
    
    # Process query when submitted (button click or Enter key)
    if submit_button or st.session_state.get('enter_pressed', False):
        # Clean and validate query
        query = query.strip() if query else ""
        
        if query and len(query) >= 3 and aws_clients and not aws_error and kb_status and smart_router:
            # Check if query is relevant to Adobe Analytics, CJA, AEP, etc.
            if not check_query_relevance(query):
                # Save user message
                save_chat_message('user', query)
                
                # Save irrelevant response
                irrelevant_response = get_irrelevant_question_response()
                save_chat_message('assistant', irrelevant_response)
                
                # Clear the query input and enter_pressed flag
                if 'query_input' in st.session_state:
                    del st.session_state.query_input
                if 'enter_pressed' in st.session_state:
                    del st.session_state.enter_pressed
                
                st.rerun()
                return
            
            # Save user message
            save_chat_message('user', query)
            
            # Set processing state
            st.session_state.processing_query = True
            st.session_state.processing_step = 0
            
            # Track query start time
            st.session_state.query_start_time = time.time()
            
            # Show processing status with timer
            processing_container = st.container()
            with processing_container:
                col1, col2 = st.columns([3, 1])
                with col1:
                    spinner_placeholder = st.empty()
                with col2:
                    # Timer placeholder removed
                    pass
            
            # Start processing
            start_time = time.time()
            
            # Create a progress bar for visual feedback
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with spinner_placeholder:
                with st.spinner("🤖 Processing your question with AI..."):
                    # Process query with optimized smart routing (includes caching)
                    result = process_query_optimized(
                        query,
                        settings.bedrock_knowledge_base_id,
                        smart_router,
                        aws_clients,
                        user_id=st.session_state.get('user_id', 'anonymous')
                    )
            
            # Calculate processing time (for internal use only)
            processing_time = time.time() - start_time
            
            # Update progress bar and status
            progress_bar.progress(100)
            status_text.success("✅ Processing complete!")
            
            # Add debug entry for successful completion
            if DEBUG_PANEL_AVAILABLE and result["success"]:
                debug_panel.add_debug_entry(
                    query=query,
                    status="completed",
                    duration=processing_time,
                    step_info="Query completed successfully",
                    source_urls=[]
                )
            
            # Track cost and usage
            if result["success"]:
                # Initialize session state for cost tracking
                if 'query_count' not in st.session_state:
                    st.session_state.query_count = 0
                if 'total_tokens_used' not in st.session_state:
                    st.session_state.total_tokens_used = 0
                if 'cost_by_model' not in st.session_state:
                    st.session_state.cost_by_model = {'haiku': 0, 'sonnet': 0, 'opus': 0}
                
                # Increment query count
                st.session_state.query_count += 1
                
                # Estimate tokens and cost (rough estimation)
                model_used = result.get('model_used', 'haiku')
                answer_length = len(result.get('answer', ''))
                query_length = len(query)
                
                # Rough token estimation (1 token ≈ 4 characters)
                estimated_tokens = (query_length + answer_length) // 4
                st.session_state.total_tokens_used += estimated_tokens
                
                # Cost calculation based on model
                cost_per_1k_tokens = {
                    'haiku': 0.00125,  # $1.25 per 1M tokens
                    'sonnet': 0.015,   # $15 per 1M tokens  
                    'opus': 0.075      # $75 per 1M tokens
                }
                
                # Ensure cost_by_model is initialized with all model keys
                if 'cost_by_model' not in st.session_state:
                    st.session_state.cost_by_model = {'haiku': 0, 'sonnet': 0, 'opus': 0}
                
                # Ensure the specific model key exists
                if model_used not in st.session_state.cost_by_model:
                    st.session_state.cost_by_model[model_used] = 0
                
                estimated_cost = (estimated_tokens / 1000) * cost_per_1k_tokens.get(model_used, 0.00125)
                st.session_state.cost_by_model[model_used] += estimated_cost
                
                # Save assistant response with metadata
                assistant_metadata = {
                    'model_used': model_used,
                    'documents_retrieved': len(result.get('documents', [])),
                    'cost': estimated_cost,
                    'routing_decision': result.get('routing_decision', {}),
                    'processing_time': time.time() - st.session_state.get('query_start_time', time.time())
                }
                # Fix links in the response before saving
                fixed_answer = fix_markdown_links(result['answer'])
                save_chat_message('assistant', fixed_answer, assistant_metadata)
                
                # Show success message
                st.success("✅ **Query processed successfully!**")
                
                
                # Store analytics data directly (synchronous)
                query_id = None
                response_id = None
                
                # Debug analytics conditions
                analytics_available = st.session_state.get('analytics_available', False)
                print(f"🔍 [DEBUG-2] Analytics available: {analytics_available}")
                print(f"🔍 [DEBUG-2] Analytics service: {analytics_service is not None}")
                print(f"🔍 [DEBUG-2] Analytics service type: {type(analytics_service)}")
                
                if analytics_available and analytics_service:
                    try:
                        print(f"🔍 [APP-2] About to track query: {query[:50]}...")
                        print(f"🔍 [APP-2] Analytics service available: {analytics_service is not None}")
                        print(f"🔍 [APP-2] Session ID: {st.session_state.get('current_session_id', 'default')}")
                        
                        # Calculate query processing time
                        query_processing_time = time.time() - st.session_state.get('query_start_time', time.time())
                        
                        # Track user query using the simplified integration with timing and model info
                        query_id = analytics_service.track_query(
                            session_id=st.session_state.get('current_session_id', 'default'),
                            query_text=query,
                            query_complexity=result.get('routing_decision', {}).get('complexity', 'simple'),
                            query_time_seconds=query_processing_time,
                            model_used=model_used
                        )
                        
                        print(f"🔍 [APP-2] Query tracking result: {query_id}")
                        
                        if query_id:
                            # Track AI response using the simplified integration
                            response_id = analytics_service.track_response(
                                query_id=query_id,
                                response_text=result['answer'],
                                model_used=model_used
                            )
                            
                            if response_id:
                                st.session_state.last_query_id = query_id
                                st.session_state.last_response_id = response_id
                                print(f"✅ [APP-2] Analytics tracking successful - Query ID: {query_id}, Response ID: {response_id}")
                            else:
                                print(f"❌ [APP-2] Response tracking failed")
                        else:
                            print(f"❌ [APP-2] Query tracking failed")
                            
                    except Exception as e:
                        print(f"❌ [APP-2] Analytics storage failed: {e}")
                        import traceback
                        print(f"❌ [APP-2] Traceback: {traceback.format_exc()}")
                else:
                    print(f"❌ [APP-2] Analytics not available - available: {st.session_state.get('analytics_available', False)}, service: {analytics_service is not None}")
                
                # Add processing message with insertion ID to the response
                if query_id:
                    processing_message = f"📊 **Query tracked successfully!** (ID: {query_id})"
                    if response_id:
                        processing_message += f" | Response ID: {response_id}"
                    st.info(processing_message)
                else:
                    st.warning("⚠️ Query tracking failed - check logs for details")
                
                # Clear processing state
                st.session_state.processing_query = False
                st.session_state.processing_step = 0
                
                # Clear the query input and enter_pressed flag after successful processing
                if 'query_input' in st.session_state:
                    del st.session_state.query_input
                if 'enter_pressed' in st.session_state:
                    del st.session_state.enter_pressed
                
                # Rerun to display the new message in chat history IMMEDIATELY
                st.rerun()
            else:
                # Save error message
                save_chat_message('assistant', f"❌ Error: {result['error']}")
                
                # Add debug entry for failed query
                if DEBUG_PANEL_AVAILABLE:
                    processing_time = time.time() - start_time
                    debug_panel.add_debug_entry(
                        query=query,
                        status="error",
                        duration=processing_time,
                        error=result.get('error', 'Unknown error'),
                        step_info="Query failed",
                        source_urls=[]
                    )
                
                st.rerun()
        else:
            st.error("❌ **System not ready!** Please check the admin dashboard for system status.")
    
    # Footer
    st.markdown("---")
    st.markdown("**Adobe Experience League Chatbot** - Powered by AWS Bedrock & Smart Routing")


def render_hybrid_demo_page():
    """Render the hybrid demo page with model comparison functionality."""
    # Check authentication
    if not check_hybrid_demo_access():
        return
    
    # Header with logout button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🔄 Hybrid AI Model Architecture Demo")
        st.markdown("**Compare Google Gemini and AWS Bedrock Claude models side-by-side**")
    with col2:
        if st.button("🚪 Logout", type="secondary", help="Logout from demo"):
            logout_hybrid_demo()
    
    # Initialize session state for hybrid demo
    if 'hybrid_model_provider' not in st.session_state:
        st.session_state.hybrid_model_provider = None
    if 'hybrid_config_manager' not in st.session_state:
        st.session_state.hybrid_config_manager = None
    if 'hybrid_query_router' not in st.session_state:
        st.session_state.hybrid_query_router = None
    if 'hybrid_comparison_ui' not in st.session_state:
        st.session_state.hybrid_comparison_ui = None
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key status
        st.subheader("🔑 API Keys")
        config_manager = HybridConfigManager()
        api_status = config_manager.validate_api_keys()
        
        # Debug information
        with st.expander("🔍 Debug Info", expanded=False):
            google_key = os.getenv('GOOGLE_API_KEY')
            aws_key = os.getenv('AWS_ACCESS_KEY_ID')
            st.write(f"Google API Key: {'✅ Set' if google_key else '❌ Not set'}")
            st.write(f"AWS Access Key: {'✅ Set' if aws_key else '❌ Not set'}")
            if google_key:
                st.write(f"Google Key (first 10 chars): {google_key[:10]}...")
            if aws_key:
                st.write(f"AWS Key (first 10 chars): {aws_key[:10]}...")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Google", "✅" if api_status['google_available'] else "❌")
        with col2:
            st.metric("AWS", "✅" if api_status['aws_available'] else "❌")
        
        if not api_status['at_least_one_available']:
            st.error("No API keys found. Please set GOOGLE_API_KEY or AWS credentials.")
            st.info("Set environment variables or add to .env file")
            return
        
        # Initialize components
        if st.button("🚀 Initialize Models"):
            with st.spinner("Initializing models..."):
                try:
                    # Initialize model provider
                    model_provider = ModelProvider()
                    st.session_state.hybrid_model_provider = model_provider
                    
                    # Initialize query router
                    query_router = QueryRouter(config_manager)
                    st.session_state.hybrid_query_router = query_router
                    
                    # Initialize comparison UI
                    comparison_ui = ComparisonUI(model_provider, query_router)
                    st.session_state.hybrid_comparison_ui = comparison_ui
                    
                    st.session_state.hybrid_config_manager = config_manager
                    
                    st.success("Models initialized successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Initialization failed: {e}")
        
        # Model status
        if st.session_state.hybrid_model_provider:
            st.subheader("🤖 Model Status")
            available_models = st.session_state.hybrid_model_provider.get_available_models()
            for model in available_models:
                st.success(f"✅ {model.title()}")
        
        # Configuration settings
        if st.session_state.hybrid_config_manager:
            st.subheader("⚙️ Settings")
            
            # Model preference
            preferred_model = st.selectbox(
                "Preferred Model:",
                ["auto", "gemini", "claude"],
                index=0,
                key="hybrid_preferred_model_selectbox"
            )
            
            # Cost vs Quality preference
            cost_vs_quality = st.slider(
                "Cost vs Quality:",
                min_value=0.0,
                max_value=1.0,
                value=0.5,
                help="0 = Cost sensitive, 1 = Quality focused",
                key="hybrid_cost_vs_quality_slider"
            )
            
            # Update configuration
            if st.button("💾 Save Settings"):
                st.session_state.hybrid_config_manager.update_user_preferences(
                    preferred_model=preferred_model,
                    cost_sensitivity=1.0 - cost_vs_quality
                )
                st.session_state.hybrid_config_manager.save_config()
                st.success("Settings saved!")
        
        # Model Links Section
        st.subheader("🔗 Model Links")
        
        # Google Gemini links
        with st.expander("🤖 Google Gemini", expanded=False):
            st.markdown("")
            st.markdown("**[Google AI Studio](https://makersuite.google.com/app/apikey)** - Get API key")
            st.markdown("**[Gemini Documentation](https://ai.google.dev/docs)** - Official docs")
            st.markdown("**[Gemini API Reference](https://ai.google.dev/api/rest)** - API reference")
            st.markdown("**[Gemini Pricing](https://ai.google.dev/pricing)** - Cost information")
        
        # AWS Bedrock Claude links
        with st.expander("🤖 AWS Bedrock Claude", expanded=False):
            st.markdown("")
            st.markdown("**[AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)** - Access Bedrock")
            st.markdown("**[Claude Documentation](https://docs.anthropic.com/claude)** - Official docs")
            st.markdown("**[Bedrock API Reference](https://docs.aws.amazon.com/bedrock/)** - API docs")
            st.markdown("**[Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)** - Cost information")
        
        # Adobe Experience League links
        with st.expander("📚 Adobe Experience League", expanded=False):
            st.markdown("")
            st.markdown("**[Adobe Analytics](https://experienceleague.adobe.com/docs/analytics/)** - Analytics docs")
            st.markdown("**[Customer Journey Analytics](https://experienceleague.adobe.com/docs/analytics-platform/)** - CJA docs")
            st.markdown("**[Adobe Experience Platform](https://experienceleague.adobe.com/docs/experience-platform/)** - AEP docs")
            st.markdown("**[Mobile SDK](https://experienceleague.adobe.com/docs/mobile/)** - Mobile docs")
    
    # Main content
    if not st.session_state.hybrid_model_provider:
        st.info("👆 Please initialize the models using the sidebar to get started.")
        
        # Show setup instructions
        with st.expander("📋 Setup Instructions", expanded=True):
            st.markdown("""
            ### Prerequisites
            
            1. **Google API Key** (for Gemini):
               - Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
               - Set environment variable: `GOOGLE_API_KEY=your_key_here`
            
            2. **AWS Credentials** (for Claude):
               - Configure AWS credentials for Bedrock access
               - Set environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
               - Or use AWS CLI: `aws configure`
            
            3. **Enable Claude Models in Bedrock**:
               - Go to [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
               - Navigate to "Model access" in the left sidebar
               - Request access to Claude models (Haiku, Sonnet, Opus)
            
            ### Usage
            
            1. **Initialize Models**: Click "🚀 Initialize Models" in the sidebar
            2. **Compare Models**: Use the "Compare Models" tab to test both models side-by-side
            3. **Smart Routing**: Use the "Smart Routing" tab to let the system choose the best model
            4. **Test Suite**: Use the "Test Suite" tab to run predefined test queries
            5. **Analytics**: Use the "Analytics" tab to view performance metrics
            """)
        return
    
    # Main interface
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🔄 Compare Models", "🧭 Smart Routing", "🧪 Test Suite", "📊 Analytics", "📝 Feedback", "🔄 Retraining"])
    
    with tab1:
        # Pass knowledge base info to comparison UI
        settings = get_cached_settings()
        aws_clients = get_cached_aws_clients(settings) if settings else None
        knowledge_base_id = settings.bedrock_knowledge_base_id if settings else None
        
        # Update comparison UI with KB info
        st.session_state.hybrid_comparison_ui.knowledge_base_id = knowledge_base_id
        st.session_state.hybrid_comparison_ui.aws_clients = aws_clients
        
        st.session_state.hybrid_comparison_ui.render_comparison_interface()
    
    with tab2:
        render_hybrid_smart_routing_interface()
    
    with tab3:
        render_hybrid_test_suite_interface()
    
    with tab4:
        render_hybrid_analytics_interface()
    
    with tab5:
        render_hybrid_feedback_interface()
    
    with tab6:
        render_hybrid_retraining_interface()


def main():
    """Main Streamlit application entry point with optimized initialization."""
    # Page selection - render immediately for fast LCP
    page_options = ["🏠 Main Chat", "ℹ️ About", "🔧 Admin Dashboard"]
    
    # Add hybrid demo if available
    if HYBRID_MODELS_AVAILABLE:
        page_options.append("🔄 Hybrid Demo")
    
    page = st.sidebar.selectbox(
        "Navigate to:",
        page_options,
        index=0
    )
    
    # Debug Mode Toggle in Sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔧 Debug Controls")
    
    debug_mode = st.sidebar.checkbox(
        "🔍 Debug Mode", 
        value=st.session_state.get('debug_mode', False),
        help="Enable debug mode for detailed query information and performance tracking"
    )
    st.session_state.debug_mode = debug_mode
    
    if debug_mode:
        st.sidebar.success("Debug Mode: ON")
        
        # Additional debug controls when debug mode is enabled
        st.sidebar.markdown("**Debug Options:**")
        
        # Query Enhancement Toggle in Sidebar
        if QUERY_ENHANCEMENT_AVAILABLE:
            query_enhancement_enabled = st.sidebar.checkbox(
                "🚀 Query Enhancement", 
                value=st.session_state.get('query_enhancement_enabled', True),
                help="Enable query enhancement for better document retrieval"
            )
            st.session_state.query_enhancement_enabled = query_enhancement_enabled
        
        # Smart Context Toggle in Sidebar
        if SMART_CONTEXT_AVAILABLE:
            smart_context_enabled = st.sidebar.checkbox(
                "🧠 Smart Context", 
                value=st.session_state.get('smart_context_enabled', True),
                help="Enable smart context management for cost optimization"
            )
            st.session_state.smart_context_enabled = smart_context_enabled
        
        # Debug panel controls
        if DEBUG_PANEL_AVAILABLE:
            st.sidebar.markdown("**Debug Panel:**")
            if st.sidebar.button("🔄 Refresh Debug Info"):
                st.rerun()
            
            if st.sidebar.button("🗑️ Clear Debug History"):
                if 'debug_history' in st.session_state:
                    st.session_state.debug_history = []
                if 'query_count' in st.session_state:
                    st.session_state.query_count = 0
                if 'total_queries' in st.session_state:
                    st.session_state.total_queries = 0
                if 'response_times' in st.session_state:
                    st.session_state.response_times = []
                if 'success_count' in st.session_state:
                    st.session_state.success_count = 0
                if 'error_count' in st.session_state:
                    st.session_state.error_count = 0
                if 'session_cost' in st.session_state:
                    st.session_state.session_cost = 0.0
                if 'cost_by_model' in st.session_state:
                    st.session_state.cost_by_model = {}
                if 'total_tokens_used' in st.session_state:
                    st.session_state.total_tokens_used = 0
                st.sidebar.success("Debug history cleared!")
                st.rerun()
    else:
        st.sidebar.info("Debug Mode: OFF")
    
    # Ultra-fast path for main chat - minimal initialization
    if page == "🏠 Main Chat":
        # Render main page immediately with minimal initialization
        render_main_page_minimal()
    
    elif page == "ℹ️ About":
        # Render About page - no initialization needed
        render_about_page()
    
    elif page == "🔄 Hybrid Demo":
        # Render Hybrid Demo - hybrid model comparison
        if not HYBRID_MODELS_AVAILABLE:
            st.error("❌ Hybrid model components not available. Please check your installation.")
            st.stop()
        render_hybrid_demo_page()
    
    else:  # Admin Dashboard - full initialization
        # Check admin access first
        if not check_admin_access():
            st.stop()
        
        # Load configuration with caching
        settings = get_cached_settings()
        config_error = None if settings else "Failed to load settings"
        
        # Initialize AWS clients with caching if configuration is loaded
        aws_clients = None
        aws_error = None
        kb_status = None
        kb_error = None
        smart_router = None
        model_test_results = None
        
        if settings:
            aws_clients = get_cached_aws_clients(settings)
            aws_error = None if aws_clients else "Failed to initialize AWS clients"
        
        # Initialize analytics service
        analytics_service = None
        if ANALYTICS_AVAILABLE:
            try:
                analytics_service = initialize_analytics_service()
                if analytics_service:
                    st.session_state.analytics_available = True
                    print("✅ Analytics service initialized successfully")
                else:
                    st.session_state.analytics_available = False
                    print("❌ Analytics service initialization returned None")
            except Exception as e:
                st.session_state.analytics_available = False
                print(f"Analytics service initialization failed: {e}")
        else:
            st.session_state.analytics_available = False
            print("❌ Analytics not available - ANALYTICS_AVAILABLE is False")
        
        # Tagging service removed for now
        
        if not config_error:
            # Initialize smart router
            haiku_only_mode = st.session_state.get('haiku_only_mode', False)
            smart_router = SmartRouter(haiku_only_mode=haiku_only_mode)
            
            # Test Knowledge Base connection if AWS clients are initialized
            if aws_clients and not aws_error:
                kb_status, kb_error = test_knowledge_base_connection(
                    settings.bedrock_knowledge_base_id,
                    aws_clients['bedrock_agent_client']
                )
                
                # Test model invocation if KB is working (only for admin dashboard)
                if kb_status and smart_router:
                    model_test_results = {}
                    current_haiku_only_mode = st.session_state.get('haiku_only_mode', smart_router.haiku_only_mode)
                    available_models = ["haiku"] if current_haiku_only_mode else ["haiku", "sonnet", "opus"]
                    for model_name in available_models:
                        if model_name in smart_router.models:
                            model_id = smart_router.models[model_name]
                            try:
                                success, message = test_model_invocation(
                                    model_id, 
                                    "Test query", 
                                    aws_clients['bedrock']
                                )
                                model_test_results[model_name] = {"success": success, "message": message}
                            except Exception as e:
                                model_test_results[model_name] = {"success": False, "message": f"Test failed: {str(e)}"}
                    
                    # Mark unavailable models as not tested
                    for model_name in smart_router.models:
                        if model_name not in available_models:
                            if current_haiku_only_mode and model_name != "haiku":
                                model_test_results[model_name] = {"success": False, "message": "Not tested - Haiku-only mode enabled"}
                            else:
                                model_test_results[model_name] = {"success": False, "message": "Not tested - model not accessible"}
        
        if settings is None:
            st.error("❌ Configuration not loaded. Please check your environment variables.")
            st.stop()
        render_admin_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, model_test_results, analytics_service)
        

if __name__ == "__main__":
    main()
