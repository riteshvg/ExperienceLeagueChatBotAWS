#!/usr/bin/env python3
"""
Add CJA and AEP files to existing metadata registry
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

def add_cja_aep_to_registry():
    """Add CJA and AEP files to existing registry"""
    
    settings = get_settings()
    s3_client = boto3.client('s3', region_name=settings.aws_default_region)
    
    # Load existing registry
    registry_path = 'data/metadata_registry.json'
    with open(registry_path, 'r', encoding='utf-8') as f:
        registry = json.load(f)
    
    print(f"📊 Current registry size: {len(registry)} entries")
    
    # Process CJA files
    print("🔍 Processing CJA files...")
    cja_response = s3_client.list_objects_v2(Bucket=settings.aws_s3_bucket, Prefix='adobe-docs/customer-journey-analytics/')
    cja_files = [obj['Key'] for obj in cja_response.get('Contents', []) if obj['Key'].endswith('.md')]
    
    # Process AEP files  
    print("🔍 Processing AEP files...")
    aep_response = s3_client.list_objects_v2(Bucket=settings.aws_s3_bucket, Prefix='adobe-docs/experience-platform/')
    aep_files = [obj['Key'] for obj in aep_response.get('Contents', []) if obj['Key'].endswith('.md')]
    
    all_files = cja_files + aep_files
    print(f"📊 Found {len(cja_files)} CJA files and {len(aep_files)} AEP files")
    
    added_count = 0
    skipped_count = 0
    
    for key in all_files:
        try:
            # Check if already exists
            if key in registry:
                skipped_count += 1
                continue
            
            # Skip certain files
            if any(skip in key for skip in ['README.md', 'metadata.md', '_includes/']):
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
    print(f"\n📊 FINAL COVERAGE:")
    
    # Count by product
    products = {}
    for key, data in registry.items():
        product = data.get('product', 'Unknown')
        products[product] = products.get(product, 0) + 1
    
    for product, count in products.items():
        print(f"  {product}: {count} entries")
    
    # Calculate coverage percentages
    print(f"\n📊 COVERAGE PERCENTAGES:")
    
    # CJA Coverage
    registry_cja_count = len([k for k, v in registry.items() if v.get('product') == 'Customer Journey Analytics'])
    cja_coverage = registry_cja_count / len(cja_files) * 100
    print(f"  CJA: {registry_cja_count}/{len(cja_files)} ({cja_coverage:.1f}%)")
    
    # AEP Coverage
    registry_aep_count = len([k for k, v in registry.items() if v.get('product') == 'Adobe Experience Platform'])
    aep_coverage = registry_aep_count / len(aep_files) * 100
    print(f"  AEP: {registry_aep_count}/{len(aep_files)} ({aep_coverage:.1f}%)")

if __name__ == "__main__":
    add_cja_aep_to_registry()
