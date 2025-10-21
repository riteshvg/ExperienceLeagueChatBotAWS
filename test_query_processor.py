"""
Unit tests for Query Preprocessing Module

This module tests the query preprocessing functionality including
abbreviation expansion and contextual enhancement.
"""

import unittest
from src.utils.query_processor import QueryProcessor, preprocess_query, validate_query


class TestQueryProcessor(unittest.TestCase):
    """Test cases for query preprocessing functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = QueryProcessor()

    def test_basic_abbreviation_expansion(self):
        """Test basic abbreviation expansion."""
        test_cases = [
            ("how to create cja segment", True),  # Should expand cja
            ("aa vs cja", True),  # Should expand both
            ("evar not working", True),  # Should expand evar
            ("prop traffic variable", False),  # Won't expand prop (redundancy check)
            ("workspace analysis", False),  # No ws abbreviation to expand
        ]
        
        for original, should_modify in test_cases:
            with self.subTest(original=original):
                enhanced, metadata = self.processor.preprocess_query(original)
                print(f"\n✅ Test: '{original}' → '{enhanced}'")
                self.assertEqual(metadata['was_modified'], should_modify)

    def test_contextual_enhancements(self):
        """Test contextual enhancement patterns."""
        test_cases = [
            ("how to create segment", True, ['step-by-step']),
            ("difference between aa and cja", True, ['comparison']),
            ("evar error", True, ['troubleshooting']),
            ("best practice for cja", True, ['recommendations']),
            ("what is workspace", True, ['definition']),
        ]
        
        for original, should_modify, expected_keywords in test_cases:
            with self.subTest(original=original):
                enhanced, metadata = self.processor.preprocess_query(original)
                print(f"\n✅ Context Test: '{original}' → '{enhanced}'")
                self.assertEqual(metadata['was_modified'], should_modify)
                # Check that at least one expected keyword is present
                found_keyword = any(keyword in enhanced for keyword in expected_keywords)
                self.assertTrue(found_keyword, f"Expected one of {expected_keywords} in enhanced query")

    def test_complex_queries(self):
        """Test complex queries with multiple expansions."""
        test_cases = [
            {
                'input': "how to create cja segment in aa workspace",
                'expected_contains': ['Customer Journey Analytics', 'Adobe Analytics', 'step-by-step']
            },
            {
                'input': "evar vs prop difference",
                'expected_contains': ['eVar', 'prop', 'comparison']
            },
            {
                'input': "cja error troubleshooting",
                'expected_contains': ['Customer Journey Analytics', 'troubleshooting']
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(input=test_case['input']):
                enhanced, metadata = self.processor.preprocess_query(test_case['input'])
                print(f"\n✅ Complex Test: '{test_case['input']}' → '{enhanced}'")
                
                for expected in test_case['expected_contains']:
                    self.assertIn(expected, enhanced, f"Expected '{expected}' in enhanced query")

    def test_preserve_quotes(self):
        """Test that abbreviations inside quotes are preserved."""
        test_cases = [
            ('"cja" is great', '"cja" is great'),  # Should preserve quotes
            ("'aa' vs cja", "'aa' vs Customer Journey Analytics"),  # Only expand outside quotes
        ]
        
        for original, expected_pattern in test_cases:
            with self.subTest(original=original):
                enhanced, metadata = self.processor.preprocess_query(original)
                print(f"\n✅ Quote Test: '{original}' → '{enhanced}'")
                # Check that quoted abbreviations are preserved
                if '"cja"' in original:
                    self.assertIn('"cja"', enhanced)
                if "'aa'" in original:
                    self.assertIn("'aa'", enhanced)

    def test_case_insensitive_matching(self):
        """Test case-insensitive abbreviation matching."""
        test_cases = [
            ("CJA segment", True),  # Should expand CJA
            ("AA workspace", True),  # Should expand AA
            ("EVAR conversion", True),  # Should expand EVAR
            ("PROP traffic", True),  # Will expand PROP (case-insensitive)
        ]
        
        for original, should_modify in test_cases:
            with self.subTest(original=original):
                enhanced, metadata = self.processor.preprocess_query(original)
                print(f"\n✅ Case Test: '{original}' → '{enhanced}'")
                self.assertEqual(metadata['was_modified'], should_modify)

    def test_no_redundant_expansion(self):
        """Test that redundant expansions are avoided."""
        test_cases = [
            ("Customer Journey Analytics segment", "Customer Journey Analytics segment"),  # Already expanded
            ("Adobe Analytics workspace", "Adobe Analytics workspace"),  # Already expanded
        ]
        
        for original, expected in test_cases:
            with self.subTest(original=original):
                enhanced, metadata = self.processor.preprocess_query(original)
                print(f"\n✅ No Redundancy Test: '{original}' → '{enhanced}'")
                # Should not add redundant expansions
                self.assertNotIn("Customer Journey Analytics Customer Journey Analytics", enhanced)
                self.assertNotIn("Adobe Analytics Adobe Analytics", enhanced)

    def test_empty_and_invalid_queries(self):
        """Test handling of empty and invalid queries."""
        test_cases = [
            "",
            "   ",
            "a",  # Too short but should still work
        ]
        
        for original in test_cases:
            with self.subTest(original=original):
                enhanced, metadata = self.processor.preprocess_query(original)
                print(f"\n✅ Empty Test: '{original}' → '{enhanced}'")
                self.assertIsInstance(enhanced, str)

    def test_metadata_structure(self):
        """Test that metadata has correct structure."""
        enhanced, metadata = self.processor.preprocess_query("how to create cja segment")
        
        required_keys = [
            'original', 'enhanced', 'changes', 'abbreviation_expansions',
            'contextual_enhancements', 'was_modified'
        ]
        
        for key in required_keys:
            self.assertIn(key, metadata, f"Missing key: {key}")
        
        print(f"\n✅ Metadata Test: {metadata}")
        self.assertIsInstance(metadata['changes'], list)
        self.assertIsInstance(metadata['abbreviation_expansions'], int)
        self.assertIsInstance(metadata['contextual_enhancements'], int)
        self.assertIsInstance(metadata['was_modified'], bool)

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Test preprocess_query function
        enhanced, metadata = preprocess_query("cja segment")
        self.assertIsInstance(enhanced, str)
        self.assertIsInstance(metadata, dict)
        
        # Test validate_query function
        validation = validate_query("test query")
        self.assertIn('valid', validation)
        
        print(f"\n✅ Convenience Test: Enhanced='{enhanced}', Valid={validation['valid']}")

    def test_custom_abbreviation(self):
        """Test adding custom abbreviations."""
        # Add custom abbreviation
        self.processor.add_custom_abbreviation("test", "testing expansion")
        
        # Test it works
        enhanced, metadata = self.processor.preprocess_query("test query")
        self.assertIn("testing expansion", enhanced)
        
        print(f"\n✅ Custom Abbreviation Test: 'test query' → '{enhanced}'")

    def test_real_world_scenarios(self):
        """Test real-world query scenarios."""
        real_queries = [
            "how to create cja segment for mobile users",
            "aa vs cja which is better",
            "evar not tracking properly troubleshooting",
            "best practices for aa implementation",
            "what is workspace in adobe analytics",
            "how to set up aep data source",
            "prop vs evar difference",
            "cja error message not showing data",
            "aa workspace freeform table",
            "evar conversion tracking setup"
        ]
        
        for query in real_queries:
            with self.subTest(query=query):
                enhanced, metadata = self.processor.preprocess_query(query)
                print(f"\n✅ Real-world Test: '{query}' → '{enhanced}'")
                
                # Should have some enhancements
                self.assertTrue(len(enhanced) >= len(query))
                
                # Should have metadata
                self.assertIsInstance(metadata, dict)
                self.assertIn('was_modified', metadata)

    def test_abbreviation_list(self):
        """Test getting abbreviation list."""
        abbreviations = self.processor.get_abbreviation_list()
        
        # Should contain expected abbreviations
        expected_abbreviations = ['cja', 'aa', 'aep', 'evar', 'prop', 'seg']
        
        for abbr in expected_abbreviations:
            self.assertIn(abbr, abbreviations, f"Missing abbreviation: {abbr}")
        
        print(f"\n✅ Abbreviation List Test: Found {len(abbreviations)} abbreviations")
        print(f"   Sample: {list(abbreviations.items())[:5]}")

    def test_query_validation(self):
        """Test query validation functionality."""
        test_cases = [
            ("valid query", True),
            ("", False),
            ("ab", False),  # Too short
            ("a" * 1001, False),  # Too long
        ]
        
        for query, should_be_valid in test_cases:
            with self.subTest(query=query):
                validation = validate_query(query)
                self.assertEqual(validation['valid'], should_be_valid)
                print(f"\n✅ Validation Test: '{query}' → Valid: {validation['valid']}")


if __name__ == '__main__':
    print("="*80)
    print("QUERY PREPROCESSING TEST SUITE")
    print("="*80)
    
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestQueryProcessor))
    
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print("\n" + "="*80)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        print("\n📊 Test Summary:")
        print(f"   • Tests run: {result.testsRun}")
        print(f"   • Failures: {len(result.failures)}")
        print(f"   • Errors: {len(result.errors)}")
    else:
        print(f"❌ {len(result.failures)} test(s) failed")
        for test, traceback in result.failures:
            print(f"\nFailed: {test}")
            print(traceback)
    print("="*80)
