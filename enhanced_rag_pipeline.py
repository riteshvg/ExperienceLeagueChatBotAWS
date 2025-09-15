"""
Enhanced RAG Pipeline with Query Enhancement

This module provides an enhanced RAG pipeline that integrates query enhancement
for improved document retrieval and response quality.
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import boto3
from query_enhancer import query_enhancer
from config.settings import get_settings_instance

logger = logging.getLogger(__name__)
settings = get_settings_instance()


@dataclass
class EnhancedSearchResult:
    """Enhanced search result with metadata"""
    content: str
    score: float
    source: str
    enhanced_query: str
    product_context: List[str]
    processing_time_ms: float


class EnhancedRAGPipeline:
    """
    Enhanced RAG Pipeline with Query Enhancement
    
    Features:
    - Query enhancement for better retrieval
    - Parallel document search
    - Result deduplication and ranking
    - Performance monitoring
    """
    
    def __init__(self):
        self.bedrock_agent_client = boto3.client(
            'bedrock-agent-runtime',
            region_name=settings.aws_default_region
        )
        self.knowledge_base_id = settings.bedrock_knowledge_base_id
        
        # Performance tracking
        self.search_times = []
        self.enhancement_times = []
        
    async def enhanced_retrieve_documents(
        self, 
        query: str, 
        top_k: int = 5,
        use_enhancement: bool = None
    ) -> List[EnhancedSearchResult]:
        """
        Enhanced document retrieval with query transformation
        
        Args:
            query: Original user query
            top_k: Number of documents to retrieve per enhanced query
            use_enhancement: Whether to use query enhancement (defaults to config)
            
        Returns:
            List of enhanced search results
        """
        start_time = time.time()
        
        # Determine if enhancement should be used
        if use_enhancement is None:
            use_enhancement = settings.query_enhancement_enabled
        
        try:
            if use_enhancement:
                # Step 1: Enhance query (50-100ms)
                enhancement_start = time.time()
                enhanced_data = query_enhancer.safe_enhance_query(query)
                enhancement_time = (time.time() - enhancement_start) * 1000
                self.enhancement_times.append(enhancement_time)
                
                logger.info(f"Query enhancement completed in {enhancement_time:.2f}ms")
                logger.info(f"Enhanced queries: {enhanced_data['enhanced_queries']}")
                logger.info(f"Detected products: {enhanced_data['detected_products']}")
                
                # Step 2: Parallel searches (200-300ms)
                search_start = time.time()
                all_results = await self._parallel_vector_search(
                    enhanced_data['enhanced_queries'][:settings.query_enhancement_max_queries],
                    top_k
                )
                search_time = (time.time() - search_start) * 1000
                self.search_times.append(search_time)
                
                # Step 3: Combine and deduplicate results
                combined_results = self._deduplicate_and_rank(
                    all_results, 
                    enhanced_data,
                    query
                )
                
            else:
                # Fallback to simple search
                search_start = time.time()
                results = await self._single_vector_search(query, top_k)
                search_time = (time.time() - search_start) * 1000
                self.search_times.append(search_time)
                
                combined_results = [
                    EnhancedSearchResult(
                        content=doc.get('content', {}).get('text', ''),
                        score=doc.get('score', 0.0),
                        source=doc.get('location', {}).get('s3Location', {}).get('uri', ''),
                        enhanced_query=query,
                        product_context=[],
                        processing_time_ms=search_time
                    )
                    for doc in results
                ]
            
            total_time = (time.time() - start_time) * 1000
            logger.info(f"Enhanced retrieval completed in {total_time:.2f}ms")
            
            return combined_results[:top_k]
            
        except Exception as e:
            logger.error(f"Enhanced retrieval failed: {e}")
            # Fallback to simple search
            return await self._fallback_search(query, top_k)
    
    async def _parallel_vector_search(
        self, 
        enhanced_queries: List[str], 
        top_k: int
    ) -> List[List[Dict]]:
        """Run multiple vector searches concurrently"""
        tasks = []
        for enhanced_query in enhanced_queries:
            task = self._single_vector_search(enhanced_query, top_k)
            tasks.append(task)
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Filter out exceptions and return valid results
            valid_results = [r for r in results if isinstance(r, list)]
            return valid_results
        except Exception as e:
            logger.error(f"Parallel search failed: {e}")
            return []
    
    async def _single_vector_search(self, query: str, top_k: int) -> List[Dict]:
        """Single vector search using Bedrock Knowledge Base"""
        try:
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': top_k
                    }
                }
            )
            
            return response.get('retrievalResults', [])
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _deduplicate_and_rank(
        self, 
        all_results: List[List[Dict]], 
        enhanced_data: Dict,
        original_query: str
    ) -> List[EnhancedSearchResult]:
        """Deduplicate and rank results from multiple searches"""
        seen_sources = set()
        ranked_results = []
        
        # Flatten all results
        all_docs = []
        for query_results in all_results:
            for doc in query_results:
                all_docs.append(doc)
        
        # Sort by score (highest first)
        all_docs.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Deduplicate and create enhanced results
        for doc in all_docs:
            source = doc.get('location', {}).get('s3Location', {}).get('uri', '')
            if source not in seen_sources:
                seen_sources.add(source)
                
                # Determine which enhanced query found this document
                enhanced_query = self._find_best_matching_query(
                    doc, enhanced_data['enhanced_queries']
                )
                
                ranked_results.append(EnhancedSearchResult(
                    content=doc.get('content', {}).get('text', ''),
                    score=doc.get('score', 0.0),
                    source=source,
                    enhanced_query=enhanced_query,
                    product_context=enhanced_data.get('detected_products', []),
                    processing_time_ms=enhanced_data.get('processing_time_ms', 0)
                ))
        
        return ranked_results
    
    def _find_best_matching_query(self, doc: Dict, enhanced_queries: List[str]) -> str:
        """Find the best matching enhanced query for a document"""
        content = doc.get('content', {}).get('text', '').lower()
        
        # Simple heuristic: find query with most word overlap
        best_query = enhanced_queries[0] if enhanced_queries else ""
        best_score = 0
        
        for query in enhanced_queries:
            query_words = set(query.lower().split())
            content_words = set(content.split())
            overlap = len(query_words.intersection(content_words))
            
            if overlap > best_score:
                best_score = overlap
                best_query = query
        
        return best_query
    
    async def _fallback_search(self, query: str, top_k: int) -> List[EnhancedSearchResult]:
        """Fallback search when enhancement fails"""
        try:
            results = await self._single_vector_search(query, top_k)
            return [
                EnhancedSearchResult(
                    content=doc.get('content', {}).get('text', ''),
                    score=doc.get('score', 0.0),
                    source=doc.get('location', {}).get('s3Location', {}).get('uri', ''),
                    enhanced_query=query,
                    product_context=[],
                    processing_time_ms=0
                )
                for doc in results
            ]
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.search_times and not self.enhancement_times:
            return {"message": "No performance data available"}
        
        stats = {}
        
        if self.search_times:
            stats['search_times'] = {
                'avg_ms': sum(self.search_times) / len(self.search_times),
                'min_ms': min(self.search_times),
                'max_ms': max(self.search_times),
                'count': len(self.search_times)
            }
        
        if self.enhancement_times:
            stats['enhancement_times'] = {
                'avg_ms': sum(self.enhancement_times) / len(self.enhancement_times),
                'min_ms': min(self.enhancement_times),
                'max_ms': max(self.enhancement_times),
                'count': len(self.enhancement_times)
            }
        
        return stats
    
    def reset_performance_stats(self):
        """Reset performance statistics"""
        self.search_times = []
        self.enhancement_times = []


# Global instance for easy import
enhanced_rag_pipeline = EnhancedRAGPipeline()
