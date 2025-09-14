"""
Optimized Streamlit application with all performance enhancements
"""

import streamlit as st
import time
import logging
from typing import Dict, Any, Optional
import asyncio
import threading

# Import performance modules
from src.performance.cache_manager import cache_manager, cached_query, cached_analytics
from src.performance.database_pool import initialize_db_pool, get_db_pool
from src.performance.async_operations import async_manager, run_async, get_async_result
from src.performance.streaming_response import stream_response, show_typing_indicator, track_progress
from src.performance.memory_manager import initialize_memory_management, cleanup_memory
from src.performance.performance_monitor import (
    get_performance_monitor, start_operation, finish_operation, 
    record_metric, time_operation, OperationTimer
)

# Import existing modules
from src.config.settings import get_settings
from src.aws.bedrock_client import BedrockClient
from src.rag.smart_router import SmartRouter
from src.integrations.streamlit_analytics_simple import StreamlitAnalyticsIntegration
from src.integrations.database_query import render_database_query_interface

logger = logging.getLogger(__name__)

class OptimizedStreamlitApp:
    """High-performance Streamlit application with all optimizations"""
    
    def __init__(self):
        self.settings = None
        self.aws_clients = None
        self.smart_router = None
        self.analytics_service = None
        self.db_pool = None
        self.performance_monitor = get_performance_monitor()
        
        # Initialize performance systems
        self._initialize_performance_systems()
        
        # Initialize application components
        self._initialize_components()
    
    def _initialize_performance_systems(self):
        """Initialize all performance optimization systems"""
        try:
            # Initialize memory management
            initialize_memory_management(max_memory_mb=1024, cleanup_interval=300)
            
            # Initialize database pool
            settings = get_settings()
            if settings and hasattr(settings, 'database_url'):
                self.db_pool = initialize_db_pool(settings.database_url, min_connections=2, max_connections=10)
            
            logger.info("✅ Performance systems initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize performance systems: {e}")
    
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
    
    @cached_query(ttl=1800)  # Cache for 30 minutes
    def _get_cached_settings(self):
        """Get settings with caching"""
        return get_settings()
    
    @cached_query(ttl=1800)  # Cache for 30 minutes
    def _get_cached_aws_clients(self):
        """Get AWS clients with caching"""
        if not self.settings:
            return None
        
        try:
            bedrock_client = BedrockClient(
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                aws_default_region=self.settings.aws_default_region
            )
            return {"bedrock": bedrock_client}
        except Exception as e:
            logger.error(f"❌ Failed to initialize AWS clients: {e}")
            return None
    
    @cached_query(ttl=1800)  # Cache for 30 minutes
    def _get_cached_smart_router(self):
        """Get smart router with caching"""
        if not self.aws_clients or not self.settings:
            return None
        
        try:
            return SmartRouter(
                bedrock_client=self.aws_clients["bedrock"],
                knowledge_base_id=self.settings.bedrock_knowledge_base_id
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize smart router: {e}")
            return None
    
    @cached_query(ttl=1800)  # Cache for 30 minutes
    def _get_cached_analytics_service(self):
        """Get analytics service with caching"""
        if not self.settings:
            return None
        
        try:
            from src.integrations.streamlit_analytics_simple import SimpleAnalyticsService, StreamlitAnalyticsIntegration
            
            analytics_service = SimpleAnalyticsService(
                database_url=self.settings.database_url
            )
            return StreamlitAnalyticsIntegration(analytics_service)
        except Exception as e:
            logger.error(f"❌ Failed to initialize analytics service: {e}")
            return None
    
    @time_operation("query_processing")
    def process_query_optimized(self, query: str, user_id: str = "anonymous") -> Dict[str, Any]:
        """Optimized query processing with performance monitoring"""
        operation_id = start_operation("query_processing", {"query_length": len(query)})
        
        try:
            # Check cache first
            cached_result = cache_manager.get_query_result(query)
            if cached_result:
                record_metric("cache_hit", 1.0, {"cache_type": "query"})
                finish_operation(operation_id, success=True)
                return cached_result
            
            record_metric("cache_miss", 1.0, {"cache_type": "query"})
            
            # Process query with smart router
            if not self.smart_router:
                raise Exception("Smart router not available")
            
            # Use async processing for non-critical operations
            result = self.smart_router.process_query(query)
            
            # Cache the result
            cache_manager.set_query_result(query, result, ttl=600)
            
            # Track analytics asynchronously
            if self.analytics_service:
                analytics_data = [{
                    'query': query,
                    'userid': user_id,
                    'date_time': time.time(),
                    'reaction': 'none',
                    'query_time_seconds': time.time() - time.time(),  # Will be updated
                    'model_used': result.get('model_used', 'unknown')
                }]
                
                # Process analytics in background
                run_async(self._process_analytics_async, analytics_data)
            
            finish_operation(operation_id, success=True)
            return result
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            finish_operation(operation_id, success=False, error=str(e))
            return {"success": False, "error": str(e)}
    
    def _process_analytics_async(self, analytics_data):
        """Process analytics data asynchronously"""
        try:
            if self.db_pool:
                self.db_pool.batch_insert_analytics(analytics_data)
        except Exception as e:
            logger.error(f"❌ Async analytics processing failed: {e}")
    
    def render_optimized_chat_interface(self):
        """Render optimized chat interface with streaming"""
        st.title("🚀 Optimized Adobe Analytics Chatbot")
        
        # Initialize session state
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'user_id' not in st.session_state:
            st.session_state.user_id = f"user_{int(time.time())}"
        
        # Chat history with streaming
        chat_container = st.container()
        
        with chat_container:
            for i, message in enumerate(st.session_state.chat_history):
                if message['role'] == 'user':
                    st.markdown(f"**👤 You:** {message['content']}")
                else:
                    # Use streaming for AI responses
                    if message.get('streaming', False):
                        stream_response(message['content'], st.container())
                    else:
                        st.markdown(f"**🤖 Assistant:** {message['content']}")
        
        # Query input with performance monitoring
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
                performance_button = st.form_submit_button("📊 Performance", use_container_width=True)
        
        # Handle form submission
        if submit_button and query:
            self._handle_query_submission(query)
        
        if clear_button:
            st.session_state.chat_history = []
            st.rerun()
        
        if performance_button:
            self._show_performance_dashboard()
    
    def _handle_query_submission(self, query: str):
        """Handle query submission with streaming and performance monitoring"""
        # Add user message
        st.session_state.chat_history.append({
            'role': 'user',
            'content': query,
            'timestamp': time.time()
        })
        
        # Show typing indicator
        with st.spinner("🤔 Thinking..."):
            # Process query with performance monitoring
            start_time = time.time()
            result = self.process_query_optimized(query, st.session_state.user_id)
            processing_time = time.time() - start_time
            
            # Record performance metrics
            record_metric("query_processing_time", processing_time, {
                "query_length": len(query),
                "success": result.get("success", False)
            })
            
            if result.get("success"):
                # Add AI response with streaming
                response_text = result.get("response", "I couldn't generate a response.")
                
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response_text,
                    'timestamp': time.time(),
                    'streaming': True
                })
                
                # Show performance info
                st.success(f"✅ Query processed in {processing_time:.2f}s")
            else:
                st.error(f"❌ Query failed: {result.get('error', 'Unknown error')}")
        
        st.rerun()
    
    def _show_performance_dashboard(self):
        """Show performance monitoring dashboard"""
        st.subheader("📊 Performance Dashboard")
        
        # Get performance summary
        summary = self.performance_monitor.get_performance_summary()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Operations", summary['overall_stats']['total_operations'])
        
        with col2:
            st.metric("Success Rate", f"{summary['recent_performance']['success_rate_last_5min']:.1%}")
        
        with col3:
            st.metric("Avg Duration", f"{summary['recent_performance']['avg_duration_last_5min']:.2f}s")
        
        with col4:
            st.metric("Active Operations", summary['active_operations'])
        
        # Cache statistics
        st.subheader("💾 Cache Statistics")
        cache_stats = cache_manager.get_all_stats()
        
        for cache_name, stats in cache_stats.items():
            with st.expandable(f"{cache_name.replace('_', ' ').title()}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Size", stats['size'])
                with col2:
                    st.metric("Hit Rate", f"{stats['hit_rate']:.1%}")
                with col3:
                    st.metric("Requests", stats['requests'])
        
        # Memory usage
        st.subheader("🧠 Memory Usage")
        from src.performance.memory_manager import get_memory_stats
        memory_stats = get_memory_stats()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Current Memory", f"{memory_stats['current_memory_mb']:.1f} MB")
        with col2:
            st.metric("Peak Memory", f"{memory_stats['peak_memory_mb']:.1f} MB")
        with col3:
            st.metric("Cleanups", memory_stats['total_cleanups'])
        
        # Database pool statistics
        if self.db_pool:
            st.subheader("🗄️ Database Pool")
            db_stats = self.db_pool.get_stats()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Pool Size", db_stats['pool_size'])
            with col2:
                st.metric("Queries Executed", db_stats['queries_executed'])
            with col3:
                st.metric("Batch Operations", db_stats['batch_operations'])
    
    def render_admin_dashboard(self):
        """Render optimized admin dashboard"""
        st.title("🔧 Optimized Admin Dashboard")
        
        # Performance overview
        self._show_performance_dashboard()
        
        # Database query interface
        st.subheader("🗄️ Database Query Interface")
        if self.db_pool:
            render_database_query_interface()
        else:
            st.error("❌ Database pool not available")
        
        # Cache management
        st.subheader("💾 Cache Management")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🧹 Clean Query Cache"):
                cache_manager.invalidate_query_cache()
                st.success("✅ Query cache cleared")
        
        with col2:
            if st.button("🧹 Clean All Caches"):
                cache_manager.query_cache.clear()
                cache_manager.model_cache.clear()
                cache_manager.analytics_cache.clear()
                st.success("✅ All caches cleared")
        
        with col3:
            if st.button("🧠 Memory Cleanup"):
                cleanup_result = cleanup_memory()
                st.success(f"✅ Memory cleanup: {cleanup_result['memory_freed_mb']:.1f}MB freed")
    
    def run(self):
        """Run the optimized application"""
        # Sidebar navigation
        st.sidebar.title("🚀 Optimized Chatbot")
        
        page = st.sidebar.radio(
            "Navigation",
            ["🏠 Main Chat", "🔧 Admin Dashboard", "📊 Performance"]
        )
        
        # Render appropriate page
        if page == "🏠 Main Chat":
            self.render_optimized_chat_interface()
        elif page == "🔧 Admin Dashboard":
            self.render_admin_dashboard()
        elif page == "📊 Performance":
            self._show_performance_dashboard()

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
