#!/usr/bin/env python3
"""
Fix CJA URLs in metadata registry by removing extra customer-journey-analytics path segment.

The correct CJA URL structure is:
- https://experienceleague.adobe.com/en/docs/customer-journey-analytics-learn/tutorials/section/file

NOT:
- https://experienceleague.adobe.com/en/docs/customer-journey-analytics-learn/tutorials/customer-journey-analytics/section/file
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional

def fix_cja_url_path(url: str) -> str:
    """Remove extra customer-journey-analytics path segment from CJA URLs"""
    if not url or 'customer-journey-analytics-learn' not in url:
        return url
    
    # Pattern: /tutorials/customer-journey-analytics/section/file
    # Should be: /tutorials/section/file
    pattern = r'/tutorials/customer-journey-analytics/([^/]+)/(.*)'
    match = re.search(pattern, url)
    
    if match:
        section = match.group(1)
        rest_of_path = match.group(2)
        fixed_url = url.replace(f'/tutorials/customer-journey-analytics/{section}/{rest_of_path}', 
                               f'/tutorials/{section}/{rest_of_path}')
        return fixed_url
    
    return url

def fix_cja_urls_in_registry(registry_path: str = 'data/metadata_registry.json'):
    """Fix CJA URLs by removing extra path segment"""
    try:
        print("🔧 Loading metadata registry...")
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
        
        fixed_count = 0
        total_cja_entries = 0
        
        print("🔍 Processing CJA entries...")
        for key, metadata in registry.items():
            if 'customer-journey-analytics' in key.lower():
                total_cja_entries += 1
                
                # Skip non-help files
                if 'help/' not in key:
                    continue
                
                old_url = metadata.get('experience_league_url', '')
                if old_url and 'customer-journey-analytics-learn' in old_url:
                    new_url = fix_cja_url_path(old_url)
                    
                    if new_url != old_url:
                        metadata['experience_league_url'] = new_url
                        fixed_count += 1
                        
                        print(f"✅ Fixed: {metadata.get('title', 'Unknown')}")
                        print(f"   Old: {old_url}")
                        print(f"   New: {new_url}")
                        print()
        
        # Save updated registry
        print(f"💾 Saving updated registry...")
        with open(registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        
        print(f"🎉 Fixed {fixed_count} CJA URLs out of {total_cja_entries} CJA entries")
        print(f"📁 Updated registry saved to {registry_path}")
        
        return fixed_count
        
    except Exception as e:
        print(f"❌ Error fixing CJA URLs: {e}")
        return 0

if __name__ == '__main__':
    print("🔧 Fixing CJA URLs by removing extra path segment...")
    print("=" * 60)
    
    fixed_count = fix_cja_urls_in_registry()
    
    if fixed_count > 0:
        print(f"\n✅ Successfully fixed {fixed_count} CJA URLs")
        print("🚀 CJA citations should now work correctly!")
    else:
        print("\n❌ No CJA URLs were fixed")
