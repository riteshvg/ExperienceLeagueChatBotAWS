"""
Database Layer for Smart Tagging System

This module provides database operations for storing and managing question tags,
including CRUD operations, analytics queries, and data integrity checks.
"""

import sqlite3
import json
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)

@dataclass
class QuestionRecord:
    """Question record with metadata."""
    id: Optional[int] = None
    question: str = ""
    user_id: str = "anonymous"
    session_id: str = ""
    timestamp: datetime = None
    context: str = ""
    created_at: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

@dataclass
class TagRecord:
    """Tag record with all tagging information."""
    id: Optional[int] = None
    question_id: int = 0
    products: List[str] = None
    question_type: str = "general"
    technical_level: str = "intermediate"
    topics: List[str] = None
    urgency: str = "low"
    confidence_score: float = 0.0
    raw_analysis: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.products is None:
            self.products = []
        if self.topics is None:
            self.topics = []
        if self.raw_analysis is None:
            self.raw_analysis = {}
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

class TaggingDatabase:
    """Database layer for managing question tags."""
    
    def __init__(self, db_path: str = "tagging.db"):
        """
        Initialize the tagging database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database schema and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create questions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    user_id TEXT NOT NULL DEFAULT 'anonymous',
                    session_id TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    context TEXT DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create tags table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER NOT NULL,
                    products TEXT NOT NULL,  -- JSON array
                    question_type TEXT NOT NULL,
                    technical_level TEXT NOT NULL,
                    topics TEXT NOT NULL,  -- JSON array
                    urgency TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    raw_analysis TEXT NOT NULL,  -- JSON object
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for performance
            self._create_indexes(cursor)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def _create_indexes(self, cursor):
        """Create database indexes for performance."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_questions_user_id ON questions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_questions_session_id ON questions(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_questions_timestamp ON questions(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_tags_question_id ON tags(question_id)",
            "CREATE INDEX IF NOT EXISTS idx_tags_question_type ON tags(question_type)",
            "CREATE INDEX IF NOT EXISTS idx_tags_technical_level ON tags(technical_level)",
            "CREATE INDEX IF NOT EXISTS idx_tags_urgency ON tags(urgency)",
            "CREATE INDEX IF NOT EXISTS idx_tags_confidence ON tags(confidence_score)",
            "CREATE INDEX IF NOT EXISTS idx_tags_created_at ON tags(created_at)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with proper error handling."""
        conn = None
        try:
            with self._lock:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def store_question_with_tags(self, question: str, tags: TagRecord, 
                               user_id: str = "anonymous", session_id: str = "",
                               context: str = "") -> Tuple[int, int]:
        """
        Store a question with its tags in a single transaction.
        
        Args:
            question: User question text
            tags: TagRecord object with tagging information
            user_id: User identifier
            session_id: Session identifier
            context: Additional context
            
        Returns:
            Tuple of (question_id, tag_id)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert question
                question_record = QuestionRecord(
                    question=question,
                    user_id=user_id,
                    session_id=session_id,
                    context=context
                )
                
                cursor.execute("""
                    INSERT INTO questions (question, user_id, session_id, timestamp, context, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    question_record.question,
                    question_record.user_id,
                    question_record.session_id,
                    question_record.timestamp.isoformat(),
                    question_record.context,
                    question_record.created_at.isoformat()
                ))
                
                question_id = cursor.lastrowid
                
                # Insert tags
                cursor.execute("""
                    INSERT INTO tags (question_id, products, question_type, technical_level, 
                                    topics, urgency, confidence_score, raw_analysis, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    question_id,
                    json.dumps(tags.products),
                    tags.question_type,
                    tags.technical_level,
                    json.dumps(tags.topics),
                    tags.urgency,
                    tags.confidence_score,
                    json.dumps(tags.raw_analysis),
                    tags.created_at.isoformat()
                ))
                
                tag_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Stored question {question_id} with tags {tag_id}")
                return question_id, tag_id
                
        except Exception as e:
            logger.error(f"Error storing question with tags: {e}")
            raise
    
    def get_question_by_id(self, question_id: int) -> Optional[QuestionRecord]:
        """Get question by ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
                row = cursor.fetchone()
                
                if row:
                    return QuestionRecord(
                        id=row['id'],
                        question=row['question'],
                        user_id=row['user_id'],
                        session_id=row['session_id'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        context=row['context'],
                        created_at=datetime.fromisoformat(row['created_at'])
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting question by ID: {e}")
            return None
    
    def get_tags_by_question_id(self, question_id: int) -> Optional[TagRecord]:
        """Get tags by question ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM tags WHERE question_id = ?", (question_id,))
                row = cursor.fetchone()
                
                if row:
                    return TagRecord(
                        id=row['id'],
                        question_id=row['question_id'],
                        products=json.loads(row['products']),
                        question_type=row['question_type'],
                        technical_level=row['technical_level'],
                        topics=json.loads(row['topics']),
                        urgency=row['urgency'],
                        confidence_score=row['confidence_score'],
                        raw_analysis=json.loads(row['raw_analysis']),
                        created_at=datetime.fromisoformat(row['created_at'])
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting tags by question ID: {e}")
            return None
    
    def get_questions_by_user(self, user_id: str, limit: int = 100, 
                            offset: int = 0) -> List[QuestionRecord]:
        """Get questions by user ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM questions 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
                
                questions = []
                for row in cursor.fetchall():
                    questions.append(QuestionRecord(
                        id=row['id'],
                        question=row['question'],
                        user_id=row['user_id'],
                        session_id=row['session_id'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        context=row['context'],
                        created_at=datetime.fromisoformat(row['created_at'])
                    ))
                
                return questions
                
        except Exception as e:
            logger.error(f"Error getting questions by user: {e}")
            return []
    
    def get_questions_by_session(self, session_id: str) -> List[QuestionRecord]:
        """Get questions by session ID."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM questions 
                    WHERE session_id = ? 
                    ORDER BY created_at ASC
                """, (session_id,))
                
                questions = []
                for row in cursor.fetchall():
                    questions.append(QuestionRecord(
                        id=row['id'],
                        question=row['question'],
                        user_id=row['user_id'],
                        session_id=row['session_id'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        context=row['context'],
                        created_at=datetime.fromisoformat(row['created_at'])
                    ))
                
                return questions
                
        except Exception as e:
            logger.error(f"Error getting questions by session: {e}")
            return []
    
    def update_tags(self, question_id: int, tags: TagRecord) -> bool:
        """Update tags for a question."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tags 
                    SET products = ?, question_type = ?, technical_level = ?, 
                        topics = ?, urgency = ?, confidence_score = ?, 
                        raw_analysis = ?
                    WHERE question_id = ?
                """, (
                    json.dumps(tags.products),
                    tags.question_type,
                    tags.technical_level,
                    json.dumps(tags.topics),
                    tags.urgency,
                    tags.confidence_score,
                    json.dumps(tags.raw_analysis),
                    question_id
                ))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating tags: {e}")
            return False
    
    def delete_question(self, question_id: int) -> bool:
        """Delete a question and its tags."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting question: {e}")
            return False
    
    def batch_store_questions(self, question_data: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """
        Store multiple questions with tags in batch.
        
        Args:
            question_data: List of dictionaries with question and tags data
            
        Returns:
            List of tuples (question_id, tag_id)
        """
        results = []
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for data in question_data:
                    # Insert question
                    cursor.execute("""
                        INSERT INTO questions (question, user_id, session_id, timestamp, context, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        data['question'],
                        data.get('user_id', 'anonymous'),
                        data.get('session_id', ''),
                        data.get('timestamp', datetime.now(timezone.utc).isoformat()),
                        data.get('context', ''),
                        datetime.now(timezone.utc).isoformat()
                    ))
                    
                    question_id = cursor.lastrowid
                    
                    # Insert tags
                    tags = data.get('tags', {})
                    cursor.execute("""
                        INSERT INTO tags (question_id, products, question_type, technical_level, 
                                        topics, urgency, confidence_score, raw_analysis, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        question_id,
                        json.dumps(tags.get('products', [])),
                        tags.get('question_type', 'general'),
                        tags.get('technical_level', 'intermediate'),
                        json.dumps(tags.get('topics', [])),
                        tags.get('urgency', 'low'),
                        tags.get('confidence_score', 0.0),
                        json.dumps(tags.get('raw_analysis', {})),
                        datetime.now(timezone.utc).isoformat()
                    ))
                    
                    tag_id = cursor.lastrowid
                    results.append((question_id, tag_id))
                
                conn.commit()
                logger.info(f"Batch stored {len(results)} questions")
                
        except Exception as e:
            logger.error(f"Error in batch store: {e}")
            raise
        
        return results
    
    def get_analytics_summary(self, start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get analytics summary for dashboard metrics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Date filter
                date_filter = ""
                params = []
                if start_date and end_date:
                    date_filter = "WHERE q.created_at BETWEEN ? AND ?"
                    params = [start_date.isoformat(), end_date.isoformat()]
                
                # Total questions
                cursor.execute(f"""
                    SELECT COUNT(*) as total_questions
                    FROM questions q
                    {date_filter}
                """, params)
                total_questions = cursor.fetchone()['total_questions']
                
                # Questions by type
                cursor.execute(f"""
                    SELECT t.question_type, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                    GROUP BY t.question_type
                    ORDER BY count DESC
                """, params)
                questions_by_type = dict(cursor.fetchall())
                
                # Questions by technical level
                cursor.execute(f"""
                    SELECT t.technical_level, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                    GROUP BY t.technical_level
                    ORDER BY count DESC
                """, params)
                questions_by_level = dict(cursor.fetchall())
                
                # Questions by urgency
                cursor.execute(f"""
                    SELECT t.urgency, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                    GROUP BY t.urgency
                    ORDER BY count DESC
                """, params)
                questions_by_urgency = dict(cursor.fetchall())
                
                # Average confidence score
                cursor.execute(f"""
                    SELECT AVG(t.confidence_score) as avg_confidence
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                """, params)
                avg_confidence = cursor.fetchone()['avg_confidence'] or 0.0
                
                # Top products
                cursor.execute(f"""
                    SELECT t.products, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                    GROUP BY t.products
                    ORDER BY count DESC
                    LIMIT 10
                """, params)
                
                top_products = []
                for row in cursor.fetchall():
                    products = json.loads(row['products'])
                    for product in products:
                        top_products.append((product, row['count']))
                
                # Top topics
                cursor.execute(f"""
                    SELECT t.topics, COUNT(*) as count
                    FROM tags t
                    JOIN questions q ON t.question_id = q.id
                    {date_filter}
                    GROUP BY t.topics
                    ORDER BY count DESC
                    LIMIT 10
                """, params)
                
                top_topics = []
                for row in cursor.fetchall():
                    topics = json.loads(row['topics'])
                    for topic in topics:
                        top_topics.append((topic, row['count']))
                
                return {
                    "total_questions": total_questions,
                    "questions_by_type": questions_by_type,
                    "questions_by_level": questions_by_level,
                    "questions_by_urgency": questions_by_urgency,
                    "average_confidence": round(avg_confidence, 3),
                    "top_products": top_products[:10],
                    "top_topics": top_topics[:10]
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {}
    
    def search_questions(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search questions by text content."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT q.*, t.*
                    FROM questions q
                    LEFT JOIN tags t ON q.id = t.question_id
                    WHERE q.question LIKE ?
                    ORDER BY q.created_at DESC
                    LIMIT ?
                """, (f"%{query}%", limit))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "question_id": row['id'],
                        "question": row['question'],
                        "user_id": row['user_id'],
                        "session_id": row['session_id'],
                        "timestamp": row['timestamp'],
                        "context": row['context'],
                        "products": json.loads(row['products']) if row['products'] else [],
                        "question_type": row['question_type'],
                        "technical_level": row['technical_level'],
                        "topics": json.loads(row['topics']) if row['topics'] else [],
                        "urgency": row['urgency'],
                        "confidence_score": row['confidence_score']
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching questions: {e}")
            return []
    
    def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database."""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup."""
        try:
            import shutil
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Table sizes
                cursor.execute("SELECT COUNT(*) as count FROM questions")
                questions_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM tags")
                tags_count = cursor.fetchone()['count']
                
                # Database size
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    "questions_count": questions_count,
                    "tags_count": tags_count,
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / (1024 * 1024), 2)
                }
                
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

# Example usage and testing
if __name__ == "__main__":
    # Initialize database
    db = TaggingDatabase("test_tagging.db")
    
    # Test data
    from src.tagging.smart_tagger import SmartTagger, TagRecord
    
    tagger = SmartTagger()
    
    # Test questions
    test_questions = [
        "How do I implement Adobe Analytics tracking?",
        "I'm getting an error with my AppMeasurement code",
        "What's the difference between Adobe Analytics and CJA?"
    ]
    
    print("Testing Tagging Database")
    print("=" * 40)
    
    for i, question in enumerate(test_questions):
        # Tag the question
        tagging_result = tagger.tag_question(question)
        
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
        question_id, tag_id = db.store_question_with_tags(
            question=question,
            tags=tag_record,
            user_id=f"test_user_{i}",
            session_id="test_session"
        )
        
        print(f"Stored question {question_id} with tags {tag_id}")
    
    # Get analytics
    analytics = db.get_analytics_summary()
    print(f"\nAnalytics Summary:")
    print(f"Total questions: {analytics.get('total_questions', 0)}")
    print(f"Questions by type: {analytics.get('questions_by_type', {})}")
    print(f"Average confidence: {analytics.get('average_confidence', 0)}")
    
    # Clean up
    os.remove("test_tagging.db")
    print("\nTest completed successfully!")
