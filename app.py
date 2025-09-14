import streamlit as st
import os
import sys
import time
import logging
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from collections import OrderedDict
from typing import Dict, Any, Optional, List, Tuple

# Add project root and src to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

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
    page_title="Adobe Experience League Chatbot",
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

def retrieve_documents_from_kb(query: str, knowledge_base_id: str, bedrock_agent_client, max_results: int = 3):
    """Retrieve relevant documents from Knowledge Base."""
    try:
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
        return [], str(e)

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
        # Step 1: Retrieve documents from Knowledge Base
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
        
        # Step 3: Prepare context from retrieved documents
        context = ""
        if documents:
            context_parts = []
            for i, doc in enumerate(documents[:3], 1):  # Use top 3 documents
                content = doc.get('content', {}).get('text', '')
                if content:
                    context_parts.append(f"Document {i}: {content[:500]}...")
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
        # Step 1: Retrieve documents from Knowledge Base
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
        
        # Step 2: Smart routing - select appropriate model with fallback
        current_haiku_only_mode = st.session_state.get('haiku_only_mode', smart_router.haiku_only_mode)
        available_models = ["haiku"] if current_haiku_only_mode else ["haiku", "sonnet", "opus"]
        routing_decision = smart_router.select_available_model(query, documents, available_models)
        
        # Step 3: Prepare context from retrieved documents
        context = ""
        if documents:
            context_parts = []
            for i, doc in enumerate(documents[:3], 1):  # Use top 3 documents
                content = doc.get('content', {}).get('text', '')
                if content:
                    context_parts.append(f"Document {i}: {content[:500]}...")
            context = "\n\n".join(context_parts)
        
        # Step 4: Invoke selected model with streaming
        full_answer = ""
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

def render_admin_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, model_test_results, analytics_service=None):
    """Render the admin page with all technical details."""
    st.title("🔧 Admin Dashboard")
    st.markdown("**System Configuration, Status, and Analytics**")
    st.markdown("---")
    
    # Create tabs for different admin sections (optimized - reduced from 9 to 4 tabs)
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 System Status", 
        "⚙️ Settings", 
        "📊 Query Analytics",
        "🔍 Database Query"
    ])
    
    with tab1:
        st.header("📊 System Status Overview")
        
        # Overall system status
        current_haiku_only_mode = st.session_state.get('haiku_only_mode', smart_router.haiku_only_mode if smart_router else False)
        if not aws_error and kb_status and smart_router:
            if current_haiku_only_mode:
                st.success("🚀 **System Status: READY** - All components operational (HAIKU-ONLY MODE ACTIVE)")
            else:
                st.success("🚀 **System Status: READY** - All components operational (SMART ROUTING MODE)")
        elif not aws_error and smart_router:
            if current_haiku_only_mode:
                st.info("🔧 **System Status: PARTIAL** - Knowledge Base testing in progress (HAIKU-ONLY MODE ACTIVE)")
            else:
                st.info("🔧 **System Status: PARTIAL** - Knowledge Base testing in progress (SMART ROUTING MODE)")
        else:
            st.warning("⚠️ **System Status: SETUP** - System setup in progress")
        
        # Component status grid
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if aws_error:
                st.error("❌ **AWS**\nConnection Failed")
            elif aws_clients:
                st.success("✅ **AWS**\nConnected")
            else:
                st.warning("⚠️ **AWS**\nNot Initialized")
        
        with col2:
            if kb_error:
                st.error("❌ **Knowledge Base**\nError")
            elif kb_status:
                st.success("✅ **Knowledge Base**\nReady")
            else:
                st.info("ℹ️ **Knowledge Base**\nPending")
        
        with col3:
            if smart_router:
                st.success("✅ **Smart Router**\nInitialized")
            else:
                st.warning("⚠️ **Smart Router**\nNot Initialized")
        
        with col4:
            if model_test_results:
                tested_models = sum(1 for result in model_test_results.values() if result["success"])
                total_models = len(model_test_results)
                st.success(f"✅ **Models**\n{tested_models}/{total_models} Working")
            else:
                st.info("ℹ️ **Models**\nTesting Pending")
        
        # Account Information section (merged from AWS Details tab)
        st.markdown("---")
        st.subheader("🏢 Account Information")
        
        if aws_error:
            st.error(f"❌ **AWS Error:** {aws_error}")
        elif aws_clients:
            st.success("✅ **AWS clients initialized successfully**")
            
            # Account details in organized sections
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Account ID:** `{aws_clients['account_id']}`")
                st.write(f"**User ARN:** `{aws_clients['user_arn']}`")
                st.write(f"**Region:** `{settings.aws_default_region}`")
            
            with col2:
                st.write(f"**S3 Bucket:** `{aws_clients['s3_status']}`")
                st.write("**Bedrock Client:** ✅ Initialized")
                st.write("**STS Client:** ✅ Initialized")
        else:
            st.warning("⚠️ AWS clients not initialized")
    
    with tab2:
        st.header("⚙️ Settings & Configuration")
        
        if aws_error:
            st.error(f"❌ **Configuration Error:** {aws_error}")
        else:
            st.success("✅ **Configuration loaded successfully**")
            
            # Configuration details in a nice format
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔧 Core Settings")
                st.write(f"**AWS Region:** `{settings.aws_default_region}`")
                st.write(f"**S3 Bucket:** `{settings.aws_s3_bucket}`")
                st.write(f"**Bedrock Model:** `{settings.bedrock_model_id}`")
                st.write(f"**Knowledge Base ID:** `{settings.bedrock_knowledge_base_id}`")
            
            with col2:
                st.subheader("🔑 Authentication")
                st.write(f"**AWS Access Key:** `{settings.aws_access_key_id[:8]}...`")
                st.write(f"**AWS Secret Key:** `{settings.aws_secret_access_key[:8]}...`")
                st.write(f"**Bedrock Region:** `{settings.bedrock_region}`")
                st.write(f"**Embedding Model:** `{settings.bedrock_embedding_model_id}`")
            
            # Debug mode toggle
            st.markdown("---")
            st.subheader("🔧 Debug Settings")
            debug_mode = st.checkbox(
                "Enable Debug Mode", 
                value=st.session_state.get('debug_mode', False),
                help="Show debug information in the main chat interface"
            )
            st.session_state.debug_mode = debug_mode
            
            if debug_mode:
                st.info("🔍 Debug mode enabled - Debug information will be shown in the main chat interface")
            else:
                st.info("🔍 Debug mode disabled - Clean interface without debug information")
            
            # Enable Haiku Only Mode (merged from Performance tab)
            st.markdown("---")
            st.subheader("🤖 Model Configuration")
            
            if smart_router:
                st.success("✅ **Smart Router: Initialized**")
                
                # Haiku-only mode indicator
                if smart_router.haiku_only_mode:
                    st.warning("⚠️ **HAIKU-ONLY MODE ACTIVE** - All queries will use Claude 3 Haiku for cost optimization (92% cost reduction)")
                    st.info("💡 This mode is enabled for one week testing. Monitor response quality and user feedback.")
                else:
                    st.info("ℹ️ **Normal Mode** - Smart routing based on query complexity and context")
                
                # Mode toggle section
                st.markdown("---")
                st.subheader("🔄 Dynamic Mode Control")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write("**Switch between modes based on your cost management needs:**")
                    st.write("• **Smart Routing**: Optimal quality with balanced costs")
                    st.write("• **Haiku-Only**: Maximum cost savings with good quality")
                
                with col2:
                    # Toggle button for Haiku-only mode
                    current_mode = smart_router.haiku_only_mode
                    new_mode = st.toggle(
                        "Enable Haiku-Only Mode",
                        value=current_mode,
                        help="Toggle to enable/disable Haiku-only mode for cost optimization"
                    )
                    
                    # Update mode if changed
                    if new_mode != current_mode:
                        smart_router.haiku_only_mode = new_mode
                        st.session_state.haiku_only_mode = new_mode
                        st.rerun()
                
                # Mode change confirmation
                if new_mode != current_mode:
                    if new_mode:
                        st.success("🔄 **Switched to Haiku-Only Mode** - All queries will now use Claude 3 Haiku")
                    else:
                        st.success("🔄 **Switched to Smart Routing Mode** - Models will be selected based on query analysis")
                
                # Cost impact analysis
                st.markdown("---")
                st.subheader("💰 Cost Impact Analysis")
                
                cost_col1, cost_col2 = st.columns(2)
                
                with cost_col1:
                    st.write("**Current Mode Cost (per 1M tokens):**")
                    if smart_router.haiku_only_mode:
                        st.metric("Haiku Only", "$1.50", "92% savings vs Sonnet")
                        st.caption("• Input: $0.25 per 1M tokens")
                        st.caption("• Output: $1.25 per 1M tokens")
                    else:
                        st.metric("Smart Routing", "Variable", "Optimized selection")
                        st.caption("• Haiku: $1.50 per 1M tokens")
                        st.caption("• Sonnet: $18.00 per 1M tokens")
                        st.caption("• Opus: $75.00 per 1M tokens")
                
                with cost_col2:
                    st.write("**Estimated Monthly Savings:**")
                    if smart_router.haiku_only_mode:
                        st.metric("Cost Reduction", "80-90%", "vs Smart Routing")
                        st.caption("• Typical usage: $15-30/month")
                        st.caption("• High usage: $50-100/month")
                    else:
                        st.metric("Balanced Cost", "Optimized", "Quality + Efficiency")
                        st.caption("• Typical usage: $50-150/month")
                        st.caption("• High usage: $200-400/month")
            else:
                st.warning("⚠️ Smart Router not initialized")
    
    with tab3:
        st.header("📊 Query Analytics Dashboard")
        
        # Check if analytics service is available
        if st.session_state.get('analytics_available', False):
            st.success("✅ **Analytics Service: Available**")
            
            # Render the analytics dashboard
            try:
                analytics_service.render_analytics_dashboard()
            except Exception as e:
                st.error(f"❌ **Analytics Dashboard Error:** {str(e)}")
                st.info("💡 **Troubleshooting:** Check database connection and configuration")
        else:
            st.warning("⚠️ **Analytics Service: Not Available**")
            st.info("""
            **To enable query analytics:**
            1. Set up a database (PostgreSQL, MySQL, or SQLite)
            2. Configure database connection in environment variables
            3. Run database migration script
            4. Restart the application
            
            **For local testing with SQLite:**
            ```bash
            export USE_SQLITE=true
            export SQLITE_DATABASE=analytics.db
            ```
            """)
            
            # Show database configuration status
            st.subheader("🔧 Database Configuration Status")
            try:
                from src.utils.database_config import get_database_info
                db_info = get_database_info()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Database Type:** {db_info.get('type', 'Unknown')}")
                    st.write(f"**Host:** {db_info.get('host', 'Unknown')}")
                    st.write(f"**Port:** {db_info.get('port', 'Unknown')}")
                
                with col2:
                    st.write(f"**Database:** {db_info.get('database', 'Unknown')}")
                    st.write(f"**Username:** {db_info.get('username', 'Unknown')}")
                    st.write(f"**Railway:** {db_info.get('is_railway', False)}")
                
            except Exception as e:
                st.error(f"Database configuration error: {e}")
    
    with tab4:
        st.header("🔍 Database Query Interface")
        
        # Check if database query interface is available
        if DATABASE_QUERY_AVAILABLE:
            st.success("✅ **Database Query Interface: Available**")
            
            # Render the database query interface
            try:
                render_database_query_interface()
            except Exception as e:
                st.error(f"❌ **Database Query Interface Error:** {str(e)}")
                st.info("💡 **Troubleshooting:** Check database connection and configuration")
        else:
            st.warning("⚠️ **Database Query Interface: Not Available**")
            st.info("""
            **To enable database query interface:**
            1. Ensure database connection is properly configured
            2. Check that all required dependencies are installed
            3. Verify database tables exist and are accessible
            
            **Required dependencies:**
            - psycopg2-binary (for PostgreSQL)
            - pandas (for data display)
            - streamlit (for UI components)
            """)

def display_aws_cost_data(cost_data):
    """Display AWS cost data in a formatted way."""
    try:
        results = cost_data.get('ResultsByTime', [])
        
        if not results:
            st.info("No cost data available for the selected period.")
            return
        
        # Calculate total costs
        total_cost = 0
        service_costs = {}
        
        for result in results:
            time_period = result.get('TimePeriod', {})
            groups = result.get('Groups', [])
            
            for group in groups:
                service = group.get('Keys', ['Unknown'])[0]
                metrics = group.get('Metrics', {})
                cost = float(metrics.get('BlendedCost', {}).get('Amount', 0))
                
                if service not in service_costs:
                    service_costs[service] = 0
                service_costs[service] += cost
                total_cost += cost
        
        # Display total cost
        st.metric("Total AWS Cost", f"${total_cost:.2f}")
        
        # Display service breakdown
        if service_costs:
            st.write("**Cost by Service:**")
            for service, cost in sorted(service_costs.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / total_cost) * 100 if total_cost > 0 else 0
                st.write(f"• **{service}:** ${cost:.2f} ({percentage:.1f}%)")
        
        # Create a simple chart if pandas is available
        try:
            import pandas as pd
            df = pd.DataFrame(list(service_costs.items()), columns=['Service', 'Cost'])
            df = df[df['Cost'] > 0]  # Only show services with costs
            if not df.empty:
                st.bar_chart(df.set_index('Service'))
        except ImportError:
            st.info("Install pandas for cost visualization charts")
            
    except Exception as e:
        st.error(f"Error displaying cost data: {str(e)}")

def display_bedrock_cost_data(cost_data):
    """Display Bedrock-specific cost data."""
    try:
        results = cost_data.get('ResultsByTime', [])
        
        if not results:
            st.info("No Bedrock cost data available for the selected period.")
            return
        
        total_cost = 0
        usage_costs = {}
        
        for result in results:
            groups = result.get('Groups', [])
            
            for group in groups:
                usage_type = group.get('Keys', ['Unknown'])[0]
                metrics = group.get('Metrics', {})
                cost = float(metrics.get('BlendedCost', {}).get('Amount', 0))
                
                if usage_type not in usage_costs:
                    usage_costs[usage_type] = 0
                usage_costs[usage_type] += cost
                total_cost += cost
        
        # Display total Bedrock cost
        st.metric("Total Bedrock Cost", f"${total_cost:.2f}")
        
        # Display usage type breakdown
        if usage_costs:
            st.write("**Cost by Usage Type:**")
            for usage_type, cost in sorted(usage_costs.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / total_cost) * 100 if total_cost > 0 else 0
                st.write(f"• **{usage_type}:** ${cost:.2f} ({percentage:.1f}%)")
        
    except Exception as e:
        st.error(f"Error displaying Bedrock cost data: {str(e)}")

def display_s3_cost_data(cost_data):
    """Display S3-specific cost data."""
    try:
        results = cost_data.get('ResultsByTime', [])
        
        if not results:
            st.info("No S3 cost data available for the selected period.")
            return
        
        total_cost = 0
        usage_costs = {}
        
        for result in results:
            groups = result.get('Groups', [])
            
            for group in groups:
                usage_type = group.get('Keys', ['Unknown'])[0]
                metrics = group.get('Metrics', {})
                cost = float(metrics.get('BlendedCost', {}).get('Amount', 0))
                
                if usage_type not in usage_costs:
                    usage_costs[usage_type] = 0
                usage_costs[usage_type] += cost
                total_cost += cost
        
        # Display total S3 cost
        st.metric("Total S3 Cost", f"${total_cost:.2f}")
        
        # Display usage type breakdown
        if usage_costs:
            st.write("**Cost by Usage Type:**")
            for usage_type, cost in sorted(usage_costs.items(), key=lambda x: x[1], reverse=True):
                percentage = (cost / total_cost) * 100 if total_cost > 0 else 0
                st.write(f"• **{usage_type}:** ${cost:.2f} ({percentage:.1f}%)")
        
    except Exception as e:
        st.error(f"Error displaying S3 cost data: {str(e)}")

def initialize_chat_history():
    """Initialize chat history in session state."""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = f"session_{int(time.time())}"
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
    st.title("📊 Adobe Experience League Chatbot")
    st.markdown("**Intelligent RAG Assistant for Adobe Analytics Documentation**")
    
    # No status messages to prevent CLS (matching optimized app)
    
    # Main content area
    st.header("💬 Ask Your Question")
    st.markdown("Ask any question about Adobe Analytics, Customer Journey Analytics, or related topics.")
    
    # Query input
    query = st.text_input(
        "Enter your question:",
        placeholder="e.g., How do I set up Adobe Analytics tracking?",
        key="query_input",
        help="Type your question about Adobe Analytics, CJA, or related topics"
    )
    
    # Submit button
    submit_button = st.button("🚀 Ask Question", type="primary", use_container_width=True, key="ask_question_button")
    
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
                        
                        # Show timing info if available (simplified)
                        if 'metadata' in message and message['metadata']:
                            metadata = message['metadata']
                            if 'processing_time' in metadata:
                                st.caption(f"⏱️ Processing Time: {metadata['processing_time']:.2f}s | 🤖 Model: {metadata.get('model_used', 'Unknown')} | 📄 Documents: {metadata.get('documents_retrieved', 0)}")
                        
                        # Skip both messages since we've displayed them
                        i += 2
                    else:
                        # Orphaned assistant message, display it
                        st.markdown(f"**🤖 Assistant:** {message['content']}")
                        
                        # Show timing info if available
                        if 'metadata' in message and message['metadata']:
                            metadata = message['metadata']
                            if 'processing_time' in metadata:
                                st.caption(f"⏱️ Processing Time: {metadata['processing_time']:.2f}s | 🤖 Model: {metadata.get('model_used', 'Unknown')} | 📄 Documents: {metadata.get('documents_retrieved', 0)}")
                        
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
    
    # Process query when submitted (lazy initialization)
    if submit_button:
        # Basic validation only (no UI messages to prevent CLS)
        if query and len(query) >= 3:
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
                        
                        # Process the query
                        process_query_with_full_initialization(query, settings, aws_clients, smart_router, analytics_service)

def process_query_with_full_initialization(query, settings, aws_clients, smart_router, analytics_service):
    """Process query with full initialization (called only when needed)."""
    # Save user message
    save_chat_message('user', query)
    
    # Track query start time
    st.session_state.query_start_time = time.time()
    
    # Process query with streaming UI
    start_time = time.time()
    
    # Reserve space for result messages to prevent CLS
    result_container = st.container()
    with result_container:
        # Initialize session state for cost tracking
        if 'query_count' not in st.session_state:
            st.session_state.query_count = 0
        if 'total_tokens_used' not in st.session_state:
            st.session_state.total_tokens_used = 0
        if 'cost_by_model' not in st.session_state:
            st.session_state.cost_by_model = {'haiku': 0, 'sonnet': 0, 'opus': 0}
        
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
            
            estimated_cost = (estimated_tokens / 1000) * cost_per_1k_tokens.get(model_used, 0.00125)
            st.session_state.cost_by_model[model_used] += estimated_cost
            
            # Save assistant response with metadata
            assistant_metadata = {
                'model_used': model_used,
                'documents_retrieved': len(documents),
                'cost': estimated_cost,
                'routing_decision': routing_decision,
                'processing_time': time.time() - st.session_state.get('query_start_time', time.time())
            }
            save_chat_message('assistant', full_response, assistant_metadata)
            
            # Clear the streaming response placeholder since it will be shown in chat history
            response_placeholder.empty()
            
            # Show success message with timing info
            st.success(f"✅ **Query processed successfully in {processing_time:.2f} seconds!**")
            
            # Rerun to display the new message in chat history IMMEDIATELY
            st.rerun()
            
            # Store analytics data in background (non-blocking)
            def store_analytics_background():
                if st.session_state.get('analytics_available', False) and analytics_service:
                    try:
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
                                
                    except Exception as e:
                        print(f"Analytics storage failed: {e}")
            
            # Start analytics processing in background thread
            analytics_thread = threading.Thread(target=store_analytics_background)
            analytics_thread.daemon = True
            analytics_thread.start()

def render_main_page(settings, aws_clients, aws_error, kb_status, kb_error, smart_router, analytics_service=None):
    """Render the clean main page focused on user experience."""
    # Initialize chat history
    initialize_chat_history()
    
    # Header section
    st.title("📊 Adobe Experience League Chatbot")
    st.markdown("**Intelligent RAG Assistant for Adobe Analytics Documentation**")
    
    # No status messages to prevent CLS (matching optimized app)
    
    # Main content area
    st.header("💬 Ask Your Question")
    st.markdown("Ask any question about Adobe Analytics, Customer Journey Analytics, or related topics.")
    
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
    
    # Create the text input
    query = st.text_input(
        "Enter your question:",
        value=st.session_state.get('query_input', ''),
        placeholder="e.g., How do I create custom events in Adobe Analytics?",
        key="query_input",
        help="Ask any question about Adobe Analytics, Customer Journey Analytics, or related topics."
    )
    
    # Submit button below the input
    submit_button = st.button("🚀 Ask Question", type="primary", use_container_width=True, key="ask_question_button")
    
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
                    
                    # Show timing info if available (simplified)
                    if 'metadata' in message and message['metadata']:
                        metadata = message['metadata']
                        if 'processing_time' in metadata:
                            st.caption(f"⏱️ Processing Time: {metadata['processing_time']:.2f}s | 🤖 Model: {metadata.get('model_used', 'Unknown')} | 📄 Documents: {metadata.get('documents_retrieved', 0)}")
                    
                    # Skip both messages since we've displayed them
                    i += 2
                else:
                    # Orphaned assistant message, display it
                    st.markdown(f"**🤖 Assistant:** {message['content']}")
                    
                    # Show timing info if available
                    if 'metadata' in message and message['metadata']:
                        metadata = message['metadata']
                        if 'processing_time' in metadata:
                            st.caption(f"⏱️ Processing Time: {metadata['processing_time']:.2f}s | 🤖 Model: {metadata.get('model_used', 'Unknown')} | 📄 Documents: {metadata.get('documents_retrieved', 0)}")
                    
                    i += 1
            else:
                # This is an orphaned user message, display it
                st.markdown(f"**👤 You:** {message['content']}")
                i += 1
            
            st.markdown("---")
    
    # Process query when submitted
    if submit_button:
        # Clean and validate query
        query = query.strip() if query else ""
        
        # Debug information (can be enabled for troubleshooting)
        if st.session_state.get('debug_mode', False):
            with st.expander("🔍 Debug Info", expanded=False):
                st.write(f"**Query value:** '{query}'")
                st.write(f"**Query length:** {len(query)}")
                st.write(f"**Session state query_input:** '{st.session_state.get('query_input', 'NOT_SET')}'")
                st.write(f"**Submit button clicked:** {submit_button}")
                st.write(f"**AWS clients available:** {aws_clients is not None}")
                st.write(f"**AWS error:** {aws_error}")
                st.write(f"**KB status:** {kb_status}")
                st.write(f"**Smart router:** {smart_router is not None}")
        
        if query and len(query) >= 3 and aws_clients and not aws_error and kb_status and smart_router:
            # Save user message
            save_chat_message('user', query)
            
            # Track query start time
            st.session_state.query_start_time = time.time()
            
            # Show processing status with timer
            processing_container = st.container()
            with processing_container:
                col1, col2 = st.columns([3, 1])
                with col1:
                    spinner_placeholder = st.empty()
                with col2:
                    timer_placeholder = st.empty()
            
            # Start timer display
            start_time = time.time()
            timer_placeholder.metric("⏱️ Processing Time", "0.0s")
            
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
            
            # Calculate and display final processing time
            processing_time = time.time() - start_time
            timer_placeholder.metric("⏱️ Processing Time", f"{processing_time:.2f}s")
            
            # Update progress bar and status
            progress_bar.progress(100)
            status_text.success("✅ Processing complete!")
            
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
                save_chat_message('assistant', result['answer'], assistant_metadata)
                
                # Show success message with timing info (matching optimized app)
                st.success(f"✅ **Query processed successfully in {processing_time:.2f} seconds!**")
                
                
                # Store analytics data in background (non-blocking)
                def store_analytics_background():
                    if st.session_state.get('analytics_available', False) and analytics_service:
                        try:
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
                                    
                        except Exception as e:
                            print(f"Analytics storage failed: {e}")
                
                # Start analytics processing in background thread
                import threading
                analytics_thread = threading.Thread(target=store_analytics_background)
                analytics_thread.daemon = True
                analytics_thread.start()
                
                # Rerun to display the new message in chat history IMMEDIATELY
                st.rerun()
            else:
                # Save error message
                save_chat_message('assistant', f"❌ Error: {result['error']}")
                st.rerun()
        else:
            st.error("❌ **System not ready!** Please check the admin dashboard for system status.")
    
    # Footer
    st.markdown("---")
    st.markdown("**Adobe Experience League Chatbot** - Powered by AWS Bedrock & Smart Routing")


def main():
    """Main Streamlit application entry point with optimized initialization."""
    # Page selection - render immediately for fast LCP
    page = st.sidebar.selectbox(
        "Navigate to:",
        ["🏠 Main Chat", "🔧 Admin Dashboard"],
        index=0
    )
    
    # Ultra-fast path for main chat - minimal initialization
    if page == "🏠 Main Chat":
        # Render main page immediately with minimal initialization
        render_main_page_minimal()
    
    else:  # Admin Dashboard - full initialization
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
