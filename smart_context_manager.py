"""
Smart Context Management System

This module provides intelligent context length management based on query complexity,
optimizing costs while maintaining response quality.
"""

import re
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

@dataclass
class ContextConfig:
    """Context configuration for different complexity levels"""
    max_chars_per_doc: int
    max_docs: int
    description: str

class SmartContextManager:
    """
    Smart Context Manager that adapts context length based on query complexity
    
    Features:
    - Query complexity detection
    - Adaptive context length
    - Cost optimization
    - Performance monitoring
    """
    
    def __init__(self):
        # Context configurations for different complexity levels
        self.context_configs = {
            QueryComplexity.SIMPLE: ContextConfig(
                max_chars_per_doc=500,
                max_docs=2,
                description="Simple queries - basic context for cost efficiency"
            ),
            QueryComplexity.MEDIUM: ContextConfig(
                max_chars_per_doc=1500,
                max_docs=3,
                description="Medium queries - balanced context for quality and cost"
            ),
            QueryComplexity.COMPLEX: ContextConfig(
                max_chars_per_doc=3000,
                max_docs=3,
                description="Complex queries - comprehensive context for detailed responses"
            )
        }
        
        # Complexity detection patterns
        self.complexity_patterns = {
            QueryComplexity.SIMPLE: [
                r'^what is\s+\w+',
                r'^how to\s+\w+',
                r'^define\s+\w+',
                r'^explain\s+\w+',
                r'^what are\s+\w+',
                r'^list\s+\w+',
                r'^show\s+\w+',
                r'^tell me about\s+\w+'
            ],
            QueryComplexity.COMPLEX: [
                r'how do i\s+.*\s+and\s+.*',  # Multiple actions
                r'what is the difference between.*and.*',  # Comparisons
                r'how can i\s+.*\s+in\s+.*\s+for\s+.*',  # Multi-part questions
                r'step by step.*process',  # Process questions
                r'best practices.*for.*',  # Best practices
                r'how to.*integrate.*with.*',  # Integration questions
                r'what are the.*requirements.*for.*',  # Requirements
                r'how does.*work.*with.*',  # How things work together
                r'compare.*and.*',  # Comparisons
                r'what are the.*steps.*to.*',  # Multi-step processes
                r'how to.*configure.*for.*',  # Configuration
                r'what is the.*architecture.*of.*',  # Architecture questions
                r'how to.*implement.*in.*',  # Implementation
                r'what are the.*considerations.*for.*',  # Considerations
                r'how to.*optimize.*for.*',  # Optimization
                r'what are the.*limitations.*of.*',  # Limitations
                r'how to.*troubleshoot.*',  # Troubleshooting
                r'what are the.*prerequisites.*for.*',  # Prerequisites
                r'how to.*migrate.*from.*to.*',  # Migration
                r'what are the.*security.*implications.*of.*'  # Security
            ]
        }
        
        # Technical complexity indicators
        self.technical_indicators = [
            'integration', 'configuration', 'implementation', 'architecture',
            'troubleshooting', 'optimization', 'migration', 'security',
            'authentication', 'authorization', 'deployment', 'monitoring',
            'scalability', 'performance', 'reliability', 'compliance',
            'governance', 'policies', 'workflows', 'pipelines',
            'apis', 'endpoints', 'middleware', 'infrastructure',
            'networking', 'storage', 'database', 'caching',
            'load balancing', 'failover', 'backup', 'recovery'
        ]
        
        # Query length thresholds
        self.length_thresholds = {
            'short': 50,      # Simple questions
            'medium': 150,    # Medium complexity
            'long': 300       # Complex questions
        }
        
        # Performance tracking
        self.complexity_detection_times = []
        self.context_usage_stats = {
            QueryComplexity.SIMPLE: 0,
            QueryComplexity.MEDIUM: 0,
            QueryComplexity.COMPLEX: 0
        }
    
    def detect_query_complexity(self, query: str) -> Tuple[QueryComplexity, Dict]:
        """
        Detect query complexity based on multiple factors
        
        Args:
            query: User query string
            
        Returns:
            Tuple of (complexity_level, detection_details)
        """
        start_time = time.time()
        
        query_lower = query.lower().strip()
        query_length = len(query)
        
        detection_details = {
            'query_length': query_length,
            'matched_patterns': [],
            'technical_indicators': [],
            'complexity_score': 0,
            'detection_time_ms': 0
        }
        
        # Check for complex patterns first
        for pattern in self.complexity_patterns[QueryComplexity.COMPLEX]:
            if re.search(pattern, query_lower, re.IGNORECASE):
                detection_details['matched_patterns'].append(pattern)
                detection_details['complexity_score'] += 3
        
        # Check for simple patterns
        for pattern in self.complexity_patterns[QueryComplexity.SIMPLE]:
            if re.search(pattern, query_lower, re.IGNORECASE):
                detection_details['matched_patterns'].append(pattern)
                detection_details['complexity_score'] += 1
        
        # Check for technical indicators
        technical_count = 0
        for indicator in self.technical_indicators:
            if indicator in query_lower:
                detection_details['technical_indicators'].append(indicator)
                technical_count += 1
                detection_details['complexity_score'] += 1
        
        # Length-based scoring
        if query_length > self.length_thresholds['long']:
            detection_details['complexity_score'] += 2
        elif query_length > self.length_thresholds['medium']:
            detection_details['complexity_score'] += 1
        
        # Question complexity indicators
        question_indicators = ['?', 'how', 'what', 'why', 'when', 'where', 'which']
        question_count = sum(1 for indicator in question_indicators if indicator in query_lower)
        detection_details['complexity_score'] += min(question_count, 2)
        
        # Determine complexity level
        if detection_details['complexity_score'] >= 5:
            complexity = QueryComplexity.COMPLEX
        elif detection_details['complexity_score'] >= 2:
            complexity = QueryComplexity.MEDIUM
        else:
            complexity = QueryComplexity.SIMPLE
        
        # Update stats
        self.context_usage_stats[complexity] += 1
        
        detection_time = (time.time() - start_time) * 1000
        detection_details['detection_time_ms'] = detection_time
        self.complexity_detection_times.append(detection_time)
        
        return complexity, detection_details
    
    def get_context_config(self, complexity: QueryComplexity) -> ContextConfig:
        """Get context configuration for given complexity level"""
        return self.context_configs[complexity]
    
    def prepare_smart_context(self, documents: List[Dict], query: str) -> Tuple[str, Dict]:
        """
        Prepare context with smart length management
        
        Args:
            documents: List of retrieved documents
            query: Original user query
            
        Returns:
            Tuple of (context_string, context_metadata)
        """
        start_time = time.time()
        
        # Detect query complexity
        complexity, detection_details = self.detect_query_complexity(query)
        
        # Get context configuration
        config = self.get_context_config(complexity)
        
        # Prepare context with appropriate length
        context_parts = []
        context_metadata = {
            'complexity': complexity.value,
            'config_used': config.description,
            'max_chars_per_doc': config.max_chars_per_doc,
            'max_docs': config.max_docs,
            'detection_details': detection_details,
            'processing_time_ms': 0
        }
        
        # Select and process documents
        selected_docs = documents[:config.max_docs]
        
        for i, doc in enumerate(selected_docs, 1):
            content = doc.get('content', {}).get('text', '')
            score = doc.get('score', 0)
            
            if content:
                # Use appropriate length based on complexity
                content_to_use = content[:config.max_chars_per_doc]
                if len(content) > config.max_chars_per_doc:
                    content_to_use += "..."
                
                context_parts.append(
                    f"Document {i} (Score: {score:.3f}): {content_to_use}"
                )
        
        context = "\n\n".join(context_parts)
        
        processing_time = (time.time() - start_time) * 1000
        context_metadata['processing_time_ms'] = processing_time
        context_metadata['context_length'] = len(context)
        context_metadata['documents_used'] = len(selected_docs)
        
        return context, context_metadata
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        if not self.complexity_detection_times:
            return {"message": "No performance data available"}
        
        stats = {
            'complexity_distribution': dict(self.context_usage_stats),
            'detection_times': {
                'avg_ms': sum(self.complexity_detection_times) / len(self.complexity_detection_times),
                'min_ms': min(self.complexity_detection_times),
                'max_ms': max(self.complexity_detection_times),
                'count': len(self.complexity_detection_times)
            },
            'context_configs': {
                level.value: {
                    'max_chars_per_doc': config.max_chars_per_doc,
                    'max_docs': config.max_docs,
                    'description': config.description
                }
                for level, config in self.context_configs.items()
            }
        }
        
        return stats
    
    def reset_stats(self):
        """Reset performance statistics"""
        self.complexity_detection_times = []
        self.context_usage_stats = {
            QueryComplexity.SIMPLE: 0,
            QueryComplexity.MEDIUM: 0,
            QueryComplexity.COMPLEX: 0
        }
    
    def update_context_config(self, complexity: QueryComplexity, max_chars: int, max_docs: int):
        """Update context configuration for a complexity level"""
        self.context_configs[complexity] = ContextConfig(
            max_chars_per_doc=max_chars,
            max_docs=max_docs,
            description=f"Updated config for {complexity.value} queries"
        )


# Global instance for easy import
smart_context_manager = SmartContextManager()
