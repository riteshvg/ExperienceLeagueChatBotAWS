"""
Citation Mapper

Converts AWS Bedrock Knowledge Base document metadata to proper Experience League URLs.
Handles Adobe Analytics, Customer Journey Analytics, and Adobe Experience Platform documentation.
"""

import re
import logging
from typing import Optional, Dict, Tuple
from urllib.parse import unquote

logger = logging.getLogger(__name__)


def extract_path_from_metadata(metadata: dict) -> Optional[str]:
    """
    Extract file path from AWS Bedrock KB metadata.
    
    Tries multiple metadata formats:
    - location.s3Location.uri
    - uri
    - metadata.x-amz-bedrock-kb-source-uri
    - source
    
    Args:
        metadata: Document metadata from AWS Bedrock KB
        
    Returns:
        Extracted file path or None
        
    Example:
        >>> extract_path_from_metadata({'location': {'s3Location': {'uri': 's3://bucket/path/file.md'}}})
        'path/file.md'
    """
    logger.debug(f"Extract path input: {metadata}")
    
    try:
        # Try location.s3Location.uri (most common)
        if 'location' in metadata:
            s3_location = metadata['location'].get('s3Location', {})
            if 'uri' in s3_location:
                uri = s3_location['uri']
                logger.debug(f"Found URI in location.s3Location: {uri}")
                return _extract_path_from_s3_uri(uri)
        
        # Try direct uri field
        if 'uri' in metadata:
            uri = metadata['uri']
            logger.debug(f"Found URI in direct uri field: {uri}")
            return _extract_path_from_s3_uri(uri)
        
        # Try metadata.x-amz-bedrock-kb-source-uri
        if 'metadata' in metadata:
            source_uri = metadata['metadata'].get('x-amz-bedrock-kb-source-uri')
            if source_uri:
                logger.debug(f"Found URI in metadata field: {source_uri}")
                return _extract_path_from_s3_uri(source_uri)
        
        # Try source field
        if 'source' in metadata:
            source = metadata['source']
            logger.debug(f"Found URI in source field: {source}")
            return _extract_path_from_s3_uri(source)
        
        logger.warning("No valid URI found in metadata")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting path from metadata: {e}")
        return None


def _extract_path_from_s3_uri(s3_uri: str) -> Optional[str]:
    """
    Extract file path from S3 URI.
    
    Args:
        s3_uri: S3 URI (e.g., s3://bucket/path/to/file.md)
        
    Returns:
        Path after bucket name (e.g., path/to/file.md)
    """
    if not s3_uri or not s3_uri.startswith('s3://'):
        return None
    
    try:
        # Remove s3:// prefix and split by /
        # Format: s3://bucket/path/to/file.md
        parts = s3_uri.replace('s3://', '').split('/', 1)
        
        if len(parts) < 2:
            return None
        
        # Return everything after bucket name
        path = parts[1]
        
        # Decode URL encoding
        path = unquote(path)
        
        return path
        
    except Exception as e:
        logger.error(f"Error extracting path from S3 URI {s3_uri}: {e}")
        return None


def map_to_experience_league_url(document_metadata: dict) -> str:
    """
    Convert document metadata to valid Experience League URL.
    
    Handles:
    - Adobe Analytics: help/{section}/{file}.md → /en/docs/analytics/{section}/{file}
    - CJA: help/{section}/{file}.md → /en/docs/analytics-platform/using/cja-{section}/{file}
    - AEP: help/{service}/{subsection}/{file}.md → /en/docs/experience-platform/{service}/{subsection}/{file}
    
    Args:
        document_metadata: Document metadata from AWS Bedrock KB
        
    Returns:
        Valid Experience League URL or fallback URL
    """
    logger.debug("=" * 80)
    logger.debug("Citation Mapper - map_to_experience_league_url")
    logger.debug(f"Input metadata keys: {document_metadata.keys()}")
    
    # Extract path from metadata
    path = extract_path_from_metadata(document_metadata)
    
    if not path:
        logger.warning("Could not extract path from metadata, using fallback URL")
        return "https://experienceleague.adobe.com/en/docs/analytics"
    
    logger.debug(f"Extracted path: {path}")
    
    # Apply product-specific transformations
    result_url = None
    
    # Adobe Analytics
    if 'adobe-docs/adobe-analytics' in path or 'analytics.en' in path:
        result_url = _map_adobe_analytics_url(path)
        logger.info(f"Adobe Analytics mapping: {path} → {result_url}")
    
    # Customer Journey Analytics
    elif 'customer-journey-analytics' in path or 'analytics-platform' in path:
        result_url = _map_cja_url(path)
        logger.info(f"CJA mapping: {path} → {result_url}")
    
    # Adobe Experience Platform (check for both variations)
    elif 'experience-platform' in path or path.startswith('aep/'):
        result_url = _map_aep_url(path)
        logger.info(f"AEP mapping: {path} → {result_url}")
    
    # Analytics APIs
    elif 'analytics-apis' in path or 'analytics-2.0-apis' in path:
        result_url = _map_analytics_api_url(path)
        logger.info(f"Analytics API mapping: {path} → {result_url}")
    
    # Fallback
    else:
        logger.warning(f"Unknown path format: {path}, using fallback")
        result_url = "https://experienceleague.adobe.com/en/docs/analytics"
    
    logger.debug(f"Generated URL: {result_url}")
    logger.debug("=" * 80)
    
    return result_url


def _map_adobe_analytics_url(path: str) -> str:
    """
    Map Adobe Analytics path to Experience League URL keeping FULL path.
    
    Pattern: help/{section}/{subsection}/{file}.md
    → https://experienceleague.adobe.com/en/docs/analytics/{section}/{subsection}/{file}
    
    Examples:
        help/components/segmentation/seg-workflow.md 
            → /components/segmentation/seg-workflow
        help/admin/admin-console/permissions/product-profile.md 
            → /admin/admin-console/permissions/product-profile
    """
    # Remove various prefixes
    path = path.replace('adobe-docs/adobe-analytics/', '')
    path = path.replace('analytics.en/', '')
    
    # Remove 'help/' prefix
    if path.startswith('help/'):
        path = path[5:]
    
    # Remove .md and .html extensions
    if path.endswith('.md'):
        path = path[:-3]
    elif path.endswith('.html'):
        path = path[:-5]
    
    # IMPORTANT: Keep full path including all subfolders!
    base_url = "https://experienceleague.adobe.com/en/docs/analytics"
    return f"{base_url}/{path}"


def _map_cja_url(path: str) -> str:
    """
    Map Customer Journey Analytics path to Experience League URL keeping FULL path.
    
    Pattern: help/{section}/{subsection}/{file}.md
    → https://experienceleague.adobe.com/en/docs/analytics-platform/{section}/{subsection}/{file}
    
    Examples:
        help/cja-main/data-views/create-dataview.md 
            → /data-views/create-dataview
        help/cja-main/connections/overview.md 
            → /connections/overview
    """
    # Remove various prefixes
    path = path.replace('adobe-docs/customer-journey-analytics/', '')
    path = path.replace('analytics-platform.en/', '')
    
    # Remove 'help/' and 'help/cja-main/' prefixes
    if path.startswith('help/cja-main/'):
        path = path[14:]  # Remove 'help/cja-main/'
    elif path.startswith('help/'):
        path = path[5:]  # Remove 'help/'
    
    # Remove .md and .html extensions
    if path.endswith('.md'):
        path = path[:-3]
    elif path.endswith('.html'):
        path = path[:-5]
    
    # IMPORTANT: Keep full path including all subfolders!
    # CJA docs have been reorganized, using simple mapping
    base_url = "https://experienceleague.adobe.com/en/docs/analytics-platform"
    return f"{base_url}/{path}"


def _map_aep_url(path: str) -> str:
    """
    Map Adobe Experience Platform path to Experience League URL keeping FULL path.
    
    Pattern: help/{service}/{subsection}/{file}.md
    → https://experienceleague.adobe.com/en/docs/experience-platform/{service}/{subsection}/{file}
    
    Examples:
        help/datastreams/configure.md → /datastreams/configure
        help/sources/connectors/adobe-applications/analytics.md 
            → /sources/connectors/adobe-applications/analytics
    """
    # Remove various prefixes
    path = path.replace('adobe-docs/experience-platform/', '')
    path = path.replace('experience-platform.en/', '')
    
    # Remove 'aep/' prefix if present
    if path.startswith('aep/'):
        path = path[4:]
    
    # Remove 'help/' prefix
    if path.startswith('help/'):
        path = path[5:]
    
    # Remove .md and .html extensions
    if path.endswith('.md'):
        path = path[:-3]
    elif path.endswith('.html'):
        path = path[:-5]
    
    # IMPORTANT: Keep full path - don't strip anything!
    base_url = "https://experienceleague.adobe.com/en/docs/experience-platform"
    return f"{base_url}/{path}"


def _map_analytics_api_url(path: str) -> str:
    """
    Map Analytics APIs path to developer.adobe.com URL.
    
    Pattern: docs/{version}/{file}.md
    → https://developer.adobe.com/analytics-apis/docs/{version}/{file}
    """
    # Remove prefixes
    path = path.replace('adobe-docs/analytics-apis/', '')
    path = path.replace('analytics-2.0-apis/', '')
    
    # Remove 'docs/' prefix
    if path.startswith('docs/'):
        path = path[5:]
    
    # Remove .md extension
    if path.endswith('.md'):
        path = path[:-3]
    
    # Build URL
    base_url = "https://developer.adobe.com/analytics-apis/docs"
    return f"{base_url}/{path}"


def extract_title_from_metadata(document_metadata: dict) -> Optional[str]:
    """
    Extract document title from metadata.
    
    Tries:
    1. metadata.title field
    2. First heading from content
    3. Generate from file path
    
    Args:
        document_metadata: Document metadata
        
    Returns:
        Document title or None
    """
    try:
        # Try metadata.title
        if 'metadata' in document_metadata:
            title = document_metadata['metadata'].get('title')
            if title:
                logger.debug(f"Found title in metadata: {title}")
                return title
        
        # Try extracting from content (first heading)
        if 'content' in document_metadata:
            content = document_metadata['content'].get('text', '')
            if content:
                # Look for markdown heading
                match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if match:
                    title = match.group(1).strip()
                    logger.debug(f"Extracted title from content: {title}")
                    return title
        
        # Generate from path
        path = extract_path_from_metadata(document_metadata)
        if path:
            # Get last part of path
            filename = path.split('/')[-1]
            # Remove .md extension
            if filename.endswith('.md'):
                filename = filename[:-3]
            # Convert to title case
            title = filename.replace('-', ' ').replace('_', ' ').title()
            # Fix common Adobe terms
            title = title.replace('Cja', 'CJA')
            title = title.replace('Aa', 'AA')
            title = title.replace('Aep', 'AEP')
            title = title.replace('Evar', 'eVar')
            title = title.replace('Api', 'API')
            logger.debug(f"Generated title from path: {title}")
            return title
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting title: {e}")
        return None


def format_citation(doc_metadata: dict, doc_title: Optional[str] = None) -> dict:
    """
    Format citation dict from document metadata.
    
    Args:
        doc_metadata: Document metadata from AWS Bedrock KB
        doc_title: Optional title (will be extracted if not provided)
        
    Returns:
        Citation dict with url, title, display, score, github_url
        
    Example:
        >>> citation = format_citation(doc_metadata)
        >>> print(citation['url'])
        'https://experienceleague.adobe.com/en/docs/analytics/components/segments/seg-workflow'
    """
    # Generate Experience League URL
    url = map_to_experience_league_url(doc_metadata)
    
    # Extract or use provided title
    title = doc_title or extract_title_from_metadata(doc_metadata)
    if not title:
        title = "Adobe Documentation"
    
    # Get relevance score
    score = doc_metadata.get('score', 0.0)
    
    # Generate GitHub URL for reference
    path = extract_path_from_metadata(doc_metadata)
    github_url = _generate_github_url(path) if path else None
    
    # Generate display text
    display = f"Source: {title}"
    if score > 0:
        display += f" (Relevance: {score:.0%})"
    
    citation = {
        'url': url,
        'title': title,
        'display': display,
        'score': score,
        'github_url': github_url,
        'path': path
    }
    
    logger.info(f"Generated citation: {title} → {url}")
    
    return citation


def _generate_github_url(path: str) -> Optional[str]:
    """Generate GitHub URL from file path."""
    try:
        if 'adobe-docs/adobe-analytics/help' in path:
            relative = path.replace('adobe-docs/adobe-analytics/', '')
            return f"https://github.com/AdobeDocs/analytics.en/blob/master/{relative}"
        
        elif 'customer-journey-analytics' in path:
            relative = path.replace('adobe-docs/customer-journey-analytics/', '')
            return f"https://github.com/AdobeDocs/analytics-platform.en/blob/master/{relative}"
        
        elif 'aep/' in path or 'experience-platform' in path:
            relative = path.replace('aep/', '')
            return f"https://github.com/AdobeDocs/experience-platform.en/blob/master/{relative}"
        
        elif 'analytics-apis' in path:
            relative = path.replace('adobe-docs/analytics-apis/', '')
            return f"https://github.com/AdobeDocs/analytics-2.0-apis/blob/master/{relative}"
        
        return None
    except Exception as e:
        logger.error(f"Error generating GitHub URL: {e}")
        return None


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

