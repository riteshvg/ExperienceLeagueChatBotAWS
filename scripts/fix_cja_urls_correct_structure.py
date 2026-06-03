#!/usr/bin/env python3
"""
Fix CJA URLs in metadata registry with correct Experience League structure.

The correct CJA URL structure is:
- https://experienceleague.adobe.com/en/docs/customer-journey-analytics-learn/tutorials/

NOT:
- https://experienceleague.adobe.com/en/docs/analytics-platform/using/cja-*
"""

import json
import re
from pathlib import Path
from typing import Dict, Optional

def generate_correct_cja_url(s3_key: str) -> str:
    """Generate correct Experience League URL from S3 key for CJA"""
    # Remove bucket prefix
    path = s3_key.replace('adobe-docs/', '')
    
    # Only process CJA files
    if 'customer-journey-analytics' not in path:
        return ""
    
    # Remove help/cja-main/ prefix
    if 'help/cja-main/' in path:
        path = path.replace('help/cja-main/', '')
    elif 'help/' in path:
        path = path.replace('help/', '')
    
    # Remove .md extension
    if path.endswith('.md'):
        path = path[:-3]
    elif path.endswith('.html'):
        path = path[:-5]
    
    # Map CJA sections to correct URL structure
    # Pattern: section/subsection/file -> tutorials/section/subsection/file
    
    # Handle special cases
    if path == 'TOC':
        return "https://experienceleague.adobe.com/en/docs/customer-journey-analytics"
    
    # Map sections to tutorial structure
    section_mapping = {
        'cja-basics': 'cja-basics',
        'architecture': 'architecture', 
        'data-prep': 'data-prep',
        'overview': 'overview',
        'data-views': 'data-views',
        'connections': 'connections',
        'components': 'components',
        'analysis-workspace': 'analysis-workspace',
        'use-cases': 'use-cases',
        'exporting': 'exporting',
        'video-clips': 'video-clips'
    }
    
    # Split path into parts
    parts = path.split('/')
    if not parts or not parts[0]:
        return "https://experienceleague.adobe.com/en/docs/customer-journey-analytics"
    
    section = parts[0]
    rest_of_path = '/'.join(parts[1:]) if len(parts) > 1 else ''
    
    # Apply section mapping
    if section in section_mapping:
        section = section_mapping[section]
    
    # Build correct URL (without extra customer-journey-analytics in path)
    if rest_of_path:
        full_path = f"tutorials/{section}/{rest_of_path}"
    else:
        full_path = f"tutorials/{section}"
    
    return f"https://experienceleague.adobe.com/en/docs/customer-journey-analytics-learn/{full_path}"

def fix_cja_urls_in_registry(registry_path: str = 'data/metadata_registry.json'):
    """Fix CJA URLs in the metadata registry with correct structure"""
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
                
                # Skip non-help files (like code-of-conduct.md)
                if 'help/' not in key:
                    continue
                
                # Generate correct URL
                correct_url = generate_correct_cja_url(key)
                
                if correct_url:
                    old_url = metadata.get('experience_league_url', 'N/A')
                    metadata['experience_league_url'] = correct_url
                    fixed_count += 1
                    
                    print(f"✅ Fixed: {metadata.get('title', 'Unknown')}")
                    print(f"   Old: {old_url}")
                    print(f"   New: {correct_url}")
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
    print("🔧 Fixing CJA URLs with correct Experience League structure...")
    print("=" * 60)
    
    fixed_count = fix_cja_urls_in_registry()
    
    if fixed_count > 0:
        print(f"\n✅ Successfully fixed {fixed_count} CJA URLs")
        print("🚀 CJA citations should now work correctly!")
    else:
        print("\n❌ No CJA URLs were fixed")
