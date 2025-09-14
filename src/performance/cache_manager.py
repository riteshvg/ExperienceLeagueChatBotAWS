"""
Intelligent caching system with TTL and LRU eviction for Streamlit chatbot
"""

import time
import threading
from typing import Any, Dict, Optional, Callable
from collections import OrderedDict
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

class LRUCache:
    """LRU Cache implementation with TTL support"""
    
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
    
    def _evict_lru(self):
        """Remove least recently used entry"""
        if self.cache:
            self.cache.popitem(last=False)
    
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
                self._evict_lru()
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                self.cache.pop(key, None)
                self.timestamps.pop(key, None)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        with self.lock:
            self._evict_expired()
            return len(self.cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            self._evict_expired()
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": getattr(self, '_hits', 0) / max(getattr(self, '_requests', 1), 1),
                "requests": getattr(self, '_requests', 0),
                "hits": getattr(self, '_hits', 0)
            }

class CacheManager:
    """Intelligent cache manager with multiple cache layers"""
    
    def __init__(self):
        # Different cache layers for different data types
        self.query_cache = LRUCache(max_size=500, default_ttl=600)  # 10 minutes
        self.model_cache = LRUCache(max_size=100, default_ttl=1800)  # 30 minutes
        self.config_cache = LRUCache(max_size=50, default_ttl=3600)  # 1 hour
        self.analytics_cache = LRUCache(max_size=200, default_ttl=300)  # 5 minutes
        
        # Cache statistics
        self.stats = {
            'query_cache': {'hits': 0, 'misses': 0, 'requests': 0},
            'model_cache': {'hits': 0, 'misses': 0, 'requests': 0},
            'config_cache': {'hits': 0, 'misses': 0, 'requests': 0},
            'analytics_cache': {'hits': 0, 'misses': 0, 'requests': 0}
        }
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_string = f"{prefix}:{json.dumps(key_data, sort_keys=True)}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _update_stats(self, cache_name: str, hit: bool):
        """Update cache statistics"""
        if hit:
            self.stats[cache_name]['hits'] += 1
        else:
            self.stats[cache_name]['misses'] += 1
        self.stats[cache_name]['requests'] += 1
    
    def get_query_result(self, query: str, model: str = None) -> Optional[Any]:
        """Get cached query result"""
        key = self._generate_key("query", query, model=model)
        result = self.query_cache.get(key)
        self._update_stats('query_cache', result is not None)
        return result
    
    def set_query_result(self, query: str, result: Any, model: str = None, ttl: int = None):
        """Cache query result"""
        key = self._generate_key("query", query, model=model)
        self.query_cache.set(key, result, ttl)
    
    def get_model_response(self, prompt: str, model: str) -> Optional[Any]:
        """Get cached model response"""
        key = self._generate_key("model", prompt, model=model)
        result = self.model_cache.get(key)
        self._update_stats('model_cache', result is not None)
        return result
    
    def set_model_response(self, prompt: str, model: str, response: Any, ttl: int = None):
        """Cache model response"""
        key = self._generate_key("model", prompt, model=model)
        self.model_cache.set(key, response, ttl)
    
    def get_config(self, config_key: str) -> Optional[Any]:
        """Get cached configuration"""
        key = self._generate_key("config", config_key)
        result = self.config_cache.get(key)
        self._update_stats('config_cache', result is not None)
        return result
    
    def set_config(self, config_key: str, value: Any, ttl: int = None):
        """Cache configuration"""
        key = self._generate_key("config", config_key)
        self.config_cache.set(key, value, ttl)
    
    def get_analytics(self, query_type: str, **params) -> Optional[Any]:
        """Get cached analytics data"""
        key = self._generate_key("analytics", query_type, **params)
        result = self.analytics_cache.get(key)
        self._update_stats('analytics_cache', result is not None)
        return result
    
    def set_analytics(self, query_type: str, data: Any, **params):
        """Cache analytics data"""
        key = self._generate_key("analytics", query_type, **params)
        self.analytics_cache.set(key, data)
    
    def invalidate_query_cache(self, pattern: str = None):
        """Invalidate query cache entries matching pattern"""
        if pattern:
            # Simple pattern matching - could be enhanced
            keys_to_remove = [key for key in self.query_cache.cache.keys() if pattern in key]
            for key in keys_to_remove:
                self.query_cache.delete(key)
        else:
            self.query_cache.clear()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {}
        for cache_name, cache in [
            ('query_cache', self.query_cache),
            ('model_cache', self.model_cache),
            ('config_cache', self.config_cache),
            ('analytics_cache', self.analytics_cache)
        ]:
            cache_stats = cache.stats()
            cache_stats.update(self.stats[cache_name])
            stats[cache_name] = cache_stats
        return stats
    
    def cleanup_expired(self):
        """Clean up expired entries from all caches"""
        for cache in [self.query_cache, self.model_cache, self.config_cache, self.analytics_cache]:
            cache._evict_expired()

# Global cache manager instance
cache_manager = CacheManager()

def cached_query(ttl: int = 600):
    """Decorator for caching query results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_manager._generate_key("query_func", func.__name__, *args, **kwargs)
            
            # Try to get from cache
            result = cache_manager.query_cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.query_cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator

def cached_analytics(ttl: int = 300):
    """Decorator for caching analytics results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = cache_manager._generate_key("analytics_func", func.__name__, *args, **kwargs)
            
            # Try to get from cache
            result = cache_manager.analytics_cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.analytics_cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator
