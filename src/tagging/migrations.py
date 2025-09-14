"""
Database Migration System for Tagging Database

This module provides database migration capabilities for schema updates
and data transformations.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import os

logger = logging.getLogger(__name__)

class DatabaseMigration:
    """Database migration system for tagging database."""
    
    def __init__(self, db_path: str):
        """
        Initialize migration system.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.migrations_table = "schema_migrations"
        self._initialize_migrations_table()
    
    def _initialize_migrations_table(self):
        """Initialize migrations tracking table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version TEXT UNIQUE NOT NULL,
                        description TEXT NOT NULL,
                        applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing migrations table: {e}")
            raise
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM schema_migrations ORDER BY applied_at")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting applied migrations: {e}")
            return []
    
    def apply_migration(self, version: str, description: str, sql_commands: List[str]) -> bool:
        """
        Apply a database migration.
        
        Args:
            version: Migration version identifier
            description: Migration description
            sql_commands: List of SQL commands to execute
            
        Returns:
            True if migration was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if migration already applied
                cursor.execute("SELECT version FROM schema_migrations WHERE version = ?", (version,))
                if cursor.fetchone():
                    logger.info(f"Migration {version} already applied")
                    return True
                
                # Apply migration
                for sql_command in sql_commands:
                    cursor.execute(sql_command)
                
                # Record migration
                cursor.execute("""
                    INSERT INTO schema_migrations (version, description, applied_at)
                    VALUES (?, ?, ?)
                """, (version, description, datetime.now(timezone.utc).isoformat()))
                
                conn.commit()
                logger.info(f"Migration {version} applied successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error applying migration {version}: {e}")
            return False
    
    def rollback_migration(self, version: str, rollback_commands: List[str]) -> bool:
        """
        Rollback a database migration.
        
        Args:
            version: Migration version to rollback
            rollback_commands: List of SQL commands to rollback the migration
            
        Returns:
            True if rollback was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if migration exists
                cursor.execute("SELECT version FROM schema_migrations WHERE version = ?", (version,))
                if not cursor.fetchone():
                    logger.warning(f"Migration {version} not found")
                    return False
                
                # Apply rollback commands
                for sql_command in rollback_commands:
                    cursor.execute(sql_command)
                
                # Remove migration record
                cursor.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
                
                conn.commit()
                logger.info(f"Migration {version} rolled back successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error rolling back migration {version}: {e}")
            return False
    
    def get_database_version(self) -> str:
        """Get current database version."""
        applied_migrations = self.get_applied_migrations()
        if applied_migrations:
            return applied_migrations[-1]  # Latest migration
        return "0.0.0"
    
    def backup_before_migration(self, backup_path: str) -> bool:
        """Create backup before applying migration."""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False

# Predefined migrations
MIGRATIONS = {
    "1.0.0": {
        "description": "Initial schema creation",
        "sql": [
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                user_id TEXT NOT NULL DEFAULT 'anonymous',
                session_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                context TEXT DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                products TEXT NOT NULL,
                question_type TEXT NOT NULL,
                technical_level TEXT NOT NULL,
                topics TEXT NOT NULL,
                urgency TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                raw_analysis TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE
            )
            """
        ]
    },
    "1.1.0": {
        "description": "Add indexes for performance",
        "sql": [
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
    },
    "1.2.0": {
        "description": "Add question search functionality",
        "sql": [
            "CREATE VIRTUAL TABLE IF NOT EXISTS questions_fts USING fts5(question, content='questions', content_rowid='id')",
            "CREATE TRIGGER IF NOT EXISTS questions_ai AFTER INSERT ON questions BEGIN INSERT INTO questions_fts(rowid, question) VALUES (new.id, new.question); END",
            "CREATE TRIGGER IF NOT EXISTS questions_ad AFTER DELETE ON questions BEGIN INSERT INTO questions_fts(questions_fts, rowid, question) VALUES('delete', old.id, old.question); END",
            "CREATE TRIGGER IF NOT EXISTS questions_au AFTER UPDATE ON questions BEGIN INSERT INTO questions_fts(questions_fts, rowid, question) VALUES('delete', old.id, old.question); INSERT INTO questions_fts(rowid, question) VALUES (new.id, new.question); END"
        ]
    }
}

def run_migrations(db_path: str, target_version: Optional[str] = None) -> bool:
    """
    Run all pending migrations.
    
    Args:
        db_path: Path to database file
        target_version: Target version to migrate to (None for latest)
        
    Returns:
        True if all migrations were successful
    """
    migration = DatabaseMigration(db_path)
    applied_migrations = migration.get_applied_migrations()
    
    # Get available migrations
    available_versions = sorted(MIGRATIONS.keys())
    
    # Determine migrations to apply
    migrations_to_apply = []
    for version in available_versions:
        if version not in applied_migrations:
            if target_version and version > target_version:
                break
            migrations_to_apply.append(version)
    
    if not migrations_to_apply:
        logger.info("No migrations to apply")
        return True
    
    # Create backup
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if not migration.backup_before_migration(backup_path):
        logger.error("Failed to create backup, aborting migration")
        return False
    
    # Apply migrations
    success = True
    for version in migrations_to_apply:
        migration_info = MIGRATIONS[version]
        if not migration.apply_migration(version, migration_info["description"], migration_info["sql"]):
            logger.error(f"Failed to apply migration {version}")
            success = False
            break
    
    if success:
        logger.info(f"Successfully applied {len(migrations_to_apply)} migrations")
        # Optionally remove backup if successful
        # os.remove(backup_path)
    else:
        logger.error("Migration failed, backup available at {backup_path}")
    
    return success

# Example usage
if __name__ == "__main__":
    # Test migrations
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    try:
        print("Testing Database Migrations")
        print("=" * 40)
        
        # Run migrations
        success = run_migrations(db_path)
        print(f"Migration success: {success}")
        
        # Check applied migrations
        migration = DatabaseMigration(db_path)
        applied = migration.get_applied_migrations()
        print(f"Applied migrations: {applied}")
        
        # Check database version
        version = migration.get_database_version()
        print(f"Database version: {version}")
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        print("Test completed")
