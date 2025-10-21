"""
Retrieval Filter Module

This module provides similarity threshold filtering for Knowledge Base retrieval results.
"""

import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def filter_retrieval_by_similarity(
    results: List[Dict],
    threshold: float = 0.6,
    min_results: int = 3,
    max_results: int = 8
) -> Tuple[List[Dict], Dict[str, any]]:
    """
    Filter retrieval results by similarity score.
    
    Args:
        results: List of retrieval results from Bedrock Knowledge Base
        threshold: Minimum similarity score to include (default: 0.6)
        min_results: Minimum number of results to return (default: 3)
        max_results: Maximum number of results to return (default: 8)
        
    Returns:
        Tuple of (filtered_results, metadata)
    """
    if not results:
        logger.warning("No results to filter")
        return [], {
            'original_count': 0,
            'filtered_count': 0,
            'threshold_used': threshold,
            'fallback_used': False,
            'avg_score': 0.0
        }
    
    original_count = len(results)
    
    # Extract scores and filter
    scored_results = []
    for result in results:
        # Bedrock returns score in the result metadata
        score = result.get('score', 0.0)
        scored_results.append({
            'result': result,
            'score': score
        })
    
    # Filter by threshold
    filtered = [item for item in scored_results if item['score'] >= threshold]
    
    # Calculate average score before filtering
    avg_score = sum(item['score'] for item in scored_results) / len(scored_results)
    
    # Check if we need to fall back to lower threshold
    fallback_used = False
    if len(filtered) < min_results and threshold > 0.5:
        logger.info(
            f"Filtered results ({len(filtered)}) below minimum ({min_results}), "
            f"falling back to threshold 0.5"
        )
        threshold = 0.5
        fallback_used = True
        filtered = [item for item in scored_results if item['score'] >= threshold]
    
    # Sort by score descending and take top max_results
    filtered.sort(key=lambda x: x['score'], reverse=True)
    filtered = filtered[:max_results]
    
    # Extract just the results
    filtered_results = [item['result'] for item in filtered]
    
    # Calculate average score after filtering
    avg_filtered_score = sum(item['score'] for item in filtered) / len(filtered) if filtered else 0.0
    
    # Create metadata
    metadata = {
        'original_count': original_count,
        'filtered_count': len(filtered_results),
        'threshold_used': threshold,
        'fallback_used': fallback_used,
        'avg_score': round(avg_score, 3),
        'avg_filtered_score': round(avg_filtered_score, 3),
        'filtered_out': original_count - len(filtered_results),
        'scores': [round(item['score'], 3) for item in filtered]
    }
    
    # Log the filtering results
    logger.info(
        f"Retrieved {original_count} docs, filtered to {len(filtered_results)} "
        f"(threshold: {threshold}, avg score: {avg_filtered_score:.3f})"
    )
    
    if fallback_used:
        logger.warning(
            f"Fallback threshold used: {len(filtered_results)} results with threshold 0.5"
        )
    
    return filtered_results, metadata


def validate_similarity_threshold(threshold: float) -> bool:
    """
    Validate that the similarity threshold is in a valid range.
    
    Args:
        threshold: The threshold value to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(threshold, (int, float)):
        logger.error(f"Threshold must be a number, got {type(threshold)}")
        return False
    
    if threshold < 0.0 or threshold > 1.0:
        logger.error(f"Threshold must be between 0.0 and 1.0, got {threshold}")
        return False
    
    return True


def get_similarity_distribution(results: List[Dict]) -> Dict[str, float]:
    """
    Analyze the distribution of similarity scores in retrieval results.
    
    Args:
        results: List of retrieval results
        
    Returns:
        Dictionary with distribution statistics
    """
    if not results:
        return {
            'min': 0.0,
            'max': 0.0,
            'avg': 0.0,
            'median': 0.0,
            'count': 0
        }
    
    scores = [result.get('score', 0.0) for result in results]
    scores.sort()
    
    count = len(scores)
    min_score = scores[0]
    max_score = scores[-1]
    avg_score = sum(scores) / count
    median_score = scores[count // 2] if count > 0 else 0.0
    
    return {
        'min': round(min_score, 3),
        'max': round(max_score, 3),
        'avg': round(avg_score, 3),
        'median': round(median_score, 3),
        'count': count
    }

