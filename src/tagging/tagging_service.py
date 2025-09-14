"""
Integrated Tagging Service

This module provides a high-level service that combines the smart tagger
with the database layer for complete tagging functionality.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import uuid

from .smart_tagger import SmartTagger, TaggingResult
from .tagging_database import TaggingDatabase, QuestionRecord, TagRecord

logger = logging.getLogger(__name__)

class TaggingService:
    """Integrated service for question tagging and storage."""
    
    def __init__(self, db_path: str = "tagging.db", config: Optional[Dict] = None):
        """
        Initialize the tagging service.
        
        Args:
            db_path: Path to SQLite database file
            config: Optional configuration for smart tagger
        """
        self.tagger = SmartTagger(config)
        self.database = TaggingDatabase(db_path)
        self.logger = logging.getLogger(__name__)
    
    def process_and_store_question(self, question: str, user_id: str = "anonymous",
                                 session_id: Optional[str] = None, context: str = "") -> Dict[str, Any]:
        """
        Process a question with smart tagging and store in database.
        
        Args:
            question: User question text
            user_id: User identifier
            session_id: Session identifier (generated if None)
            context: Additional context
            
        Returns:
            Dictionary with processing results and metadata
        """
        try:
            # Generate session ID if not provided
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            # Tag the question
            tagging_result = self.tagger.tag_question(question)
            
            # Create tag record
            tag_record = TagRecord(
                products=tagging_result.products,
                question_type=tagging_result.question_type.value,
                technical_level=tagging_result.technical_level.value,
                topics=tagging_result.topics,
                urgency=tagging_result.urgency,
                confidence_score=tagging_result.confidence_score,
                raw_analysis=tagging_result.raw_analysis
            )
            
            # Store in database
            question_id, tag_id = self.database.store_question_with_tags(
                question=question,
                tags=tag_record,
                user_id=user_id,
                session_id=session_id,
                context=context
            )
            
            # Prepare result
            result = {
                "question_id": question_id,
                "tag_id": tag_id,
                "session_id": session_id,
                "tagging_result": {
                    "products": tagging_result.products,
                    "question_type": tagging_result.question_type.value,
                    "technical_level": tagging_result.technical_level.value,
                    "topics": tagging_result.topics,
                    "urgency": tagging_result.urgency,
                    "confidence_score": tagging_result.confidence_score,
                    "bedrock_enhancement_needed": self.tagger.should_use_bedrock_enhancement(tagging_result)
                },
                "summary": self.tagger.get_tagging_summary(tagging_result),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(f"Processed question {question_id}: {result['summary']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing question: {e}")
            return {
                "error": str(e),
                "question_id": None,
                "tag_id": None,
                "session_id": session_id,
                "tagging_result": None,
                "summary": "Error occurred during processing",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def get_question_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get question history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of questions to return
            
        Returns:
            List of question records with tags
        """
        try:
            questions = self.database.get_questions_by_user(user_id, limit)
            results = []
            
            for question in questions:
                tags = self.database.get_tags_by_question_id(question.id)
                if tags:
                    results.append({
                        "question_id": question.id,
                        "question": question.question,
                        "user_id": question.user_id,
                        "session_id": question.session_id,
                        "timestamp": question.timestamp.isoformat(),
                        "context": question.context,
                        "products": tags.products,
                        "question_type": tags.question_type,
                        "technical_level": tags.technical_level,
                        "topics": tags.topics,
                        "urgency": tags.urgency,
                        "confidence_score": tags.confidence_score
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting question history: {e}")
            return []
    
    def get_session_questions(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all questions for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of question records with tags
        """
        try:
            questions = self.database.get_questions_by_session(session_id)
            results = []
            
            for question in questions:
                tags = self.database.get_tags_by_question_id(question.id)
                if tags:
                    results.append({
                        "question_id": question.id,
                        "question": question.question,
                        "user_id": question.user_id,
                        "session_id": question.session_id,
                        "timestamp": question.timestamp.isoformat(),
                        "context": question.context,
                        "products": tags.products,
                        "question_type": tags.question_type,
                        "technical_level": tags.technical_level,
                        "topics": tags.topics,
                        "urgency": tags.urgency,
                        "confidence_score": tags.confidence_score
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error getting session questions: {e}")
            return []
    
    def search_questions(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search questions by text content.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching questions with tags
        """
        try:
            return self.database.search_questions(query, limit)
        except Exception as e:
            self.logger.error(f"Error searching questions: {e}")
            return []
    
    def get_analytics_dashboard_data(self, start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get analytics data for dashboard.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            
        Returns:
            Analytics data dictionary
        """
        try:
            analytics = self.database.get_analytics_summary(start_date, end_date)
            
            # Add additional computed metrics
            total_questions = analytics.get('total_questions', 0)
            if total_questions > 0:
                analytics['confidence_distribution'] = self._get_confidence_distribution()
                analytics['product_usage_trends'] = self._get_product_usage_trends()
                analytics['question_type_trends'] = self._get_question_type_trends()
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting analytics data: {e}")
            return {}
    
    def _get_confidence_distribution(self) -> Dict[str, int]:
        """Get confidence score distribution."""
        try:
            with self.database._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN confidence_score >= 0.8 THEN 'high'
                            WHEN confidence_score >= 0.6 THEN 'medium'
                            ELSE 'low'
                        END as confidence_level,
                        COUNT(*) as count
                    FROM tags
                    GROUP BY confidence_level
                """)
                return dict(cursor.fetchall())
        except Exception as e:
            self.logger.error(f"Error getting confidence distribution: {e}")
            return {}
    
    def _get_product_usage_trends(self) -> List[Dict[str, Any]]:
        """Get product usage trends over time."""
        try:
            with self.database._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        products,
                        COUNT(*) as count
                    FROM tags
                    WHERE created_at >= date('now', '-30 days')
                    GROUP BY DATE(created_at), products
                    ORDER BY date DESC
                """)
                
                trends = []
                for row in cursor.fetchall():
                    products = json.loads(row['products'])
                    for product in products:
                        trends.append({
                            'date': row['date'],
                            'product': product,
                            'count': row['count']
                        })
                
                return trends
        except Exception as e:
            self.logger.error(f"Error getting product usage trends: {e}")
            return []
    
    def _get_question_type_trends(self) -> List[Dict[str, Any]]:
        """Get question type trends over time."""
        try:
            with self.database._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        question_type,
                        COUNT(*) as count
                    FROM tags
                    WHERE created_at >= date('now', '-30 days')
                    GROUP BY DATE(created_at), question_type
                    ORDER BY date DESC
                """)
                
                trends = []
                for row in cursor.fetchall():
                    trends.append({
                        'date': row['date'],
                        'question_type': row['question_type'],
                        'count': row['count']
                    })
                
                return trends
        except Exception as e:
            self.logger.error(f"Error getting question type trends: {e}")
            return []
    
    def update_question_tags(self, question_id: int, new_tags: Dict[str, Any]) -> bool:
        """
        Update tags for an existing question.
        
        Args:
            question_id: Question ID to update
            new_tags: New tagging data
            
        Returns:
            True if update was successful
        """
        try:
            # Get existing tags
            existing_tags = self.database.get_tags_by_question_id(question_id)
            if not existing_tags:
                return False
            
            # Update with new data
            if 'products' in new_tags:
                existing_tags.products = new_tags['products']
            if 'question_type' in new_tags:
                existing_tags.question_type = new_tags['question_type']
            if 'technical_level' in new_tags:
                existing_tags.technical_level = new_tags['technical_level']
            if 'topics' in new_tags:
                existing_tags.topics = new_tags['topics']
            if 'urgency' in new_tags:
                existing_tags.urgency = new_tags['urgency']
            if 'confidence_score' in new_tags:
                existing_tags.confidence_score = new_tags['confidence_score']
            if 'raw_analysis' in new_tags:
                existing_tags.raw_analysis = new_tags['raw_analysis']
            
            return self.database.update_tags(question_id, existing_tags)
            
        except Exception as e:
            self.logger.error(f"Error updating question tags: {e}")
            return False
    
    def delete_question(self, question_id: int) -> bool:
        """
        Delete a question and its tags.
        
        Args:
            question_id: Question ID to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            return self.database.delete_question(question_id)
        except Exception as e:
            self.logger.error(f"Error deleting question: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            return self.database.get_database_stats()
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
    
    def backup_database(self, backup_path: str) -> bool:
        """Create database backup."""
        try:
            return self.database.backup_database(backup_path)
        except Exception as e:
            self.logger.error(f"Error backing up database: {e}")
            return False

# Example usage
if __name__ == "__main__":
    import json
    
    # Initialize service
    service = TaggingService("test_tagging_service.db")
    
    # Test questions
    test_questions = [
        "How do I implement Adobe Analytics tracking?",
        "I'm getting an error with my AppMeasurement code",
        "What's the difference between Adobe Analytics and CJA?"
    ]
    
    print("Testing Tagging Service")
    print("=" * 40)
    
    # Process questions
    for i, question in enumerate(test_questions):
        result = service.process_and_store_question(
            question=question,
            user_id=f"test_user_{i}",
            session_id="test_session"
        )
        
        print(f"Question {i+1}: {question}")
        print(f"Result: {result['summary']}")
        print(f"Products: {result['tagging_result']['products']}")
        print(f"Type: {result['tagging_result']['question_type']}")
        print(f"Confidence: {result['tagging_result']['confidence_score']:.2f}")
        print("-" * 40)
    
    # Get analytics
    analytics = service.get_analytics_dashboard_data()
    print(f"Analytics: {json.dumps(analytics, indent=2)}")
    
    # Clean up
    import os
    if os.path.exists("test_tagging_service.db"):
        os.remove("test_tagging_service.db")
    print("Test completed")
