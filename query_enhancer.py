"""
Adobe Experience League RAG Query Enhancement Module

This module provides fast query enhancement for Adobe-specific terms and products
without heavy LLM processing, targeting 200-400ms latency improvement.
"""

import re
import time
import hashlib
from functools import lru_cache
from typing import List, Dict, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class AdobeQueryEnhancer:
    """
    Fast query enhancement system for Adobe Experience League RAG
    
    Features:
    - Adobe product detection and expansion
    - Technical synonym replacement
    - Query context enhancement
    - Caching for performance
    """
    
    def __init__(self):
        # Adobe product mapping with abbreviations and common names
        self.adobe_products = {
            # Adobe Analytics
            "analytics": "Adobe Analytics",
            "aa": "Adobe Analytics",
            "adobe analytics": "Adobe Analytics",
            "analytics implementation": "Adobe Analytics",
            "analytics setup": "Adobe Analytics",
            "analytics configuration": "Adobe Analytics",
            "analytics tracking": "Adobe Analytics",
            "analytics dashboard": "Adobe Analytics",
            "analytics reports": "Adobe Analytics",
            "analytics data": "Adobe Analytics",
            
            # Adobe Target
            "target": "Adobe Target",
            "at": "Adobe Target",
            "adobe target": "Adobe Target",
            "personalization": "Adobe Target",
            "ab testing": "Adobe Target",
            "a/b testing": "Adobe Target",
            "targeting": "Adobe Target",
            "audience targeting": "Adobe Target",
            "experience targeting": "Adobe Target",
            
            # Adobe Campaign
            "campaign": "Adobe Campaign",
            "ac": "Adobe Campaign",
            "adobe campaign": "Adobe Campaign",
            "email marketing": "Adobe Campaign",
            "email campaigns": "Adobe Campaign",
            "marketing automation": "Adobe Campaign",
            "campaign management": "Adobe Campaign",
            
            # Adobe Experience Manager
            "aem": "Adobe Experience Manager",
            "experience manager": "Adobe Experience Manager",
            "adobe experience manager": "Adobe Experience Manager",
            "cms": "Adobe Experience Manager",
            "content management": "Adobe Experience Manager",
            "web content": "Adobe Experience Manager",
            "sites": "Adobe Experience Manager",
            
            # Adobe Experience Platform
            "aep": "Adobe Experience Platform",
            "experience platform": "Adobe Experience Platform",
            "adobe experience platform": "Adobe Experience Platform",
            "platform": "Adobe Experience Platform",
            "data platform": "Adobe Experience Platform",
            "customer data platform": "Adobe Experience Platform",
            "cdp": "Adobe Experience Platform",
            "real-time cdp": "Adobe Experience Platform",
            "rtcdp": "Adobe Experience Platform",
            
            # Customer Journey Analytics
            "cja": "Customer Journey Analytics",
            "customer journey analytics": "Customer Journey Analytics",
            "journey analytics": "Customer Journey Analytics",
            "cross-channel analytics": "Customer Journey Analytics",
            "attribution": "Customer Journey Analytics",
            
            # Adobe Journey Optimizer
            "ajo": "Adobe Journey Optimizer",
            "journey optimizer": "Adobe Journey Optimizer",
            "adobe journey optimizer": "Adobe Journey Optimizer",
            "journey orchestration": "Adobe Journey Optimizer",
            "customer journey": "Adobe Journey Optimizer",
            "journey management": "Adobe Journey Optimizer",
            
            # Web SDK specific terms
            "web sdk": "Adobe Experience Platform Web SDK",
            "websdk": "Adobe Experience Platform Web SDK",
            "identitydata": "identity data",
            "identity data": "identity data",
            "ecid": "ECID",
            "core id": "CORE ID",
            "identitymap": "identityMap",
            "getidentity": "getIdentity",
            "sendevent": "sendEvent",
            
            # Adobe Audience Manager
            "aam": "Adobe Audience Manager",
            "audience manager": "Adobe Audience Manager",
            "adobe audience manager": "Adobe Audience Manager",
            "data management platform": "Adobe Audience Manager",
            "dmp": "Adobe Audience Manager",
            
            # Adobe Commerce
            "commerce": "Adobe Commerce",
            "magento": "Adobe Commerce",
            "adobe commerce": "Adobe Commerce",
            "ecommerce": "Adobe Commerce",
            "online store": "Adobe Commerce",
        }
        
        # Technical synonyms for Adobe context
        self.technical_synonyms = {
            "track": ["measure", "collect", "capture", "record", "monitor", "log"],
            "setup": ["implement", "configure", "install", "deploy", "initialize", "establish"],
            "dashboard": ["workspace", "report", "visualization", "view", "console"],
            "segment": ["audience", "cohort", "classification", "group", "subset"],
            "event": ["action", "interaction", "activity", "occurrence", "trigger"],
            "visitor": ["user", "customer", "individual", "person", "visitor"],
            "campaign": ["marketing", "promotion", "journey", "initiative", "program"],
            "content": ["asset", "creative", "material", "resource", "element"],
            "data": ["information", "metrics", "insights", "analytics", "statistics"],
            "integration": ["connection", "linking", "synchronization", "coupling"],
            "configuration": ["setup", "settings", "parameters", "options", "config"],
            "implementation": ["deployment", "setup", "installation", "configuration"],
            "reporting": ["analytics", "insights", "metrics", "dashboards", "reports"],
            "personalization": ["customization", "targeting", "individualization"],
            "audience": ["segment", "group", "cohort", "target", "demographic"],
            "workflow": ["process", "procedure", "pipeline", "sequence", "flow"],
            "api": ["interface", "endpoint", "service", "integration"],
            "schema": ["structure", "model", "format", "template", "blueprint"],
            "dataset": ["data collection", "data source", "table", "file"],
            "ingestion": ["import", "loading", "processing", "collection", "acquisition"]
        }
        
        # Adobe-specific context terms
        self.adobe_context_terms = [
            "adobe", "experience", "cloud", "marketing", "analytics", "platform",
            "journey", "campaign", "target", "manager", "optimizer", "commerce"
        ]
        
        # Common misspellings and variations
        self.misspellings = {
            "adobe": ["adobe", "adob", "adobe"],
            "analytics": ["analytics", "analitics", "analytics"],
            "experience": ["experience", "experiance", "experiance"],
            "platform": ["platform", "platfrom", "platform"],
            "journey": ["journey", "journy", "journey"],
            "campaign": ["campaign", "campain", "campaign"],
            "target": ["target", "targt", "target"],
            "manager": ["manager", "manger", "manager"],
            "optimizer": ["optimizer", "optimiser", "optimizer"],
            "commerce": ["commerce", "comerce", "commerce"]
        }
        
        # Query patterns for product detection
        self.product_patterns = {
            "analytics": [
                r"\b(analytics|aa|adobe analytics)\b",
                r"\b(track|measure|collect|report|dashboard|metric)\b.*\b(analytics|data|event)\b",
                r"\b(implementation|setup|configuration)\b.*\b(analytics|tracking)\b"
            ],
            "target": [
                r"\b(target|at|adobe target|personalization)\b",
                r"\b(ab testing|a/b testing|testing|experiment)\b",
                r"\b(audience|targeting|experience)\b.*\b(target|personalization)\b"
            ],
            "campaign": [
                r"\b(campaign|ac|adobe campaign|email)\b",
                r"\b(email marketing|marketing automation)\b",
                r"\b(campaign management|email campaigns)\b"
            ],
            "aem": [
                r"\b(aem|experience manager|adobe experience manager|cms)\b",
                r"\b(content management|web content|sites)\b",
                r"\b(cms|content management system)\b"
            ],
            "aep": [
                r"\b(aep|experience platform|adobe experience platform|platform)\b",
                r"\b(data platform|customer data platform|cdp|rtcdp)\b",
                r"\b(schema|dataset|ingestion|data ingestion)\b"
            ],
            "cja": [
                r"\b(cja|customer journey analytics|journey analytics)\b",
                r"\b(cross-channel|attribution|journey)\b.*\b(analytics|data)\b"
            ],
            "ajo": [
                r"\b(ajo|journey optimizer|adobe journey optimizer)\b",
                r"\b(journey orchestration|customer journey)\b",
                r"\b(journey management|orchestration)\b"
            ],
            "web_sdk": [
                r"\b(web sdk|websdk|adobe experience platform web sdk)\b",
                r"\b(identitydata|identity data|ecid|core id)\b",
                r"\b(identitymap|getidentity|sendevent)\b",
                r"\b(web sdk|websdk).*\b(identity|ecid|tracking)\b"
            ]
        }
    
    def enhance_query(self, original_query: str) -> Dict:
        """
        Fast query enhancement without LLM calls
        
        Args:
            original_query: The original user query
            
        Returns:
            Dict containing:
                - original: Original query
                - enhanced_queries: List of enhanced query variations
                - detected_products: List of detected Adobe products
                - processing_time_ms: Processing time in milliseconds
        """
        start_time = time.time()
        
        try:
            # Normalize query
            normalized_query = self._normalize_query(original_query)
            
            # Detect Adobe products
            detected_products = self._detect_adobe_products(normalized_query)
            
            # Generate enhanced queries
            enhanced_queries = self._generate_enhanced_queries(normalized_query, detected_products)
            
            # Add original query if not already included
            if original_query not in enhanced_queries:
                enhanced_queries.insert(0, original_query)
            
            # Limit to 5 enhanced queries for better coverage but not too many
            enhanced_queries = enhanced_queries[:5]
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'original': original_query,
                'enhanced_queries': enhanced_queries,
                'detected_products': detected_products,
                'processing_time_ms': round(processing_time, 2)
            }
            
        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}")
            return {
                'original': original_query,
                'enhanced_queries': [original_query],
                'detected_products': [],
                'processing_time_ms': 0
            }
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for consistent processing"""
        # Convert to lowercase and strip whitespace
        normalized = query.lower().strip()
        
        # Fix common misspellings
        for correct, variations in self.misspellings.items():
            for variation in variations:
                if variation != correct:
                    normalized = re.sub(r'\b' + re.escape(variation) + r'\b', correct, normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _detect_adobe_products(self, query: str) -> List[str]:
        """Detect Adobe products mentioned in query"""
        detected = set()
        
        # Direct product mentions
        for term, product in self.adobe_products.items():
            if re.search(r'\b' + re.escape(term) + r'\b', query, re.IGNORECASE):
                detected.add(product)
        
        # Pattern-based detection
        for product, patterns in self.product_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    detected.add(self.adobe_products.get(product, product))
        
        return list(detected)
    
    def _generate_enhanced_queries(self, query: str, detected_products: List[str]) -> List[str]:
        """Generate enhanced query variations"""
        enhanced_queries = []
        
        # 1. Product-specific enhancement
        if detected_products:
            for product in detected_products:
                enhanced_query = f"{product} {query}"
                enhanced_queries.append(enhanced_query)
        
        # 2. Web SDK specific enhancements
        if any(term in query.lower() for term in ['web sdk', 'websdk', 'identitydata', 'identity data']):
            # Add ECID and CORE ID terms for Web SDK identity queries
            if 'identity' in query.lower():
                enhanced_queries.append(f"{query} ECID CORE ID")
                enhanced_queries.append(f"Web SDK identity overview {query}")
                enhanced_queries.append(f"identity data Web SDK ECID tracking")
        
        # 3. Synonym expansion
        synonym_enhanced = self._apply_synonym_expansion(query)
        if synonym_enhanced != query:
            enhanced_queries.append(synonym_enhanced)
        
        # 4. Adobe context enhancement
        if not any(term in query.lower() for term in self.adobe_context_terms):
            context_enhanced = f"Adobe {query}"
            enhanced_queries.append(context_enhanced)
        
        # 5. Technical term enhancement
        tech_enhanced = self._apply_technical_enhancement(query)
        if tech_enhanced != query:
            enhanced_queries.append(tech_enhanced)
        
        return enhanced_queries
    
    def _apply_synonym_expansion(self, query: str) -> str:
        """Apply synonym expansion to query"""
        enhanced_query = query
        
        for original, synonyms in self.technical_synonyms.items():
            # Replace original term with first synonym
            pattern = r'\b' + re.escape(original) + r'\b'
            if re.search(pattern, enhanced_query, re.IGNORECASE):
                enhanced_query = re.sub(pattern, synonyms[0], enhanced_query, flags=re.IGNORECASE)
        
        return enhanced_query
    
    def _apply_technical_enhancement(self, query: str) -> str:
        """Apply technical enhancement to query"""
        enhanced_query = query
        
        # Add technical context for common queries
        technical_enhancements = {
            r'\btrack\b': 'track and measure',
            r'\bsetup\b': 'setup and configure',
            r'\bcreate\b': 'create and implement',
            r'\bconfigure\b': 'configure and customize',
            r'\bimplement\b': 'implement and deploy',
            r'\bmanage\b': 'manage and monitor',
            r'\banalyze\b': 'analyze and report',
            r'\boptimize\b': 'optimize and improve'
        }
        
        for pattern, replacement in technical_enhancements.items():
            if re.search(pattern, enhanced_query, re.IGNORECASE):
                enhanced_query = re.sub(pattern, replacement, enhanced_query, flags=re.IGNORECASE)
                break  # Only apply one enhancement per query
        
        return enhanced_query
    
    @lru_cache(maxsize=500)
    def cached_enhance_query(self, query_hash: str) -> Dict:
        """Cached version of query enhancement for performance"""
        # This will be called with the actual query, not hash
        # The hash is used as the cache key
        pass
    
    def get_query_hash(self, query: str) -> str:
        """Generate hash for query caching"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def safe_enhance_query(self, query: str) -> Dict:
        """
        Query enhancement with fallbacks
        If enhancement fails, return original query
        """
        try:
            return self.enhance_query(query)
        except Exception as e:
            logger.warning(f"Query enhancement failed: {e}")
            return {
                'original': query,
                'enhanced_queries': [query],
                'detected_products': [],
                'processing_time_ms': 0
            }


# Global instance for easy import
query_enhancer = AdobeQueryEnhancer()
