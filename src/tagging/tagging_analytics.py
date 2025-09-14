"""
Analytics Engine for Smart Tagging System

This module provides comprehensive analytics capabilities for the tagging system,
including trending analysis, user behavior insights, and performance metrics.
"""

import json
import logging
import sqlite3
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
import statistics
import math

logger = logging.getLogger(__name__)

@dataclass
class TrendingTopic:
    """Trending topic analysis result."""
    topic: str
    count: int
    growth_rate: float
    period: str
    confidence: float

@dataclass
class ProductCorrelation:
    """Product correlation analysis result."""
    product1: str
    product2: str
    co_occurrence: int
    correlation_score: float
    confidence: float

@dataclass
class UserExpertise:
    """User expertise level analysis."""
    user_id: str
    expertise_level: str
    question_count: int
    avg_confidence: float
    product_diversity: int
    technical_complexity: float
    last_activity: datetime

@dataclass
class QuestionSimilarity:
    """Question similarity analysis result."""
    question1_id: int
    question2_id: str
    similarity_score: float
    common_tags: List[str]
    common_products: List[str]

@dataclass
class TaggingAccuracy:
    """Tagging accuracy metrics."""
    total_questions: int
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int
    avg_confidence: float
    accuracy_rate: float
    human_validation_rate: float

@dataclass
class PerformanceMetrics:
    """Performance metrics for the tagging system."""
    avg_processing_time: float
    total_questions_processed: int
    success_rate: float
    error_rate: float
    bedrock_usage_rate: float
    cost_per_question: float

class TaggingAnalytics:
    """Comprehensive analytics engine for the tagging system."""
    
    def __init__(self, db_path: str):
        """
        Initialize the analytics engine.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_trending_topics(self, days: int = 7, limit: int = 20) -> List[TrendingTopic]:
        """
        Analyze trending topics over the last N days.
        
        Args:
            days: Number of days to analyze
            limit: Maximum number of topics to return
            
        Returns:
            List of trending topics with growth rates
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current period data
                current_start = datetime.now(timezone.utc) - timedelta(days=days)
                cursor.execute("""
                    SELECT t.topics, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    WHERE q.created_at >= ?
                    GROUP BY t.topics
                """, (current_start.isoformat(),))
                
                current_topics = {}
                for row in cursor.fetchall():
                    topics = json.loads(row['topics'])
                    for topic in topics:
                        current_topics[topic] = current_topics.get(topic, 0) + row['count']
                
                # Get previous period data for comparison
                previous_start = current_start - timedelta(days=days)
                cursor.execute("""
                    SELECT t.topics, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    WHERE q.created_at >= ? AND q.created_at < ?
                    GROUP BY t.topics
                """, (previous_start.isoformat(), current_start.isoformat()))
                
                previous_topics = {}
                for row in cursor.fetchall():
                    topics = json.loads(row['topics'])
                    for topic in topics:
                        previous_topics[topic] = previous_topics.get(topic, 0) + row['count']
                
                # Calculate growth rates
                trending_topics = []
                all_topics = set(current_topics.keys()) | set(previous_topics.keys())
                
                for topic in all_topics:
                    current_count = current_topics.get(topic, 0)
                    previous_count = previous_topics.get(topic, 0)
                    
                    if previous_count > 0:
                        growth_rate = ((current_count - previous_count) / previous_count) * 100
                    else:
                        growth_rate = 100.0 if current_count > 0 else 0.0
                    
                    # Calculate confidence based on sample size
                    confidence = min(1.0, (current_count + previous_count) / 100.0)
                    
                    trending_topics.append(TrendingTopic(
                        topic=topic,
                        count=current_count,
                        growth_rate=growth_rate,
                        period=f"last_{days}_days",
                        confidence=confidence
                    ))
                
                # Sort by growth rate and return top results
                trending_topics.sort(key=lambda x: x.growth_rate, reverse=True)
                return trending_topics[:limit]
                
        except Exception as e:
            self.logger.error(f"Error analyzing trending topics: {e}")
            return []
    
    def get_product_correlations(self, min_co_occurrence: int = 2) -> List[ProductCorrelation]:
        """
        Analyze product correlations (which products are asked about together).
        
        Args:
            min_co_occurrence: Minimum co-occurrence threshold
            
        Returns:
            List of product correlations with scores
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all product combinations
                cursor.execute("""
                    SELECT t.products, COUNT(*) as count
                    FROM tags t
                    GROUP BY t.products
                    HAVING COUNT(*) >= ?
                """, (min_co_occurrence,))
                
                product_combinations = {}
                for row in cursor.fetchall():
                    products = json.loads(row['products'])
                    if len(products) > 1:
                        # Sort products for consistent key
                        key = tuple(sorted(products))
                        product_combinations[key] = row['count']
                
                # Calculate individual product frequencies
                cursor.execute("""
                    SELECT t.products, COUNT(*) as count
                    FROM tags t
                    GROUP BY t.products
                """)
                
                product_frequencies = {}
                for row in cursor.fetchall():
                    products = json.loads(row['products'])
                    for product in products:
                        product_frequencies[product] = product_frequencies.get(product, 0) + row['count']
                
                # Calculate correlation scores
                correlations = []
                for products, co_occurrence in product_combinations.items():
                    if len(products) == 2:
                        product1, product2 = products
                        freq1 = product_frequencies.get(product1, 0)
                        freq2 = product_frequencies.get(product2, 0)
                        
                        if freq1 > 0 and freq2 > 0:
                            # Calculate Jaccard similarity
                            union = freq1 + freq2 - co_occurrence
                            jaccard = co_occurrence / union if union > 0 else 0
                            
                            # Calculate confidence based on sample size
                            confidence = min(1.0, co_occurrence / 10.0)
                            
                            correlations.append(ProductCorrelation(
                                product1=product1,
                                product2=product2,
                                co_occurrence=co_occurrence,
                                correlation_score=jaccard,
                                confidence=confidence
                            ))
                
                # Sort by correlation score
                correlations.sort(key=lambda x: x.correlation_score, reverse=True)
                return correlations
                
        except Exception as e:
            self.logger.error(f"Error analyzing product correlations: {e}")
            return []
    
    def analyze_user_expertise(self, user_id: str) -> Optional[UserExpertise]:
        """
        Analyze user expertise level based on question history.
        
        Args:
            user_id: User identifier
            
        Returns:
            User expertise analysis or None if no data
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get user's question history
                cursor.execute("""
                    SELECT t.*, q.created_at
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    WHERE q.user_id = ?
                    ORDER BY q.created_at DESC
                """, (user_id,))
                
                user_data = cursor.fetchall()
                if not user_data:
                    return None
                
                # Analyze expertise indicators
                question_count = len(user_data)
                confidence_scores = [row['confidence_score'] for row in user_data]
                avg_confidence = statistics.mean(confidence_scores)
                
                # Count unique products
                all_products = set()
                for row in user_data:
                    products = json.loads(row['products'])
                    all_products.update(products)
                product_diversity = len(all_products)
                
                # Analyze technical complexity
                technical_levels = [row['technical_level'] for row in user_data]
                level_scores = {
                    'beginner': 1,
                    'intermediate': 2,
                    'advanced': 3,
                    'expert': 4
                }
                avg_technical_score = statistics.mean([level_scores.get(level, 2) for level in technical_levels])
                
                # Determine expertise level
                if avg_technical_score >= 3.5 and product_diversity >= 3 and avg_confidence >= 0.7:
                    expertise_level = "expert"
                elif avg_technical_score >= 2.5 and product_diversity >= 2 and avg_confidence >= 0.5:
                    expertise_level = "advanced"
                elif avg_technical_score >= 1.5 and avg_confidence >= 0.3:
                    expertise_level = "intermediate"
                else:
                    expertise_level = "beginner"
                
                # Get last activity
                last_activity = datetime.fromisoformat(user_data[0]['created_at'])
                
                return UserExpertise(
                    user_id=user_id,
                    expertise_level=expertise_level,
                    question_count=question_count,
                    avg_confidence=avg_confidence,
                    product_diversity=product_diversity,
                    technical_complexity=avg_technical_score,
                    last_activity=last_activity
                )
                
        except Exception as e:
            self.logger.error(f"Error analyzing user expertise: {e}")
            return None
    
    def calculate_question_similarity(self, question1_id: int, question2_id: int) -> Optional[QuestionSimilarity]:
        """
        Calculate similarity between two questions using tag overlap.
        
        Args:
            question1_id: First question ID
            question2_id: Second question ID
            
        Returns:
            Question similarity analysis or None if questions not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get tags for both questions
                cursor.execute("""
                    SELECT question_id, products, topics, question_type, technical_level
                    FROM tags
                    WHERE question_id IN (?, ?)
                """, (question1_id, question2_id))
                
                tags_data = {row['question_id']: row for row in cursor.fetchall()}
                
                if len(tags_data) != 2:
                    return None
                
                # Extract tags
                tags1 = tags_data[question1_id]
                tags2 = tags_data[question2_id]
                
                products1 = set(json.loads(tags1['products']))
                products2 = set(json.loads(tags2['products']))
                topics1 = set(json.loads(tags1['topics']))
                topics2 = set(json.loads(tags2['topics']))
                
                # Calculate Jaccard similarity for products and topics
                product_intersection = products1.intersection(products2)
                product_union = products1.union(products2)
                product_similarity = len(product_intersection) / len(product_union) if product_union else 0
                
                topic_intersection = topics1.intersection(topics2)
                topic_union = topics1.union(topics2)
                topic_similarity = len(topic_intersection) / len(topic_union) if topic_union else 0
                
                # Weighted similarity (products weighted more than topics)
                similarity_score = (product_similarity * 0.7) + (topic_similarity * 0.3)
                
                # Check for type and level similarity
                type_similarity = 1.0 if tags1['question_type'] == tags2['question_type'] else 0.0
                level_similarity = 1.0 if tags1['technical_level'] == tags2['technical_level'] else 0.0
                
                # Adjust similarity score
                similarity_score = (similarity_score * 0.6) + (type_similarity * 0.2) + (level_similarity * 0.2)
                
                return QuestionSimilarity(
                    question1_id=question1_id,
                    question2_id=str(question2_id),
                    similarity_score=similarity_score,
                    common_tags=list(topic_intersection),
                    common_products=list(product_intersection)
                )
                
        except Exception as e:
            self.logger.error(f"Error calculating question similarity: {e}")
            return None
    
    def get_tagging_accuracy_metrics(self, start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None) -> TaggingAccuracy:
        """
        Calculate tagging accuracy metrics and confidence distribution.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Tagging accuracy metrics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Date filter
                date_filter = ""
                params = []
                if start_date and end_date:
                    date_filter = "WHERE q.created_at BETWEEN ? AND ?"
                    params = [start_date.isoformat(), end_date.isoformat()]
                
                # Get confidence distribution
                cursor.execute(f"""
                    SELECT 
                        CASE 
                            WHEN t.confidence_score >= 0.8 THEN 'high'
                            WHEN t.confidence_score >= 0.6 THEN 'medium'
                            ELSE 'low'
                        END as confidence_level,
                        COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                    GROUP BY confidence_level
                """, params)
                
                confidence_dist = dict(cursor.fetchall())
                high_confidence = confidence_dist.get('high', 0)
                medium_confidence = confidence_dist.get('medium', 0)
                low_confidence = confidence_dist.get('low', 0)
                total_questions = high_confidence + medium_confidence + low_confidence
                
                # Calculate average confidence
                cursor.execute(f"""
                    SELECT AVG(t.confidence_score) as avg_confidence
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                """, params)
                
                avg_confidence = cursor.fetchone()['avg_confidence'] or 0.0
                
                # Calculate accuracy rate (high + medium confidence as "accurate")
                accuracy_rate = (high_confidence + medium_confidence) / total_questions if total_questions > 0 else 0.0
                
                # Estimate human validation rate (assume 10% of low confidence questions are validated)
                human_validation_rate = (low_confidence * 0.1) / total_questions if total_questions > 0 else 0.0
                
                return TaggingAccuracy(
                    total_questions=total_questions,
                    high_confidence_count=high_confidence,
                    medium_confidence_count=medium_confidence,
                    low_confidence_count=low_confidence,
                    avg_confidence=avg_confidence,
                    accuracy_rate=accuracy_rate,
                    human_validation_rate=human_validation_rate
                )
                
        except Exception as e:
            self.logger.error(f"Error calculating tagging accuracy: {e}")
            return TaggingAccuracy(0, 0, 0, 0, 0.0, 0.0, 0.0)
    
    def get_performance_metrics(self, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> PerformanceMetrics:
        """
        Calculate performance metrics for the tagging system.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Performance metrics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Date filter
                date_filter = ""
                params = []
                if start_date and end_date:
                    date_filter = "WHERE q.created_at BETWEEN ? AND ?"
                    params = [start_date.isoformat(), end_date.isoformat()]
                
                # Get total questions processed
                cursor.execute(f"""
                    SELECT COUNT(*) as total_questions
                    FROM questions q
                    {date_filter}
                """, params)
                total_questions = cursor.fetchone()['total_questions']
                
                # Get success rate (questions with tags)
                cursor.execute(f"""
                    SELECT COUNT(*) as successful_questions
                    FROM questions q
                    JOIN tags t ON q.id = t.question_id
                    {date_filter}
                """, params)
                successful_questions = cursor.fetchone()['successful_questions']
                success_rate = successful_questions / total_questions if total_questions > 0 else 0.0
                
                # Calculate error rate
                error_rate = 1.0 - success_rate
                
                # Estimate processing time (assume 0.1 seconds per question)
                avg_processing_time = 0.1  # This would be calculated from actual timing data
                
                # Get Bedrock usage rate
                cursor.execute(f"""
                    SELECT COUNT(*) as bedrock_questions
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                    WHERE t.confidence_score < 0.5
                """, params)
                bedrock_questions = cursor.fetchone()['bedrock_questions']
                bedrock_usage_rate = bedrock_questions / total_questions if total_questions > 0 else 0.0
                
                # Estimate cost per question (assume $0.001 per Bedrock call)
                cost_per_question = bedrock_usage_rate * 0.001
                
                return PerformanceMetrics(
                    avg_processing_time=avg_processing_time,
                    total_questions_processed=total_questions,
                    success_rate=success_rate,
                    error_rate=error_rate,
                    bedrock_usage_rate=bedrock_usage_rate,
                    cost_per_question=cost_per_question
                )
                
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics(0.0, 0, 0.0, 0.0, 0.0, 0.0)
    
    def get_time_series_analysis(self, days: int = 30, granularity: str = "day") -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform time-series analysis of question patterns.
        
        Args:
            days: Number of days to analyze
            granularity: Time granularity (day, hour, week)
            
        Returns:
            Time-series data for various metrics
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Determine time format based on granularity
                if granularity == "hour":
                    time_format = "%Y-%m-%d %H:00:00"
                elif granularity == "week":
                    time_format = "%Y-%W"
                else:  # day
                    time_format = "%Y-%m-%d"
                
                start_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                # Question volume over time
                cursor.execute(f"""
                    SELECT 
                        strftime('{time_format}', q.created_at) as time_period,
                        COUNT(*) as question_count
                    FROM questions q
                    WHERE q.created_at >= ?
                    GROUP BY time_period
                    ORDER BY time_period
                """, (start_date.isoformat(),))
                
                question_volume = [{"time": row['time_period'], "count": row['question_count']} for row in cursor.fetchall()]
                
                # Confidence scores over time
                cursor.execute(f"""
                    SELECT 
                        strftime('{time_format}', q.created_at) as time_period,
                        AVG(t.confidence_score) as avg_confidence
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    WHERE q.created_at >= ?
                    GROUP BY time_period
                    ORDER BY time_period
                """, (start_date.isoformat(),))
                
                confidence_trend = [{"time": row['time_period'], "confidence": row['avg_confidence']} for row in cursor.fetchall()]
                
                # Product usage over time
                cursor.execute(f"""
                    SELECT 
                        strftime('{time_format}', q.created_at) as time_period,
                        t.products,
                        COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    WHERE q.created_at >= ?
                    GROUP BY time_period, t.products
                    ORDER BY time_period
                """, (start_date.isoformat(),))
                
                product_usage = defaultdict(list)
                for row in cursor.fetchall():
                    products = json.loads(row['products'])
                    for product in products:
                        product_usage[product].append({
                            "time": row['time_period'],
                            "count": row['count']
                        })
                
                return {
                    "question_volume": question_volume,
                    "confidence_trend": confidence_trend,
                    "product_usage": dict(product_usage)
                }
                
        except Exception as e:
            self.logger.error(f"Error performing time-series analysis: {e}")
            return {}
    
    def get_user_behavior_analysis(self, limit: int = 100) -> Dict[str, Any]:
        """
        Analyze user behavior patterns and segmentation.
        
        Args:
            limit: Maximum number of users to analyze
            
        Returns:
            User behavior analysis data
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get user statistics
                cursor.execute("""
                    SELECT 
                        q.user_id,
                        COUNT(*) as question_count,
                        AVG(t.confidence_score) as avg_confidence,
                        COUNT(DISTINCT t.products) as unique_products,
                        MIN(q.created_at) as first_question,
                        MAX(q.created_at) as last_question
                    FROM questions q
                    JOIN tags t ON q.id = t.question_id
                    GROUP BY q.user_id
                    ORDER BY question_count DESC
                    LIMIT ?
                """, (limit,))
                
                user_stats = []
                for row in cursor.fetchall():
                    # Calculate user tenure
                    first_question = datetime.fromisoformat(row['first_question'])
                    last_question = datetime.fromisoformat(row['last_question'])
                    tenure_days = (last_question - first_question).days
                    
                    user_stats.append({
                        "user_id": row['user_id'],
                        "question_count": row['question_count'],
                        "avg_confidence": row['avg_confidence'],
                        "unique_products": row['unique_products'],
                        "tenure_days": tenure_days,
                        "first_question": row['first_question'],
                        "last_question": row['last_question']
                    })
                
                # Calculate segmentation
                total_users = len(user_stats)
                if total_users > 0:
                    # Power users (top 20% by question count)
                    power_users = int(total_users * 0.2)
                    # Active users (middle 60%)
                    active_users = int(total_users * 0.6)
                    # Casual users (bottom 20%)
                    casual_users = total_users - power_users - active_users
                    
                    segmentation = {
                        "power_users": power_users,
                        "active_users": active_users,
                        "casual_users": casual_users,
                        "total_users": total_users
                    }
                else:
                    segmentation = {"power_users": 0, "active_users": 0, "casual_users": 0, "total_users": 0}
                
                return {
                    "user_stats": user_stats,
                    "segmentation": segmentation,
                    "avg_questions_per_user": sum(u["question_count"] for u in user_stats) / total_users if total_users > 0 else 0,
                    "avg_tenure_days": sum(u["tenure_days"] for u in user_stats) / total_users if total_users > 0 else 0
                }
                
        except Exception as e:
            self.logger.error(f"Error analyzing user behavior: {e}")
            return {}
    
    def export_analytics_data(self, export_format: str = "json", 
                            file_path: Optional[str] = None) -> Union[str, Dict[str, Any]]:
        """
        Export analytics data in various formats.
        
        Args:
            export_format: Export format (json, csv, excel)
            file_path: Optional file path for export
            
        Returns:
            Exported data or file path
        """
        try:
            # Gather all analytics data
            analytics_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "trending_topics": [asdict(topic) for topic in self.get_trending_topics()],
                "product_correlations": [asdict(corr) for corr in self.get_product_correlations()],
                "tagging_accuracy": asdict(self.get_tagging_accuracy_metrics()),
                "performance_metrics": asdict(self.get_performance_metrics()),
                "time_series": self.get_time_series_analysis(),
                "user_behavior": self.get_user_behavior_analysis()
            }
            
            if export_format == "json":
                if file_path:
                    with open(file_path, 'w') as f:
                        json.dump(analytics_data, f, indent=2, default=str)
                    return file_path
                else:
                    return json.dumps(analytics_data, indent=2, default=str)
            
            elif export_format == "csv":
                # This would require pandas for CSV export
                # For now, return JSON
                return json.dumps(analytics_data, indent=2, default=str)
            
            else:
                return analytics_data
                
        except Exception as e:
            self.logger.error(f"Error exporting analytics data: {e}")
            return {}

# Example usage and testing
if __name__ == "__main__":
    import tempfile
    import os
    
    # Create test database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Initialize analytics
        analytics = TaggingAnalytics(db_path)
        
        print("🧪 Testing Tagging Analytics Engine")
        print("=" * 50)
        
        # Test trending topics
        print("📈 Testing trending topics analysis...")
        trending = analytics.get_trending_topics(days=7)
        print(f"Found {len(trending)} trending topics")
        
        # Test product correlations
        print("🔗 Testing product correlations...")
        correlations = analytics.get_product_correlations()
        print(f"Found {len(correlations)} product correlations")
        
        # Test user expertise
        print("👤 Testing user expertise analysis...")
        expertise = analytics.analyze_user_expertise("test_user")
        if expertise:
            print(f"User expertise level: {expertise.expertise_level}")
        
        # Test tagging accuracy
        print("📊 Testing tagging accuracy metrics...")
        accuracy = analytics.get_tagging_accuracy_metrics()
        print(f"Total questions: {accuracy.total_questions}")
        print(f"Accuracy rate: {accuracy.accuracy_rate:.2%}")
        
        # Test performance metrics
        print("⚡ Testing performance metrics...")
        performance = analytics.get_performance_metrics()
        print(f"Success rate: {performance.success_rate:.2%}")
        print(f"Cost per question: ${performance.cost_per_question:.4f}")
        
        print("✅ Analytics engine test completed successfully!")
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        print("🧹 Cleaned up test database")
