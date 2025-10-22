"""
Extract metadata from Adobe documentation repositories on GitHub.
Creates a metadata registry for all documents.
"""

import os
import re
import json
import yaml
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# GitHub repository configurations
REPOS = {
    'adobe-analytics': {
        'owner': 'AdobeDocs',
        'repo': 'analytics.en',
        'product': 'Adobe Analytics',
        'base_path': 'help',
        'experience_league_base': 'https://experienceleague.adobe.com/en/docs/analytics'
    },
    'customer-journey-analytics': {
        'owner': 'AdobeDocs',
        'repo': 'analytics-platform.en',
        'product': 'Customer Journey Analytics',
        'base_path': 'help',
        'experience_league_base': 'https://experienceleague.adobe.com/en/docs/analytics-platform'
    },
    'experience-platform': {
        'owner': 'AdobeDocs',
        'repo': 'experience-platform.en',
        'product': 'Adobe Experience Platform',
        'base_path': 'help',
        'experience_league_base': 'https://experienceleague.adobe.com/en/docs/experience-platform'
    }
}


def extract_frontmatter(content: str) -> Optional[Dict]:
    """Extract YAML frontmatter from markdown content"""
    # Match frontmatter between --- delimiters
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(pattern, content, re.DOTALL)
    
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1))
            return frontmatter if frontmatter else {}
        except yaml.YAMLError as e:
            print(f"Error parsing frontmatter: {e}")
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


def parse_toc_file(toc_content: str, base_folder: str) -> Dict[str, Dict]:
    """Parse TOC.md file to extract titles and paths"""
    toc_map = {}
    current_section = None
    
    lines = toc_content.split('\n')
    for line in lines:
        line = line.strip()
        
        # Match TOC entries: + [Title](path.md)
        pattern = r'\+\s+\[(.+?)\]\((.+?\.md)\)'
        match = re.match(pattern, line)
        
        if match:
            title = match.group(1)
            relative_path = match.group(2)
            
            # Build full path
            full_path = os.path.join(base_folder, relative_path).replace('\\', '/')
            
            toc_map[full_path] = {
                'toc_title': title,
                'section': current_section
            }
        
        # Track section headers: + Section {#section-id}
        section_pattern = r'\+\s+(.+?)\s+\{#(.+?)\}'
        section_match = re.match(section_pattern, line)
        if section_match:
            current_section = section_match.group(1)
    
    return toc_map


def fetch_github_file(owner: str, repo: str, path: str, github_token: Optional[str] = None) -> Optional[str]:
    """Fetch file content from GitHub"""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    headers = {'Accept': 'application/vnd.github.v3.raw'}
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            print(f"Failed to fetch {path}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching {path}: {e}")
        return None


def get_file_last_modified(owner: str, repo: str, path: str, github_token: Optional[str] = None) -> Optional[str]:
    """Get last modified date from GitHub commit history"""
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?path={path}&per_page=1"
    
    headers = {}
    if github_token:
        headers['Authorization'] = f'token {github_token}'
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200 and response.json():
            commit = response.json()[0]
            return commit['commit']['author']['date']
        return None
    except Exception as e:
        print(f"Error getting last modified for {path}: {e}")
        return None


def list_markdown_files(owner: str, repo: str, base_path: str, github_token: Optional[str] = None) -> List[str]:
    """Recursively list all .md files in repository"""
    markdown_files = []
    
    def traverse_directory(path: str):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                items = response.json()
                
                for item in items:
                    if item['type'] == 'file' and item['name'].endswith('.md'):
                        # Skip TOC.md and metadata.md files
                        if item['name'] not in ['TOC.md', 'metadata.md', 'README.md']:
                            markdown_files.append(item['path'])
                    
                    elif item['type'] == 'dir':
                        # Recursively traverse subdirectories
                        traverse_directory(item['path'])
        except Exception as e:
            print(f"Error traversing {path}: {e}")
    
    traverse_directory(base_path)
    return markdown_files


def generate_experience_league_url(repo_config: Dict, file_path: str) -> str:
    """Generate Experience League URL from file path"""
    # Remove base_path prefix and .md extension
    clean_path = file_path.replace(f"{repo_config['base_path']}/", '').replace('.md', '')
    
    # Remove cja-main if present for CJA
    if repo_config['product'] == 'Customer Journey Analytics':
        clean_path = clean_path.replace('cja-main/', '')
    
    return f"{repo_config['experience_league_base']}/{clean_path}"


def generate_github_url(repo_config: Dict, file_path: str) -> str:
    """Generate GitHub URL for source file"""
    return f"https://github.com/{repo_config['owner']}/{repo_config['repo']}/blob/main/{file_path}"


def extract_document_metadata(
    owner: str, 
    repo: str, 
    file_path: str, 
    repo_config: Dict,
    toc_map: Dict,
    github_token: Optional[str] = None
) -> Dict:
    """Extract complete metadata for a document"""
    
    print(f"  Processing: {file_path}")
    
    # Fetch file content
    content = fetch_github_file(owner, repo, file_path, github_token)
    if not content:
        return {}
    
    # Extract frontmatter
    frontmatter = extract_frontmatter(content)
    
    # Extract H1 title
    h1_title = extract_h1_title(content)
    
    # Get TOC information
    toc_info = toc_map.get(file_path, {})
    
    # Get last modified date
    last_modified = get_file_last_modified(owner, repo, file_path, github_token)
    
    # Generate title (priority: frontmatter > TOC > H1 > filename)
    title = (
        frontmatter.get('title') or 
        toc_info.get('toc_title') or 
        h1_title or 
        os.path.basename(file_path).replace('.md', '').replace('-', ' ').title()
    )
    
    # Build metadata
    metadata = {
        # Identification
        'source_file': file_path,
        'doc_id': frontmatter.get('exl-id', f"generated-{hash(file_path)}"),
        
        # URLs
        'experience_league_url': generate_experience_league_url(repo_config, file_path),
        'github_url': generate_github_url(repo_config, file_path),
        
        # Content metadata
        'title': title,
        'description': frontmatter.get('description', ''),
        'section': toc_info.get('section', ''),
        
        # Classification
        'product': repo_config['product'],
        'product_key': next(k for k, v in REPOS.items() if v == repo_config),
        'feature': frontmatter.get('feature', ''),
        'doc_type': frontmatter.get('doc-type', 'Article'),
        
        # Audience
        'role': frontmatter.get('role', 'User'),
        'level': frontmatter.get('level', 'Beginner'),
        
        # Timestamps
        'last_updated': last_modified,
        'extracted_at': datetime.utcnow().isoformat(),
        
        # Search optimization
        'keywords': frontmatter.get('keywords', []),
    }
    
    return metadata


def build_metadata_registry(github_token: Optional[str] = None, max_files_per_repo: int = 10) -> Dict:
    """Build complete metadata registry for all Adobe docs"""
    
    print("Building metadata registry...")
    print("=" * 80)
    
    registry = {}
    
    for product_key, repo_config in REPOS.items():
        print(f"\nProcessing {repo_config['product']}...")
        print("-" * 80)
        
        # Fetch TOC files
        toc_map = {}
        toc_path = f"{repo_config['base_path']}/TOC.md"
        toc_content = fetch_github_file(repo_config['owner'], repo_config['repo'], toc_path, github_token)
        
        if toc_content:
            toc_map = parse_toc_file(toc_content, repo_config['base_path'])
            print(f"  Parsed {len(toc_map)} entries from TOC.md")
        
        # List all markdown files
        markdown_files = list_markdown_files(
            repo_config['owner'], 
            repo_config['repo'], 
            repo_config['base_path'],
            github_token
        )
        
        print(f"  Found {len(markdown_files)} markdown files")
        
        # Extract metadata for each file (limited for testing)
        for file_path in markdown_files[:max_files_per_repo]:
            metadata = extract_document_metadata(
                repo_config['owner'],
                repo_config['repo'],
                file_path,
                repo_config,
                toc_map,
                github_token
            )
            
            if metadata:
                # Store by source_file path
                registry[file_path] = metadata
        
        print(f"  Extracted metadata for {len([m for m in registry.values() if m.get('product_key') == product_key])} documents from {product_key}")
    
    return registry


def save_metadata_registry(registry: Dict, output_path: str = 'data/metadata_registry.json'):
    """Save metadata registry to JSON file"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Metadata registry saved to {output_file}")
    print(f"Total documents: {len(registry)}")


if __name__ == '__main__':
    # Optional: Set GitHub token for higher API rate limits
    github_token = os.environ.get('GITHUB_TOKEN')
    
    if not github_token:
        print("⚠️  No GITHUB_TOKEN found. API rate limit: 60 requests/hour")
        print("   To increase limit to 5000/hour, set GITHUB_TOKEN env variable")
        print()
    
    # Build registry (limit to 10 files per repo for testing)
    print("Starting metadata extraction (limited to 10 files per repo for testing)...")
    print("To extract all files, modify max_files_per_repo parameter")
    print()
    
    registry = build_metadata_registry(github_token, max_files_per_repo=10)
    
    # Save to file
    save_metadata_registry(registry, 'data/metadata_registry.json')
    
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
    print(f"Registry saved to: data/metadata_registry.json")
    print()

