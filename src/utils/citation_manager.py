"""
Citation Manager

Converts S3 URIs to proper documentation URLs and formats citations.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from urllib.parse import unquote

logger = logging.getLogger(__name__)


class CitationManager:
    """Manages citation extraction and URL conversion for documentation sources."""
    
    def __init__(self):
        # Mapping of S3 prefixes to documentation bases
        # Pattern: S3 path without help/ -> Experience League URL
        self.url_mappings = {
            'adobe-docs/adobe-analytics/help': {
                'base_url': 'https://experienceleague.adobe.com/en/docs/analytics',
                'repo_url': 'https://github.com/AdobeDocs/analytics.en/blob/master/help',
                'type': 'experience_league',
                'strip_prefix': 'adobe-docs/adobe-analytics/help/'
            },
            'adobe-docs/customer-journey-analytics/help/cja-main': {
                'base_url': 'https://experienceleague.adobe.com/en/docs/analytics-platform',
                'repo_url': 'https://github.com/AdobeDocs/analytics-platform.en/blob/master/help/cja-main',
                'type': 'experience_league',
                'strip_prefix': 'adobe-docs/customer-journey-analytics/help/cja-main/',
                'note': 'CJA URLs may not map 1:1 to file paths due to content reorganization'
            },
            'aep': {
                'base_url': 'https://experienceleague.adobe.com/en/docs/experience-platform',
                'repo_url': 'https://github.com/AdobeDocs/experience-platform.en/blob/master',
                'type': 'experience_league',
                'strip_prefix': 'aep/'
            },
            'adobe-docs/analytics-apis/docs': {
                'base_url': 'https://developer.adobe.com/analytics-apis/docs',
                'repo_url': 'https://github.com/AdobeDocs/analytics-2.0-apis/blob/master/docs',
                'type': 'developer',
                'strip_prefix': 'adobe-docs/analytics-apis/docs/'
            }
        }
    
    def s3_uri_to_url(self, s3_uri: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Convert S3 URI to readable documentation URL.
        
        Args:
            s3_uri: S3 URI (e.g., s3://bucket/adobe-docs/adobe-analytics/help/components/metrics/overview.md)
            
        Returns:
            Tuple of (experience_league_url, github_url)
        """
        if not s3_uri or not s3_uri.startswith('s3://'):
            return None, None
        
        try:
            # Extract path from S3 URI
            # Format: s3://bucket/prefix/path/to/file.md
            parts = s3_uri.replace('s3://', '').split('/', 1)
            if len(parts) < 2:
                return None, None
            
            path = parts[1]  # Everything after bucket name
            
            # Decode URL encoding
            path = unquote(path)
            
            # Find matching URL mapping
            experience_league_url = None
            github_url = None
            
            for prefix, mapping in self.url_mappings.items():
                if path.startswith(prefix):
                    # Extract the relative path using the strip_prefix
                    strip_prefix = mapping.get('strip_prefix', prefix + '/')
                    if path.startswith(strip_prefix):
                        relative_path = path[len(strip_prefix):]
                    else:
                        relative_path = path[len(prefix):].lstrip('/')
                    
                    # Remove .md extension for Experience League URL
                    if relative_path.endswith('.md'):
                        doc_path = relative_path[:-3]
                    else:
                        doc_path = relative_path
                    
                    # Build Experience League URL (without .md)
                    experience_league_url = f"{mapping['base_url']}/{doc_path}"
                    
                    # Build GitHub URL (with .md, for reference)
                    github_url = f"{mapping['repo_url']}/{relative_path}"
                    
                    break
            
            return experience_league_url, github_url
            
        except Exception as e:
            logger.error(f"Error converting S3 URI to URL: {s3_uri} - {e}")
            return None, None
    
    def _clean_relative_path(self, path: str) -> str:
        """Clean up relative path by removing common prefixes."""
        # Remove common documentation path prefixes
        prefixes_to_remove = ['help/', 'docs/', 'src/', 'content/']
        
        for prefix in prefixes_to_remove:
            if path.startswith(prefix):
                path = path[len(prefix):]
                break
        
        return path
    
    def extract_citations(self, documents: List[Dict]) -> List[Dict]:
        """
        Extract citation information from retrieved documents.
        
        Args:
            documents: List of retrieval results from Bedrock KB
            
        Returns:
            List of citation dictionaries with metadata
        """
        citations = []
        seen_urls = set()  # Avoid duplicate citations
        
        for idx, doc in enumerate(documents, 1):
            try:
                # Get S3 location
                location = doc.get('location', {})
                s3_uri = location.get('s3Location', {}).get('uri', '')
                
                if not s3_uri:
                    continue
                
                # Convert to URLs
                experience_league_url, github_url = self.s3_uri_to_url(s3_uri)
                
                # Skip if no valid URL or duplicate
                if not experience_league_url or experience_league_url in seen_urls:
                    continue
                
                seen_urls.add(experience_league_url)
                
                # Extract document title from path
                title = self._extract_title_from_url(experience_league_url)
                
                # Get relevance score
                score = doc.get('score', 0.0)
                
                # Get content preview
                content = doc.get('content', {}).get('text', '')
                preview = content[:200] + '...' if len(content) > 200 else content
                
                citations.append({
                    'id': idx,
                    'title': title,
                    'experience_league_url': experience_league_url,
                    'github_url': github_url,
                    's3_uri': s3_uri,
                    'score': score,
                    'preview': preview
                })
                
            except Exception as e:
                logger.error(f"Error extracting citation from document: {e}")
                continue
        
        return citations
    
    def _extract_title_from_url(self, url: str) -> str:
        """Extract a readable title from the documentation URL."""
        try:
            # Get the last part of the URL path
            parts = url.rstrip('/').split('/')
            last_part = parts[-1] if parts else 'Documentation'
            
            # Convert from URL format to readable title
            # e.g., "calculated-metrics" -> "Calculated Metrics"
            title = last_part.replace('-', ' ').replace('_', ' ').title()
            
            # Handle common Adobe terms
            title = title.replace('Cja', 'CJA')
            title = title.replace('Aa', 'AA')
            title = title.replace('Aep', 'AEP')
            title = title.replace('Evar', 'eVar')
            title = title.replace('Api', 'API')
            
            return title
            
        except Exception as e:
            logger.error(f"Error extracting title from URL: {url} - {e}")
            return "Documentation"
    
    def format_citations_markdown(self, citations: List[Dict]) -> str:
        """
        Format citations as markdown for display.
        
        Args:
            citations: List of citation dictionaries
            
        Returns:
            Formatted markdown string
        """
        if not citations:
            return ""
        
        markdown = "\n\n---\n\n### 📚 Sources\n\n"
        
        for citation in citations:
            # Primary link to Experience League
            markdown += f"{citation['id']}. **[{citation['title']}]({citation['experience_league_url']})** "
            markdown += f"(Relevance: {citation['score']:.2%})"
            
            # Add GitHub source link as backup
            markdown += f" • [View on GitHub →]({citation['github_url']})\n"
        
        return markdown
    
    def format_citations_html(self, citations: List[Dict]) -> str:
        """
        Format citations as HTML for display.
        
        Args:
            citations: List of citation dictionaries
            
        Returns:
            Formatted HTML string
        """
        if not citations:
            return ""
        
        html = """
        <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #007bff; border-radius: 4px;">
            <h4 style="margin-top: 0; color: #007bff;">📚 Sources</h4>
            <ol style="margin: 10px 0; padding-left: 20px;">
        """
        
        for citation in citations:
            relevance_color = "#28a745" if citation['score'] > 0.7 else "#ffc107" if citation['score'] > 0.5 else "#6c757d"
            
            html += f"""
                <li style="margin-bottom: 10px;">
                    <a href="{citation['experience_league_url']}" target="_blank" style="color: #007bff; text-decoration: none; font-weight: 500;">
                        {citation['title']}
                    </a>
                    <span style="color: {relevance_color}; font-size: 0.85em; margin-left: 8px;">
                        ({citation['score']:.0%} relevant)
                    </span>
                    <br>
                    <a href="{citation['github_url']}" target="_blank" style="color: #6c757d; font-size: 0.8em; text-decoration: none;">
                        View source on GitHub →
                    </a>
                </li>
            """
        
        html += """
            </ol>
        </div>
        """
        
        return html
    
    def get_inline_citations(self, citations: List[Dict]) -> List[str]:
        """
        Get inline citation references (e.g., [1], [2], [3]).
        
        Args:
            citations: List of citation dictionaries
            
        Returns:
            List of citation references
        """
        return [f"[{c['id']}]" for c in citations]


# Global instance
citation_manager = CitationManager()

