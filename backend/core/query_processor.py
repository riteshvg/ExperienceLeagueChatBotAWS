"""
Query Preprocessing Module

This module provides intelligent query preprocessing for Adobe-specific abbreviations
and contextual enhancement to improve retrieval quality.
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Handles query preprocessing and abbreviation expansion."""
    
    def __init__(self):
        """Initialize the query processor with Adobe-specific mappings."""
        
        # Adobe abbreviation expansions
        self.abbreviations = {
            # Core Adobe Products
            'cja': 'Customer Journey Analytics',
            'aa': 'Adobe Analytics',
            'aep': 'Adobe Experience Platform',
            'ajo': 'Adobe Journey Optimizer',
            'aam': 'Adobe Audience Manager',
            'at': 'Adobe Target',
            'acp': 'Adobe Campaign',
            'aem': 'Adobe Experience Manager',
            
            # Analytics Components
            'evar': 'eVar conversion variable',
            'prop': 'prop traffic variable',
            'calc metric': 'calculated metric',
            'calc': 'calculated',
            'seg': 'segment',
            'dim': 'dimension',
            'met': 'metric',
            'event': 'success event',
            'conversion': 'conversion event',
            
            # Technical Terms
            's.t()': 's.t() page view tracking',
            's.tl()': 's.tl() link tracking',
            'visitor id': 'visitor ID',
            'hit': 'hit data',
            'visit': 'visit data',
            'page view': 'page view',
            'bounce rate': 'bounce rate',
            'session': 'session data',
            
            # Data Sources
            'rs': 'report suite',
            'dv': 'data view',
            'ds': 'data source',
            'conn': 'connection',
            'schema': 'XDM schema',
            'profile': 'profile data',
            'identity': 'identity namespace',
            
            # UI Elements
            'freeform': 'Freeform Table',
            'cohort': 'Cohort Analysis',
            'flow': 'Flow Analysis',
            'fallout': 'Fallout Analysis',
            'pathing': 'Pathing Analysis',
            'attribution': 'Attribution IQ',
            'anomaly': 'Anomaly Detection',
            'calendar': 'Calendar Events',
            'alert': 'Intelligent Alerts',
            
            # Common Abbreviations
            'api': 'API',
            'sdk': 'SDK',
            'ui': 'user interface',
            'ux': 'user experience',
            'etl': 'ETL',
            'rtcdp': 'Real-time Customer Data Platform',
            'cdp': 'Customer Data Platform',
            'dmp': 'Data Management Platform',
            'crm': 'CRM',
            'cms': 'Content Management System'
        }
        
        # Contextual enhancement patterns
        self.context_patterns = {
            'how_to': {
                'patterns': [r'\bhow to\b', r'\bhow do i\b', r'\bhow can i\b', r'\bcreate\b', r'\bset up\b', r'\bconfigure\b', r'\bbuild\b'],
                'enhancement': 'step-by-step guide tutorial'
            },
            'comparison': {
                'patterns': [r'\bdifference between\b', r'\bvs\b', r'\bversus\b', r'\bcompare\b', r'\bcontrast\b'],
                'enhancement': 'comparison explanation'
            },
            'troubleshooting': {
                'patterns': [r'\berror\b', r'\bnot working\b', r'\bfailed\b', r'\bissue\b', r'\bproblem\b', r'\bfix\b', r'\bresolve\b'],
                'enhancement': 'troubleshooting fix'
            },
            'best_practices': {
                'patterns': [r'\bbest practice\b', r'\brecommendation\b', r'\bguideline\b', r'\btip\b', r'\boptimize\b'],
                'enhancement': 'recommendations guidelines'
            },
            'definition': {
                'patterns': [r'\bwhat is\b', r'\bdefine\b', r'\bmeaning\b', r'\bexplain\b'],
                'enhancement': 'definition explanation'
            }
        }
    
    def preprocess_query(self, query: str) -> Tuple[str, Dict[str, any]]:
        """
        Preprocess query with abbreviation expansion and contextual enhancement.
        
        Args:
            query: Original user query
            
        Returns:
            Tuple of (enhanced_query, metadata)
        """
        if not query or not query.strip():
            return query, {'original': query, 'enhanced': query, 'changes': []}
        
        original_query = query.strip()
        enhanced_query = original_query
        
        # Track changes for logging
        changes = []
        
        # Step 1: Expand abbreviations
        enhanced_query, abbreviation_changes = self._expand_abbreviations(enhanced_query)
        changes.extend(abbreviation_changes)
        
        # Step 2: Add product-specific enhancements
        enhanced_query, product_changes = self._add_product_specific_enhancements(enhanced_query)
        changes.extend(product_changes)
        
        # Step 3: Add contextual enhancements
        enhanced_query, context_changes = self._add_contextual_enhancements(enhanced_query)
        changes.extend(context_changes)
        
        # Step 4: Clean up the query
        enhanced_query = self._clean_query(enhanced_query)
        
        # Create metadata
        metadata = {
            'original': original_query,
            'enhanced': enhanced_query,
            'changes': changes,
            'abbreviation_expansions': len([c for c in changes if c['type'] == 'abbreviation']),
            'product_specific_enhancements': len([c for c in changes if c['type'] == 'product_specific']),
            'contextual_enhancements': len([c for c in changes if c['type'] == 'context']),
            'was_modified': enhanced_query != original_query
        }
        
        # Log changes if any
        if metadata['was_modified']:
            logger.info(f"Query preprocessing: '{original_query}' → '{enhanced_query}'")
            logger.debug(f"Changes: {changes}")
        
        return enhanced_query, metadata
    
    def _expand_abbreviations(self, query: str) -> Tuple[str, List[Dict]]:
        """
        Expand Adobe-specific abbreviations in the query.

        Matches are collected first on a stable snapshot of the string, then
        applied right-to-left so that earlier positions remain valid throughout.
        """
        changes = []
        processed_query = query

        # Longest abbreviation first to avoid clobbering substrings
        sorted_abbreviations = sorted(
            self.abbreviations.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )

        for abbreviation, expansion in sorted_abbreviations:
            pattern = r'\b' + re.escape(abbreviation) + r'\b'

            # Snapshot all valid matches in the current string before mutating it
            candidates = [
                m for m in re.finditer(pattern, processed_query, re.IGNORECASE)
                if not self._is_inside_quotes(processed_query, m.start())
                and not self._would_create_redundancy(processed_query, m, expansion)
            ]

            # Replace right-to-left so left-side positions stay valid
            for match in reversed(candidates):
                original_text = match.group()
                processed_query = (
                    processed_query[:match.start()]
                    + expansion
                    + processed_query[match.end():]
                )
                changes.append({
                    'type': 'abbreviation',
                    'original': original_text,
                    'replacement': expansion,
                    'position': match.start(),
                })

        return processed_query, changes
    
    def _add_contextual_enhancements(self, query: str) -> Tuple[str, List[Dict]]:
        """
        Add contextual enhancements based on query patterns.
        
        Args:
            query: Query to enhance
            
        Returns:
            Tuple of (enhanced_query, changes)
        """
        changes = []
        enhanced_query = query
        
        # Check each context pattern
        for context_type, context_data in self.context_patterns.items():
            patterns = context_data['patterns']
            enhancement = context_data['enhancement']
            
            # Check if any pattern matches
            for pattern in patterns:
                if re.search(pattern, enhanced_query, re.IGNORECASE):
                    # Add enhancement if not already present
                    if enhancement.lower() not in enhanced_query.lower():
                        enhanced_query += f" {enhancement}"
                        changes.append({
                            'type': 'context',
                            'context_type': context_type,
                            'enhancement': enhancement,
                            'pattern_matched': pattern
                        })
                    break  # Only add one enhancement per context type
        
        return enhanced_query, changes
    
    def _add_product_specific_enhancements(self, query: str) -> Tuple[str, List[Dict]]:
        """
        Add product-specific enhancements to distinguish between Adobe products.
        
        Args:
            query: Query to process
            
        Returns:
            Tuple of (enhanced_query, changes)
        """
        enhanced_query = query
        changes = []
        
        # Detect Adobe Journey Optimizer queries (check first — "journey" is ambiguous)
        ajo_patterns = [
            r'\badobe journey optimizer\b',
            r'\bjourney optimizer\b',
            r'\bajo\b',
            r'\bjourney canvas\b',
            r'\bdecision management\b',
            r'\boffer library\b',
            r'\bsuppression rules?\b',
            r'\bmessage frequency\b',
            r'\bcapping rules?\b',
        ]

        # Detect Customer Journey Analytics queries
        cja_patterns = [
            r'\bcustomer journey analytics\b',
            r'\bcja\b',
            r'\bjourney analytics\b',
            r'\bcross-device analytics\b',
            r'\bdata view\b',
            r'\bconnection\b.*\bcja\b',
            r'\bcja.*\bconnection\b',
            r'\bcustomer.*journey.*analytics\b',
        ]

        # Detect Adobe Analytics queries
        aa_patterns = [
            r'\badobe analytics\b',
            r'\banalytics\b(?!.*\bjourney\b)(?!.*\bcustomer\b)',
            r'\breport suite\b',
            r'\bevar\b',
            r'\bprop\b',
            r'\bsegments?\b',
            r'\bcalculated metrics?\b',
            r'\battribution\b',
            r'\bcohort\b',
            r'\bflow\b',
            r'\bfallout\b',
        ]

        is_ajo_query = any(re.search(pattern, query.lower()) for pattern in ajo_patterns)
        is_cja_query = any(re.search(pattern, query.lower()) for pattern in cja_patterns) if not is_ajo_query else False

        # Check for Adobe Analytics patterns (only if not AJO or CJA)
        is_aa_query = False
        if not is_ajo_query and not is_cja_query:
            is_aa_query = any(re.search(pattern, query.lower()) for pattern in aa_patterns)

        # Add product-specific keywords to disambiguate
        if is_ajo_query:
            enhanced_query += " Adobe Journey Optimizer AJO journey canvas decision management"
            changes.append({
                'type': 'product_specific',
                'action': 'added_ajo_keywords',
                'description': 'Added AJO-specific keywords to route to Journey Optimizer docs',
            })
            logger.info("AJO query detected, adding Journey Optimizer keywords")

        elif is_cja_query and not is_aa_query:
            enhanced_query += " Customer Journey Analytics CJA cross-device analytics"
            changes.append({
                'type': 'product_specific',
                'action': 'added_cja_keywords',
                'description': 'Added CJA-specific keywords to disambiguate from Adobe Analytics',
            })
            logger.info("CJA query detected, adding CJA-specific keywords")

        elif is_aa_query and not is_cja_query:
            enhanced_query += " Adobe Analytics report suite segments calculated metrics"
            changes.append({
                'type': 'product_specific',
                'action': 'added_aa_keywords',
                'description': 'Added Adobe Analytics-specific keywords to disambiguate from CJA',
            })
            logger.info("Adobe Analytics query detected, adding AA-specific keywords")

        elif 'journey' in query.lower() and not is_cja_query and not is_ajo_query:
            # Truly ambiguous journey reference (not CJA, not AJO) — lean toward AA
            enhanced_query += " Adobe Analytics journey analysis workspace"
            changes.append({
                'type': 'product_specific',
                'action': 'clarified_journey',
                'description': 'Clarified ambiguous journey query as Adobe Analytics Journey features',
            })
            logger.info("Ambiguous journey query detected, clarifying as Adobe Analytics")

        return enhanced_query, changes
    
    def _clean_query(self, query: str) -> str:
        """
        Clean up the enhanced query.
        
        Args:
            query: Query to clean
            
        Returns:
            Cleaned query
        """
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Remove duplicate words (simple approach)
        words = query.split()
        cleaned_words = []
        seen_words = set()
        
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen_words or len(word) > 3:  # Keep short words
                cleaned_words.append(word)
                seen_words.add(word_lower)
        
        return ' '.join(cleaned_words).strip()
    
    def _is_inside_quotes(self, text: str, position: int) -> bool:
        """
        Check if a position is inside quotes.
        
        Args:
            text: Text to check
            position: Position to check
            
        Returns:
            True if inside quotes
        """
        # Count quotes before the position
        quotes_before = text[:position].count('"') + text[:position].count("'")
        return quotes_before % 2 == 1
    
    def _would_create_redundancy(self, query: str, match: re.Match, expansion: str) -> bool:
        """
        Check if expansion would create redundancy.
        
        Args:
            query: Original query
            match: Match object
            expansion: Proposed expansion
            
        Returns:
            True if would create redundancy
        """
        # Check if expansion is already present nearby
        start = max(0, match.start() - 100)
        end = min(len(query), match.end() + 100)
        context = query[start:end].lower()
        
        # Check for exact phrase matches that would be redundant
        expansion_lower = expansion.lower()
        
        # Split expansion into meaningful parts (words > 4 chars)
        expansion_words = [w for w in expansion_lower.split() if len(w) > 4]
        
        # If most of the expansion is already present, skip
        words_found = sum(1 for word in expansion_words if word in context)
        if len(expansion_words) > 0 and words_found >= len(expansion_words) * 0.7:
            return True
        
        return False
    
    def get_abbreviation_list(self) -> Dict[str, str]:
        """
        Get the list of supported abbreviations.
        
        Returns:
            Dictionary of abbreviations and their expansions
        """
        return self.abbreviations.copy()
    
    def add_custom_abbreviation(self, abbreviation: str, expansion: str):
        """
        Add a custom abbreviation expansion.
        
        Args:
            abbreviation: Abbreviation to add
            expansion: Full expansion
        """
        self.abbreviations[abbreviation.lower()] = expansion
        logger.info(f"Added custom abbreviation: {abbreviation} → {expansion}")
    
    def validate_query(self, query: str) -> Dict[str, any]:
        """
        Validate a query and return analysis.
        
        Args:
            query: Query to validate
            
        Returns:
            Validation results
        """
        if not query or not query.strip():
            return {
                'valid': False,
                'error': 'Empty query',
                'suggestions': ['Please provide a question about Adobe Analytics, CJA, or AEP']
            }
        
        if len(query.strip()) < 3:
            return {
                'valid': False,
                'error': 'Query too short',
                'suggestions': ['Please provide a more detailed question']
            }
        
        if len(query) > 1000:
            return {
                'valid': False,
                'error': 'Query too long',
                'suggestions': ['Please provide a more concise question']
            }
        
        # Check for potential abbreviations
        potential_abbreviations = []
        words = query.lower().split()
        for word in words:
            if word in self.abbreviations:
                potential_abbreviations.append(word)
        
        return {
            'valid': True,
            'potential_abbreviations': potential_abbreviations,
            'suggestions': []
        }


# Global instance for easy import
query_processor = QueryProcessor()


def preprocess_query(query: str) -> Tuple[str, Dict[str, any]]:
    """
    Convenience function to preprocess a query.
    
    Args:
        query: Query to preprocess
        
    Returns:
        Tuple of (enhanced_query, metadata)
    """
    return query_processor.preprocess_query(query)


def validate_query(query: str) -> Dict[str, any]:
    """
    Convenience function to validate a query.
    
    Args:
        query: Query to validate
        
    Returns:
        Validation results
    """
    return query_processor.validate_query(query)
