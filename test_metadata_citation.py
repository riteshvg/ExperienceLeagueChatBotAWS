#!/usr/bin/env python3
"""
Test metadata-driven citation mapper
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.citation_mapper import (
    format_citation,
    lookup_metadata_by_path,
    METADATA_REGISTRY,
    get_registry_stats
)

print("=" * 80)
print("METADATA-DRIVEN CITATION MAPPER TEST")
print("=" * 80)

# Check registry loaded
stats = get_registry_stats()
print(f"\n📊 Registry Stats:")
print(f"   Total Documents: {stats['total_documents']}")
print(f"   Has Registry: {stats['has_registry']}")

if stats['products']:
    print(f"\n   Documents by Product:")
    for product, count in stats['products'].items():
        print(f"      • {product}: {count}")

# Test with a known document
print("\n" + "=" * 80)
print("TEST 1: Lookup Known Document")
print("=" * 80)

test_path = "s3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/admin/home.md"
metadata = lookup_metadata_by_path(test_path)

if metadata:
    print(f"✅ Found metadata!")
    print(f"   Title: {metadata['title']}")
    print(f"   URL: {metadata['experience_league_url']}")
    print(f"   Product: {metadata['product']}")
else:
    print(f"❌ No metadata found for: {test_path}")

# Test citation formatting
print("\n" + "=" * 80)
print("TEST 2: Format Citation with Registry")
print("=" * 80)

doc_metadata = {
    'content': {'text': 'Sample content'},
    'score': 0.85,
    'location': {
        's3Location': {
            'uri': 's3://experienceleaguechatbot/adobe-docs/adobe-analytics/help/admin/home.md'
        }
    }
}

citation = format_citation(doc_metadata)

print(f"Citation Generated:")
print(f"   Title: {citation['title']}")
print(f"   URL: {citation['url']}")
print(f"   GitHub: {citation['github_url']}")
print(f"   Product: {citation['product']}")
print(f"   Description: {citation['description']}")
print(f"   Source: {citation['metadata_source']}")
print(f"   Display: {citation['display']}")

# Test fallback
print("\n" + "=" * 80)
print("TEST 3: Fallback for Unknown Document")
print("=" * 80)

unknown_doc = {
    'content': {'text': 'Unknown content'},
    'score': 0.65,
    'location': {
        's3Location': {
            'uri': 's3://bucket/some/unknown/path/document.md'
        }
    }
}

citation_fallback = format_citation(unknown_doc)

print(f"Fallback Citation:")
print(f"   Title: {citation_fallback['title']}")
print(f"   URL: {citation_fallback['url']}")
print(f"   Source: {citation_fallback['metadata_source']}")

# Sample registry entries
print("\n" + "=" * 80)
print("SAMPLE REGISTRY ENTRIES")
print("=" * 80)

for i, (key, metadata) in enumerate(list(METADATA_REGISTRY.items())[:5]):
    print(f"\n{i+1}. {metadata['title']}")
    print(f"   Key: {key}")
    print(f"   URL: {metadata['experience_league_url']}")
    print(f"   Product: {metadata['product']}")

print("\n" + "=" * 80)
print("✅ TESTS COMPLETE!")
print("=" * 80)

