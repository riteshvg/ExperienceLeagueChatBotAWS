"""
Memory management and cleanup routines for Streamlit chatbot
"""

import gc
import threading
import time
import logging
from typing import Dict, List, Any, Optional
import streamlit as st
from datetime import datetime, timedelta

# Optional psutil import with fallback
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    # Fallback psutil-like interface
    class MockPsutil:
        class Process:
            def memory_info(self):
                class MemoryInfo:
                    def __init__(self):
                        self.rss = 0
                        self.vms = 0
                return MemoryInfo()
            
            def memory_percent(self):
                return 0.0
        
        def virtual_memory(self):
            class VirtualMemory:
                def __init__(self):
                    self.available = 0
                    self.total = 0
            return VirtualMemory()
    
    psutil = MockPsutil()

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages memory usage and cleanup for the application"""
    
    def __init__(self, max_memory_mb: int = 1024, cleanup_interval: int = 300):
        self.max_memory_mb = max_memory_mb
        self.cleanup_interval = cleanup_interval
        self.memory_history = []
        self.cleanup_callbacks = []
        self.is_monitoring = False
        self.monitor_thread = None
        self.stats = {
            'total_cleanups': 0,
            'memory_freed_mb': 0,
            'gc_collections': 0,
            'peak_memory_mb': 0,
            'current_memory_mb': 0
        }
    
    def start_monitoring(self):
        """Start memory monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("🔍 Memory monitoring started")
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        logger.info("🛑 Memory monitoring stopped")
    
    def _monitor_loop(self):
        """Memory monitoring loop"""
        while self.is_monitoring:
            try:
                current_memory = self.get_memory_usage()
                self.stats['current_memory_mb'] = current_memory
                
                # Update peak memory
                if current_memory > self.stats['peak_memory_mb']:
                    self.stats['peak_memory_mb'] = current_memory
                
                # Record memory history
                self.memory_history.append({
                    'timestamp': datetime.now(),
                    'memory_mb': current_memory
                })
                
                # Keep only last 100 records
                if len(self.memory_history) > 100:
                    self.memory_history = self.memory_history[-100:]
                
                # Check if cleanup is needed
                if current_memory > self.max_memory_mb:
                    logger.warning(f"⚠️ Memory usage high: {current_memory:.1f}MB > {self.max_memory_mb}MB")
                    self.cleanup_memory()
                
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"❌ Memory monitoring error: {e}")
                time.sleep(60)  # Wait before retrying
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        if not PSUTIL_AVAILABLE:
            return 0.0
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / 1024 / 1024  # Convert to MB
        except Exception as e:
            logger.error(f"❌ Failed to get memory usage: {e}")
            return 0.0
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get detailed memory information"""
        if not PSUTIL_AVAILABLE:
            return {
                'rss_mb': 0.0,
                'vms_mb': 0.0,
                'percent': 0.0,
                'available_mb': 0.0,
                'total_mb': 0.0
            }
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                'total_mb': psutil.virtual_memory().total / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"❌ Failed to get memory info: {e}")
            return {}
    
    def cleanup_memory(self) -> Dict[str, Any]:
        """Perform memory cleanup"""
        logger.info("🧹 Starting memory cleanup...")
        cleanup_start = time.time()
        
        # Get initial memory
        initial_memory = self.get_memory_usage()
        
        # Run garbage collection
        collected = gc.collect()
        self.stats['gc_collections'] += 1
        
        # Run custom cleanup callbacks
        for callback in self.cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"❌ Cleanup callback error: {e}")
        
        # Clear Streamlit session state if needed
        self._cleanup_session_state()
        
        # Get final memory
        final_memory = self.get_memory_usage()
        memory_freed = initial_memory - final_memory
        
        self.stats['total_cleanups'] += 1
        self.stats['memory_freed_mb'] += memory_freed
        
        cleanup_time = time.time() - cleanup_start
        
        logger.info(f"✅ Memory cleanup completed: {memory_freed:.1f}MB freed in {cleanup_time:.2f}s")
        
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_freed_mb': memory_freed,
            'cleanup_time_s': cleanup_time,
            'gc_collected': collected
        }
    
    def _cleanup_session_state(self):
        """Clean up Streamlit session state"""
        try:
            # Remove old chat history (keep last 50 messages)
            if 'chat_history' in st.session_state:
                chat_history = st.session_state.chat_history
                if len(chat_history) > 50:
                    st.session_state.chat_history = chat_history[-50:]
                    logger.debug("🧹 Cleaned up old chat history")
            
            # Remove old analytics data
            if 'analytics_data' in st.session_state:
                analytics_data = st.session_state.analytics_data
                if len(analytics_data) > 100:
                    st.session_state.analytics_data = analytics_data[-100:]
                    logger.debug("🧹 Cleaned up old analytics data")
            
            # Remove old cache data
            if 'cache_data' in st.session_state:
                cache_data = st.session_state.cache_data
                if len(cache_data) > 200:
                    st.session_state.cache_data = cache_data[-200:]
                    logger.debug("🧹 Cleaned up old cache data")
            
        except Exception as e:
            logger.error(f"❌ Session state cleanup error: {e}")
    
    def add_cleanup_callback(self, callback):
        """Add a custom cleanup callback"""
        self.cleanup_callbacks.append(callback)
    
    def remove_cleanup_callback(self, callback):
        """Remove a cleanup callback"""
        if callback in self.cleanup_callbacks:
            self.cleanup_callbacks.remove(callback)
    
    def get_memory_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get memory usage history for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            record for record in self.memory_history
            if record['timestamp'] > cutoff_time
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory management statistics"""
        return {
            **self.stats,
            'is_monitoring': self.is_monitoring,
            'max_memory_mb': self.max_memory_mb,
            'cleanup_interval': self.cleanup_interval,
            'history_records': len(self.memory_history)
        }

class CacheCleaner:
    """Specialized cache cleaner for different cache types"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.cleanup_schedules = {}
    
    def schedule_cleanup(self, cache_name: str, interval_minutes: int = 30):
        """Schedule regular cleanup for a cache"""
        self.cleanup_schedules[cache_name] = {
            'interval': interval_minutes * 60,  # Convert to seconds
            'last_cleanup': 0
        }
    
    def cleanup_if_needed(self, cache_name: str):
        """Clean up cache if scheduled time has passed"""
        if cache_name not in self.cleanup_schedules:
            return
        
        schedule = self.cleanup_schedules[cache_name]
        current_time = time.time()
        
        if current_time - schedule['last_cleanup'] > schedule['interval']:
            self._cleanup_cache(cache_name)
            schedule['last_cleanup'] = current_time
    
    def _cleanup_cache(self, cache_name: str):
        """Clean up a specific cache"""
        try:
            if cache_name == 'query_cache':
                from src.performance.cache_manager import cache_manager
                cache_manager.query_cache._evict_expired()
                logger.debug("🧹 Cleaned up query cache")
            
            elif cache_name == 'model_cache':
                from src.performance.cache_manager import cache_manager
                cache_manager.model_cache._evict_expired()
                logger.debug("🧹 Cleaned up model cache")
            
            elif cache_name == 'analytics_cache':
                from src.performance.cache_manager import cache_manager
                cache_manager.analytics_cache._evict_expired()
                logger.debug("🧹 Cleaned up analytics cache")
            
        except Exception as e:
            logger.error(f"❌ Cache cleanup error for {cache_name}: {e}")

# Global memory manager instance
memory_manager = MemoryManager()

def initialize_memory_management(max_memory_mb: int = 1024, cleanup_interval: int = 300):
    """Initialize memory management"""
    global memory_manager
    memory_manager = MemoryManager(max_memory_mb, cleanup_interval)
    memory_manager.start_monitoring()
    return memory_manager

def get_memory_usage() -> float:
    """Get current memory usage in MB"""
    return memory_manager.get_memory_usage()

def cleanup_memory() -> Dict[str, Any]:
    """Perform immediate memory cleanup"""
    return memory_manager.cleanup_memory()

def add_cleanup_callback(callback):
    """Add a custom cleanup callback"""
    memory_manager.add_cleanup_callback(callback)

def get_memory_stats() -> Dict[str, Any]:
    """Get memory management statistics"""
    return memory_manager.get_stats()
