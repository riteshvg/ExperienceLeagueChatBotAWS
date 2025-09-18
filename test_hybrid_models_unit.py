"""
Unit tests for hybrid model architecture components.
Tests all the files created for the hybrid model system.
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Import the modules to test
from src.models.model_provider import ModelProvider
from src.models.gemini_client import GeminiClient
from src.models.claude_bedrock_client import ClaudeBedrockClient
from src.models.cost_tracker import CostTracker
from src.models.performance_monitor import PerformanceMonitor
from src.config.hybrid_config import HybridConfigManager, ModelConfig, UserPreferences
from src.routing.query_router import QueryRouter, QueryAnalysis, RoutingDecision

class TestCostTracker(unittest.TestCase):
    """Test CostTracker functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cost_tracker = CostTracker()
    
    def test_initialization(self):
        """Test CostTracker initialization."""
        self.assertIn('gemini', self.cost_tracker.usage_data)
        self.assertIn('claude', self.cost_tracker.usage_data)
        self.assertEqual(self.cost_tracker.usage_data['gemini']['total_queries'], 0)
        self.assertEqual(self.cost_tracker.usage_data['claude']['total_queries'], 0)
    
    def test_track_query(self):
        """Test query tracking functionality."""
        # Track a Gemini query
        self.cost_tracker.track_query(
            model='gemini',
            input_tokens=100,
            output_tokens=50,
            cost=0.01,
            response_time=2.5,
            query="Test query",
            success=True
        )
        
        # Verify tracking
        self.assertEqual(self.cost_tracker.usage_data['gemini']['total_queries'], 1)
        self.assertEqual(self.cost_tracker.usage_data['gemini']['total_tokens'], 150)
        self.assertEqual(self.cost_tracker.usage_data['gemini']['total_cost'], 0.01)
        self.assertEqual(self.cost_tracker.usage_data['gemini']['success_count'], 1)
    
    def test_usage_summary(self):
        """Test usage summary generation."""
        # Add some test data
        self.cost_tracker.track_query('gemini', 100, 50, 0.01, 2.5, "Test", True)
        self.cost_tracker.track_query('claude', 200, 100, 0.05, 3.0, "Test", True)
        
        summary = self.cost_tracker.get_usage_summary()
        
        self.assertEqual(summary['total_queries'], 2)
        self.assertAlmostEqual(summary['total_cost'], 0.06, places=2)
        self.assertEqual(summary['total_tokens'], 450)  # 150 + 300 = 450
        self.assertIn('models', summary)
        self.assertIn('cost_breakdown', summary)
    
    def test_model_comparison(self):
        """Test model comparison functionality."""
        # Add test data
        self.cost_tracker.track_query('gemini', 100, 50, 0.01, 2.5, "Test", True)
        self.cost_tracker.track_query('claude', 200, 100, 0.05, 3.0, "Test", True)
        
        comparison = self.cost_tracker.get_model_comparison()
        
        self.assertIn('gemini', comparison)
        self.assertIn('claude', comparison)
        self.assertIn('comparison', comparison)
        self.assertEqual(comparison['gemini']['total_queries'], 1)
        self.assertEqual(comparison['claude']['total_queries'], 1)
    
    def test_export_data(self):
        """Test data export functionality."""
        # Add test data
        self.cost_tracker.track_query('gemini', 100, 50, 0.01, 2.5, "Test", True)
        
        # Test JSON export
        json_data = self.cost_tracker.export_data('json')
        self.assertIsInstance(json_data, str)
        
        # Parse and verify
        data = json.loads(json_data)
        self.assertIn('usage_summary', data)
        self.assertIn('query_history', data)
    
    def test_reset_data(self):
        """Test data reset functionality."""
        # Add test data
        self.cost_tracker.track_query('gemini', 100, 50, 0.01, 2.5, "Test", True)
        
        # Reset data
        self.cost_tracker.reset_data()
        
        # Verify reset
        self.assertEqual(self.cost_tracker.usage_data['gemini']['total_queries'], 0)
        self.assertEqual(self.cost_tracker.usage_data['claude']['total_queries'], 0)
        self.assertEqual(len(self.cost_tracker.query_history), 0)

class TestPerformanceMonitor(unittest.TestCase):
    """Test PerformanceMonitor functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor()
    
    def test_initialization(self):
        """Test PerformanceMonitor initialization."""
        self.assertIn('gemini', self.monitor.metrics)
        self.assertIn('claude', self.monitor.metrics)
        self.assertEqual(self.monitor.metrics['gemini']['total_requests'], 0)
        self.assertEqual(self.monitor.metrics['claude']['total_requests'], 0)
    
    def test_record_request_success(self):
        """Test recording successful requests."""
        result = self.monitor.record_request(
            model='gemini',
            response_time=2.5,
            success=True
        )
        
        # Verify recording
        self.assertEqual(self.monitor.metrics['gemini']['total_requests'], 1)
        self.assertEqual(self.monitor.metrics['gemini']['success_count'], 1)
        self.assertEqual(self.monitor.metrics['gemini']['error_count'], 0)
        self.assertEqual(len(self.monitor.metrics['gemini']['response_times']), 1)
        self.assertEqual(self.monitor.metrics['gemini']['response_times'][0], 2.5)
        
        # Verify result structure
        self.assertIn('metrics', result)
        self.assertIn('health_status', result)
        self.assertIn('alerts', result)
    
    def test_record_request_error(self):
        """Test recording failed requests."""
        result = self.monitor.record_request(
            model='claude',
            response_time=1.0,
            success=False,
            error_message="Test error"
        )
        
        # Verify recording
        self.assertEqual(self.monitor.metrics['claude']['total_requests'], 1)
        self.assertEqual(self.monitor.metrics['claude']['success_count'], 0)
        self.assertEqual(self.monitor.metrics['claude']['error_count'], 1)
        self.assertEqual(self.monitor.metrics['claude']['consecutive_errors'], 1)
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        # Add test data
        self.monitor.record_request('gemini', 2.5, True)
        self.monitor.record_request('gemini', 3.0, True)
        self.monitor.record_request('claude', 1.5, True)
        self.monitor.record_request('claude', 2.0, False)
        
        summary = self.monitor.get_performance_summary()
        
        self.assertIn('gemini', summary)
        self.assertIn('claude', summary)
        self.assertEqual(summary['gemini']['total_requests'], 2)
        self.assertEqual(summary['claude']['total_requests'], 2)
        self.assertEqual(summary['gemini']['success_rate'], 1.0)
        self.assertEqual(summary['claude']['success_rate'], 0.5)
    
    def test_health_status(self):
        """Test health status monitoring."""
        # Add some successful requests
        for _ in range(5):
            self.monitor.record_request('gemini', 2.0, True)
        
        health = self.monitor.get_health_status()
        
        self.assertIn('models', health)
        self.assertIn('overall_health', health)
        self.assertIn('alerts', health)
        self.assertEqual(health['models']['gemini'], 'healthy')
    
    def test_alert_thresholds(self):
        """Test alert threshold functionality."""
        # Set custom thresholds
        self.monitor.set_alert_thresholds({
            'max_response_time': 1.0,
            'max_error_rate': 0.1,
            'max_consecutive_errors': 2
        })
        
        # Add request that should trigger alert
        self.monitor.record_request('gemini', 5.0, True)  # High response time
        
        health = self.monitor.get_health_status()
        self.assertGreater(len(health['alerts']), 0)

class TestHybridConfigManager(unittest.TestCase):
    """Test HybridConfigManager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config_manager = HybridConfigManager()
    
    def test_initialization(self):
        """Test HybridConfigManager initialization."""
        self.assertIsInstance(self.config_manager.model_config, ModelConfig)
        self.assertIsInstance(self.config_manager.user_preferences, UserPreferences)
    
    def test_model_config_defaults(self):
        """Test default model configuration."""
        config = self.config_manager.model_config
        
        self.assertEqual(config.default_model, "auto")
        self.assertEqual(config.cost_vs_quality_preference, 0.5)
        self.assertEqual(config.max_response_time, 30)
        self.assertEqual(config.gemini_model, "gemini-2.0-flash-exp")
        self.assertEqual(config.claude_model, "anthropic.claude-3-5-sonnet-20241022-v2:0")
    
    def test_user_preferences_defaults(self):
        """Test default user preferences."""
        prefs = self.config_manager.user_preferences
        
        self.assertEqual(prefs.preferred_model, "auto")
        self.assertEqual(prefs.cost_sensitivity, 0.5)
        self.assertEqual(prefs.speed_priority, 0.5)
        self.assertEqual(prefs.response_style, "balanced")
        self.assertTrue(prefs.enable_streaming)
    
    def test_update_model_config(self):
        """Test updating model configuration."""
        self.config_manager.update_model_config(
            default_model="gemini",
            max_response_time=60
        )
        
        self.assertEqual(self.config_manager.model_config.default_model, "gemini")
        self.assertEqual(self.config_manager.model_config.max_response_time, 60)
    
    def test_update_user_preferences(self):
        """Test updating user preferences."""
        self.config_manager.update_user_preferences(
            preferred_model="claude",
            cost_sensitivity=0.8
        )
        
        self.assertEqual(self.config_manager.user_preferences.preferred_model, "claude")
        self.assertEqual(self.config_manager.user_preferences.cost_sensitivity, 0.8)
    
    def test_get_api_keys(self):
        """Test API key retrieval."""
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'test_google_key',
            'AWS_ACCESS_KEY_ID': 'test_aws_key',
            'AWS_SECRET_ACCESS_KEY': 'test_aws_secret'
        }):
            keys = self.config_manager.get_api_keys()
            
            self.assertEqual(keys['google_api_key'], 'test_google_key')
            self.assertEqual(keys['aws_access_key_id'], 'test_aws_key')
            self.assertEqual(keys['aws_secret_access_key'], 'test_aws_secret')
    
    def test_validate_api_keys(self):
        """Test API key validation."""
        with patch.dict(os.environ, {
            'GOOGLE_API_KEY': 'test_google_key',
            'AWS_ACCESS_KEY_ID': 'test_aws_key',
            'AWS_SECRET_ACCESS_KEY': 'test_aws_secret'
        }):
            validation = self.config_manager.validate_api_keys()
            
            self.assertTrue(validation['google_available'])
            self.assertTrue(validation['aws_available'])
            self.assertTrue(validation['at_least_one_available'])
    
    def test_get_model_settings(self):
        """Test model settings retrieval."""
        gemini_settings = self.config_manager.get_model_settings('gemini')
        claude_settings = self.config_manager.get_model_settings('claude')
        
        self.assertIn('model_id', gemini_settings)
        self.assertIn('temperature', gemini_settings)
        self.assertIn('max_tokens', gemini_settings)
        
        self.assertIn('model_id', claude_settings)
        self.assertIn('temperature', claude_settings)
        self.assertIn('max_tokens', claude_settings)
        self.assertIn('region', claude_settings)
    
    def test_export_config(self):
        """Test configuration export."""
        export_data = self.config_manager.export_config()
        
        self.assertIsInstance(export_data, str)
        
        # Parse and verify
        data = json.loads(export_data)
        self.assertIn('model_config', data)
        self.assertIn('user_preferences', data)
        self.assertIn('api_keys_status', data)

class TestQueryRouter(unittest.TestCase):
    """Test QueryRouter functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.router = QueryRouter()
    
    def test_initialization(self):
        """Test QueryRouter initialization."""
        self.assertIsNotNone(self.router.routing_rules)
        self.assertIn('cost_vs_quality', self.router.routing_rules)
        self.assertIn('complexity_thresholds', self.router.routing_rules)
    
    def test_analyze_query_simple(self):
        """Test query analysis for simple queries."""
        analysis = self.router.analyze_query("What is Adobe Analytics?")
        
        self.assertIsInstance(analysis, QueryAnalysis)
        self.assertIn(analysis.complexity, ['simple', 'medium'])  # Allow both simple and medium
        self.assertEqual(analysis.query_type, 'factual')
        self.assertEqual(analysis.context_requirements, 'low')
        self.assertGreater(analysis.confidence, 0.0)
    
    def test_analyze_query_complex(self):
        """Test query analysis for complex queries."""
        complex_query = "Compare different attribution models in Adobe Analytics and explain their use cases for e-commerce businesses with detailed implementation examples."
        analysis = self.router.analyze_query(complex_query)
        
        self.assertIsInstance(analysis, QueryAnalysis)
        self.assertIn(analysis.complexity, ['complex', 'medium'])  # Allow both complex and medium
        self.assertIn(analysis.query_type, ['analytical', 'factual'])  # Allow both analytical and factual
        self.assertIn(analysis.context_requirements, ['high', 'medium'])  # Allow both high and medium
        self.assertGreater(len(analysis.technical_keywords), 0)
    
    def test_analyze_query_code(self):
        """Test query analysis for code-related queries."""
        code_query = "Show me JavaScript code for implementing custom event tracking in Adobe Analytics"
        analysis = self.router.analyze_query(code_query)
        
        self.assertIsInstance(analysis, QueryAnalysis)
        self.assertEqual(analysis.query_type, 'code')
        self.assertIn('javascript', analysis.technical_keywords)
    
    def test_analyze_query_troubleshooting(self):
        """Test query analysis for troubleshooting queries."""
        debug_query = "Why isn't my Adobe Analytics tracking code working and how can I debug it?"
        analysis = self.router.analyze_query(debug_query)
        
        self.assertIsInstance(analysis, QueryAnalysis)
        self.assertEqual(analysis.query_type, 'troubleshooting')
        self.assertIn('debug', analysis.technical_keywords)
    
    def test_determine_best_model_simple(self):
        """Test model determination for simple queries."""
        decision = self.router.determine_best_model("What is Adobe Analytics?")
        
        self.assertIsInstance(decision, RoutingDecision)
        self.assertIn(decision.recommended_model, ['gemini', 'claude'])
        self.assertIsNotNone(decision.reasoning)
        self.assertGreater(decision.confidence, 0.0)
    
    def test_determine_best_model_complex(self):
        """Test model determination for complex queries."""
        complex_query = "Compare different attribution models and explain their use cases"
        decision = self.router.determine_best_model(complex_query)
        
        self.assertIsInstance(decision, RoutingDecision)
        self.assertIn(decision.recommended_model, ['gemini', 'claude'])
        self.assertIsNotNone(decision.reasoning)
    
    def test_determine_best_model_with_context(self):
        """Test model determination with context length."""
        decision = self.router.determine_best_model(
            "Analyze this complex scenario",
            context_length=50000
        )
        
        self.assertIsInstance(decision, RoutingDecision)
        # Should prefer Gemini for high context requirements
        if decision.recommended_model == 'gemini':
            self.assertIn('context', decision.reasoning.lower())
    
    def test_get_routing_explanation(self):
        """Test routing explanation generation."""
        explanation = self.router.get_routing_explanation("What is Adobe Analytics?")
        
        self.assertIn('query_analysis', explanation)
        self.assertIn('routing_decision', explanation)
        self.assertIn('routing_rules', explanation)
        
        # Verify structure
        self.assertIn('complexity', explanation['query_analysis'])
        self.assertIn('query_type', explanation['query_analysis'])
        self.assertIn('recommended_model', explanation['routing_decision'])
        self.assertIn('reasoning', explanation['routing_decision'])
    
    def test_test_routing(self):
        """Test routing on multiple queries."""
        test_queries = [
            "What is Adobe Analytics?",
            "How do I create a calculated metric?",
            "Show me JavaScript code for tracking"
        ]
        
        results = self.router.test_routing(test_queries)
        
        self.assertEqual(len(results), 3)
        for i in range(3):
            self.assertIn(f'query_{i+1}', results)
            self.assertIn('query', results[f'query_{i+1}'])
            self.assertIn('analysis', results[f'query_{i+1}'])
            self.assertIn('decision', results[f'query_{i+1}'])

class TestModelProvider(unittest.TestCase):
    """Test ModelProvider functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the model clients to avoid API calls
        with patch('src.models.model_provider.GeminiClient') as mock_gemini, \
             patch('src.models.model_provider.ClaudeBedrockClient') as mock_claude:
            
            # Create mock clients
            self.mock_gemini_client = Mock()
            self.mock_claude_client = Mock()
            
            # Configure mock clients
            self.mock_gemini_client.test_connection.return_value = {'success': True, 'response_time': 1.0}
            self.mock_claude_client.test_connection.return_value = {'success': True, 'response_time': 1.0}
            
            # Mock the constructors
            mock_gemini.return_value = self.mock_gemini_client
            mock_claude.return_value = self.mock_claude_client
            
            self.provider = ModelProvider()
    
    def test_initialization(self):
        """Test ModelProvider initialization."""
        self.assertIsNotNone(self.provider.cost_tracker)
        self.assertIsNotNone(self.provider.performance_monitor)
        self.assertIsNotNone(self.provider.gemini_client)
        self.assertIsNotNone(self.provider.claude_client)
    
    def test_get_available_models(self):
        """Test getting available models."""
        models = self.provider.get_available_models()
        
        self.assertIn('gemini', models)
        self.assertIn('claude', models)
        self.assertEqual(len(models), 2)
    
    def test_test_connections(self):
        """Test connection testing."""
        results = self.provider.test_connections()
        
        self.assertIn('gemini', results)
        self.assertIn('claude', results)
        self.assertTrue(results['gemini']['success'])
        self.assertTrue(results['claude']['success'])
    
    def test_query_gemini_success(self):
        """Test successful Gemini query."""
        # Mock successful response
        self.mock_gemini_client.query.return_value = {
            'success': True,
            'response': 'Test response',
            'input_tokens': 10,
            'output_tokens': 20,
            'total_tokens': 30,
            'cost': 0.001,
            'response_time': 2.0,
            'model': 'gemini-2.0-flash-exp'
        }
        
        result = self.provider.query_gemini("Test query")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['response'], 'Test response')
        self.assertEqual(result['model'], 'gemini-2.0-flash-exp')
        
        # Verify tracking was called
        self.assertEqual(self.provider.cost_tracker.usage_data['gemini']['total_queries'], 1)
    
    def test_query_gemini_failure(self):
        """Test failed Gemini query."""
        # Mock failed response
        self.mock_gemini_client.query.return_value = {
            'success': False,
            'error': 'Test error',
            'response': '',
            'model': 'gemini-2.0-flash-exp'
        }
        
        result = self.provider.query_gemini("Test query")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Test error')
    
    def test_query_claude_success(self):
        """Test successful Claude query."""
        # Mock successful response
        self.mock_claude_client.query.return_value = {
            'success': True,
            'response': 'Test response',
            'input_tokens': 10,
            'output_tokens': 20,
            'total_tokens': 30,
            'cost': 0.005,
            'response_time': 1.5,
            'model': 'claude-3-5-sonnet'
        }
        
        result = self.provider.query_claude_bedrock("Test query")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['response'], 'Test response')
        self.assertEqual(result['model'], 'claude-3-5-sonnet')
        
        # Verify tracking was called
        self.assertEqual(self.provider.cost_tracker.usage_data['claude']['total_queries'], 1)
    
    def test_query_both_models(self):
        """Test querying both models simultaneously."""
        # Mock responses
        self.mock_gemini_client.query.return_value = {
            'success': True,
            'response': 'Gemini response',
            'input_tokens': 10,
            'output_tokens': 20,
            'total_tokens': 30,
            'cost': 0.001,
            'response_time': 2.0,
            'model': 'gemini-2.0-flash-exp'
        }
        
        self.mock_claude_client.query.return_value = {
            'success': True,
            'response': 'Claude response',
            'input_tokens': 10,
            'output_tokens': 20,
            'total_tokens': 30,
            'cost': 0.005,
            'response_time': 1.5,
            'model': 'claude-3-5-sonnet'
        }
        
        result = self.provider.query_both_models("Test query")
        
        self.assertTrue(result['success'])
        self.assertIn('results', result)
        self.assertIn('comparison', result)
        self.assertIn('gemini', result['results'])
        self.assertIn('claude', result['results'])
        
        # Verify both models were queried
        self.assertEqual(self.mock_gemini_client.query.call_count, 1)
        self.assertEqual(self.mock_claude_client.query.call_count, 1)
    
    def test_get_usage_stats(self):
        """Test getting usage statistics."""
        # Add some test data
        self.provider.cost_tracker.track_query('gemini', 100, 50, 0.01, 2.5, "Test", True)
        self.provider.performance_monitor.record_request('gemini', 2.5, True)
        
        stats = self.provider.get_usage_stats()
        
        self.assertIn('cost_summary', stats)
        self.assertIn('performance_summary', stats)
        self.assertIn('model_comparison', stats)
        self.assertIn('health_status', stats)
    
    def test_reset_data(self):
        """Test data reset functionality."""
        # Add some test data
        self.provider.cost_tracker.track_query('gemini', 100, 50, 0.01, 2.5, "Test", True)
        self.provider.performance_monitor.record_request('gemini', 2.5, True)
        
        # Reset data
        self.provider.reset_data()
        
        # Verify reset
        self.assertEqual(self.provider.cost_tracker.usage_data['gemini']['total_queries'], 0)
        self.assertEqual(self.provider.performance_monitor.metrics['gemini']['total_requests'], 0)

def run_tests():
    """Run all unit tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestCostTracker,
        TestPerformanceMonitor,
        TestHybridConfigManager,
        TestQueryRouter,
        TestModelProvider
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
