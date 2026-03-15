#!/usr/bin/env python3
"""
Test script for the Tagging Analytics Engine
"""

import sys
import os
import tempfile
import json
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.tagging.tagging_analytics import TaggingAnalytics
from src.tagging.simple_visualization import SimpleTaggingVisualization
from src.tagging.tagging_database import TaggingDatabase
from src.tagging.smart_tagger import SmartTagger

def create_test_data(db_path: str, num_questions: int = 50):
    """Create test data for analytics testing."""
    db = TaggingDatabase(db_path)
    tagger = SmartTagger()
    
    # Sample questions with different characteristics
    test_questions = [
        "How do I implement Adobe Analytics tracking on my website?",
        "I'm getting an error with my AppMeasurement code, can you help?",
        "What's the difference between Adobe Analytics and Customer Journey Analytics?",
        "How to configure cross-device tracking in CJA?",
        "I need help with Adobe Experience Platform data collection setup",
        "How do I create custom segments in Adobe Analytics?",
        "My Adobe Launch rules are not firing correctly",
        "What are the best practices for GDPR compliance in Adobe Analytics?",
        "How to integrate Adobe Analytics with mobile apps?",
        "Can you help me with Adobe Analytics API authentication?",
        "How do I set up Adobe Analytics for e-commerce tracking?",
        "I'm having issues with Adobe Analytics data collection",
        "What's the difference between Adobe Analytics and Google Analytics?",
        "How to implement Adobe Analytics on a React application?",
        "I need help with Adobe Analytics custom variables",
        "How do I configure Adobe Analytics for cross-domain tracking?",
        "What are the Adobe Analytics implementation best practices?",
        "How to troubleshoot Adobe Analytics data discrepancies?",
        "I need help with Adobe Analytics report configuration",
        "How do I integrate Adobe Analytics with Adobe Experience Platform?"
    ]
    
    # Create multiple questions by repeating and varying
    all_questions = []
    for i in range(num_questions):
        base_question = test_questions[i % len(test_questions)]
        # Add some variation
        if i > len(test_questions):
            base_question = f"{base_question} (Question {i+1})"
        
        all_questions.append({
            "question": base_question,
            "user_id": f"user_{i % 10}",  # 10 different users
            "session_id": f"session_{i % 5}",  # 5 different sessions
            "context": f"Test context {i}"
        })
    
    # Store questions with tags
    for i, question_data in enumerate(all_questions):
        # Tag the question
        tagging_result = tagger.tag_question(question_data["question"])
        
        # Create tag record
        from src.tagging.tagging_database import TagRecord
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
        db.store_question_with_tags(
            question=question_data["question"],
            tags=tag_record,
            user_id=question_data["user_id"],
            session_id=question_data["session_id"],
            context=question_data["context"]
        )
    
    print(f"✅ Created {num_questions} test questions with tags")

def test_analytics_engine():
    """Test the analytics engine functionality."""
    
    print("🧪 Testing Tagging Analytics Engine")
    print("=" * 60)
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Create test data
        create_test_data(db_path, 50)
        
        # Initialize analytics
        analytics = TaggingAnalytics(db_path)
        
        # Test 1: Trending topics analysis
        print("\n📈 Test 1: Trending Topics Analysis")
        trending = analytics.get_trending_topics(days=7, limit=10)
        print(f"✅ Found {len(trending)} trending topics")
        for topic in trending[:5]:
            print(f"   - {topic.topic}: {topic.count} questions (+{topic.growth_rate:.1f}%)")
        
        # Test 2: Product correlations
        print("\n🔗 Test 2: Product Correlations")
        correlations = analytics.get_product_correlations(min_co_occurrence=2)
        print(f"✅ Found {len(correlations)} product correlations")
        for corr in correlations[:5]:
            print(f"   - {corr.product1} ↔ {corr.product2}: {corr.correlation_score:.3f}")
        
        # Test 3: User expertise analysis
        print("\n👤 Test 3: User Expertise Analysis")
        for user_id in ["user_0", "user_1", "user_2"]:
            expertise = analytics.analyze_user_expertise(user_id)
            if expertise:
                print(f"   - {user_id}: {expertise.expertise_level} (confidence: {expertise.avg_confidence:.3f})")
        
        # Test 4: Question similarity
        print("\n🔍 Test 4: Question Similarity")
        similarity = analytics.calculate_question_similarity(1, 2)
        if similarity:
            print(f"   - Similarity between Q1 and Q2: {similarity.similarity_score:.3f}")
            print(f"   - Common products: {similarity.common_products}")
            print(f"   - Common topics: {similarity.common_tags}")
        
        # Test 5: Tagging accuracy metrics
        print("\n📊 Test 5: Tagging Accuracy Metrics")
        accuracy = analytics.get_tagging_accuracy_metrics()
        print(f"   - Total questions: {accuracy.total_questions}")
        print(f"   - High confidence: {accuracy.high_confidence_count}")
        print(f"   - Medium confidence: {accuracy.medium_confidence_count}")
        print(f"   - Low confidence: {accuracy.low_confidence_count}")
        print(f"   - Average confidence: {accuracy.avg_confidence:.3f}")
        print(f"   - Accuracy rate: {accuracy.accuracy_rate:.1%}")
        
        # Test 6: Performance metrics
        print("\n⚡ Test 6: Performance Metrics")
        performance = analytics.get_performance_metrics()
        print(f"   - Total questions processed: {performance.total_questions_processed}")
        print(f"   - Success rate: {performance.success_rate:.1%}")
        print(f"   - Error rate: {performance.error_rate:.1%}")
        print(f"   - Bedrock usage rate: {performance.bedrock_usage_rate:.1%}")
        print(f"   - Cost per question: ${performance.cost_per_question:.4f}")
        
        # Test 7: Time series analysis
        print("\n📅 Test 7: Time Series Analysis")
        time_series = analytics.get_time_series_analysis(days=30, granularity="day")
        question_volume = time_series.get('question_volume', [])
        print(f"   - Time series data points: {len(question_volume)}")
        if question_volume:
            print(f"   - Latest period: {question_volume[-1]['time']} ({question_volume[-1]['count']} questions)")
        
        # Test 8: User behavior analysis
        print("\n👥 Test 8: User Behavior Analysis")
        user_behavior = analytics.get_user_behavior_analysis(limit=20)
        segmentation = user_behavior.get('segmentation', {})
        print(f"   - Total users: {segmentation.get('total_users', 0)}")
        print(f"   - Power users: {segmentation.get('power_users', 0)}")
        print(f"   - Active users: {segmentation.get('active_users', 0)}")
        print(f"   - Casual users: {segmentation.get('casual_users', 0)}")
        print(f"   - Avg questions per user: {user_behavior.get('avg_questions_per_user', 0):.1f}")
        
        # Test 9: Export functionality
        print("\n💾 Test 9: Export Functionality")
        export_data = analytics.export_analytics_data(export_format="json")
        if isinstance(export_data, str):
            data = json.loads(export_data)
            print(f"   - Exported data size: {len(export_data)} characters")
            print(f"   - Contains trending topics: {'trending_topics' in data}")
            print(f"   - Contains performance metrics: {'performance_metrics' in data}")
        
        print("\n🎉 All analytics tests completed successfully!")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
        print("🧹 Cleaned up test database")

def test_visualization_helpers():
    """Test the visualization helpers."""
    
    print("\n🎨 Testing Visualization Helpers")
    print("=" * 60)
    
    try:
        viz = SimpleTaggingVisualization()
        
        # Test data
        trending_data = [
            {"topic": "adobe_analytics", "count": 25, "growth_rate": 15.5},
            {"topic": "implementation", "count": 20, "growth_rate": 8.2},
            {"topic": "troubleshooting", "count": 18, "growth_rate": -5.1}
        ]
        
        accuracy_data = {
            "high_confidence_count": 45,
            "medium_confidence_count": 30,
            "low_confidence_count": 25
        }
        
        performance_data = {
            "success_rate": 0.85,
            "error_rate": 0.15,
            "bedrock_usage_rate": 0.25,
            "cost_per_question": 0.0005
        }
        
        user_behavior_data = {
            "segmentation": {
                "power_users": 5,
                "active_users": 15,
                "casual_users": 10,
                "total_users": 30
            }
        }
        
        # Test formatting functions
        print("📊 Testing formatting functions...")
        
        # Trending topics table
        trending_table = viz.format_trending_topics_table(trending_data)
        print("✅ Trending topics table created")
        print(trending_table[:200] + "..." if len(trending_table) > 200 else trending_table)
        
        # Confidence distribution
        confidence_summary = viz.format_confidence_distribution(accuracy_data)
        print("✅ Confidence distribution summary created")
        print(confidence_summary[:200] + "..." if len(confidence_summary) > 200 else confidence_summary)
        
        # Performance metrics
        performance_summary = viz.format_performance_metrics(performance_data)
        print("✅ Performance metrics summary created")
        
        # User segmentation
        user_summary = viz.format_user_segmentation(user_behavior_data)
        print("✅ User segmentation summary created")
        
        # Analytics report
        analytics_data = {
            "trending_topics": trending_data,
            "tagging_accuracy": accuracy_data,
            "performance_metrics": performance_data,
            "user_behavior": user_behavior_data
        }
        
        report = viz.create_analytics_report(analytics_data)
        print(f"✅ Analytics report created ({len(report)} characters)")
        
        print("\n🎉 All visualization tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Visualization test failed: {e}")

if __name__ == "__main__":
    test_analytics_engine()
    test_visualization_helpers()
    print("\n🎉 All analytics engine tests completed successfully!")
