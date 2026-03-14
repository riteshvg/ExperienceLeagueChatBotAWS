"""
Cache service for storing query responses and reducing LLM calls.
Uses LRU cache with TTL for efficient memory management.
"""
import time
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class CacheEntry:
    """Represents a cached query response"""
    def __init__(self, data: Dict[str, Any], ttl: int = 3600):
        self.data = data
        self.created_at = time.time()
        self.ttl = ttl  # Time to live in seconds
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Dict[str, Any]:
        """Access the cache entry and update statistics"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.data


class CacheService:
    """
    LRU cache service with TTL for query responses.
    Automatically evicts expired entries and least recently used entries.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize cache service
        
        Args:
            max_size: Maximum number of entries in cache
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired': 0
        }
    
    def _normalize_query(self, query: str) -> str:
        """
        Normalize query for consistent caching.
        Removes extra whitespace and converts to lowercase.
        """
        return ' '.join(query.strip().lower().split())
    
    def _generate_cache_key(self, query: str, user_id: Optional[str] = None) -> str:
        """
        Generate cache key from query and optional user_id.
        Uses MD5 hash for consistent key generation.
        """
        normalized_query = self._normalize_query(query)
        key_string = f"{user_id or 'anonymous'}:{normalized_query}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, query: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response for a query
        
        Returns:
            Cached response data if found and not expired, None otherwise
        """
        cache_key = self._generate_cache_key(query, user_id)
        
        if cache_key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        entry = self.cache[cache_key]
        
        # Check if expired
        if entry.is_expired():
            del self.cache[cache_key]
            self.stats['expired'] += 1
            self.stats['misses'] += 1
            logger.debug(f"Cache entry expired for query: {query[:50]}...")
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(cache_key)
        
        # Update access statistics
        self.stats['hits'] += 1
        logger.info(f"✅ Cache hit for query: {query[:50]}...")
        
        return entry.access()
    
    def set(
        self,
        query: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Store response in cache
        
        Args:
            query: The query string
            data: Response data to cache
            user_id: Optional user ID for user-specific caching
            ttl: Optional time-to-live in seconds (uses default if not provided)
        """
        cache_key = self._generate_cache_key(query, user_id)
        
        # Remove if already exists
        if cache_key in self.cache:
            del self.cache[cache_key]
        
        # Evict if cache is full
        if len(self.cache) >= self.max_size:
            # Remove least recently used (first item)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.stats['evictions'] += 1
            logger.debug(f"Evicted cache entry: {oldest_key}")
        
        # Add new entry
        entry = CacheEntry(data, ttl or self.default_ttl)
        self.cache[cache_key] = entry
        logger.debug(f"Cached response for query: {query[:50]}...")
    
    def invalidate(self, query: str, user_id: Optional[str] = None) -> bool:
        """
        Remove a specific entry from cache
        
        Returns:
            True if entry was found and removed, False otherwise
        """
        cache_key = self._generate_cache_key(query, user_id)
        if cache_key in self.cache:
            del self.cache[cache_key]
            logger.debug(f"Invalidated cache entry for query: {query[:50]}...")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
            self.stats['expired'] += len(expired_keys)
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': round(hit_rate, 2),
            'evictions': self.stats['evictions'],
            'expired': self.stats['expired'],
            'total_requests': total_requests
        }
    
    def get_size(self) -> int:
        """Get current cache size"""
        return len(self.cache)

