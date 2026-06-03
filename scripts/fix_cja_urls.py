#!/usr/bin/env python3
"""
Fix CJA URLs in existing metadata registry.
Updates only the CJA entries with correct URL format.
"""

import json
import re
from pathlib import Path

def fix_cja_url(s3_key: str) -> str:
    """Generate correct CJA URL using the same logic as citation_mapper_fallback.py"""
    # Remove bucket prefix
    path = s3_key.replace('adobe-docs/', '')
    
    # Customer Journey Analytics - Use correct /using/cja- prefix
    if 'customer-journey-analytics/help' in path:
        # Remove prefixes
        clean = path.replace('customer-journey-analytics/help/cja-main/', '')
        clean = clean.replace('customer-journey-analytics/help/', '')
        clean = clean.replace('.md', '')
        
        # Extract section (first folder)
        parts = clean.split('/')
        if not parts:
            return f"https://experienceleague.adobe.com/en/docs/analytics-platform/using/{clean}"
        
        section = parts[0]
        rest_of_path = '/'.join(parts[1:]) if len(parts) > 1 else ''
        
        # Map sections to CJA format
        section_mapping = {
            'data-views': 'cja-dataviews',
            'connections': 'cja-connections', 
            'components': 'cja-components',
            'getting-started': 'cja-overview',
            'analysis-workspace': 'cja-workspace',
            'use-cases': 'cja-usecases',
            'architecture': 'cja-architecture',
            'exporting': 'cja-exporting',
            'video-clips': 'cja-videos',
            'cja-basics': 'cja-basics'
        }
        
        # Apply mapping
        if section in section_mapping:
            section = section_mapping[section]
        elif not section.startswith('cja-'):
            section = f'cja-{section}'
        
        # Build full path with /using/ prefix
        if rest_of_path:
            full_path = f"using/{section}/{rest_of_path}"
        else:
            full_path = f"using/{section}"
        
        return f"https://experienceleague.adobe.com/en/docs/analytics-platform/{full_path}"
    
    return None

def fix_cja_urls_in_registry(registry_path: str = 'data/metadata_registry.json'):
    """Fix CJA URLs in the metadata registry"""
    print("🔧 Fixing CJA URLs in metadata registry...")
    
    # Load registry
    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    
    fixed_count = 0
    total_cja = 0
    
    # Fix CJA entries
    for key, metadata in registry.items():
        if 'customer-journey-analytics' in key.lower() or 'cja' in key.lower():
            total_cja += 1
            
            # Skip non-help files (like code-of-conduct.md)
            if 'help/' not in key:
                continue
                
            # Generate correct URL
            correct_url = fix_cja_url(key)
            
            if correct_url:
                old_url = metadata.get('experience_league_url', 'N/A')
                metadata['experience_league_url'] = correct_url
                fixed_count += 1
                
                print(f"✅ Fixed: {metadata.get('title', 'Unknown')}")
                print(f"   Old: {old_url}")
                print(f"   New: {correct_url}")
                print()
    
    # Save updated registry
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    
    print(f"🎉 Fixed {fixed_count} CJA URLs out of {total_cja} CJA entries")
    print(f"📁 Updated registry saved to {registry_path}")

if __name__ == '__main__':
    fix_cja_urls_in_registry()
