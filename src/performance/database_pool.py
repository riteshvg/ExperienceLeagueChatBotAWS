"""
Database connection pooling and batch operations for performance optimization
"""

import threading
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from queue import Queue, Empty
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseConnectionPool:
    """Thread-safe database connection pool with batch operations"""
    
    def __init__(self, database_url: str, min_connections: int = 2, max_connections: int = 10):
        self.database_url = database_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.pool = None
        self.lock = threading.Lock()
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'queries_executed': 0,
            'batch_operations': 0,
            'errors': 0
        }
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections,
                dsn=self.database_url,
                cursor_factory=RealDictCursor
            )
            logger.info(f"✅ Database pool initialized: {self.min_connections}-{self.max_connections} connections")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            with self.lock:
                conn = self.pool.getconn()
                self.stats['active_connections'] += 1
                return conn
        except Exception as e:
            logger.error(f"❌ Failed to get database connection: {e}")
            self.stats['errors'] += 1
            raise
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        try:
            with self.lock:
                self.pool.putconn(conn)
                self.stats['active_connections'] -= 1
        except Exception as e:
            logger.error(f"❌ Failed to return database connection: {e}")
            self.stats['errors'] += 1
    
    def execute_query(self, query: str, params: Optional[List] = None, fetch: bool = True) -> Tuple[bool, Optional[List[Dict]], str]:
        """Execute a single query with connection pooling"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            start_time = time.time()
            cursor.execute(query, params)
            
            if fetch:
                result = cursor.fetchall()
                # Convert to list of dicts
                result = [dict(row) for row in result]
            else:
                result = None
            
            conn.commit()
            self.stats['queries_executed'] += 1
            
            execution_time = time.time() - start_time
            logger.debug(f"Query executed in {execution_time:.3f}s")
            
            return True, result, f"Query executed successfully in {execution_time:.3f}s"
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.stats['errors'] += 1
            logger.error(f"❌ Query execution failed: {e}")
            return False, None, str(e)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.return_connection(conn)
    
    def execute_batch(self, queries: List[Tuple[str, Optional[List]]]) -> List[Tuple[bool, Optional[List[Dict]], str]]:
        """Execute multiple queries in a single transaction"""
        conn = None
        cursor = None
        results = []
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            start_time = time.time()
            
            for query, params in queries:
                try:
                    cursor.execute(query, params)
                    result = cursor.fetchall() if cursor.description else None
                    if result:
                        result = [dict(row) for row in result]
                    results.append((True, result, "Success"))
                except Exception as e:
                    results.append((False, None, str(e)))
                    logger.error(f"❌ Batch query failed: {e}")
            
            conn.commit()
            self.stats['batch_operations'] += 1
            self.stats['queries_executed'] += len(queries)
            
            execution_time = time.time() - start_time
            logger.info(f"Batch of {len(queries)} queries executed in {execution_time:.3f}s")
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.stats['errors'] += 1
            logger.error(f"❌ Batch execution failed: {e}")
            # Return error for all queries
            results = [(False, None, str(e))] * len(queries)
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.return_connection(conn)
        
        return results
    
    def batch_insert_analytics(self, analytics_data: List[Dict[str, Any]]) -> bool:
        """Batch insert analytics data for better performance"""
        if not analytics_data:
            return True
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Prepare batch insert query
            insert_query = """
                INSERT INTO query_analytics 
                (query, userid, date_time, reaction, query_time_seconds, model_used,
                 products, question_type, technical_level, topics, urgency, confidence_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Prepare data for batch insert
            batch_data = []
            for data in analytics_data:
                batch_data.append((
                    data.get('query', ''),
                    data.get('userid', 'anonymous'),
                    data.get('date_time', datetime.now()),
                    data.get('reaction', 'none'),
                    data.get('query_time_seconds'),
                    data.get('model_used'),
                    data.get('products', '[]'),
                    data.get('question_type', 'unknown'),
                    data.get('technical_level', 'unknown'),
                    data.get('topics', '[]'),
                    data.get('urgency', 'low'),
                    data.get('confidence_score', 0.0)
                ))
            
            # Execute batch insert
            cursor.executemany(insert_query, batch_data)
            conn.commit()
            
            self.stats['batch_operations'] += 1
            self.stats['queries_executed'] += len(analytics_data)
            
            logger.info(f"✅ Batch inserted {len(analytics_data)} analytics records")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.stats['errors'] += 1
            logger.error(f"❌ Batch insert failed: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.return_connection(conn)
    
    def get_analytics_summary_batch(self, table_name: str) -> Dict[str, Any]:
        """Get analytics summary with optimized batch queries"""
        queries = []
        
        if table_name == "query_analytics":
            # Count total records
            queries.append(("SELECT COUNT(*) as count FROM query_analytics", None))
            
            # Feedback breakdown
            queries.append(("""
                SELECT 
                    CASE 
                        WHEN reaction = 'positive' THEN 'positive'
                        WHEN reaction = 'negative' THEN 'negative'
                        WHEN reaction = 'none' THEN 'none'
                        ELSE reaction
                    END as reaction_display,
                    COUNT(*) as count
                FROM query_analytics 
                WHERE reaction IS NOT NULL
                GROUP BY reaction
                ORDER BY count DESC
            """, None))
            
            # Daily activity
            queries.append("""
                SELECT 
                    DATE(date_time) as date,
                    COUNT(*) as queries
                FROM query_analytics 
                GROUP BY DATE(date_time)
                ORDER BY date DESC
                LIMIT 7
            """, None)
            
            # Tagging breakdown
            queries.append("""
                SELECT 
                    COALESCE(t.question_type, 'unknown') as question_type,
                    COALESCE(t.technical_level, 'unknown') as technical_level,
                    COALESCE(t.urgency, 'low') as urgency,
                    COUNT(*) as count
                FROM query_analytics qa
                LEFT JOIN questions q ON qa.query = q.question
                LEFT JOIN tags t ON q.id = t.question_id
                GROUP BY t.question_type, t.technical_level, t.urgency
                ORDER BY count DESC
            """, None)
        
        # Execute all queries in batch
        results = self.execute_batch(queries)
        
        # Process results
        summary = {}
        if results[0][0]:  # Total count
            summary['total_records'] = results[0][1][0]['count'] if results[0][1] else 0
        
        if len(results) > 1 and results[1][0]:  # Feedback breakdown
            feedback_data = results[1][1] or []
            summary['feedback_breakdown'] = {row['reaction_display']: row['count'] for row in feedback_data}
        
        if len(results) > 2 and results[2][0]:  # Daily activity
            daily_data = results[2][1] or []
            summary['daily_activity'] = {str(row['date']): row['queries'] for row in daily_data}
        
        if len(results) > 3 and results[3][0]:  # Tagging breakdown
            tagging_data = results[3][1] or []
            # Process tagging data
            question_types = {}
            technical_levels = {}
            urgency_levels = {}
            
            for row in tagging_data:
                qtype = row['question_type']
                tlevel = row['technical_level']
                urgency = row['urgency']
                count = row['count']
                
                question_types[qtype] = question_types.get(qtype, 0) + count
                technical_levels[tlevel] = technical_levels.get(tlevel, 0) + count
                urgency_levels[urgency] = urgency_levels.get(urgency, 0) + count
            
            summary['tagging_breakdown'] = {
                'question_types': question_types,
                'technical_levels': technical_levels,
                'urgency_levels': urgency_levels
            }
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database pool statistics"""
        return {
            **self.stats,
            'pool_size': self.pool.size if self.pool else 0,
            'min_connections': self.min_connections,
            'max_connections': self.max_connections
        }
    
    def close(self):
        """Close the connection pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("✅ Database connection pool closed")

# Global database pool instance
db_pool = None

def initialize_db_pool(database_url: str, min_connections: int = 2, max_connections: int = 10):
    """Initialize the global database pool"""
    global db_pool
    db_pool = DatabaseConnectionPool(database_url, min_connections, max_connections)
    return db_pool

def get_db_pool() -> Optional[DatabaseConnectionPool]:
    """Get the global database pool instance"""
    return db_pool
