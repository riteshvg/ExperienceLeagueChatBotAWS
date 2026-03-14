"""
Unit tests for cache service
"""
import pytest
import time
from app.services.cache_service import CacheService, CacheEntry


class TestCacheEntry:
    """Test CacheEntry class"""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation"""
        data = {"answer": "test", "model": "haiku"}
        entry = CacheEntry(data, ttl=60)
        
        assert entry.data == data
        assert entry.ttl == 60
        assert entry.access_count == 0
        assert not entry.is_expired()
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration"""
        data = {"answer": "test"}
        entry = CacheEntry(data, ttl=0.1)  # Very short TTL
        
        assert not entry.is_expired()
        time.sleep(0.2)
        assert entry.is_expired()
    
    def test_cache_entry_access(self):
        """Test cache entry access tracking"""
        data = {"answer": "test"}
        entry = CacheEntry(data)
        
        assert entry.access_count == 0
        result = entry.access()
        assert entry.access_count == 1
        assert result == data
        assert entry.last_accessed > entry.created_at


class TestCacheService:
    """Test CacheService class"""
    
    def test_cache_initialization(self):
        """Test cache service initialization"""
        cache = CacheService(max_size=100, default_ttl=3600)
        
        assert cache.max_size == 100
        assert cache.default_ttl == 3600
        assert cache.get_size() == 0
    
    def test_cache_set_and_get(self):
        """Test setting and getting from cache"""
        cache = CacheService(max_size=10)
        query = "What is Adobe Analytics?"
        data = {"answer": "Adobe Analytics is...", "model": "haiku"}
        
        # Cache miss
        assert cache.get(query) is None
        
        # Set cache
        cache.set(query, data)
        assert cache.get_size() == 1
        
        # Cache hit
        result = cache.get(query)
        assert result is not None
        assert result["answer"] == data["answer"]
    
    def test_cache_normalization(self):
        """Test query normalization"""
        cache = CacheService()
        query1 = "What is Adobe Analytics?"
        query2 = "  what is adobe analytics?  "
        data = {"answer": "test"}
        
        cache.set(query1, data)
        result = cache.get(query2)
        
        # Should find the same query (normalized)
        assert result is not None
    
    def test_cache_expiration(self):
        """Test cache entry expiration"""
        cache = CacheService(default_ttl=0.1)  # Very short TTL
        query = "test query"
        data = {"answer": "test"}
        
        cache.set(query, data)
        assert cache.get(query) is not None
        
        time.sleep(0.2)
        assert cache.get(query) is None  # Should be expired
    
    def test_cache_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = CacheService(max_size=3)
        
        # Fill cache
        for i in range(3):
            cache.set(f"query_{i}", {"answer": f"answer_{i}"})
        
        assert cache.get_size() == 3
        
        # Add one more - should evict oldest
        cache.set("query_3", {"answer": "answer_3"})
        assert cache.get_size() == 3
        assert cache.get("query_0") is None  # Should be evicted
        assert cache.get("query_3") is not None  # Should be present
    
    def test_cache_invalidate(self):
        """Test cache invalidation"""
        cache = CacheService()
        query = "test query"
        data = {"answer": "test"}
        
        cache.set(query, data)
        assert cache.get(query) is not None
        
        cache.invalidate(query)
        assert cache.get(query) is None
    
    def test_cache_clear(self):
        """Test clearing all cache"""
        cache = CacheService()
        
        for i in range(5):
            cache.set(f"query_{i}", {"answer": f"answer_{i}"})
        
        assert cache.get_size() == 5
        cache.clear()
        assert cache.get_size() == 0
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = CacheService()
        
        # Initial stats
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['size'] == 0
        
        # Add some entries and test
        cache.set("query1", {"answer": "answer1"})
        cache.set("query2", {"answer": "answer2"})
        
        cache.get("query1")  # Hit
        cache.get("query1")  # Hit
        cache.get("query3")  # Miss
        
        stats = cache.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['size'] == 2
        assert stats['hit_rate'] > 0
    
    def test_cache_user_specific(self):
        """Test user-specific caching"""
        cache = CacheService()
        query = "test query"
        data1 = {"answer": "answer1"}
        data2 = {"answer": "answer2"}
        
        cache.set(query, data1, user_id="user1")
        cache.set(query, data2, user_id="user2")
        
        assert cache.get(query, user_id="user1")["answer"] == "answer1"
        assert cache.get(query, user_id="user2")["answer"] == "answer2"
        assert cache.get(query) is None  # No user_id should not match

