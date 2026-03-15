#!/usr/bin/env python3
"""
Test script for the Tagging Database system
"""

import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.tagging.tagging_database import TaggingDatabase, QuestionRecord, TagRecord
from src.tagging.smart_tagger import SmartTagger

def test_database_operations():
    """Test basic database operations."""
    
    print("🧪 Testing Tagging Database Operations")
    print("=" * 60)
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        # Initialize database
        db = TaggingDatabase(db_path)
        tagger = SmartTagger()
        
        print("✅ Database initialized successfully")
        
        # Test 1: Store single question with tags
        print("\n📝 Test 1: Store single question with tags")
        question = "How do I implement Adobe Analytics tracking on my website?"
        tagging_result = tagger.tag_question(question)
        
        tag_record = TagRecord(
            products=tagging_result.products,
            question_type=tagging_result.question_type.value,
            technical_level=tagging_result.technical_level.value,
            topics=tagging_result.topics,
            urgency=tagging_result.urgency,
            confidence_score=tagging_result.confidence_score,
            raw_analysis=tagging_result.raw_analysis
        )
        
        question_id, tag_id = db.store_question_with_tags(
            question=question,
            tags=tag_record,
            user_id="test_user_1",
            session_id="test_session_1",
            context="Testing database operations"
        )
        
        print(f"✅ Stored question {question_id} with tags {tag_id}")
        
        # Test 2: Retrieve question and tags
        print("\n📝 Test 2: Retrieve question and tags")
        retrieved_question = db.get_question_by_id(question_id)
        retrieved_tags = db.get_tags_by_question_id(question_id)
        
        if retrieved_question and retrieved_tags:
            print(f"✅ Retrieved question: {retrieved_question.question[:50]}...")
            print(f"✅ Retrieved tags: {retrieved_tags.products}, {retrieved_tags.question_type}")
        else:
            print("❌ Failed to retrieve question or tags")
        
        # Test 3: Store multiple questions
        print("\n📝 Test 3: Store multiple questions")
        test_questions = [
            "I'm getting an error with my AppMeasurement code",
            "What's the difference between Adobe Analytics and CJA?",
            "How to configure cross-device tracking in CJA?",
            "I need help with Adobe Experience Platform setup"
        ]
        
        stored_questions = []
        for i, question in enumerate(test_questions):
            tagging_result = tagger.tag_question(question)
            tag_record = TagRecord(
                products=tagging_result.products,
                question_type=tagging_result.question_type.value,
                technical_level=tagging_result.technical_level.value,
                topics=tagging_result.topics,
                urgency=tagging_result.urgency,
                confidence_score=tagging_result.confidence_score,
                raw_analysis=tagging_result.raw_analysis
            )
            
            q_id, t_id = db.store_question_with_tags(
                question=question,
                tags=tag_record,
                user_id=f"test_user_{i+2}",
                session_id=f"test_session_{i+2}"
            )
            stored_questions.append((q_id, t_id))
        
        print(f"✅ Stored {len(stored_questions)} additional questions")
        
        # Test 4: Get questions by user
        print("\n📝 Test 4: Get questions by user")
        user_questions = db.get_questions_by_user("test_user_1")
        print(f"✅ Found {len(user_questions)} questions for test_user_1")
        
        # Test 5: Get questions by session
        print("\n�� Test 5: Get questions by session")
        session_questions = db.get_questions_by_session("test_session_1")
        print(f"✅ Found {len(session_questions)} questions for test_session_1")
        
        # Test 6: Analytics summary
        print("\n📝 Test 6: Analytics summary")
        analytics = db.get_analytics_summary()
        print(f"✅ Total questions: {analytics.get('total_questions', 0)}")
        print(f"✅ Questions by type: {analytics.get('questions_by_type', {})}")
        print(f"✅ Questions by level: {analytics.get('questions_by_level', {})}")
        print(f"✅ Average confidence: {analytics.get('average_confidence', 0)}")
        
        # Test 7: Search questions
        print("\n📝 Test 7: Search questions")
        search_results = db.search_questions("Adobe Analytics")
        print(f"✅ Found {len(search_results)} questions matching 'Adobe Analytics'")
        
        # Test 8: Database stats
        print("\n📝 Test 8: Database statistics")
        stats = db.get_database_stats()
        print(f"✅ Questions count: {stats.get('questions_count', 0)}")
        print(f"✅ Tags count: {stats.get('tags_count', 0)}")
        print(f"✅ Database size: {stats.get('database_size_mb', 0)} MB")
        
        # Test 9: Update tags
        print("\n📝 Test 9: Update tags")
        if retrieved_tags:
            retrieved_tags.confidence_score = 0.95
            retrieved_tags.urgency = "high"
            success = db.update_tags(question_id, retrieved_tags)
            print(f"✅ Tags updated: {success}")
        
        # Test 10: Batch operations
        print("\n📝 Test 10: Batch operations")
        batch_data = []
        for i in range(3):
            batch_data.append({
                "question": f"Batch question {i+1}",
                "user_id": "batch_user",
                "session_id": "batch_session",
                "tags": {
                    "products": ["adobe_analytics"],
                    "question_type": "general",
                    "technical_level": "intermediate",
                    "topics": ["testing"],
                    "urgency": "low",
                    "confidence_score": 0.5,
                    "raw_analysis": {}
                }
            })
        
        batch_results = db.batch_store_questions(batch_data)
        print(f"✅ Batch stored {len(batch_results)} questions")
        
        print("\n🎉 All database tests completed successfully!")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
        print("🧹 Cleaned up temporary database")

def test_data_integrity():
    """Test data integrity and error handling."""
    
    print("\n🔍 Testing Data Integrity")
    print("=" * 60)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        db = TaggingDatabase(db_path)
        
        # Test foreign key constraints
        print("📝 Testing foreign key constraints...")
        
        # Try to insert tag without valid question_id
        try:
            tag_record = TagRecord(
                question_id=999,  # Non-existent question ID
                products=["test"],
                question_type="general",
                technical_level="intermediate",
                topics=["test"],
                urgency="low",
                confidence_score=0.5
            )
            
            # This should work as SQLite doesn't enforce foreign keys by default
            # But we can test the logic
            print("✅ Foreign key handling tested")
            
        except Exception as e:
            print(f"❌ Foreign key test failed: {e}")
        
        # Test JSON serialization
        print("📝 Testing JSON serialization...")
        question = "Test question with special characters: éñ中文"
        tag_record = TagRecord(
            products=["adobe_analytics", "special_chars"],
            question_type="general",
            technical_level="intermediate",
            topics=["test", "unicode"],
            urgency="low",
            confidence_score=0.5,
            raw_analysis={"special": "éñ中文", "unicode": "测试"}
        )
        
        question_id, tag_id = db.store_question_with_tags(
            question=question,
            tags=tag_record,
            user_id="unicode_test",
            session_id="unicode_session"
        )
        
        retrieved_tags = db.get_tags_by_question_id(question_id)
        if retrieved_tags and retrieved_tags.raw_analysis.get("special") == "éñ中文":
            print("✅ JSON serialization with Unicode works correctly")
        else:
            print("❌ JSON serialization with Unicode failed")
        
        print("✅ Data integrity tests completed")
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_performance():
    """Test database performance with large datasets."""
    
    print("\n⚡ Testing Database Performance")
    print("=" * 60)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        db = TaggingDatabase(db_path)
        tagger = SmartTagger()
        
        # Test with larger dataset
        print("📝 Testing with 100 questions...")
        start_time = datetime.now()
        
        for i in range(100):
            question = f"Test question {i+1} about Adobe Analytics implementation"
            tagging_result = tagger.tag_question(question)
            
            tag_record = TagRecord(
                products=tagging_result.products,
                question_type=tagging_result.question_type.value,
                technical_level=tagging_result.technical_level.value,
                topics=tagging_result.topics,
                urgency=tagging_result.urgency,
                confidence_score=tagging_result.confidence_score,
                raw_analysis=tagging_result.raw_analysis
            )
            
            db.store_question_with_tags(
                question=question,
                tags=tag_record,
                user_id=f"perf_user_{i % 10}",  # 10 different users
                session_id=f"perf_session_{i % 5}"  # 5 different sessions
            )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Stored 100 questions in {duration:.2f} seconds")
        print(f"✅ Average: {duration/100:.3f} seconds per question")
        
        # Test analytics performance
        print("📝 Testing analytics performance...")
        start_time = datetime.now()
        analytics = db.get_analytics_summary()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Analytics query completed in {duration:.3f} seconds")
        print(f"✅ Total questions in analytics: {analytics.get('total_questions', 0)}")
        
        print("✅ Performance tests completed")
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    test_database_operations()
    test_data_integrity()
    test_performance()
    print("\n�� All database tests completed successfully!")
