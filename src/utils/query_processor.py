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
        
        # Step 2: Add contextual enhancements
        enhanced_query, context_changes = self._add_contextual_enhancements(enhanced_query)
        changes.extend(context_changes)
        
        # Step 3: Clean up the query
        enhanced_query = self._clean_query(enhanced_query)
        
        # Create metadata
        metadata = {
            'original': original_query,
            'enhanced': enhanced_query,
            'changes': changes,
            'abbreviation_expansions': len([c for c in changes if c['type'] == 'abbreviation']),
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
        
        Args:
            query: Query to process
            
        Returns:
            Tuple of (processed_query, changes)
        """
        changes = []
        processed_query = query
        
        # Sort abbreviations by length (longest first) to avoid partial matches
        sorted_abbreviations = sorted(
            self.abbreviations.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )
        
        for abbreviation, expansion in sorted_abbreviations:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(abbreviation) + r'\b'
            
            # Case-insensitive matching
            matches = re.finditer(pattern, processed_query, re.IGNORECASE)
            
            for match in matches:
                # Check if this is inside quotes (preserve original)
                if self._is_inside_quotes(processed_query, match.start()):
                    continue
                
                # Check if this would create a redundant expansion
                if self._would_create_redundancy(processed_query, match, expansion):
                    continue
                
                # Replace the abbreviation
                original_text = match.group()
                processed_query = (
                    processed_query[:match.start()] +
                    expansion +
                    processed_query[match.end():]
                )
                
                changes.append({
                    'type': 'abbreviation',
                    'original': original_text,
                    'replacement': expansion,
                    'position': match.start()
                })
                
                # Recalculate positions for subsequent matches
                offset = len(expansion) - len(original_text)
                for change in changes:
                    if change['position'] > match.start():
                        change['position'] += offset
        
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
