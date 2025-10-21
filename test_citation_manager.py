#!/usr/bin/env python3
"""
Test script for Citation Manager
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.citation_manager import citation_manager

def test_s3_uri_conversion():
    """Test S3 URI to URL conversion."""
    print("=" * 80)
    print("TESTING S3 URI TO URL CONVERSION")
    print("=" * 80)
    
    test_cases = [
        "s3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/metrics/overview.md",
        "s3://experienceleaguechatbot/adobe-docs/customer-journey-analytics/help/data-views/create-dataview.md",
        "s3://experienceleaguechatbot/aep/sources/connectors/adobe-applications/analytics.md",
        "s3://experienceleaguechatbot/adobe-docs/analytics-apis/docs/2.0/getting-started.md",
    ]
    
    for s3_uri in test_cases:
        print(f"\n🔍 Testing: {s3_uri}")
        experience_league_url, github_url = citation_manager.s3_uri_to_url(s3_uri)
        
        if experience_league_url:
            print(f"✅ Experience League: {experience_league_url}")
            print(f"✅ GitHub: {github_url}")
        else:
            print(f"❌ Failed to convert URL")
    
    print("\n" + "=" * 80)

def test_citation_extraction():
    """Test citation extraction from mock documents."""
    print("\nTESTING CITATION EXTRACTION")
    print("=" * 80)
    
    # Mock retrieval results
    mock_documents = [
        {
            'content': {'text': 'This is about Customer Journey Analytics segments and how to create them...'},
            'score': 0.85,
            'location': {
                's3Location': {
                    'uri': 's3://experienceleaguechatbot/adobe-docs/customer-journey-analytics/help/components/filters/create-filters.md'
                }
            }
        },
        {
            'content': {'text': 'Adobe Analytics eVars (conversion variables) are used to track custom values...'},
            'score': 0.78,
            'location': {
                's3Location': {
                    'uri': 's3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/dimensions/evar.md'
                }
            }
        },
        {
            'content': {'text': 'Calculated metrics in Adobe Analytics allow you to create custom metrics...'},
            'score': 0.72,
            'location': {
                's3Location': {
                    'uri': 's3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/components/calculated-metrics/overview.md'
                }
            }
        },
        {
            'content': {'text': 'Low quality result that should still be included.'},
            'score': 0.55,
            'location': {
                's3Location': {
                    'uri': 's3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/getting-started.md'
                }
            }
        }
    ]
    
    print(f"\n🔍 Extracting citations from {len(mock_documents)} documents...\n")
    
    citations = citation_manager.extract_citations(mock_documents)
    
    print(f"✅ Extracted {len(citations)} citations:")
    for citation in citations:
        print(f"\n{citation['id']}. {citation['title']}")
        print(f"   URL: {citation['experience_league_url']}")
        print(f"   Relevance: {citation['score']:.0%}")
        print(f"   Preview: {citation['preview'][:100]}...")
    
    print("\n" + "=" * 80)

def test_citation_formatting():
    """Test citation formatting (markdown and HTML)."""
    print("\nTESTING CITATION FORMATTING")
    print("=" * 80)
    
    mock_citations = [
        {
            'id': 1,
            'title': 'Create Filters',
            'experience_league_url': 'https://experienceleague.adobe.com/en/docs/analytics-platform/components/filters/create-filters',
            'github_url': 'https://github.com/AdobeDocs/analytics-platform.en/blob/master/help/components/filters/create-filters.md',
            'score': 0.85,
            'preview': 'This is about Customer Journey Analytics segments...'
        },
        {
            'id': 2,
            'title': 'Evar',
            'experience_league_url': 'https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar',
            'github_url': 'https://github.com/AdobeDocs/analytics.en/blob/master/help/components/dimensions/evar.md',
            'score': 0.78,
            'preview': 'Adobe Analytics eVars (conversion variables)...'
        }
    ]
    
    print("\n📝 Markdown Format:")
    print("-" * 80)
    markdown = citation_manager.format_citations_markdown(mock_citations)
    print(markdown)
    
    print("\n" + "=" * 80)
    print("\n🌐 HTML Format:")
    print("-" * 80)
    html = citation_manager.format_citations_html(mock_citations)
    print(html)
    
    print("\n" + "=" * 80)

def test_title_extraction():
    """Test title extraction from URLs."""
    print("\nTESTING TITLE EXTRACTION")
    print("=" * 80)
    
    test_urls = [
        "https://experienceleague.adobe.com/en/docs/analytics-platform/components/filters/create-filters",
        "https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar",
        "https://experienceleague.adobe.com/en/docs/analytics/components/calculated-metrics/overview",
        "https://experienceleague.adobe.com/en/docs/experience-platform/sources/connectors/adobe-applications/analytics",
    ]
    
    for url in test_urls:
        title = citation_manager._extract_title_from_url(url)
        print(f"\n📄 URL: {url}")
        print(f"   Title: {title}")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    print("\n")
    print("=" * 80)
    print("CITATION MANAGER TEST SUITE")
    print("=" * 80)
    
    test_s3_uri_conversion()
    test_citation_extraction()
    test_citation_formatting()
    test_title_extraction()
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED!")
    print("=" * 80)
    print("\n💡 Citation Manager Features:")
    print("   • S3 URI → Experience League URL conversion")
    print("   • S3 URI → GitHub URL conversion")
    print("   • Automatic citation extraction")
    print("   • Markdown formatting")
    print("   • HTML formatting")
    print("   • Title extraction from URLs")
    print("   • Duplicate URL detection")
    print("   • Relevance score display")
    print("\n")

