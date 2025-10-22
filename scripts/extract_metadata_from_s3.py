"""
Extract metadata from Adobe documentation files stored in S3.
Creates a metadata registry for all documents.
"""

import os
import sys
import re
import json
import boto3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import yaml
except ImportError:
    print("Installing pyyaml...")
    os.system("pip install pyyaml")
    import yaml

# S3 Configuration
from config.settings import get_settings

def extract_frontmatter(content: str) -> Dict:
    """Extract YAML frontmatter from markdown content"""
    # Match frontmatter between --- delimiters
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(pattern, content, re.DOTALL)
    
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter if frontmatter else {}
        except yaml.YAMLError as e:
            print(f"  Error parsing frontmatter: {e}")
            return {}
    return {}


def extract_h1_title(content: str) -> Optional[str]:
    """Extract first H1 heading from markdown"""
    # Remove frontmatter first
    content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)
    
    # Find first H1
    pattern = r'^#\s+(.+)$'
    match = re.search(pattern, content, re.MULTILINE)
    
    return match.group(1).strip() if match else None


def generate_title(file_path: str, frontmatter: Dict, h1_title: Optional[str]) -> str:
    """Generate document title from available sources"""
    # Priority: frontmatter.title > H1 > filename
    title = (
        frontmatter.get('title') or 
        h1_title or 
        os.path.basename(file_path).replace('.md', '').replace('-', ' ').replace('_', ' ').title()
    )
    
    # Fix common Adobe terms
    title = title.replace('Cja', 'CJA')
    title = title.replace('Aa', 'AA')
    title = title.replace('Aep', 'AEP')
    title = title.replace('Evar', 'eVar')
    title = title.replace('Api', 'API')
    
    return title


def generate_experience_league_url(s3_key: str) -> str:
    """Generate Experience League URL from S3 key"""
    # Remove bucket prefix
    path = s3_key.replace('adobe-docs/', '')
    
    # Adobe Analytics
    if 'adobe-analytics/help' in path:
        clean = path.replace('adobe-analytics/help/', '')
        clean = clean.replace('.md', '')
        return f"https://experienceleague.adobe.com/en/docs/analytics/{clean}"
    
    # Customer Journey Analytics
    elif 'customer-journey-analytics/help' in path:
        clean = path.replace('customer-journey-analytics/help/cja-main/', '')
        clean = clean.replace('customer-journey-analytics/help/', '')
        clean = clean.replace('.md', '')
        return f"https://experienceleague.adobe.com/en/docs/analytics-platform/{clean}"
    
    # Adobe Experience Platform
    elif 'experience-platform/help' in path or path.startswith('aep/'):
        clean = path.replace('experience-platform/help/', '').replace('aep/', '')
        clean = clean.replace('.md', '')
        return f"https://experienceleague.adobe.com/en/docs/experience-platform/{clean}"
    
    # Analytics APIs
    elif 'analytics-apis/docs' in path:
        clean = path.replace('analytics-apis/docs/', '')
        clean = clean.replace('.md', '')
        return f"https://developer.adobe.com/analytics-apis/docs/{clean}"
    
    return "https://experienceleague.adobe.com/en/docs"


def generate_github_url(s3_key: str) -> str:
    """Generate GitHub URL from S3 key"""
    # Adobe Analytics
    if 'adobe-analytics' in s3_key:
        path = s3_key.replace('adobe-docs/adobe-analytics/', '')
        return f"https://github.com/AdobeDocs/analytics.en/blob/master/{path}"
    
    # CJA
    elif 'customer-journey-analytics' in s3_key:
        path = s3_key.replace('adobe-docs/customer-journey-analytics/', '')
        return f"https://github.com/AdobeDocs/analytics-platform.en/blob/master/{path}"
    
    # AEP
    elif 'experience-platform' in s3_key:
        path = s3_key.replace('adobe-docs/experience-platform/', '').replace('aep/', '')
        return f"https://github.com/AdobeDocs/experience-platform.en/blob/master/{path}"
    
    # APIs
    elif 'analytics-apis' in s3_key:
        path = s3_key.replace('adobe-docs/analytics-apis/', '')
        return f"https://github.com/AdobeDocs/analytics-2.0-apis/blob/master/{path}"
    
    return ""


def identify_product(s3_key: str) -> str:
    """Identify product from S3 key"""
    if 'adobe-analytics' in s3_key:
        return 'Adobe Analytics'
    elif 'customer-journey-analytics' in s3_key:
        return 'Customer Journey Analytics'
    elif 'experience-platform' in s3_key or s3_key.startswith('aep/'):
        return 'Adobe Experience Platform'
    elif 'analytics-apis' in s3_key:
        return 'Analytics APIs'
    return 'Unknown'


def extract_metadata_from_s3(bucket_name: str, max_files: int = 50) -> Dict:
    """Extract metadata from markdown files in S3"""
    
    print(f"Extracting metadata from S3 bucket: {bucket_name}")
    print("=" * 80)
    
    # Initialize S3 client
    settings = get_settings()
    s3_client = boto3.client('s3', region_name=settings.aws_default_region)
    
    registry = {}
    file_count = 0
    
    # List all .md files in bucket
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name)
    
    for page in pages:
        if file_count >= max_files:
            break
            
        for obj in page.get('Contents', []):
            if file_count >= max_files:
                break
                
            key = obj['Key']
            
            # Only process .md files (skip TOC, README, etc.)
            if not key.endswith('.md'):
                continue
            
            if any(skip in key for skip in ['TOC.md', 'README.md', 'metadata.md', '_includes/']):
                continue
            
            try:
                # Fetch file content from S3
                response = s3_client.get_object(Bucket=bucket_name, Key=key)
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
                    
                    # Audience
                    'role': frontmatter.get('role', 'User'),
                    'level': frontmatter.get('level', 'Beginner'),
                    
                    # Timestamps
                    'last_modified_s3': obj['LastModified'].isoformat(),
                    'extracted_at': datetime.utcnow().isoformat(),
                    
                    # Search optimization
                    'keywords': frontmatter.get('keywords', []),
                }
                
                registry[key] = metadata
                file_count += 1
                
                if file_count % 10 == 0:
                    print(f"  Processed {file_count} files...")
                
            except Exception as e:
                print(f"  Error processing {key}: {e}")
                continue
    
    return registry


def save_metadata_registry(registry: Dict, output_path: str = 'data/metadata_registry.json'):
    """Save metadata registry to JSON file"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Metadata registry saved to {output_file}")
    print(f"   Total documents: {len(registry)}")


if __name__ == '__main__':
    # Get settings
    settings = get_settings()
    
    # Extract metadata from S3
    print(f"Starting extraction from S3 bucket: {settings.aws_s3_bucket}")
    print(f"Limited to 50 files for testing")
    print()
    
    registry = extract_metadata_from_s3(settings.aws_s3_bucket, max_files=50)
    
    # Save registry
    save_metadata_registry(registry)
    
    # Print summary
    print("\n" + "=" * 80)
    print("METADATA EXTRACTION COMPLETE")
    print("=" * 80)
    
    # Stats by product
    product_counts = {}
    for metadata in registry.values():
        product = metadata['product']
        product_counts[product] = product_counts.get(product, 0) + 1
    
    print("\nDocuments by Product:")
    for product, count in sorted(product_counts.items()):
        print(f"  • {product}: {count} documents")
    
    print(f"\nTotal Documents: {len(registry)}")
    
    # Sample entries
    print("\nSample Entries:")
    for i, (key, metadata) in enumerate(list(registry.items())[:3]):
        print(f"\n{i+1}. {metadata['title']}")
        print(f"   Product: {metadata['product']}")
        print(f"   URL: {metadata['experience_league_url']}")
        print(f"   S3: {key}")
    
    print()

