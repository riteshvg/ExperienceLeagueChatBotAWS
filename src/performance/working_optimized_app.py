"""
Working optimized Streamlit application that integrates with existing infrastructure
"""

import streamlit as st
import time
import logging
from typing import Dict, Any, Optional
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

# Global instances
query_cache = SimpleLRUCache(max_size=500, default_ttl=600)
performance_monitor = SimplePerformanceMonitor()

class OptimizedStreamlitApp:
    """Working optimized Streamlit application"""
    
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
            # Import SmartRouter from the main app.py
            from app import SmartRouter
            
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
            
            # Process query with smart router
            if not self.smart_router:
                raise Exception("Smart router not available")
            
            # Use the existing query processing logic from app.py
            from app import process_query_with_smart_routing
            
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
        
        # Initialize session state
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'user_id' not in st.session_state:
            st.session_state.user_id = f"user_{int(time.time())}"
        
        # Chat history
        chat_container = st.container()
        
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                if message['role'] == 'user':
                    st.markdown(f"**👤 You:** {message['content']}")
                else:
                    # Simple streaming effect
                    st.markdown(f"**🤖 Assistant:** {message['content']}")
        
        # Query input
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
        
        # Show processing indicator
        with st.spinner("🤔 Processing your question..."):
            # Process query with performance monitoring
            result = self.process_query_optimized(query, st.session_state.user_id)
            
            if result.get("success"):
                # Add AI response
                response_text = result.get("answer", "I couldn't generate a response.")
                
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response_text,
                    'timestamp': time.time()
                })
                
                st.success("✅ Query processed successfully!")
            else:
                st.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
        
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
