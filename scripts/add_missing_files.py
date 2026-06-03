#!/usr/bin/env python3
"""
Add missing files to metadata registry for 100% coverage
"""

import json
import boto3
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from scripts.extract_metadata_from_s3 import (
    extract_frontmatter, 
    extract_h1_title, 
    generate_title, 
    identify_product,
    generate_experience_league_url,
    generate_github_url
)

def add_missing_files_to_registry():
    """Add missing files to metadata registry"""
    
    settings = get_settings()
    s3_client = boto3.client('s3', region_name=settings.aws_default_region)
    
    # Load existing registry
    registry_path = 'data/metadata_registry.json'
    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    
    print(f"📊 Current registry size: {len(registry)} entries")
    
    # Missing CJA files
    missing_cja_files = [
        'adobe-docs/customer-journey-analytics/help/cja-main/TOC.md',
        'adobe-docs/customer-journey-analytics/help/cja-main/components/calc-metrics/moving-your-calculated-metrics-from-adobe-analytics-to-customer-journey-analytics.md',
        'adobe-docs/customer-journey-analytics/help/cja-main/components/filters/moving-adobe-analytics-segments-to-customer-journey-analytics.md',
        'adobe-docs/customer-journey-analytics/help/cja-main/data-prep/ingest-map-and-transform-adobe-analytics-data.md',
        'adobe-docs/customer-journey-analytics/help/video-clips/TOC.md',
        'adobe-docs/customer-journey-analytics/metadata.md'
    ]
    
    # Missing AEP files
    missing_aep_files = [
        'adobe-docs/experience-platform/README.md',
        'adobe-docs/experience-platform/help/_includes/record-delete-quotas-and-entitlements.md',
        'adobe-docs/experience-platform/help/access-control/TOC.md',
        'adobe-docs/experience-platform/help/accessibility/TOC.md',
        'adobe-docs/experience-platform/help/administrative-tags/TOC.md',
        'adobe-docs/experience-platform/help/ai-assistant/TOC.md',
        'adobe-docs/experience-platform/help/assurance/TOC.md',
        'adobe-docs/experience-platform/help/assurance/views/adobe-analytics-streaming-media.md',
        'adobe-docs/experience-platform/help/assurance/views/adobe-analytics.md',
        'adobe-docs/experience-platform/help/catalog/TOC.md',
        'adobe-docs/experience-platform/help/data-governance/TOC.md',
        'adobe-docs/experience-platform/help/data-science-workspace/TOC.md',
        'adobe-docs/experience-platform/help/destinations/TOC.md',
        'adobe-docs/experience-platform/help/edge-network/TOC.md'
    ]
    
    all_missing_files = missing_cja_files + missing_aep_files
    
    print(f"🔍 Processing {len(all_missing_files)} missing files...")
    
    added_count = 0
    skipped_count = 0
    
    for key in all_missing_files:
        try:
            # Check if already exists
            if key in registry:
                print(f"⏭️  Skipping {key} (already exists)")
                skipped_count += 1
                continue
            
            # Fetch file content from S3
            response = s3_client.get_object(Bucket=settings.aws_s3_bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            
            # Extract metadata
            frontmatter = extract_frontmatter(content)
            h1_title = extract_h1_title(content)
            
            # Generate title
            title = generate_title(key, frontmatter, h1_title)
            
            # Identify product
            product = identify_product(key)
            
            # Build metadata entry
            metadata = {
                # Identification
                'source_file': key,
                's3_key': key,
                'doc_id': frontmatter.get('exl-id', f"generated-{hash(key)}"),
                
                # URLs
                'experience_league_url': generate_experience_league_url(key),
                'github_url': generate_github_url(key),
                
                # Content metadata
                'title': title,
                'description': frontmatter.get('description', ''),
                
                # Classification
                'product': product,
                'feature': frontmatter.get('feature', ''),
                'doc_type': frontmatter.get('doc-type', 'Article'),
                'role': frontmatter.get('role', 'User'),
                'level': frontmatter.get('level', 'Beginner'),
                
                # Timestamps
                'last_modified_s3': response['LastModified'].isoformat(),
                'extracted_at': datetime.utcnow().isoformat(),
                
                # Additional
                'keywords': frontmatter.get('keywords', [])
            }
            
            # Add to registry
            registry[key] = metadata
            added_count += 1
            
            print(f"✅ Added {product}: {title}")
            
        except Exception as e:
            print(f"❌ Error processing {key}: {e}")
            continue
    
    # Save updated registry
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 COMPLETED!")
    print(f"📊 Registry size: {len(registry)} entries")
    print(f"✅ Added: {added_count} files")
    print(f"⏭️  Skipped: {skipped_count} files")
    
    # Verify coverage
    print(f"\n📊 VERIFICATION:")
    
    # Count by product
    products = {}
    for key, data in registry.items():
        product = data.get('product', 'Unknown')
        products[product] = products.get(product, 0) + 1
    
    for product, count in products.items():
        print(f"  {product}: {count} entries")

if __name__ == "__main__":
    add_missing_files_to_registry()
