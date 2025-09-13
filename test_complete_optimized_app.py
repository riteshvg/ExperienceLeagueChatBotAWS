#!/usr/bin/env python3
"""
Comprehensive unit tests for the complete optimized Streamlit app
"""

import unittest
import sys
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work"""
    print("🧪 Testing imports...")
    
    try:
        from src.performance.complete_optimized_app import (
            OptimizedStreamlitApp, SimpleLRUCache, SimplePerformanceMonitor,
            SmartRouter, process_query_with_smart_routing, retrieve_documents_from_kb,
            invoke_bedrock_model
        )
        print("✅ Successfully imported all components")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_cache_functionality():
    """Test cache functionality"""
    print("\n🧪 Testing cache functionality...")
    
    try:
        from src.performance.complete_optimized_app import SimpleLRUCache
        
        # Test basic operations
        cache = SimpleLRUCache(max_size=3, default_ttl=1)
        
        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        print("✅ Basic cache operations work")
        
        # Test TTL
        cache.set("ttl_key", "ttl_value", ttl=0.1)
        assert cache.get("ttl_key") == "ttl_value"
        time.sleep(0.2)
        assert cache.get("ttl_key") is None
        print("✅ Cache TTL works")
        
        # Test LRU eviction
        for i in range(4):
            cache.set(f"key_{i}", f"value_{i}")
        assert cache.get("key_0") is None  # Should be evicted
        assert cache.get("key_3") == "value_3"  # Should still be there
        print("✅ Cache LRU eviction works")
        
        # Test clear
        cache.clear()
        assert cache.get("key_3") is None
        print("✅ Cache clear works")
        
        return True
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_monitor():
    """Test performance monitor"""
    print("\n🧪 Testing performance monitor...")
    
    try:
        from src.performance.complete_optimized_app import SimplePerformanceMonitor
        
        monitor = SimplePerformanceMonitor()
        
        # Test single operation
        op_id = monitor.start_operation("test")
        time.sleep(0.1)
        duration = monitor.finish_operation(op_id)
        assert duration > 0.09 and duration < 0.2
        print("✅ Single operation timing works")
        
        # Test multiple operations
        for i in range(5):
            op_id = monitor.start_operation("test")
            time.sleep(0.01)
            monitor.finish_operation(op_id)
        
        stats = monitor.get_stats()
        assert "test" in stats
        assert stats["test"]["count"] == 6  # 1 + 5
        print("✅ Multiple operations tracking works")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance monitor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_smart_router():
    """Test smart router"""
    print("\n🧪 Testing smart router...")
    
    try:
        from src.performance.complete_optimized_app import SmartRouter
        
        # Test router initialization
        router = SmartRouter(haiku_only_mode=False)
        assert router is not None
        assert "haiku" in router.models
        assert "sonnet" in router.models
        print("✅ Smart router initialization works")
        
        # Test model selection
        documents = [{"content": {"text": "test document"}}]
        available_models = ["haiku", "sonnet"]
        
        decision = router.select_available_model("test query", documents, available_models)
        assert "model_id" in decision
        assert "model_name" in decision
        assert "complexity" in decision
        print("✅ Model selection works")
        
        # Test haiku-only mode
        router_haiku = SmartRouter(haiku_only_mode=True)
        decision_haiku = router_haiku.select_available_model("test query", documents, ["haiku", "sonnet"])
        assert decision_haiku["model_name"] == "haiku"
        print("✅ Haiku-only mode works")
        
        return True
        
    except Exception as e:
        print(f"❌ Smart router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_query_processing_functions():
    """Test query processing functions"""
    print("\n🧪 Testing query processing functions...")
    
    try:
        from src.performance.complete_optimized_app import (
            retrieve_documents_from_kb, invoke_bedrock_model, process_query_with_smart_routing
        )
        
        # Test retrieve_documents_from_kb with mock
        mock_client = Mock()
        mock_client.retrieve.return_value = {
            'retrievalResults': [
                {'content': {'text': 'test document 1'}},
                {'content': {'text': 'test document 2'}}
            ]
        }
        
        documents, error = retrieve_documents_from_kb("test query", "test_kb", mock_client)
        assert error is None
        assert len(documents) == 2
        print("✅ Document retrieval works")
        
        # Test invoke_bedrock_model with mock
        mock_bedrock_client = Mock()
        mock_bedrock_client.region = "us-east-1"
        
        with patch('src.performance.complete_optimized_app.BedrockClient') as mock_bedrock_class:
            mock_instance = Mock()
            mock_instance.generate_text.return_value = "Test response"
            mock_bedrock_class.return_value = mock_instance
            
            answer, error = invoke_bedrock_model("test_model", "test query", mock_bedrock_client)
            assert error is None
            assert answer == "Test response"
            print("✅ Model invocation works")
        
        # Test process_query_with_smart_routing with mocks
        mock_aws_clients = {
            'bedrock_agent_client': mock_client,
            'bedrock': mock_bedrock_client
        }
        
        mock_router = Mock()
        mock_router.select_available_model.return_value = {
            'model_id': 'test_model',
            'model_name': 'haiku',
            'complexity': 'simple'
        }
        
        with patch('src.performance.complete_optimized_app.invoke_bedrock_model') as mock_invoke:
            mock_invoke.return_value = ("Test response", None)
            
            result = process_query_with_smart_routing("test query", "test_kb", mock_router, mock_aws_clients)
            assert result["success"] == True
            assert result["answer"] == "Test response"
            print("✅ Complete query processing works")
        
        return True
        
    except Exception as e:
        print(f"❌ Query processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_initialization():
    """Test app initialization"""
    print("\n🧪 Testing app initialization...")
    
    try:
        from src.performance.complete_optimized_app import OptimizedStreamlitApp
        
        # Mock the external dependencies
        with patch('src.performance.complete_optimized_app.Settings') as mock_settings, \
             patch('src.performance.complete_optimized_app.BedrockClient') as mock_bedrock, \
             patch('src.performance.complete_optimized_app.SimpleAnalyticsService') as mock_analytics, \
             patch('src.performance.complete_optimized_app.StreamlitAnalyticsIntegration') as mock_integration, \
             patch('src.performance.complete_optimized_app.get_s3_client') as mock_s3, \
             patch('src.performance.complete_optimized_app.get_sts_client') as mock_sts, \
             patch('src.performance.complete_optimized_app.get_bedrock_agent_client') as mock_agent, \
             patch('src.performance.complete_optimized_app.get_cost_explorer_client') as mock_cost:
            
            # Setup mocks
            mock_settings_instance = Mock()
            mock_settings_instance.aws_default_region = "us-east-1"
            mock_settings_instance.bedrock_model_id = "test_model"
            mock_settings_instance.bedrock_region = "us-east-1"
            mock_settings_instance.bedrock_knowledge_base_id = "test_kb"
            mock_settings_instance.database_url = "postgresql://test"
            mock_settings.return_value = mock_settings_instance
            
            mock_bedrock.return_value = Mock()
            mock_analytics.return_value = Mock()
            mock_integration.return_value = Mock()
            mock_s3.return_value = Mock()
            mock_sts.return_value = Mock()
            mock_agent.return_value = Mock()
            mock_cost.return_value = Mock()
            
            # Test app creation
            app = OptimizedStreamlitApp()
            assert app is not None
            print("✅ App initializes successfully")
            
            # Test that components are initialized
            assert app.settings is not None
            assert app.aws_clients is not None
            assert app.smart_router is not None
            assert app.analytics_service is not None
            print("✅ All components initialized")
            
            return True
            
    except Exception as e:
        print(f"❌ App initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_end_to_end_query_processing():
    """Test end-to-end query processing"""
    print("\n🧪 Testing end-to-end query processing...")
    
    try:
        from src.performance.complete_optimized_app import OptimizedStreamlitApp
        
        # Mock all dependencies
        with patch('src.performance.complete_optimized_app.Settings') as mock_settings, \
             patch('src.performance.complete_optimized_app.BedrockClient') as mock_bedrock, \
             patch('src.performance.complete_optimized_app.SimpleAnalyticsService') as mock_analytics, \
             patch('src.performance.complete_optimized_app.StreamlitAnalyticsIntegration') as mock_integration, \
             patch('src.performance.complete_optimized_app.get_s3_client') as mock_s3, \
             patch('src.performance.complete_optimized_app.get_sts_client') as mock_sts, \
             patch('src.performance.complete_optimized_app.get_bedrock_agent_client') as mock_agent, \
             patch('src.performance.complete_optimized_app.get_cost_explorer_client') as mock_cost, \
             patch('src.performance.complete_optimized_app.retrieve_documents_from_kb') as mock_retrieve, \
             patch('src.performance.complete_optimized_app.invoke_bedrock_model') as mock_invoke:
            
            # Setup mocks
            mock_settings_instance = Mock()
            mock_settings_instance.aws_default_region = "us-east-1"
            mock_settings_instance.bedrock_model_id = "test_model"
            mock_settings_instance.bedrock_region = "us-east-1"
            mock_settings_instance.bedrock_knowledge_base_id = "test_kb"
            mock_settings_instance.database_url = "postgresql://test"
            mock_settings.return_value = mock_settings_instance
            
            mock_bedrock.return_value = Mock()
            mock_analytics.return_value = Mock()
            mock_integration.return_value = Mock()
            mock_s3.return_value = Mock()
            mock_sts.return_value = Mock()
            mock_agent.return_value = Mock()
            mock_cost.return_value = Mock()
            
            # Mock query processing
            mock_retrieve.return_value = ([{"content": {"text": "test document"}}], None)
            mock_invoke.return_value = ("Test response from AI", None)
            
            # Create app and test query processing
            app = OptimizedStreamlitApp()
            result = app.process_query_optimized("test query")
            
            # Verify result
            assert result["success"] == True
            assert "answer" in result
            assert result["answer"] == "Test response from AI"
            print("✅ End-to-end query processing works")
            
            # Test caching
            result2 = app.process_query_optimized("test query")
            assert result == result2  # Should be identical due to caching
            print("✅ Query caching works")
            
            return True
            
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_thread_safety():
    """Test thread safety"""
    print("\n🧪 Testing thread safety...")
    
    try:
        from src.performance.complete_optimized_app import SimpleLRUCache, SimplePerformanceMonitor
        
        # Test cache thread safety
        cache = SimpleLRUCache(max_size=100, default_ttl=10)
        results = []
        
        def worker(thread_id):
            for i in range(20):
                key = f"thread_{thread_id}_{i}"
                value = f"value_{thread_id}_{i}"
                cache.set(key, value)
                results.append(cache.get(key))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All operations should have succeeded
        assert len(results) == 100  # 5 threads * 20 operations
        assert all(result is not None for result in results)
        print("✅ Cache thread safety works")
        
        # Test performance monitor thread safety
        monitor = SimplePerformanceMonitor()
        monitor_results = []
        
        def monitor_worker(thread_id):
            for i in range(10):
                op_id = monitor.start_operation(f"thread_{thread_id}")
                time.sleep(0.01)
                duration = monitor.finish_operation(op_id)
                monitor_results.append(duration)
        
        # Create multiple threads
        monitor_threads = []
        for i in range(3):
            thread = threading.Thread(target=monitor_worker, args=(i,))
            monitor_threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in monitor_threads:
            thread.join()
        
        # All operations should have succeeded
        assert len(monitor_results) == 30  # 3 threads * 10 operations
        assert all(duration > 0 for duration in monitor_results)
        print("✅ Performance monitor thread safety works")
        
        return True
        
    except Exception as e:
        print(f"❌ Thread safety test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Comprehensive Unit Tests for Complete Optimized App")
    print("=" * 70)
    
    tests = [
        test_imports,
        test_cache_functionality,
        test_performance_monitor,
        test_smart_router,
        test_query_processing_functions,
        test_app_initialization,
        test_end_to_end_query_processing,
        test_thread_safety
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 70)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The complete optimized app is ready!")
        print("\n🚀 To run the complete optimized app:")
        print("streamlit run src/performance/complete_optimized_app.py")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
