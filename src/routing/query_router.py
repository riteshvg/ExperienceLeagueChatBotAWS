"""
Intelligent query routing system for hybrid model architecture.
Determines optimal model based on query characteristics and user preferences.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class QueryAnalysis:
    """Analysis results for a query."""
    complexity: str  # simple, medium, complex
    query_type: str  # factual, analytical, code, troubleshooting
    context_requirements: str  # low, medium, high
    technical_keywords: List[str]
    query_length: int
    estimated_tokens: int
    confidence: float

@dataclass
class RoutingDecision:
    """Routing decision for a query."""
    recommended_model: str  # gemini, claude, auto
    reasoning: str
    confidence: float
    alternative_model: Optional[str] = None
    estimated_cost: float = 0.0
    estimated_time: float = 0.0

class QueryRouter:
    """Intelligent query routing system."""
    
    def __init__(self, config_manager=None):
        """Initialize query router."""
        self.config_manager = config_manager
        self.routing_rules = self._initialize_routing_rules()
        
        # Technical keywords for complexity analysis
        self.technical_keywords = {
            'adobe_analytics': [
                'adobe analytics', 'aa', 'evars', 'props', 'events', 'segments',
                'calculated metrics', 'virtual report suites', 'data warehouse',
                'attribution', 'conversion', 'funnel', 'pathing', 'cohort'
            ],
            'customer_journey': [
                'customer journey analytics', 'cja', 'cross-channel', 'identity',
                'stitching', 'personas', 'journey mapping', 'touchpoints'
            ],
            'experience_platform': [
                'adobe experience platform', 'aep', 'real-time cdp', 'profiles',
                'schemas', 'datasets', 'data governance', 'privacy'
            ],
            'implementation': [
                'implementation', 'tracking', 'sdk', 'javascript', 'mobile sdk',
                'server-side', 'data layer', 'tag manager', 'gtm'
            ],
            'troubleshooting': [
                'debug', 'troubleshoot', 'issue', 'problem', 'error', 'fix',
                'not working', 'broken', 'missing data'
            ],
            'advanced': [
                'machine learning', 'ai', 'predictive', 'anomaly detection',
                'statistical analysis', 'regression', 'correlation', 'clustering'
            ]
        }
        
        # Query type patterns
        self.query_patterns = {
            'factual': [
                r'what is',
                r'define',
                r'explain',
                r'describe',
                r'how does.*work'
            ],
            'analytical': [
                r'compare',
                r'analyze',
                r'evaluate',
                r'which.*better',
                r'pros and cons',
                r'advantages.*disadvantages'
            ],
            'code': [
                r'show.*code',
                r'javascript',
                r'implementation',
                r'example',
                r'sample',
                r'how to.*implement'
            ],
            'troubleshooting': [
                r'why.*not.*working',
                r'debug',
                r'troubleshoot',
                r'fix',
                r'error',
                r'issue',
                r'problem'
            ]
        }
        
        logger.info("Query router initialized")
    
    def _initialize_routing_rules(self) -> Dict[str, Any]:
        """Initialize routing rules based on configuration."""
        if self.config_manager:
            config = self.config_manager.get_model_selection_criteria()
            return {
                'cost_vs_quality': config['cost_vs_quality'],
                'max_response_time': config['max_response_time'],
                'max_cost_per_query': config['max_cost_per_query'],
                'complexity_thresholds': config['complexity_thresholds'],
                'user_preferences': config['user_preferences']
            }
        else:
            return {
                'cost_vs_quality': 0.5,
                'max_response_time': 30,
                'max_cost_per_query': 1.0,
                'complexity_thresholds': {'simple': 50, 'complex': 200},
                'user_preferences': {'preferred_model': 'auto', 'cost_sensitivity': 0.5, 'speed_priority': 0.5}
            }
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze query characteristics to determine complexity and requirements.
        
        Args:
            query: The query to analyze
            
        Returns:
            QueryAnalysis object with analysis results
        """
        query_lower = query.lower()
        query_length = len(query)
        
        # Count technical keywords
        technical_keywords_found = []
        for category, keywords in self.technical_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    technical_keywords_found.append(keyword)
        
        # Determine query type
        query_type = self._classify_query_type(query_lower)
        
        # Determine complexity
        complexity = self._classify_complexity(
            query_length, 
            technical_keywords_found, 
            query_type
        )
        
        # Determine context requirements
        context_requirements = self._classify_context_requirements(
            query_length, 
            technical_keywords_found, 
            query_type
        )
        
        # Estimate tokens (rough approximation)
        estimated_tokens = self._estimate_tokens(query)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            query_length, 
            len(technical_keywords_found), 
            query_type
        )
        
        return QueryAnalysis(
            complexity=complexity,
            query_type=query_type,
            context_requirements=context_requirements,
            technical_keywords=technical_keywords_found,
            query_length=query_length,
            estimated_tokens=estimated_tokens,
            confidence=confidence
        )
    
    def _classify_query_type(self, query_lower: str) -> str:
        """Classify the type of query."""
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return query_type
        
        return 'factual'  # Default to factual
    
    def _classify_complexity(self, query_length: int, technical_keywords: List[str], query_type: str) -> str:
        """Classify query complexity."""
        thresholds = self.routing_rules['complexity_thresholds']
        
        # Base complexity on length
        if query_length < thresholds['simple']:
            base_complexity = 'simple'
        elif query_length < thresholds['complex']:
            base_complexity = 'medium'
        else:
            base_complexity = 'complex'
        
        # Adjust based on technical keywords
        keyword_count = len(technical_keywords)
        if keyword_count >= 5:
            return 'complex'
        elif keyword_count >= 3:
            return 'medium' if base_complexity == 'simple' else 'complex'
        elif keyword_count >= 1:
            return 'medium' if base_complexity == 'simple' else base_complexity
        else:
            return base_complexity
    
    def _classify_context_requirements(self, query_length: int, technical_keywords: List[str], query_type: str) -> str:
        """Classify context requirements."""
        if query_type in ['analytical', 'troubleshooting'] or query_length > 200:
            return 'high'
        elif query_type in ['code'] or len(technical_keywords) >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _estimate_tokens(self, query: str) -> int:
        """Estimate token count for the query."""
        # Rough estimation: ~4 characters per token
        return len(query) // 4
    
    def _calculate_confidence(self, query_length: int, keyword_count: int, query_type: str) -> float:
        """Calculate confidence in the analysis."""
        # Base confidence
        confidence = 0.7
        
        # Adjust based on query length
        if query_length > 100:
            confidence += 0.1
        if query_length > 200:
            confidence += 0.1
        
        # Adjust based on technical keywords
        if keyword_count > 0:
            confidence += 0.1
        if keyword_count > 3:
            confidence += 0.1
        
        # Adjust based on query type
        if query_type in ['analytical', 'troubleshooting']:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def determine_best_model(
        self, 
        query: str, 
        context_length: int = 0,
        available_models: List[str] = None
    ) -> RoutingDecision:
        """
        Determine the best model for a query.
        
        Args:
            query: The query to route
            context_length: Length of context to be included
            available_models: List of available models
            
        Returns:
            RoutingDecision with recommended model and reasoning
        """
        if available_models is None:
            available_models = ['gemini', 'claude']
        
        # Analyze the query
        analysis = self.analyze_query(query)
        
        # Get user preferences
        user_prefs = self.routing_rules['user_preferences']
        cost_vs_quality = self.routing_rules['cost_vs_quality']
        
        # Determine recommended model
        recommended_model, reasoning = self._select_model(
            analysis, 
            context_length, 
            available_models, 
            user_prefs, 
            cost_vs_quality
        )
        
        # Calculate confidence
        confidence = analysis.confidence
        
        # Estimate cost and time
        estimated_cost = self._estimate_cost(recommended_model, analysis.estimated_tokens)
        estimated_time = self._estimate_time(recommended_model, analysis.complexity)
        
        # Determine alternative model
        alternative_model = None
        if len(available_models) > 1:
            alternative_model = next(
                (model for model in available_models if model != recommended_model), 
                None
            )
        
        return RoutingDecision(
            recommended_model=recommended_model,
            reasoning=reasoning,
            confidence=confidence,
            alternative_model=alternative_model,
            estimated_cost=estimated_cost,
            estimated_time=estimated_time
        )
    
    def _select_model(
        self, 
        analysis: QueryAnalysis, 
        context_length: int, 
        available_models: List[str],
        user_prefs: Dict[str, Any],
        cost_vs_quality: float
    ) -> Tuple[str, str]:
        """Select the best model based on analysis."""
        
        # Check user preference
        if user_prefs['preferred_model'] != 'auto' and user_prefs['preferred_model'] in available_models:
            return user_prefs['preferred_model'], "User preferred model"
        
        # Model selection logic
        if analysis.context_requirements == 'high' and 'gemini' in available_models:
            return 'gemini', f"High context requirements ({analysis.context_requirements}) - Gemini has larger context window"
        
        if analysis.complexity == 'simple' and 'claude' in available_models:
            return 'claude', f"Simple query - Claude is faster and more cost-effective"
        
        if analysis.query_type == 'code' and 'claude' in available_models:
            return 'claude', f"Code-related query - Claude excels at code generation"
        
        if analysis.query_type == 'troubleshooting' and 'claude' in available_models:
            return 'claude', f"Troubleshooting query - Claude is better at problem-solving"
        
        if analysis.complexity == 'complex' and 'gemini' in available_models:
            return 'gemini', f"Complex query - Gemini handles complex reasoning better"
        
        if cost_vs_quality < 0.5 and 'gemini' in available_models:
            return 'gemini', f"Cost-sensitive query - Gemini is more cost-effective"
        
        if cost_vs_quality > 0.5 and 'claude' in available_models:
            return 'claude', f"Quality-focused query - Claude provides higher quality responses"
        
        # Default fallback
        if 'claude' in available_models:
            return 'claude', "Default fallback to Claude"
        elif 'gemini' in available_models:
            return 'gemini', "Default fallback to Gemini"
        else:
            return available_models[0], "Only available model"
    
    def _estimate_cost(self, model: str, estimated_tokens: int) -> float:
        """Estimate cost for a query."""
        # Rough cost estimates per 1K tokens
        cost_per_1k = {
            'gemini': 0.000075,  # $0.075 per 1M tokens
            'claude': 0.003      # $3.00 per 1M tokens
        }
        
        return (estimated_tokens / 1000) * cost_per_1k.get(model, 0.001)
    
    def _estimate_time(self, model: str, complexity: str) -> float:
        """Estimate response time for a query."""
        # Base response times in seconds
        base_times = {
            'gemini': 3.0,
            'claude': 2.0
        }
        
        # Complexity multipliers
        complexity_multipliers = {
            'simple': 1.0,
            'medium': 1.5,
            'complex': 2.0
        }
        
        base_time = base_times.get(model, 2.5)
        multiplier = complexity_multipliers.get(complexity, 1.0)
        
        return base_time * multiplier
    
    def get_routing_explanation(self, query: str) -> Dict[str, Any]:
        """Get detailed explanation of routing decision."""
        analysis = self.analyze_query(query)
        decision = self.determine_best_model(query)
        
        return {
            'query_analysis': {
                'complexity': analysis.complexity,
                'query_type': analysis.query_type,
                'context_requirements': analysis.context_requirements,
                'technical_keywords': analysis.technical_keywords,
                'query_length': analysis.query_length,
                'estimated_tokens': analysis.estimated_tokens,
                'confidence': analysis.confidence
            },
            'routing_decision': {
                'recommended_model': decision.recommended_model,
                'reasoning': decision.reasoning,
                'confidence': decision.confidence,
                'alternative_model': decision.alternative_model,
                'estimated_cost': decision.estimated_cost,
                'estimated_time': decision.estimated_time
            },
            'routing_rules': self.routing_rules
        }
    
    def update_routing_rules(self, new_rules: Dict[str, Any]):
        """Update routing rules."""
        self.routing_rules.update(new_rules)
        logger.info(f"Routing rules updated: {new_rules}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return ['gemini', 'claude']
    
    def test_routing(self, test_queries: List[str]) -> Dict[str, Any]:
        """Test routing decisions on a set of queries."""
        results = {}
        
        for i, query in enumerate(test_queries):
            try:
                analysis = self.analyze_query(query)
                decision = self.determine_best_model(query)
                
                results[f"query_{i+1}"] = {
                    'query': query,
                    'analysis': {
                        'complexity': analysis.complexity,
                        'query_type': analysis.query_type,
                        'confidence': analysis.confidence
                    },
                    'decision': {
                        'model': decision.recommended_model,
                        'reasoning': decision.reasoning,
                        'confidence': decision.confidence
                    }
                }
            except Exception as e:
                results[f"query_{i+1}"] = {
                    'query': query,
                    'error': str(e)
                }
        
        return results
