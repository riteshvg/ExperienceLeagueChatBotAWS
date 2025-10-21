"""
Test script for similarity threshold filtering.

This script validates the retrieval filter functionality.
"""

import unittest
from src.utils.retrieval_filter import (
    filter_retrieval_by_similarity,
    validate_similarity_threshold,
    get_similarity_distribution
)


class TestSimilarityFilter(unittest.TestCase):
    """Test cases for similarity threshold filtering."""

    def test_filter_high_quality_results(self):
        """Test filtering with high-quality results."""
        # Create mock results with varying scores
        results = [
            {'content': {'text': 'Doc 1'}, 'score': 0.85},
            {'content': {'text': 'Doc 2'}, 'score': 0.78},
            {'content': {'text': 'Doc 3'}, 'score': 0.72},
            {'content': {'text': 'Doc 4'}, 'score': 0.65},
            {'content': {'text': 'Doc 5'}, 'score': 0.58},
            {'content': {'text': 'Doc 6'}, 'score': 0.45},
        ]
        
        filtered, metadata = filter_retrieval_by_similarity(
            results=results,
            threshold=0.6,
            min_results=3,
            max_results=8
        )
        
        # Should filter out scores < 0.6
        self.assertEqual(len(filtered), 4)
        self.assertEqual(metadata['original_count'], 6)
        self.assertEqual(metadata['filtered_count'], 4)
        self.assertEqual(metadata['threshold_used'], 0.6)
        self.assertFalse(metadata['fallback_used'])
        print("\n✅ High-quality filtering test passed")
        print(f"   Original: {metadata['original_count']}, Filtered: {metadata['filtered_count']}")
        print(f"   Average score: {metadata['avg_filtered_score']}")

    def test_filter_with_fallback(self):
        """Test filtering with fallback to lower threshold."""
        # Create mock results with mostly low scores
        results = [
            {'content': {'text': 'Doc 1'}, 'score': 0.55},
            {'content': {'text': 'Doc 2'}, 'score': 0.52},
            {'content': {'text': 'Doc 3'}, 'score': 0.51},
            {'content': {'text': 'Doc 4'}, 'score': 0.48},
            {'content': {'text': 'Doc 5'}, 'score': 0.45},
        ]
        
        filtered, metadata = filter_retrieval_by_similarity(
            results=results,
            threshold=0.6,
            min_results=3,
            max_results=8
        )
        
        # Should fall back to 0.5 threshold and get 3 results
        self.assertEqual(len(filtered), 3)
        self.assertTrue(metadata['fallback_used'])
        self.assertEqual(metadata['threshold_used'], 0.5)
        print("\n✅ Fallback threshold test passed")
        print(f"   Threshold used: {metadata['threshold_used']}")
        print(f"   Fallback used: {metadata['fallback_used']}")
        print(f"   Results: {len(filtered)}")

    def test_filter_empty_results(self):
        """Test filtering with empty results."""
        results = []
        
        filtered, metadata = filter_retrieval_by_similarity(
            results=results,
            threshold=0.6,
            min_results=3,
            max_results=8
        )
        
        self.assertEqual(len(filtered), 0)
        self.assertEqual(metadata['original_count'], 0)
        print("\n✅ Empty results test passed")

    def test_filter_max_results_limit(self):
        """Test that max_results limit is enforced."""
        # Create 15 results
        results = [
            {'content': {'text': f'Doc {i}'}, 'score': 0.9 - (i * 0.01)}
            for i in range(15)
        ]
        
        filtered, metadata = filter_retrieval_by_similarity(
            results=results,
            threshold=0.5,
            min_results=3,
            max_results=8
        )
        
        # Should limit to 8 results
        self.assertEqual(len(filtered), 8)
        self.assertEqual(metadata['filtered_count'], 8)
        print("\n✅ Max results limit test passed")
        print(f"   Limited to: {metadata['filtered_count']} results")

    def test_validate_threshold(self):
        """Test threshold validation."""
        # Valid thresholds
        self.assertTrue(validate_similarity_threshold(0.5))
        self.assertTrue(validate_similarity_threshold(0.6))
        self.assertTrue(validate_similarity_threshold(0.8))
        self.assertTrue(validate_similarity_threshold(1.0))
        
        # Invalid thresholds
        self.assertFalse(validate_similarity_threshold(-0.1))
        self.assertFalse(validate_similarity_threshold(1.5))
        self.assertFalse(validate_similarity_threshold("0.6"))
        
        print("\n✅ Threshold validation test passed")

    def test_similarity_distribution(self):
        """Test similarity distribution analysis."""
        results = [
            {'content': {'text': 'Doc 1'}, 'score': 0.85},
            {'content': {'text': 'Doc 2'}, 'score': 0.78},
            {'content': {'text': 'Doc 3'}, 'score': 0.72},
            {'content': {'text': 'Doc 4'}, 'score': 0.65},
            {'content': {'text': 'Doc 5'}, 'score': 0.58},
        ]
        
        distribution = get_similarity_distribution(results)
        
        self.assertEqual(distribution['count'], 5)
        self.assertEqual(distribution['min'], 0.58)
        self.assertEqual(distribution['max'], 0.85)
        self.assertAlmostEqual(distribution['avg'], 0.716, places=2)
        
        print("\n✅ Distribution analysis test passed")
        print(f"   Min: {distribution['min']}, Max: {distribution['max']}")
        print(f"   Avg: {distribution['avg']}, Median: {distribution['median']}")

    def test_real_world_scenario(self):
        """Test a real-world scenario with mixed quality results."""
        # Simulate typical retrieval results
        results = [
            {'content': {'text': 'Highly relevant doc'}, 'score': 0.92},
            {'content': {'text': 'Relevant doc'}, 'score': 0.78},
            {'content': {'text': 'Somewhat relevant'}, 'score': 0.65},
            {'content': {'text': 'Marginally relevant'}, 'score': 0.58},
            {'content': {'text': 'Low relevance'}, 'score': 0.45},
            {'content': {'text': 'Very low relevance'}, 'score': 0.32},
        ]
        
        filtered, metadata = filter_retrieval_by_similarity(
            results=results,
            threshold=0.6,
            min_results=3,
            max_results=8
        )
        
        # Should keep top 3 results
        self.assertEqual(len(filtered), 3)
        self.assertGreaterEqual(filtered[0]['score'], 0.6)
        
        print("\n✅ Real-world scenario test passed")
        print(f"   Retrieved: {metadata['original_count']} docs")
        print(f"   Filtered to: {metadata['filtered_count']} docs")
        print(f"   Average score: {metadata['avg_filtered_score']}")
        print(f"   Scores: {metadata['scores']}")


if __name__ == '__main__':
    print("="*80)
    print("SIMILARITY THRESHOLD FILTERING TEST SUITE")
    print("="*80)
    
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSimilarityFilter))
    
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print("\n" + "="*80)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        for test, traceback in result.failures:
            print(f"\nFailed: {test}")
            print(traceback)
    print("="*80)

