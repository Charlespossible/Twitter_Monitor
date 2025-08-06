import sqlite3
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class DataStorage:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.logger = logging.getLogger(__name__)
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with required tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create mentions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mentions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_id TEXT NOT NULL,
                    handle TEXT NOT NULL,
                    author TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    url TEXT NOT NULL,
                    notified BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create state table to track last checked timestamps
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_url)
        try:
            yield conn
        except Exception as e:
            self.logger.error(f"Database error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_last_checked(self, handle: str) -> Optional[datetime]:
        """Get the last checked timestamp for a handle"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM state WHERE key = ?", 
                (f"last_checked_{handle}",)
            )
            result = cursor.fetchone()
            if result:
                return datetime.fromisoformat(result[0])
            return None
    
    def update_last_checked(self, handle: str, timestamp: datetime):
        """Update the last checked timestamp for a handle"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (f"last_checked_{handle}", timestamp.isoformat())
            )
            conn.commit()
    
    def add_mention(self, mention_data: Dict[str, Any]):
        """Add a new mention to the database"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO mentions (tweet_id, handle, author, text, timestamp, url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                mention_data['tweet_id'],
                mention_data['handle'],
                mention_data['author'],
                mention_data['text'],
                mention_data['timestamp'],
                mention_data['url']
            ))
            conn.commit()
    
    def get_unnotified_mentions(self) -> List[Dict[str, Any]]:
        """Get all mentions that haven't been notified yet"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, tweet_id, handle, author, text, timestamp, url
                FROM mentions
                WHERE notified = 0
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_as_notified(self, mention_ids: List[int]):
        """Mark mentions as notified"""
        if not mention_ids:
            return
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ', '.join(['?'] * len(mention_ids))
            cursor.execute(
                f"UPDATE mentions SET notified = 1 WHERE id IN ({placeholders})",
                mention_ids
            )
            conn.commit()
    
    def get_weekly_mentions(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get all mentions within a date range for the weekly report"""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT handle, author, text, timestamp, url
                FROM mentions
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            ''', (start_date.isoformat(), end_date.isoformat()))
            return [dict(row) for row in cursor.fetchall()]