"""
Complete optimized Streamlit application with end-to-end functionality
"""

import streamlit as st
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
import threading
from collections import OrderedDict
import hashlib
import json
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, "src"))

# Import existing modules
from config.settings import Settings
from src.utils.bedrock_client import BedrockClient
from src.integrations.streamlit_analytics_simple import SimpleAnalyticsService, StreamlitAnalyticsIntegration

logger = logging.getLogger(__name__)

# Simple LRU Cache implementation
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

# Simple performance monitor
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

# Smart Router implementation (simplified)
class SmartRouter:
    """Smart router for selecting appropriate Bedrock models based on query analysis."""
    
    def __init__(self, haiku_only_mode=False):
        self.models = {
            "haiku": "us.anthropic.claude-3-haiku-20240307-v1:0",
            "sonnet": "us.anthropic.claude-3-sonnet-20240229-v1:0",
            "opus": "us.anthropic.claude-3-opus-20240229-v1:0"
        }
        self.haiku_only_mode = haiku_only_mode
        self.high_relevance_threshold = 0.8
        self.medium_relevance_threshold = 0.6
    
    def select_available_model(self, query: str, documents: List[Dict], available_models: List[str]) -> Dict[str, Any]:
        """Select the best model based on query complexity and document relevance."""
        try:
            # Simple heuristic: use haiku for short queries, sonnet for complex ones
            query_length = len(query.split())
            
            if self.haiku_only_mode or "haiku" in available_models:
                selected_model = "haiku"
                model_id = self.models["haiku"]
            elif query_length < 10 and "haiku" in available_models:
                selected_model = "haiku"
                model_id = self.models["haiku"]
            elif "sonnet" in available_models:
                selected_model = "sonnet"
                model_id = self.models["sonnet"]
            else:
                selected_model = "haiku"
                model_id = self.models["haiku"]
            
            return {
                "model_id": model_id,
                "model_name": selected_model,
                "complexity": "simple" if query_length < 10 else "complex",
                "reasoning": f"Selected {selected_model} based on query length ({query_length} words)"
            }
        except Exception as e:
            # Fallback to haiku
            return {
                "model_id": self.models["haiku"],
                "model_name": "haiku",
                "complexity": "simple",
                "reasoning": f"Fallback to haiku due to error: {str(e)}"
            }

# Helper functions for query processing
def retrieve_documents_from_kb(query: str, knowledge_base_id: str, bedrock_agent_client, max_results: int = 3) -> Tuple[List[Dict], Optional[str]]:
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

def invoke_bedrock_model(model_id: str, query: str, bedrock_client, context: str = "") -> Tuple[str, Optional[str]]:
    """Invoke Bedrock model with proper request format based on model type."""
    try:
        # Use the BedrockClient's generate_text method
        prompt = f"{context}\n\nQuery: {query}" if context else query
        
        # Get region from bedrock_client or use default
        region = getattr(bedrock_client, 'region', 'us-east-1')
        
        # Create a temporary BedrockClient with the specific model_id
        temp_client = BedrockClient(model_id=model_id, region=region)
        
        # Generate text using the appropriate method
        answer = temp_client.generate_text(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7,
            top_p=0.9
        )
        
        return answer, None
            
    except Exception as e:
        return "", str(e)

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
        available_models = ["haiku"] if smart_router.haiku_only_mode else ["haiku", "sonnet", "opus"]
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
                "model_used": routing_decision.get('model_name', routing_decision.get('model', 'unknown'))
            }
        
        return {
            "success": True,
            "error": None,
            "documents": documents,
            "routing_decision": routing_decision,
            "answer": answer,
            "model_used": routing_decision.get('model_name', routing_decision.get('model', 'unknown'))
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

# Global instances
query_cache = SimpleLRUCache(max_size=500, default_ttl=600)
performance_monitor = SimplePerformanceMonitor()

class OptimizedStreamlitApp:
    """Complete optimized Streamlit application with end-to-end functionality"""
    
    def __init__(self):
        self.settings = None
        self.aws_clients = None
        self.smart_router = None
        self.analytics_service = None
        
        # Initialize components
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize application components with caching"""
        try:
            # Get settings with caching
            self.settings = self._get_cached_settings()
            
            if self.settings:
                # Initialize AWS clients with caching
                self.aws_clients = self._get_cached_aws_clients()
                
                # Initialize smart router with caching
                self.smart_router = self._get_cached_smart_router()
                
                # Initialize analytics service
                self.analytics_service = self._get_cached_analytics_service()
            
            logger.info("✅ Application components initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize components: {e}")
    
    def _get_cached_settings(self):
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
    
    def _get_cached_aws_clients(self):
        """Get AWS clients with caching"""
        cache_key = "aws_clients"
        cached = query_cache.get(cache_key)
        if cached:
            return cached
        
        if not self.settings:
            return None
        
        try:
            # Import AWS utilities
            from src.utils.aws_utils import (
                get_s3_client, get_sts_client, get_bedrock_agent_client, get_cost_explorer_client
            )
            
            # Initialize all AWS clients like in the main app
            s3_client = get_s3_client(self.settings.aws_default_region)
            sts_client = get_sts_client(self.settings.aws_default_region)
            bedrock_client = BedrockClient(
                model_id=self.settings.bedrock_model_id,
                region=self.settings.bedrock_region
            )
            bedrock_agent_client = get_bedrock_agent_client(self.settings.bedrock_region)
            cost_explorer_client = get_cost_explorer_client(self.settings.aws_default_region)
            
            clients = {
                "s3": s3_client,
                "sts": sts_client,
                "bedrock": bedrock_client,
                "bedrock_agent_client": bedrock_agent_client,
                "cost_explorer": cost_explorer_client
            }
            query_cache.set(cache_key, clients, ttl=1800)  # 30 minutes
            return clients
        except Exception as e:
            logger.error(f"❌ Failed to initialize AWS clients: {e}")
            return None
    
    def _get_cached_smart_router(self):
        """Get smart router with caching"""
        cache_key = "smart_router"
        cached = query_cache.get(cache_key)
        if cached:
            return cached
        
        try:
            router = SmartRouter(haiku_only_mode=False)
            query_cache.set(cache_key, router, ttl=1800)  # 30 minutes
            return router
        except Exception as e:
            logger.error(f"❌ Failed to initialize smart router: {e}")
            return None
    
    def _get_cached_analytics_service(self):
        """Get analytics service with caching"""
        cache_key = "analytics_service"
        cached = query_cache.get(cache_key)
        if cached:
            return cached
        
        if not self.settings:
            return None
        
        try:
            analytics_service = SimpleAnalyticsService(
                database_url=self.settings.database_url
            )
            service = StreamlitAnalyticsIntegration(analytics_service)
            query_cache.set(cache_key, service, ttl=1800)  # 30 minutes
            return service
        except Exception as e:
            logger.error(f"❌ Failed to initialize analytics service: {e}")
            return None
    
    def process_query_optimized(self, query: str, user_id: str = "anonymous") -> Dict[str, Any]:
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
            if not self.smart_router or not self.aws_clients:
                raise Exception("Smart router or AWS clients not available")
            
            result = process_query_with_smart_routing(
                query,
                self.settings.bedrock_knowledge_base_id,
                self.smart_router,
                self.aws_clients
            )
            
            # Cache the result
            query_cache.set(cache_key, result, ttl=600)  # 10 minutes
            
            duration = performance_monitor.finish_operation(operation_id)
            logger.info(f"✅ Query processed in {duration:.3f}s")
            
            return result
            
        except Exception as e:
            performance_monitor.finish_operation(operation_id)
            logger.error(f"❌ Query processing failed: {e}")
            return {"success": False, "error": str(e)}
    
    def render_optimized_chat_interface(self):
        """Render optimized chat interface with streaming"""
        st.title("🚀 Optimized Adobe Analytics Chatbot")
        
        # Performance info
        with st.expander("📊 Performance Info", expanded=False):
            cache_stats = {
                'size': len(query_cache.cache),
                'max_size': query_cache.max_size
            }
            perf_stats = performance_monitor.get_stats()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Cache Size", f"{cache_stats['size']}/{cache_stats['max_size']}")
                st.metric("Cache Hit Rate", "N/A")  # Would need more complex tracking
            
            with col2:
                if 'query_processing' in perf_stats:
                    st.metric("Avg Query Time", f"{perf_stats['query_processing']['avg_duration']:.2f}s")
                    st.metric("Total Queries", perf_stats['query_processing']['count'])
        
        # System status
        st.subheader("🔧 System Status")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Settings", "✅" if self.settings else "❌")
        with col2:
            st.metric("AWS Clients", "✅" if self.aws_clients else "❌")
        with col3:
            st.metric("Smart Router", "✅" if self.smart_router else "❌")
        with col4:
            st.metric("Analytics", "✅" if self.analytics_service else "❌")
        
        # Initialize session state
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'user_id' not in st.session_state:
            st.session_state.user_id = f"user_{int(time.time())}"
        
        # Chat history
        st.subheader("💬 Chat History")
        chat_container = st.container()
        
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                if message['role'] == 'user':
                    st.markdown(f"**👤 You:** {message['content']}")
                else:
                    # Display response with metadata
                    st.markdown(f"**🤖 Assistant:** {message['content']}")
                    
                    # Show timing info if available
                    if 'metadata' in message and message['metadata']:
                        metadata = message['metadata']
                        if 'processing_time' in metadata:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.caption(f"⏱️ **Processing Time:** {metadata['processing_time']:.2f}s")
                            with col2:
                                st.caption(f"🤖 **Model:** {metadata.get('model_used', 'Unknown')}")
                            with col3:
                                st.caption(f"📄 **Documents:** {metadata.get('documents_found', 0)}")
                    
                    if 'metadata' in message:
                        with st.expander("🔍 Response Details", expanded=False):
                            st.json(message['metadata'])
        
        # Query input
        st.subheader("❓ Ask a Question")
        with st.form("query_form"):
            query = st.text_area(
                "Ask a question about Adobe Analytics:",
                placeholder="e.g., How do I implement Adobe Analytics on my website?",
                height=100
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                submit_button = st.form_submit_button("🚀 Ask", use_container_width=True)
            
            with col2:
                clear_button = st.form_submit_button("🗑️ Clear", use_container_width=True)
            
            with col3:
                cache_button = st.form_submit_button("💾 Clear Cache", use_container_width=True)
        
        # Handle form submission
        if submit_button and query:
            self._handle_query_submission(query)
        
        if clear_button:
            st.session_state.chat_history = []
            st.rerun()
        
        if cache_button:
            query_cache.clear()
            st.success("✅ Cache cleared!")
            st.rerun()
    
    def _handle_query_submission(self, query: str):
        """Handle query submission with performance monitoring"""
        # Add user message
        st.session_state.chat_history.append({
            'role': 'user',
            'content': query,
            'timestamp': time.time()
        })
        
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
            with st.spinner("🤔 Processing your question..."):
                # Process query with performance monitoring
                result = self.process_query_optimized(query, st.session_state.user_id)
        
        # Calculate and display final processing time
        processing_time = time.time() - start_time
        timer_placeholder.metric("⏱️ Processing Time", f"{processing_time:.2f}s")
        
        # Update progress bar and status
        progress_bar.progress(100)
        status_text.success("✅ Processing complete!")
            
        if result.get("success"):
            # Add AI response with metadata
            response_data = {
                'role': 'assistant',
                'content': result.get("answer", "I couldn't generate a response."),
                'timestamp': time.time(),
                'metadata': {
                        'model_used': result.get("model_used"),
                        'routing_decision': result.get("routing_decision"),
                        'documents_found': len(result.get("documents", [])),
                        'processing_time': processing_time,
                        'success': True
                    }
                }
            
            st.session_state.chat_history.append(response_data)
            
            # Show success message with timing info
            st.success(f"✅ **Query processed successfully in {processing_time:.2f} seconds!**")
            
            # Show additional timing info
            with st.expander("⏱️ Performance Details", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Processing Time", f"{processing_time:.2f}s")
                with col2:
                    st.metric("Model Used", result.get('model_used', 'Unknown'))
                with col3:
                    st.metric("Documents Retrieved", len(result.get('documents', [])))
            
            # Show performance info
            if 'routing_decision' in result:
                st.info(f"🤖 Used model: {result['routing_decision'].get('model_name', 'unknown')}")
        else:
            st.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
            
            # Add error message to chat
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': f"Sorry, I encountered an error: {result.get('error', 'Unknown error')}",
                'timestamp': time.time(),
                'metadata': {
                    'success': False,
                    'error': result.get('error')
                }
            })
        
        st.rerun()
    
    def render_admin_dashboard(self):
        """Render optimized admin dashboard"""
        st.title("🔧 Optimized Admin Dashboard")
        
        # Performance overview
        st.subheader("📊 Performance Overview")
        
        perf_stats = performance_monitor.get_stats()
        cache_stats = {
            'size': len(query_cache.cache),
            'max_size': query_cache.max_size
        }
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Cache Size", f"{cache_stats['size']}/{cache_stats['max_size']}")
        
        with col2:
            if 'query_processing' in perf_stats:
                st.metric("Avg Query Time", f"{perf_stats['query_processing']['avg_duration']:.2f}s")
            else:
                st.metric("Avg Query Time", "N/A")
        
        with col3:
            if 'query_processing' in perf_stats:
                st.metric("Total Queries", perf_stats['query_processing']['count'])
            else:
                st.metric("Total Queries", "0")
        
        with col4:
            st.metric("Cache Utilization", f"{(cache_stats['size']/cache_stats['max_size'])*100:.1f}%")
        
        # Detailed performance stats
        if perf_stats:
            st.subheader("📈 Detailed Performance Stats")
            for operation, stats in perf_stats.items():
                with st.expander(f"{operation.replace('_', ' ').title()}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Count", stats['count'])
                    with col2:
                        st.metric("Avg Duration", f"{stats['avg_duration']:.3f}s")
                    with col3:
                        st.metric("Max Duration", f"{stats['max_duration']:.3f}s")
        
        # Cache management
        st.subheader("💾 Cache Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🧹 Clear Query Cache"):
                query_cache.clear()
                st.success("✅ Query cache cleared")
        
        with col2:
            if st.button("🧹 Clear All Caches"):
                query_cache.clear()
                st.success("✅ All caches cleared")
        
        # System status
        st.subheader("🔧 System Status")
        
        status_items = [
            ("Settings", self.settings is not None),
            ("AWS Clients", self.aws_clients is not None),
            ("Smart Router", self.smart_router is not None),
            ("Analytics Service", self.analytics_service is not None)
        ]
        
        for item, status in status_items:
            st.write(f"{'✅' if status else '❌'} {item}: {'Available' if status else 'Not Available'}")
    
    def run(self):
        """Run the optimized application"""
        # Sidebar navigation
        st.sidebar.title("🚀 Optimized Chatbot")
        
        page = st.sidebar.radio(
            "Navigation",
            ["🏠 Main Chat", "🔧 Admin Dashboard"]
        )
        
        # Render appropriate page
        if page == "🏠 Main Chat":
            self.render_optimized_chat_interface()
        elif page == "🔧 Admin Dashboard":
            self.render_admin_dashboard()

# Global app instance
app = None

def get_optimized_app():
    """Get the optimized app instance"""
    global app
    if app is None:
        app = OptimizedStreamlitApp()
    return app

def main():
    """Main entry point for optimized application"""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Get and run optimized app
    optimized_app = get_optimized_app()
    optimized_app.run()

if __name__ == "__main__":
    main()
