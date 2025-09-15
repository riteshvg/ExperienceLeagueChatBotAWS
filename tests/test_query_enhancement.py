"""
Test cases for Adobe Experience League RAG Query Enhancement System

This module contains comprehensive test cases for the query enhancement functionality,
including Adobe product detection, synonym expansion, and performance testing.
"""

import pytest
import time
from query_enhancer import AdobeQueryEnhancer
from enhanced_rag_pipeline import EnhancedRAGPipeline


class TestAdobeQueryEnhancer:
    """Test cases for AdobeQueryEnhancer class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.enhancer = AdobeQueryEnhancer()
    
    def test_adobe_product_detection(self):
        """Test Adobe product detection functionality"""
        test_cases = [
            # Direct product mentions
            ("How to setup Adobe Analytics?", ["Adobe Analytics"]),
            ("AEP data ingestion guide", ["Adobe Experience Platform"]),
            ("Target personalization setup", ["Adobe Target"]),
            ("Campaign email marketing", ["Adobe Campaign"]),
            ("AEM content management", ["Adobe Experience Manager"]),
            ("CJA journey analytics", ["Customer Journey Analytics"]),
            ("AJO journey optimization", ["Adobe Journey Optimizer"]),
            
            # Abbreviations
            ("AA implementation steps", ["Adobe Analytics"]),
            ("AEP schema creation", ["Adobe Experience Platform"]),
            ("AT audience targeting", ["Adobe Target"]),
            ("AC email campaigns", ["Adobe Campaign"]),
            ("AEM CMS setup", ["Adobe Experience Manager"]),
            ("CJA attribution analysis", ["Customer Journey Analytics"]),
            ("AJO journey orchestration", ["Adobe Journey Optimizer"]),
            
            # Context-based detection
            ("analytics implementation guide", ["Adobe Analytics"]),
            ("platform data ingestion", ["Adobe Experience Platform"]),
            ("personalization configuration", ["Adobe Target"]),
            ("email marketing automation", ["Adobe Campaign"]),
            ("content management system", ["Adobe Experience Manager"]),
            ("journey analytics reporting", ["Customer Journey Analytics"]),
            ("journey orchestration setup", ["Adobe Journey Optimizer"]),
        ]
        
        for query, expected_products in test_cases:
            result = self.enhancer.enhance_query(query)
            detected_products = result['detected_products']
            
            # Check that at least one expected product is detected
            assert any(product in detected_products for product in expected_products), \
                f"Query '{query}' should detect {expected_products}, got {detected_products}"
    
    def test_synonym_expansion(self):
        """Test technical synonym expansion"""
        test_cases = [
            ("track events", "measure events"),
            ("setup analytics", "implement analytics"),
            ("create dashboard", "create workspace"),
            ("manage segments", "manage audiences"),
            ("configure campaign", "configure marketing"),
        ]
        
        for original, expected_contains in test_cases:
            result = self.enhancer.enhance_query(original)
            enhanced_queries = result['enhanced_queries']
            
            # Check that at least one enhanced query contains the expected term
            assert any(expected_contains in eq.lower() for eq in enhanced_queries), \
                f"Query '{original}' should expand to contain '{expected_contains}'"
    
    def test_query_normalization(self):
        """Test query normalization and misspelling correction"""
        test_cases = [
            ("adobe analitics setup", "adobe analytics setup"),
            ("experiance platform", "experience platform"),
            ("journy optimizer", "journey optimizer"),
            ("campain management", "campaign management"),
        ]
        
        for original, expected_normalized in test_cases:
            normalized = self.enhancer._normalize_query(original)
            assert expected_normalized in normalized, \
                f"Query '{original}' should normalize to contain '{expected_normalized}'"
    
    def test_enhanced_query_generation(self):
        """Test enhanced query generation"""
        query = "track custom events"
        result = self.enhancer.enhance_query(query)
        
        # Should have multiple enhanced queries
        assert len(result['enhanced_queries']) > 1, "Should generate multiple enhanced queries"
        
        # Original query should be included
        assert query in result['enhanced_queries'], "Original query should be included"
        
        # Should have processing time
        assert result['processing_time_ms'] >= 0, "Should have processing time"
    
    def test_performance_requirements(self):
        """Test that enhancement meets performance requirements (<400ms)"""
        test_queries = [
            "How to setup Adobe Analytics tracking?",
            "AEP data ingestion workflow",
            "Target personalization configuration",
            "Campaign email automation",
            "AEM content management setup",
            "CJA journey analytics reporting",
            "AJO journey orchestration",
        ]
        
        for query in test_queries:
            start_time = time.time()
            result = self.enhancer.enhance_query(query)
            processing_time = (time.time() - start_time) * 1000
            
            assert processing_time < 400, \
                f"Query enhancement took {processing_time:.2f}ms, should be <400ms"
            assert result['processing_time_ms'] < 400, \
                f"Reported processing time {result['processing_time_ms']:.2f}ms should be <400ms"
    
    def test_error_handling(self):
        """Test error handling and fallback behavior"""
        # Test with empty query
        result = self.enhancer.safe_enhance_query("")
        assert result['original'] == ""
        assert result['enhanced_queries'] == [""]
        assert result['detected_products'] == []
        
        # Test with None input
        result = self.enhancer.safe_enhance_query(None)
        assert result['original'] is None
        assert result['enhanced_queries'] == [None]
        assert result['detected_products'] == []
    
    def test_caching_functionality(self):
        """Test query caching for performance"""
        query = "Adobe Analytics implementation guide"
        
        # First call
        start_time = time.time()
        result1 = self.enhancer.enhance_query(query)
        first_call_time = (time.time() - start_time) * 1000
        
        # Second call (should be faster due to caching)
        start_time = time.time()
        result2 = self.enhancer.enhance_query(query)
        second_call_time = (time.time() - start_time) * 1000
        
        # Results should be identical
        assert result1['enhanced_queries'] == result2['enhanced_queries']
        assert result1['detected_products'] == result2['detected_products']
        
        # Second call should be faster (cached)
        assert second_call_time <= first_call_time, \
            "Cached query should be faster or equal to first call"
    
    def test_adobe_specific_queries(self):
        """Test Adobe-specific query patterns"""
        test_cases = [
            # Analytics queries
            ("How to track custom events?", ["Adobe Analytics"]),
            ("AA implementation steps", ["Adobe Analytics"]),
            ("analytics dashboard creation", ["Adobe Analytics"]),
            ("analytics reporting setup", ["Adobe Analytics"]),
            
            # AEP queries
            ("AEP data ingestion", ["Adobe Experience Platform"]),
            ("platform schema creation", ["Adobe Experience Platform"]),
            ("experience platform setup", ["Adobe Experience Platform"]),
            ("CDP configuration", ["Adobe Experience Platform"]),
            
            # Target queries
            ("Target personalization", ["Adobe Target"]),
            ("AT audience targeting", ["Adobe Target"]),
            ("ab testing setup", ["Adobe Target"]),
            ("experience targeting", ["Adobe Target"]),
            
            # Campaign queries
            ("Campaign email marketing", ["Adobe Campaign"]),
            ("AC automation setup", ["Adobe Campaign"]),
            ("email campaign management", ["Adobe Campaign"]),
            ("marketing automation", ["Adobe Campaign"]),
            
            # AEM queries
            ("AEM content management", ["Adobe Experience Manager"]),
            ("experience manager setup", ["Adobe Experience Manager"]),
            ("CMS configuration", ["Adobe Experience Manager"]),
            ("web content management", ["Adobe Experience Manager"]),
            
            # CJA queries
            ("CJA journey analytics", ["Customer Journey Analytics"]),
            ("journey analytics reporting", ["Customer Journey Analytics"]),
            ("cross-channel analytics", ["Customer Journey Analytics"]),
            ("attribution analysis", ["Customer Journey Analytics"]),
            
            # AJO queries
            ("AJO journey optimization", ["Adobe Journey Optimizer"]),
            ("journey orchestration", ["Adobe Journey Optimizer"]),
            ("customer journey management", ["Adobe Journey Optimizer"]),
            ("journey optimizer setup", ["Adobe Journey Optimizer"]),
        ]
        
        for query, expected_products in test_cases:
            result = self.enhancer.enhance_query(query)
            detected_products = result['detected_products']
            
            # Should detect at least one expected product
            assert any(product in detected_products for product in expected_products), \
                f"Query '{query}' should detect {expected_products}, got {detected_products}"
            
            # Should generate enhanced queries
            assert len(result['enhanced_queries']) > 0, f"Query '{query}' should generate enhanced queries"
            
            # Should have reasonable processing time
            assert result['processing_time_ms'] < 100, \
                f"Query '{query}' processing time {result['processing_time_ms']:.2f}ms should be <100ms"


class TestEnhancedRAGPipeline:
    """Test cases for EnhancedRAGPipeline class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.pipeline = EnhancedRAGPipeline()
    
    def test_performance_stats(self):
        """Test performance statistics tracking"""
        # Initially no stats
        stats = self.pipeline.get_performance_stats()
        assert "No performance data available" in stats["message"]
        
        # Reset stats
        self.pipeline.reset_performance_stats()
        stats = self.pipeline.get_performance_stats()
        assert "No performance data available" in stats["message"]
    
    def test_fallback_search(self):
        """Test fallback search functionality"""
        # This would require mocking the AWS clients
        # For now, just test that the method exists and handles errors gracefully
        try:
            result = self.pipeline._fallback_search("test query", 5)
            assert isinstance(result, list)
        except Exception as e:
            # Expected to fail without proper AWS setup
            assert "bedrock" in str(e).lower() or "aws" in str(e).lower()


class TestIntegration:
    """Integration tests for the complete query enhancement system"""
    
    def test_end_to_end_enhancement(self):
        """Test end-to-end query enhancement workflow"""
        enhancer = AdobeQueryEnhancer()
        
        # Test a complex query
        query = "How to setup Adobe Analytics tracking for custom events?"
        result = enhancer.enhance_query(query)
        
        # Verify result structure
        assert 'original' in result
        assert 'enhanced_queries' in result
        assert 'detected_products' in result
        assert 'processing_time_ms' in result
        
        # Verify content
        assert result['original'] == query
        assert len(result['enhanced_queries']) > 0
        assert 'Adobe Analytics' in result['detected_products']
        assert result['processing_time_ms'] < 400
    
    def test_performance_benchmark(self):
        """Benchmark performance across multiple queries"""
        enhancer = AdobeQueryEnhancer()
        
        test_queries = [
            "Adobe Analytics setup",
            "AEP data ingestion",
            "Target personalization",
            "Campaign automation",
            "AEM content management",
            "CJA journey analytics",
            "AJO journey optimization",
        ]
        
        total_time = 0
        successful_queries = 0
        
        for query in test_queries:
            start_time = time.time()
            result = enhancer.enhance_query(query)
            processing_time = (time.time() - start_time) * 1000
            
            total_time += processing_time
            if result['processing_time_ms'] < 400:
                successful_queries += 1
        
        avg_time = total_time / len(test_queries)
        success_rate = successful_queries / len(test_queries)
        
        assert avg_time < 200, f"Average processing time {avg_time:.2f}ms should be <200ms"
        assert success_rate >= 0.9, f"Success rate {success_rate:.2%} should be >=90%"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
