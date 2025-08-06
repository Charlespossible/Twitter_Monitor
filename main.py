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

        # Determine filesystem path for SQLite
        if self.db_url.startswith('sqlite:///'):
            self.db_path = self.db_url[10:]
        else:
            self.db_path = self.db_url

        # Ensure the directory for the database exists
        self._ensure_db_directory()

        # Initialize the database
        self._init_db()

        # Verify the database was created successfully
        self._verify_database()

    def _ensure_db_directory(self):
        """Ensure the directory for the database file exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                self.logger.info(f"Created database directory: {db_dir}")
            except Exception as e:
                self.logger.error(f"Failed to create database directory: {e}")
                raise

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        except sqlite3.Error as e:
            self.logger.error(f"Database connection error: {e}")
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _init_db(self):
        """Initialize the database with required tables"""
        try:
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
                # Create state table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS state (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                self.logger.info("Database initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    def _verify_database(self):
        """Verify that the database was created successfully"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mentions'")
                mentions_exists = cursor.fetchone() is not None
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='state'")
                state_exists = cursor.fetchone() is not None
                if mentions_exists and state_exists:
                    self.logger.info("Database verification successful: All required tables exist")
                else:
                    missing = []
                    if not mentions_exists:
                        missing.append('mentions')
                    if not state_exists:
                        missing.append('state')
                    msg = f"Missing tables: {', '.join(missing)}"
                    self.logger.error(msg)
                    raise Exception(msg)
        except Exception as e:
            self.logger.error(f"Database verification error: {e}")
            raise

    def get_last_checked(self, handle: str) -> Optional[datetime]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM state WHERE key = ?", (f"last_checked_{handle}",)
            )
            row = cursor.fetchone()
            return datetime.fromisoformat(row[0]) if row else None

    def update_last_checked(self, handle: str, timestamp: datetime):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (f"last_checked_{handle}", timestamp.isoformat())
            )
            conn.commit()

    def add_mention(self, mention_data: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO mentions (tweet_id, handle, author, text, timestamp, url)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    mention_data['tweet_id'],
                    mention_data['handle'],
                    mention_data['author'],
                    mention_data['text'],
                    mention_data['timestamp'],
                    mention_data['url']
                )
            )
            conn.commit()

    def get_unnotified_mentions(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, tweet_id, handle, author, text, timestamp, url
                FROM mentions WHERE notified = 0
                '''
            )
            return [dict(r) for r in cursor.fetchall()]

    def mark_as_notified(self, mention_ids: List[int]):
        if not mention_ids:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?']*len(mention_ids))
            cursor.execute(
                f"UPDATE mentions SET notified=1 WHERE id IN ({placeholders})", mention_ids
            )
            conn.commit()

    def get_weekly_mentions(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT handle, author, text, timestamp, url
                FROM mentions
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
                ''', (start_date.isoformat(), end_date.isoformat())
            )
            return [dict(r) for r in cursor.fetchall()]
