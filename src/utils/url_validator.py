"""
URL Validator for Citations

Validates Experience League URLs in real-time to filter out 404 errors.
Uses async requests with caching to minimize latency.
"""

import asyncio
import logging
import time
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger(__name__)

# URL validation cache
# Format: {url: {'status': 200, 'validated_at': datetime, 'valid': True}}
URL_CACHE = {}
CACHE_TTL_HOURS = 24  # Cache validation results for 24 hours


def is_cache_valid(url: str) -> Optional[bool]:
    """Check if URL validation result is in cache and still valid"""
    if url not in URL_CACHE:
        return None
    
    cache_entry = URL_CACHE[url]
    validated_at = cache_entry.get('validated_at')
    
    # Check if cache is expired
    if validated_at:
        age = datetime.now() - validated_at
        if age > timedelta(hours=CACHE_TTL_HOURS):
            # Cache expired
            return None
    
    return cache_entry.get('valid', None)


async def validate_url_async(session: aiohttp.ClientSession, url: str, timeout: int = 3) -> Tuple[str, bool, int]:
    """
    Validate a single URL asynchronously.
    
    Args:
        session: aiohttp ClientSession
        url: URL to validate
        timeout: Timeout in seconds (default 3)
    
    Returns:
        Tuple of (url, is_valid, status_code)
    """
    # Check cache first
    cached_result = is_cache_valid(url)
    if cached_result is not None:
        logger.debug(f"Cache hit for {url}: {cached_result}")
        status = URL_CACHE[url].get('status', 0)
        return url, cached_result, status
    
    try:
        # Use HEAD request for faster validation
        async with session.head(url, timeout=timeout, allow_redirects=True) as response:
            status_code = response.status
            is_valid = status_code in [200, 301, 302]  # Accept redirects as valid
            
            # Cache the result
            URL_CACHE[url] = {
                'status': status_code,
                'valid': is_valid,
                'validated_at': datetime.now()
            }
            
            logger.debug(f"URL validated: {url} → {status_code} ({'valid' if is_valid else 'invalid'})")
            return url, is_valid, status_code
            
    except asyncio.TimeoutError:
        logger.warning(f"URL validation timeout: {url}")
        # Don't cache timeouts - might be temporary
        return url, False, 408  # Request Timeout
        
    except Exception as e:
        logger.warning(f"URL validation error for {url}: {e}")
        # Don't cache errors - might be temporary
        return url, False, 0


async def validate_urls_batch_async(urls: List[str], timeout: int = 3) -> Dict[str, Tuple[bool, int]]:
    """
    Validate multiple URLs in parallel.
    
    Args:
        urls: List of URLs to validate
        timeout: Timeout per URL in seconds
    
    Returns:
        Dict mapping URL to (is_valid, status_code)
    """
    if not urls:
        return {}
    
    logger.info(f"Validating {len(urls)} URLs (timeout: {timeout}s)")
    start_time = time.time()
    
    # Create aiohttp session with custom headers and SSL context
    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; ExperienceLeagueChatbot/1.0; +https://github.com/riteshvg/ExperienceLeagueChatBotAWS)'
    }
    
    # Create SSL context (disable verification for URL checking only)
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    async with aiohttp.ClientSession(timeout=timeout_obj, headers=headers, connector=connector) as session:
        # Create tasks for all URLs
        tasks = [validate_url_async(session, url, timeout) for url in urls]
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    validation_results = {}
    for result in results:
        if isinstance(result, tuple):
            url, is_valid, status_code = result
            validation_results[url] = (is_valid, status_code)
        else:
            # Exception occurred
            logger.error(f"URL validation exception: {result}")
    
    elapsed = time.time() - start_time
    valid_count = sum(1 for is_valid, _ in validation_results.values() if is_valid)
    logger.info(f"URL validation complete: {valid_count}/{len(urls)} valid in {elapsed:.2f}s")
    
    return validation_results


def validate_urls_batch(urls: List[str], timeout: int = 3) -> Dict[str, Tuple[bool, int]]:
    """
    Synchronous wrapper for validate_urls_batch_async.
    
    Args:
        urls: List of URLs to validate
        timeout: Timeout per URL in seconds
    
    Returns:
        Dict mapping URL to (is_valid, status_code)
    """
    try:
        # Run async function
        return asyncio.run(validate_urls_batch_async(urls, timeout))
    except Exception as e:
        logger.error(f"Error in batch URL validation: {e}")
        # Return all as invalid on error
        return {url: (False, 0) for url in urls}


def filter_valid_citations(citations: List[Dict], validate_urls: bool = True, timeout: int = 3) -> List[Dict]:
    """
    Filter citations to only include those with valid URLs.
    
    Args:
        citations: List of citation dicts with 'url' field
        validate_urls: Whether to validate URLs (default True)
        timeout: Timeout per URL in seconds
    
    Returns:
        List of citations with valid URLs only
    """
    if not validate_urls or not citations:
        return citations
    
    # Extract URLs to validate
    urls = [citation.get('url') for citation in citations if citation.get('url')]
    
    if not urls:
        return citations
    
    # Validate all URLs in parallel
    validation_results = validate_urls_batch(urls, timeout)
    
    # Filter citations
    valid_citations = []
    filtered_count = 0
    
    for citation in citations:
        url = citation.get('url')
        if not url:
            continue
        
        is_valid, status_code = validation_results.get(url, (False, 0))
        
        if is_valid:
            # Add validation metadata to citation
            citation['url_validated'] = True
            citation['url_status'] = status_code
            valid_citations.append(citation)
        else:
            # Log filtered citation
            logger.warning(f"Filtered invalid URL ({status_code}): {url} - {citation.get('title', 'Unknown')}")
            filtered_count += 1
    
    if filtered_count > 0:
        logger.info(f"Filtered {filtered_count} invalid citations, {len(valid_citations)} valid citations remaining")
    
    return valid_citations


def clear_url_cache():
    """Clear the URL validation cache"""
    global URL_CACHE
    old_size = len(URL_CACHE)
    URL_CACHE = {}
    logger.info(f"URL cache cleared ({old_size} entries removed)")


def get_cache_stats() -> Dict:
    """Get URL validation cache statistics"""
    total = len(URL_CACHE)
    valid = sum(1 for entry in URL_CACHE.values() if entry.get('valid', False))
    invalid = total - valid
    
    return {
        'total_cached': total,
        'valid': valid,
        'invalid': invalid,
        'cache_ttl_hours': CACHE_TTL_HOURS
    }

