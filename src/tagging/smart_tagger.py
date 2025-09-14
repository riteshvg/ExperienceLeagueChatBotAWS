"""
Smart Auto-Tagging System for Adobe Experience League Chatbot

This module provides intelligent auto-tagging capabilities for user questions,
including product detection, question classification, and technical level assessment.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class TechnicalLevel(Enum):
    """Technical expertise levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class QuestionType(Enum):
    """Question classification types."""
    IMPLEMENTATION = "implementation"
    TROUBLESHOOTING = "troubleshooting"
    CONFIGURATION = "configuration"
    REPORTING = "reporting"
    API = "api"
    INTEGRATION = "integration"
    PRIVACY = "privacy"
    MOBILE = "mobile"
    GENERAL = "general"

@dataclass
class TaggingResult:
    """Result of the smart tagging process."""
    products: List[str]
    question_type: QuestionType
    technical_level: TechnicalLevel
    topics: List[str]
    confidence_score: float
    urgency: str
    raw_analysis: Dict[str, Any]

class SmartTagger:
    """Smart auto-tagging system for Adobe Experience League questions."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the Smart Tagger.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or self._get_default_config()
        self._initialize_patterns()
        self._initialize_keywords()
        
    def _get_default_config(self) -> Dict:
        """Get default configuration."""
        return {
            "confidence_threshold": 0.7,
            "bedrock_enhancement_threshold": 0.5,
            "urgency_thresholds": {
                "high": 0.8,
                "medium": 0.6,
                "low": 0.4
            },
            "enable_bedrock_enhancement": True,
            "log_level": "INFO"
        }
    
    def _initialize_patterns(self):
        """Initialize regex patterns for product detection."""
        self.patterns = {
            "adobe_analytics": [
                r'\b(?:adobe analytics|aa|analytics)\b',
                r'\b(?:omniture|sitecatalyst)\b',
                r'\b(?:appmeasurement|s_code)\b',
                r'\b(?:visitor api|visitor id)\b'
            ],
            "customer_journey_analytics": [
                r'\b(?:customer journey analytics|cja)\b',
                r'\b(?:cross-device|cross device)\b',
                r'\b(?:person id|personid)\b',
                r'\b(?:data view|dataview)\b'
            ],
            "adobe_experience_platform": [
                r'\b(?:adobe experience platform|aep|experience platform)\b',
                r'\b(?:real-time cdp|rtcdp)\b',
                r'\b(?:profile service|identity service)\b',
                r'\b(?:data lake|datalake)\b'
            ],
            "adobe_launch": [
                r'\b(?:adobe launch|launch|dynamic tag manager|dtm)\b',
                r'\b(?:data collection|data collection ui)\b',
                r'\b(?:property|environment|rule)\b'
            ],
            "adobe_tags": [
                r'\b(?:adobe tags|tags)\b',
                r'\b(?:tag management|tagmanager)\b'
            ],
            "data_collection": [
                r'\b(?:data collection|data collection ui)\b',
                r'\b(?:web sdk|websdk|alloy)\b',
                r'\b(?:edge network|edge)\b'
            ],
            "appmeasurement": [
                r'\b(?:appmeasurement|s_code|s_code\.js)\b',
                r'\b(?:analytics\.js|analytics\.min\.js)\b'
            ],
            "aep_web_sdk": [
                r'\b(?:aep web sdk|web sdk|alloy)\b',
                r'\b(?:adobe alloy|alloy\.js)\b'
            ]
        }
        
        # Compile patterns for better performance
        self.compiled_patterns = {}
        for product, patterns in self.patterns.items():
            self.compiled_patterns[product] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def _initialize_keywords(self):
        """Initialize keyword libraries for classification."""
        self.keywords = {
            "question_types": {
                QuestionType.IMPLEMENTATION: [
                    "implement", "setup", "install", "configure", "deploy",
                    "tracking", "code", "javascript", "sdk", "api",
                    "integration", "connect", "link"
                ],
                QuestionType.TROUBLESHOOTING: [
                    "error", "issue", "problem", "not working", "broken",
                    "fix", "debug", "troubleshoot", "why", "how to fix",
                    "not showing", "missing", "incorrect"
                ],
                QuestionType.CONFIGURATION: [
                    "config", "settings", "options", "preferences",
                    "customize", "modify", "change", "update",
                    "admin", "permissions", "access"
                ],
                QuestionType.REPORTING: [
                    "report", "dashboard", "visualization", "chart",
                    "metric", "kpi", "analysis", "insights",
                    "data", "export", "schedule"
                ],
                QuestionType.API: [
                    "api", "rest", "endpoint", "request", "response",
                    "authentication", "token", "key", "credentials",
                    "webhook", "integration"
                ],
                QuestionType.INTEGRATION: [
                    "integrate", "connect", "sync", "import", "export",
                    "third party", "partner", "connector", "bridge"
                ],
                QuestionType.PRIVACY: [
                    "privacy", "gdpr", "ccpa", "consent", "opt-out",
                    "data protection", "personal data", "pii"
                ],
                QuestionType.MOBILE: [
                    "mobile", "ios", "android", "app", "sdk",
                    "push notification", "deep link", "attribution"
                ]
            },
            "technical_levels": {
                TechnicalLevel.BEGINNER: [
                    "what is", "how to", "tutorial", "guide", "basics",
                    "getting started", "first time", "new to", "learn"
                ],
                TechnicalLevel.INTERMEDIATE: [
                    "custom", "advanced", "complex", "multiple",
                    "optimize", "performance", "best practice"
                ],
                TechnicalLevel.ADVANCED: [
                    "architecture", "enterprise", "scalable", "custom code",
                    "api", "integration", "automation", "workflow"
                ],
                TechnicalLevel.EXPERT: [
                    "debug", "troubleshoot", "performance", "optimization",
                    "custom implementation", "advanced configuration"
                ]
            },
            "topics": [
                "tracking", "variables", "segments", "reports", "implementation",
                "privacy", "mobile", "api", "integration", "configuration",
                "troubleshooting", "performance", "analytics", "data collection",
                "visitor id", "cross-device", "attribution", "conversion",
                "funnel", "pathing", "cohort", "retention", "lifetime value"
            ]
        }
    
    def detect_products(self, question: str) -> List[Tuple[str, float]]:
        """
        Detect Adobe products mentioned in the question.
        
        Args:
            question: User question text
            
        Returns:
            List of tuples (product_name, confidence_score)
        """
        products = []
        question_lower = question.lower()
        
        for product, patterns in self.compiled_patterns.items():
            max_confidence = 0.0
            
            for pattern in patterns:
                matches = pattern.findall(question_lower)
                if matches:
                    # Calculate confidence based on match count and pattern specificity
                    match_count = len(matches)
                    pattern_confidence = min(0.9, 0.3 + (match_count * 0.2))
                    max_confidence = max(max_confidence, pattern_confidence)
            
            if max_confidence > 0.1:  # Minimum threshold
                products.append((product, max_confidence))
        
        # Sort by confidence score
        products.sort(key=lambda x: x[1], reverse=True)
        return products
    
    def classify_question_type(self, question: str) -> Tuple[QuestionType, float]:
        """
        Classify the type of question.
        
        Args:
            question: User question text
            
        Returns:
            Tuple of (question_type, confidence_score)
        """
        question_lower = question.lower()
        scores = {}
        
        for question_type, keywords in self.keywords["question_types"].items():
            score = 0.0
            for keyword in keywords:
                if keyword in question_lower:
                    score += 1.0
            
            # Normalize score
            if keywords:
                scores[question_type] = min(1.0, score / len(keywords))
            else:
                scores[question_type] = 0.0
        
        # Find best match
        if scores:
            best_type = max(scores, key=scores.get)
            confidence = scores[best_type]
            
            # If confidence is too low, default to general
            if confidence < 0.1:
                best_type = QuestionType.GENERAL
                confidence = 0.5
        else:
            best_type = QuestionType.GENERAL
            confidence = 0.5
        
        return best_type, confidence
    
    def assess_technical_level(self, question: str) -> Tuple[TechnicalLevel, float]:
        """
        Assess the technical level of the question.
        
        Args:
            question: User question text
            
        Returns:
            Tuple of (technical_level, confidence_score)
        """
        question_lower = question.lower()
        scores = {}
        
        for level, keywords in self.keywords["technical_levels"].items():
            score = 0.0
            for keyword in keywords:
                if keyword in question_lower:
                    score += 1.0
            
            # Normalize score
            if keywords:
                scores[level] = min(1.0, score / len(keywords))
            else:
                scores[level] = 0.0
        
        # Find best match
        if scores:
            best_level = max(scores, key=scores.get)
            confidence = scores[best_level]
            
            # If confidence is too low, default to intermediate
            if confidence < 0.1:
                best_level = TechnicalLevel.INTERMEDIATE
                confidence = 0.5
        else:
            best_level = TechnicalLevel.INTERMEDIATE
            confidence = 0.5
        
        return best_level, confidence
    
    def extract_topics(self, question: str) -> List[Tuple[str, float]]:
        """
        Extract relevant topics from the question.
        
        Args:
            question: User question text
            
        Returns:
            List of tuples (topic, confidence_score)
        """
        topics = []
        question_lower = question.lower()
        
        for topic in self.keywords["topics"]:
            if topic in question_lower:
                # Calculate confidence based on context
                confidence = 0.5
                
                # Boost confidence for exact matches
                if f" {topic} " in f" {question_lower} ":
                    confidence = 0.8
                elif topic in question_lower:
                    confidence = 0.6
                
                topics.append((topic, confidence))
        
        # Sort by confidence score
        topics.sort(key=lambda x: x[1], reverse=True)
        return topics
    
    def calculate_urgency(self, question: str, products: List[str], 
                         question_type: QuestionType) -> str:
        """
        Calculate urgency level based on question content.
        
        Args:
            question: User question text
            products: Detected products
            question_type: Classified question type
            
        Returns:
            Urgency level: "high", "medium", or "low"
        """
        urgency_indicators = {
            "high": [
                "urgent", "critical", "broken", "not working", "error",
                "production", "live", "down", "failing", "emergency"
            ],
            "medium": [
                "issue", "problem", "help", "support", "question",
                "troubleshoot", "debug", "fix"
            ]
        }
        
        question_lower = question.lower()
        
        # Check for high urgency indicators
        for indicator in urgency_indicators["high"]:
            if indicator in question_lower:
                return "high"
        
        # Check for medium urgency indicators
        for indicator in urgency_indicators["medium"]:
            if indicator in question_lower:
                return "medium"
        
        # Default to low urgency
        return "low"
    
    def calculate_confidence_score(self, product_confidence: float, 
                                 type_confidence: float, 
                                 level_confidence: float) -> float:
        """
        Calculate overall confidence score.
        
        Args:
            product_confidence: Product detection confidence
            type_confidence: Question type confidence
            level_confidence: Technical level confidence
            
        Returns:
            Overall confidence score (0.0 to 1.0)
        """
        # Weighted average
        weights = {
            "product": 0.4,
            "type": 0.3,
            "level": 0.3
        }
        
        confidence = (
            product_confidence * weights["product"] +
            type_confidence * weights["type"] +
            level_confidence * weights["level"]
        )
        
        return min(1.0, max(0.0, confidence))
    
    def tag_question(self, question: str) -> TaggingResult:
        """
        Perform comprehensive tagging of a question.
        
        Args:
            question: User question text
            
        Returns:
            TaggingResult object with all tagging information
        """
        try:
            logger.info(f"Tagging question: {question[:100]}...")
            
            # Detect products
            products_with_scores = self.detect_products(question)
            products = [product for product, _ in products_with_scores]
            product_confidence = max([score for _, score in products_with_scores], default=0.0)
            
            # Classify question type
            question_type, type_confidence = self.classify_question_type(question)
            
            # Assess technical level
            technical_level, level_confidence = self.assess_technical_level(question)
            
            # Extract topics
            topics_with_scores = self.extract_topics(question)
            topics = [topic for topic, _ in topics_with_scores]
            
            # Calculate urgency
            urgency = self.calculate_urgency(question, products, question_type)
            
            # Calculate overall confidence
            confidence_score = self.calculate_confidence_score(
                product_confidence, type_confidence, level_confidence
            )
            
            # Prepare raw analysis
            raw_analysis = {
                "products_detected": products_with_scores,
                "topics_detected": topics_with_scores,
                "question_type_confidence": type_confidence,
                "technical_level_confidence": level_confidence,
                "product_confidence": product_confidence
            }
            
            result = TaggingResult(
                products=products,
                question_type=question_type,
                technical_level=technical_level,
                topics=topics,
                confidence_score=confidence_score,
                urgency=urgency,
                raw_analysis=raw_analysis
            )
            
            logger.info(f"Tagging completed. Confidence: {confidence_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error during tagging: {e}")
            # Return default result on error
            return TaggingResult(
                products=[],
                question_type=QuestionType.GENERAL,
                technical_level=TechnicalLevel.INTERMEDIATE,
                topics=[],
                confidence_score=0.0,
                urgency="low",
                raw_analysis={"error": str(e)}
            )
    
    def should_use_bedrock_enhancement(self, result: TaggingResult) -> bool:
        """
        Determine if Bedrock enhancement should be used.
        
        Args:
            result: TaggingResult object
            
        Returns:
            True if Bedrock enhancement should be used
        """
        if not self.config.get("enable_bedrock_enhancement", True):
            return False
        
        threshold = self.config.get("bedrock_enhancement_threshold", 0.5)
        return result.confidence_score < threshold
    
    def get_tagging_summary(self, result: TaggingResult) -> str:
        """
        Get a human-readable summary of the tagging result.
        
        Args:
            result: TaggingResult object
            
        Returns:
            Formatted summary string
        """
        summary_parts = []
        
        if result.products:
            summary_parts.append(f"Products: {', '.join(result.products)}")
        
        summary_parts.append(f"Type: {result.question_type.value}")
        summary_parts.append(f"Level: {result.technical_level.value}")
        
        if result.topics:
            summary_parts.append(f"Topics: {', '.join(result.topics[:3])}")  # Top 3 topics
        
        summary_parts.append(f"Confidence: {result.confidence_score:.2f}")
        summary_parts.append(f"Urgency: {result.urgency}")
        
        return " | ".join(summary_parts)

# Example usage and testing
if __name__ == "__main__":
    # Initialize the tagger
    tagger = SmartTagger()
    
    # Test questions
    test_questions = [
        "How do I implement Adobe Analytics tracking on my website?",
        "I'm getting an error with my AppMeasurement code, can you help?",
        "What's the difference between Adobe Analytics and Customer Journey Analytics?",
        "How to configure cross-device tracking in CJA?",
        "I need help with Adobe Experience Platform data collection setup"
    ]
    
    print("Smart Tagger Test Results:")
    print("=" * 50)
    
    for question in test_questions:
        result = tagger.tag_question(question)
        summary = tagger.get_tagging_summary(result)
        print(f"Q: {question}")
        print(f"A: {summary}")
        print(f"Bedrock Enhancement: {tagger.should_use_bedrock_enhancement(result)}")
        print("-" * 50)
