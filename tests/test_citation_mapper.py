#!/usr/bin/env python3
"""
Unit tests for Citation Mapper

Tests URL mapping from AWS Bedrock KB metadata to Experience League URLs.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.citation_mapper import (
    extract_path_from_metadata,
    map_to_experience_league_url,
    extract_title_from_metadata,
    format_citation,
    _extract_path_from_s3_uri,
    _map_adobe_analytics_url,
    _map_cja_url,
    _map_aep_url,
    _map_analytics_api_url,
    _generate_github_url
)


class TestCitationMapper(unittest.TestCase):
    """Test suite for citation mapper functionality."""
    
    # C2: Test Adobe Analytics URL mapping
    def test_adobe_analytics_url_mapping(self):
        """Test Adobe Analytics URL mapping."""
        print("\n" + "="*80)
        print("C2: TESTING ADOBE ANALYTICS URL MAPPING")
        print("="*80)
        
        test_cases = [
            {
                'input': 'adobe-docs/adobe-analytics/help/components/segments/seg-workflow.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/analytics/components/segments/seg-workflow',
                'name': 'Segment Workflow'
            },
            {
                'input': 'adobe-docs/adobe-analytics/help/admin/admin-console/permissions/product-profile.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/analytics/admin/admin-console/permissions/product-profile',
                'name': 'Product Profile'
            },
            {
                'input': 'adobe-docs/adobe-analytics/help/components/dimensions/evar.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar',
                'name': 'eVar Dimension'
            },
            {
                'input': 'adobe-docs/adobe-analytics/help/analyze/analysis-workspace/home.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/analytics/analyze/analysis-workspace/home',
                'name': 'Analysis Workspace Home'
            }
        ]
        
        for case in test_cases:
            result = _map_adobe_analytics_url(case['input'])
            print(f"\n✓ Test: {case['name']}")
            print(f"  Input:    {case['input']}")
            print(f"  Expected: {case['expected']}")
            print(f"  Got:      {result}")
            self.assertEqual(result, case['expected'], f"Failed for {case['name']}")
        
        print("\n✅ All Adobe Analytics URL mappings passed!")
    
    # C3: Test Customer Journey Analytics URL mapping
    def test_cja_url_mapping(self):
        """Test Customer Journey Analytics URL mapping with cja- prefix verification."""
        print("\n" + "="*80)
        print("C3: TESTING CUSTOMER JOURNEY ANALYTICS URL MAPPING")
        print("="*80)
        
        test_cases = [
            {
                'input': 'adobe-docs/customer-journey-analytics/help/cja-main/data-views/create-dataview.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/analytics-platform/data-views/create-dataview',
                'name': 'Data Views'
            },
            {
                'input': 'adobe-docs/customer-journey-analytics/help/cja-main/connections/overview.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/analytics-platform/connections/overview',
                'name': 'Connections Overview'
            },
            {
                'input': 'adobe-docs/customer-journey-analytics/help/cja-main/analysis-workspace/annotations/create-an-annotation.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/analytics-platform/analysis-workspace/annotations/create-an-annotation',
                'name': 'Create Annotation'
            }
        ]
        
        for case in test_cases:
            result = _map_cja_url(case['input'])
            print(f"\n✓ Test: {case['name']}")
            print(f"  Input:    {case['input']}")
            print(f"  Expected: {case['expected']}")
            print(f"  Got:      {result}")
            self.assertEqual(result, case['expected'], f"Failed for {case['name']}")
        
        print("\n✅ All CJA URL mappings passed!")
    
    # C4: Test Adobe Experience Platform URL mapping
    def test_aep_url_mapping(self):
        """Test Adobe Experience Platform URL mapping."""
        print("\n" + "="*80)
        print("C4: TESTING ADOBE EXPERIENCE PLATFORM URL MAPPING")
        print("="*80)
        
        test_cases = [
            {
                'input': 'aep/sources/connectors/adobe-applications/analytics.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/experience-platform/sources/connectors/adobe-applications/analytics',
                'name': 'Analytics Connector'
            },
            {
                'input': 'aep/web-sdk/commands/configure/overview.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/experience-platform/web-sdk/commands/configure/overview',
                'name': 'Web SDK Configure'
            },
            {
                'input': 'aep/destinations/catalog/advertising/google-ads-destination.md',
                'expected': 'https://experienceleague.adobe.com/en/docs/experience-platform/destinations/catalog/advertising/google-ads-destination',
                'name': 'Google Ads Destination'
            }
        ]
        
        for case in test_cases:
            result = _map_aep_url(case['input'])
            print(f"\n✓ Test: {case['name']}")
            print(f"  Input:    {case['input']}")
            print(f"  Expected: {case['expected']}")
            print(f"  Got:      {result}")
            self.assertEqual(result, case['expected'], f"Failed for {case['name']}")
        
        print("\n✅ All AEP URL mappings passed!")
    
    # C5: Test fallback URL when path cannot be determined
    def test_fallback_url(self):
        """Test fallback URL when path cannot be determined."""
        print("\n" + "="*80)
        print("C5: TESTING FALLBACK URL")
        print("="*80)
        
        # Empty metadata
        result = map_to_experience_league_url({})
        print(f"\n✓ Empty metadata")
        print(f"  Expected: https://experienceleague.adobe.com/en/docs/analytics")
        print(f"  Got:      {result}")
        self.assertEqual(result, "https://experienceleague.adobe.com/en/docs/analytics")
        
        # Metadata without location
        result = map_to_experience_league_url({'content': {'text': 'Some text'}})
        print(f"\n✓ No location in metadata")
        print(f"  Expected: https://experienceleague.adobe.com/en/docs/analytics")
        print(f"  Got:      {result}")
        self.assertEqual(result, "https://experienceleague.adobe.com/en/docs/analytics")
        
        print("\n✅ Fallback URL tests passed!")
    
    # C6: Test path extraction from S3 location
    def test_path_extraction_from_s3(self):
        """Test path extraction from S3 location."""
        print("\n" + "="*80)
        print("C6: TESTING PATH EXTRACTION FROM S3")
        print("="*80)
        
        metadata = {
            'location': {
                's3Location': {
                    'uri': 's3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/metrics/overview.md'
                }
            }
        }
        
        path = extract_path_from_metadata(metadata)
        expected = 'adobe-docs/adobe-analytics/help/components/metrics/overview.md'
        
        print(f"\n✓ S3 location extraction")
        print(f"  Input:    {metadata['location']['s3Location']['uri']}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {path}")
        
        self.assertEqual(path, expected)
        print("\n✅ S3 path extraction passed!")
    
    # C7: Test path extraction from direct URI
    def test_path_extraction_from_direct_uri(self):
        """Test path extraction from direct URI field."""
        print("\n" + "="*80)
        print("C7: TESTING PATH EXTRACTION FROM DIRECT URI")
        print("="*80)
        
        metadata = {
            'uri': 's3://experienceleaguechatbot/aep/sources/connectors/adobe-applications/analytics.md'
        }
        
        path = extract_path_from_metadata(metadata)
        expected = 'aep/sources/connectors/adobe-applications/analytics.md'
        
        print(f"\n✓ Direct URI extraction")
        print(f"  Input:    {metadata['uri']}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {path}")
        
        self.assertEqual(path, expected)
        print("\n✅ Direct URI extraction passed!")
    
    # C8: Test edge cases (API docs, learn repos)
    def test_edge_cases(self):
        """Test edge cases including API docs and learn repos."""
        print("\n" + "="*80)
        print("C8: TESTING EDGE CASES")
        print("="*80)
        
        # API documentation
        api_path = 'adobe-docs/analytics-apis/docs/2.0/getting-started.md'
        api_result = _map_analytics_api_url(api_path)
        api_expected = 'https://developer.adobe.com/analytics-apis/docs/2.0/getting-started'
        
        print(f"\n✓ API Documentation")
        print(f"  Input:    {api_path}")
        print(f"  Expected: {api_expected}")
        print(f"  Got:      {api_result}")
        self.assertEqual(api_result, api_expected)
        
        # URL-encoded paths
        encoded_uri = 's3://bucket/path%20with%20spaces/file.md'
        decoded_path = _extract_path_from_s3_uri(encoded_uri)
        print(f"\n✓ URL-encoded path")
        print(f"  Input:    {encoded_uri}")
        print(f"  Got:      {decoded_path}")
        self.assertIn('path with spaces', decoded_path)
        
        # Missing .md extension
        no_md_path = 'adobe-docs/adobe-analytics/help/components/overview'
        no_md_result = _map_adobe_analytics_url(no_md_path)
        print(f"\n✓ Path without .md extension")
        print(f"  Input:    {no_md_path}")
        print(f"  Got:      {no_md_result}")
        self.assertIn('/components/overview', no_md_result)
        
        print("\n✅ All edge cases passed!")
    
    # Additional comprehensive tests
    def test_title_extraction(self):
        """Test title extraction from various sources."""
        print("\n" + "="*80)
        print("TESTING TITLE EXTRACTION")
        print("="*80)
        
        # From markdown content
        metadata_with_heading = {
            'content': {
                'text': '# Segment Workflow Guide\n\nThis guide explains segments...'
            }
        }
        title = extract_title_from_metadata(metadata_with_heading)
        print(f"\n✓ Title from content heading: '{title}'")
        self.assertEqual(title, "Segment Workflow Guide")
        
        # From filename
        metadata_with_path = {
            'location': {
                's3Location': {
                    'uri': 's3://bucket/adobe-docs/adobe-analytics/help/components/calculated-metrics-overview.md'
                }
            }
        }
        title = extract_title_from_metadata(metadata_with_path)
        print(f"\n✓ Title from filename: '{title}'")
        self.assertIn('Calculated Metrics', title)
        
        print("\n✅ Title extraction tests passed!")
    
    def test_complete_citation_formatting(self):
        """Test complete citation formatting."""
        print("\n" + "="*80)
        print("TESTING COMPLETE CITATION FORMATTING")
        print("="*80)
        
        doc_metadata = {
            'content': {
                'text': '# Build segments\n\nSegments in Adobe Analytics allow you to...'
            },
            'score': 0.85,
            'location': {
                's3Location': {
                    'uri': 's3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/segmentation/seg-workflow.md'
                }
            }
        }
        
        citation = format_citation(doc_metadata)
        
        print(f"\n✓ Complete Citation:")
        print(f"  Title:      {citation['title']}")
        print(f"  URL:        {citation['url']}")
        print(f"  Display:    {citation['display']}")
        print(f"  Score:      {citation['score']}")
        print(f"  GitHub URL: {citation['github_url']}")
        
        self.assertEqual(citation['title'], "Build segments")
        self.assertIn('experienceleague.adobe.com/en/docs/analytics', citation['url'])
        self.assertEqual(citation['score'], 0.85)
        self.assertIsNotNone(citation['github_url'])
        self.assertIn('github.com/AdobeDocs', citation['github_url'])
        
        print("\n✅ Complete citation formatting passed!")
    
    def test_github_url_generation(self):
        """Test GitHub URL generation for all products."""
        print("\n" + "="*80)
        print("TESTING GITHUB URL GENERATION")
        print("="*80)
        
        test_cases = [
            {
                'path': 'adobe-docs/adobe-analytics/help/components/metrics/overview.md',
                'expected_contains': 'github.com/AdobeDocs/analytics.en',
                'name': 'Adobe Analytics'
            },
            {
                'path': 'adobe-docs/customer-journey-analytics/help/cja-main/connections/overview.md',
                'expected_contains': 'github.com/AdobeDocs/analytics-platform.en',
                'name': 'CJA'
            },
            {
                'path': 'aep/sources/connectors/adobe-applications/analytics.md',
                'expected_contains': 'github.com/AdobeDocs/experience-platform.en',
                'name': 'AEP'
            }
        ]
        
        for case in test_cases:
            github_url = _generate_github_url(case['path'])
            print(f"\n✓ {case['name']}:")
            print(f"  Path: {case['path']}")
            print(f"  URL:  {github_url}")
            self.assertIsNotNone(github_url)
            self.assertIn(case['expected_contains'], github_url)
        
        print("\n✅ GitHub URL generation passed!")


def run_tests():
    """Run all tests with detailed output."""
    print("\n" + "="*80)
    print("CITATION MAPPER TEST SUITE")
    print("="*80)
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(TestCitationMapper('test_adobe_analytics_url_mapping'))
    suite.addTest(TestCitationMapper('test_cja_url_mapping'))
    suite.addTest(TestCitationMapper('test_aep_url_mapping'))
    suite.addTest(TestCitationMapper('test_fallback_url'))
    suite.addTest(TestCitationMapper('test_path_extraction_from_s3'))
    suite.addTest(TestCitationMapper('test_path_extraction_from_direct_uri'))
    suite.addTest(TestCitationMapper('test_edge_cases'))
    suite.addTest(TestCitationMapper('test_title_extraction'))
    suite.addTest(TestCitationMapper('test_complete_citation_formatting'))
    suite.addTest(TestCitationMapper('test_github_url_generation'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*80)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"   Tests run: {result.testsRun}")
        print(f"   Failures: {len(result.failures)}")
        print(f"   Errors: {len(result.errors)}")
    print("="*80)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

