"""
Citation Mapper with Metadata Registry

Uses document metadata registry for accurate URL generation and rich citations.
Falls back to pattern-based mapping when metadata not found.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Global metadata registry
METADATA_REGISTRY = {}


def load_metadata_registry(registry_path: str = 'data/metadata_registry.json'):
    """Load metadata registry from JSON file"""
    global METADATA_REGISTRY
    
    try:
        registry_file = Path(registry_path)
        if registry_file.exists():
            with open(registry_file, 'r', encoding='utf-8') as f:
                METADATA_REGISTRY = json.load(f)
            logger.info(f"✅ Loaded metadata registry with {len(METADATA_REGISTRY)} entries")
            return True
        else:
            logger.warning(f"⚠️ Metadata registry not found at {registry_path}")
            return False
    except Exception as e:
        logger.error(f"❌ Error loading metadata registry: {e}")
        return False


# Load registry on module import
load_metadata_registry()


def normalize_path_for_lookup(path: str) -> str:
    """
    Normalize S3/file path for metadata registry lookup.
    
    Converts various path formats to the registry key format.
    """
    # Remove S3 prefix
    path = re.sub(r'^s3://[^/]+/', '', path)
    
    # The registry uses S3 keys directly, so we need to match that format
    # Example registry key: "adobe-docs/adobe-analytics/help/admin/home.md"
    
    # If path doesn't start with 'adobe-docs/', it might be a partial path
    # Try to find matching keys in the registry
    
    return path


def lookup_metadata_by_path(source_path: str) -> Optional[Dict]:
    """
    Look up document metadata by source file path.
    
    Tries multiple path variations to find a match in the registry.
    """
    if not METADATA_REGISTRY:
        logger.warning("Metadata registry is empty")
        return None
    
    normalized_path = normalize_path_for_lookup(source_path)
    logger.debug(f"Looking up metadata for: {normalized_path}")
    
    # Direct lookup
    if normalized_path in METADATA_REGISTRY:
        logger.debug(f"✅ Found exact match: {normalized_path}")
        return METADATA_REGISTRY[normalized_path]
    
    # Try variations
    variations = [
        normalized_path,
        normalized_path.replace('.html', '.md'),
        f"{normalized_path}.md" if not normalized_path.endswith('.md') else normalized_path,
    ]
    
    for variation in variations:
        if variation in METADATA_REGISTRY:
            logger.debug(f"✅ Found match with variation: {variation}")
            return METADATA_REGISTRY[variation]
    
    # Try fuzzy matching (search for key containing the path)
    for registry_key in METADATA_REGISTRY.keys():
        if normalized_path.endswith(registry_key) or registry_key.endswith(normalized_path):
            logger.debug(f"✅ Found fuzzy match: {registry_key}")
            return METADATA_REGISTRY[registry_key]
    
    logger.warning(f"⚠️ No metadata found for: {source_path}")
    return None


def extract_path_from_metadata(doc_metadata: dict) -> Optional[str]:
    """Extract file path from various document metadata formats"""
    # Try S3 location (most common for Bedrock KB)
    if 'location' in doc_metadata:
        location = doc_metadata['location']
        if isinstance(location, dict) and 's3Location' in location:
            s3_uri = location['s3Location'].get('uri', '')
            if s3_uri:
                return s3_uri
    
    # Try direct URI
    if 'uri' in doc_metadata:
        return doc_metadata['uri']
    
    # Try metadata field
    if 'metadata' in doc_metadata:
        inner_meta = doc_metadata['metadata']
        if isinstance(inner_meta, dict):
            if 'x-amz-bedrock-kb-source-uri' in inner_meta:
                return inner_meta['x-amz-bedrock-kb-source-uri']
            if 'source' in inner_meta:
                return inner_meta['source']
    
    # Try source attribute
    if 'source' in doc_metadata:
        return doc_metadata['source']
    
    return None


def format_citation(doc_metadata: dict, doc_title: Optional[str] = None) -> Dict:
    """
    Format citation using metadata registry for accuracy.
    
    Falls back to pattern-based URL generation if metadata not found.
    
    Args:
        doc_metadata: Document metadata from AWS Bedrock KB retrieval
        doc_title: Optional pre-extracted title (will be auto-extracted if None)
    
    Returns:
        Formatted citation dict with url, title, display, score, etc.
    """
    # Extract source path
    source_path = extract_path_from_metadata(doc_metadata)
    
    # Get relevance score
    score = doc_metadata.get('score', 0.0)
    
    if not source_path:
        logger.warning("No source path found in document metadata")
        return _create_fallback_citation(doc_metadata, score)
    
    # Look up in metadata registry
    metadata = lookup_metadata_by_path(source_path)
    
    if metadata:
        # ✅ Use metadata from registry
        citation = {
            'url': metadata['experience_league_url'],
            'github_url': metadata.get('github_url', ''),
            'title': metadata['title'],
            'description': metadata.get('description', ''),
            'section': metadata.get('section', ''),
            'product': metadata['product'],
            'doc_type': metadata.get('doc_type', 'Article'),
            'role': metadata.get('role', ''),
            'level': metadata.get('level', ''),
            'last_updated': metadata.get('last_updated', ''),
            'score': score,
            'path': source_path,
            'metadata_source': 'registry',
            'display': f"**[{metadata['title']}]({metadata['experience_league_url']})** (Relevance: {score:.2%})"
        }
        
        logger.info(f"✅ Citation from registry: {metadata['title']} → {metadata['experience_league_url']}")
        return citation
    
    else:
        # ⚠️ Fallback to pattern-based URL generation
        logger.warning(f"⚠️ Using fallback URL mapping for: {source_path}")
        return _create_fallback_citation(doc_metadata, score)


def _create_fallback_citation(doc_metadata: dict, score: float) -> Dict:
    """Create citation using fallback pattern-based URL generation"""
    from .citation_mapper_fallback import (
        map_to_experience_league_url as fallback_map_url,
        extract_title_from_metadata as fallback_extract_title
    )
    
    # Use fallback URL mapping
    url = fallback_map_url(doc_metadata)
    
    # Try to extract title
    title = fallback_extract_title(doc_metadata)
    if not title:
        # Generate from path
        source_path = extract_path_from_metadata(doc_metadata)
        if source_path:
            filename = Path(source_path).stem
            title = filename.replace('-', ' ').replace('_', ' ').title()
        else:
            title = "Adobe Documentation"
    
    # Build fallback citation
    citation = {
        'url': url,
        'github_url': '',
        'title': title,
        'description': '',
        'section': '',
        'product': 'Adobe',
        'doc_type': 'Article',
        'role': '',
        'level': '',
        'last_updated': '',
        'score': score,
        'path': extract_path_from_metadata(doc_metadata) or '',
        'metadata_source': 'fallback',
        'display': f"**[{title}]({url})** (Relevance: {score:.2%})"
    }
    
    logger.info(f"⚠️ Citation from fallback: {title} → {url}")
    return citation


def reload_metadata_registry():
    """Reload metadata registry from disk"""
    success = load_metadata_registry()
    if success:
        logger.info(f"🔄 Metadata registry reloaded: {len(METADATA_REGISTRY)} entries")
    else:
        logger.error("❌ Failed to reload metadata registry")
    return success


def get_registry_stats() -> Dict:
    """Get statistics about the metadata registry"""
    if not METADATA_REGISTRY:
        return {
            'total_documents': 0,
            'products': {},
            'doc_types': {},
            'has_registry': False
        }
    
    products = {}
    doc_types = {}
    
    for metadata in METADATA_REGISTRY.values():
        # Count by product
        product = metadata.get('product', 'Unknown')
        products[product] = products.get(product, 0) + 1
        
        # Count by doc type
        doc_type = metadata.get('doc_type', 'Unknown')
        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
    
    return {
        'total_documents': len(METADATA_REGISTRY),
        'products': products,
        'doc_types': doc_types,
        'has_registry': True
    }


# Backward compatibility functions
def map_to_experience_league_url(document_metadata: dict) -> str:
    """
    Backward compatible wrapper for format_citation.
    Returns just the URL for compatibility.
    """
    citation = format_citation(document_metadata)
    return citation['url']


def extract_title_from_metadata(document_metadata: dict) -> Optional[str]:
    """
    Backward compatible wrapper for format_citation.
    Returns just the title for compatibility.
    """
    citation = format_citation(document_metadata)
    return citation['title']
