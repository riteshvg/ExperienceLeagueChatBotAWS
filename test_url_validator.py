#!/usr/bin/env python3
"""
Test URL Validator
"""

import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.url_validator import (
    validate_urls_batch,
    filter_valid_citations,
    get_cache_stats,
    clear_url_cache
)

print("=" * 80)
print("URL VALIDATOR TEST")
print("=" * 80)

# Test URLs (mix of valid and invalid)
test_urls = [
    "https://experienceleague.adobe.com/en/docs/analytics/admin/admin-console/permissions/product-profile",  # Should be 200
    "https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar",  # Should be 200
    "https://experienceleague.adobe.com/en/docs/analytics/invalid/path/that/does/not/exist",  # Should be 404
    "https://experienceleague.adobe.com/en/docs/analytics-platform/connections/overview",  # Check this one
]

print("\n📊 Testing URL Validation (Parallel)...")
print(f"   URLs to test: {len(test_urls)}")
print(f"   Timeout: 3 seconds per URL")
print()

start_time = time.time()
results = validate_urls_batch(test_urls, timeout=3)
elapsed = time.time() - start_time

print(f"\n✅ Validation complete in {elapsed:.2f} seconds")
print(f"   Average time per URL: {elapsed/len(test_urls):.2f}s (parallel)")
print()

# Display results
print("Results:")
for url, (is_valid, status_code) in results.items():
    status_emoji = "✅" if is_valid else "❌"
    short_url = url.split('experienceleague.adobe.com')[-1][:60]
    print(f"  {status_emoji} [{status_code}] ...{short_url}")

# Test citation filtering
print("\n" + "=" * 80)
print("CITATION FILTERING TEST")
print("=" * 80)

mock_citations = [
    {
        'title': 'Product Profiles',
        'url': 'https://experienceleague.adobe.com/en/docs/analytics/admin/admin-console/permissions/product-profile',
        'score': 0.85
    },
    {
        'title': 'eVar Dimension',
        'url': 'https://experienceleague.adobe.com/en/docs/analytics/components/dimensions/evar',
        'score': 0.78
    },
    {
        'title': 'Invalid Page',
        'url': 'https://experienceleague.adobe.com/en/docs/analytics/invalid/path/that/does/not/exist',
        'score': 0.65
    },
]

print(f"\nOriginal citations: {len(mock_citations)}")
print()

valid_citations = filter_valid_citations(mock_citations, validate_urls=True, timeout=3)

print(f"\nFiltered citations: {len(valid_citations)}")
print()

for citation in valid_citations:
    print(f"  ✅ {citation['title']}")
    print(f"     URL: {citation['url']}")
    print(f"     Status: {citation.get('url_status', 'Unknown')}")
    print()

# Cache stats
print("=" * 80)
print("CACHE STATISTICS")
print("=" * 80)

stats = get_cache_stats()
print(f"\nCache Stats:")
print(f"  Total cached: {stats['total_cached']}")
print(f"  Valid: {stats['valid']}")
print(f"  Invalid: {stats['invalid']}")
print(f"  TTL: {stats['cache_ttl_hours']} hours")

# Test cache hit (should be instant)
print("\n" + "=" * 80)
print("CACHE PERFORMANCE TEST")
print("=" * 80)

print("\nSecond validation (should use cache):")
start_time = time.time()
results2 = validate_urls_batch(test_urls[:2], timeout=3)
elapsed2 = time.time() - start_time

print(f"  Time: {elapsed2:.3f}s (cached, should be <0.01s)")

if elapsed2 < 0.1:
    print(f"  ✅ Cache working! ({elapsed2*1000:.1f}ms)")
else:
    print(f"  ⚠️ Cache might not be working ({elapsed2:.3f}s)")

print("\n" + "=" * 80)
print("✅ ALL TESTS COMPLETE!")
print("=" * 80)

