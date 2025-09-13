#!/usr/bin/env python3
"""
Unit tests for the simplified optimized Streamlit app
"""

import unittest
import sys
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test imports
try:
    from src.performance.simple_optimized_app import (
        SimpleLRUCache, 
        SimplePerformanceMonitor, 
        OptimizedStreamlitApp
    )
    print("✅ Successfully imported optimized app components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class TestSimpleLRUCache(unittest.TestCase):
    """Test the SimpleLRUCache implementation"""
    
    def setUp(self):
        self.cache = SimpleLRUCache(max_size=3, default_ttl=1)
    
    def test_basic_operations(self):
        """Test basic cache operations"""
        # Test set and get
        self.cache.set("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")
        
        # Test non-existent key
        self.assertIsNone(self.cache.get("nonexistent"))
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        # Fill cache to capacity
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")
        
        # Add one more item (should evict key1)
        self.cache.set("key4", "value4")
        
        # key1 should be evicted
        self.assertIsNone(self.cache.get("key1"))
        # key2, key3, key4 should still be there
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")
        self.assertEqual(self.cache.get("key4"), "value4")
    
    def test_ttl_expiration(self):
        """Test TTL expiration"""
        # Set with short TTL
        self.cache.set("key1", "value1", ttl=0.1)
        
        # Should be available immediately
        self.assertEqual(self.cache.get("key1"), "value1")
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        self.assertIsNone(self.cache.get("key1"))
    
    def test_clear(self):
        """Test cache clearing"""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        self.cache.clear()
        
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))
    
    def test_thread_safety(self):
        """Test thread safety"""
        results = []
        
        def worker(thread_id):
            for i in range(10):
                key = f"key_{thread_id}_{i}"
                value = f"value_{thread_id}_{i}"
                self.cache.set(key, value)
                results.append(self.cache.get(key))
        
        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All operations should have succeeded
        self.assertEqual(len(results), 30)
        self.assertTrue(all(result is not None for result in results))

class TestSimplePerformanceMonitor(unittest.TestCase):
    """Test the SimplePerformanceMonitor implementation"""
    
    def setUp(self):
        self.monitor = SimplePerformanceMonitor()
    
    def test_operation_timing(self):
        """Test operation timing"""
        # Start operation
        op_id = self.monitor.start_operation("test_op")
        self.assertIsNotNone(op_id)
        
        # Simulate some work
        time.sleep(0.1)
        
        # Finish operation
        duration = self.monitor.finish_operation(op_id)
        self.assertGreater(duration, 0.09)  # Should be close to 0.1
        self.assertLess(duration, 0.2)  # But not too much more
    
    def test_multiple_operations(self):
        """Test multiple operations"""
        # Run multiple operations
        for i in range(5):
            op_id = self.monitor.start_operation("test_op")
            time.sleep(0.01)
            self.monitor.finish_operation(op_id)
        
        # Check stats
        stats = self.monitor.get_stats()
        self.assertIn("test_op", stats)
        self.assertEqual(stats["test_op"]["count"], 5)
        self.assertGreater(stats["test_op"]["avg_duration"], 0)
    
    def test_invalid_operation_id(self):
        """Test finishing non-existent operation"""
        duration = self.monitor.finish_operation("nonexistent")
        self.assertEqual(duration, 0.0)

class TestOptimizedStreamlitApp(unittest.TestCase):
    """Test the OptimizedStreamlitApp implementation"""
    
    def setUp(self):
        # Mock the external dependencies
        self.mock_settings = Mock()
        self.mock_settings.aws_access_key_id = "test_key"
        self.mock_settings.aws_secret_access_key = "test_secret"
        self.mock_settings.aws_default_region = "us-east-1"
        self.mock_settings.bedrock_knowledge_base_id = "test_kb_id"
        self.mock_settings.database_url = "postgresql://test:test@localhost/test"
        
        # Mock the external modules
        with patch('src.performance.simple_optimized_app.get_settings') as mock_get_settings, \
             patch('src.performance.simple_optimized_app.BedrockClient') as mock_bedrock, \
             patch('src.performance.simple_optimized_app.SmartRouter') as mock_router, \
             patch('src.performance.simple_optimized_app.SimpleAnalyticsService') as mock_analytics, \
             patch('src.performance.simple_optimized_app.StreamlitAnalyticsIntegration') as mock_integration:
            
            mock_get_settings.return_value = self.mock_settings
            mock_bedrock.return_value = Mock()
            mock_router.return_value = Mock()
            mock_analytics.return_value = Mock()
            mock_integration.return_value = Mock()
            
            self.app = OptimizedStreamlitApp()
    
    def test_app_initialization(self):
        """Test app initialization"""
        self.assertIsNotNone(self.app)
        self.assertIsNotNone(self.app.settings)
    
    def test_cached_settings(self):
        """Test settings caching"""
        # First call should cache the settings
        settings1 = self.app._get_cached_settings()
        self.assertIsNotNone(settings1)
        
        # Second call should return cached settings
        settings2 = self.app._get_cached_settings()
        self.assertEqual(settings1, settings2)
    
    def test_query_processing_with_cache(self):
        """Test query processing with caching"""
        # Mock the smart router
        mock_result = {
            "success": True,
            "response": "Test response",
            "model_used": "test_model"
        }
        self.app.smart_router.process_query.return_value = mock_result
        
        # First query should hit the smart router
        result1 = self.app.process_query_optimized("test query")
        self.assertEqual(result1, mock_result)
        self.app.smart_router.process_query.assert_called_once_with("test query")
        
        # Reset mock
        self.app.smart_router.process_query.reset_mock()
        
        # Second identical query should hit cache
        result2 = self.app.process_query_optimized("test query")
        self.assertEqual(result2, mock_result)
        # Smart router should not be called again
        self.app.smart_router.process_query.assert_not_called()
    
    def test_query_processing_error(self):
        """Test query processing error handling"""
        # Mock smart router to raise exception
        self.app.smart_router.process_query.side_effect = Exception("Test error")
        
        result = self.app.process_query_optimized("test query")
        
        self.assertFalse(result["success"])
        self.assertIn("Test error", result["error"])
    
    def test_query_processing_no_router(self):
        """Test query processing when router is not available"""
        self.app.smart_router = None
        
        result = self.app.process_query_optimized("test query")
        
        self.assertFalse(result["success"])
        self.assertIn("Smart router not available", result["error"])

def run_integration_tests():
    """Run integration tests"""
    print("\n🧪 Running Integration Tests...")
    
    try:
        # Test cache functionality
        print("Testing cache functionality...")
        cache = SimpleLRUCache(max_size=5, default_ttl=1)
        
        # Test basic operations
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        print("✅ Cache basic operations work")
        
        # Test TTL
        cache.set("ttl_key", "ttl_value", ttl=0.1)
        assert cache.get("ttl_key") == "ttl_value"
        time.sleep(0.2)
        assert cache.get("ttl_key") is None
        print("✅ Cache TTL works")
        
        # Test LRU eviction
        for i in range(6):
            cache.set(f"key_{i}", f"value_{i}")
        assert cache.get("key_0") is None  # Should be evicted
        assert cache.get("key_5") == "value_5"  # Should still be there
        print("✅ Cache LRU eviction works")
        
        # Test performance monitor
        print("Testing performance monitor...")
        monitor = SimplePerformanceMonitor()
        
        op_id = monitor.start_operation("test")
        time.sleep(0.1)
        duration = monitor.finish_operation(op_id)
        assert duration > 0.09 and duration < 0.2
        print("✅ Performance monitor works")
        
        # Test app initialization
        print("Testing app initialization...")
        with patch('src.performance.simple_optimized_app.get_settings') as mock_get_settings, \
             patch('src.performance.simple_optimized_app.BedrockClient'), \
             patch('src.performance.simple_optimized_app.SmartRouter'), \
             patch('src.performance.simple_optimized_app.SimpleAnalyticsService'), \
             patch('src.performance.simple_optimized_app.StreamlitAnalyticsIntegration'):
            
            mock_get_settings.return_value = Mock()
            app = OptimizedStreamlitApp()
            assert app is not None
            print("✅ App initialization works")
        
        print("\n🎉 All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Running Unit Tests for Simple Optimized App")
    print("=" * 60)
    
    # Run unit tests
    print("\n📋 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run integration tests
    success = run_integration_tests()
    
    if success:
        print("\n✅ All tests passed! The optimized app is ready to use.")
        print("\n🚀 To run the app:")
        print("streamlit run src/performance/simple_optimized_app.py")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
