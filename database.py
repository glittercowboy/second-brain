# database.py
"""
Phase 5 (Modified): SQLite Database with Multi-Category Support
---------------------------------------------------------------
This file creates the 'transcriptions' table (if it doesn't exist)
and inserts transcriptions + AI data (categories, keywords).
"""

import sqlite3
import logging
from datetime import datetime

DB_NAME = "journal.db"

def initialize_db():
    """
    Creates the 'transcriptions' table if it does not exist,
    including columns for category (multi) and keywords.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    transcription TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    categories TEXT,   -- comma-separated list of categories
                    keywords TEXT
                )
            """)
            conn.commit()
            logging.info("Database initialized or already exists.")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

def insert_transcription_with_ai(user_id: str, message_id: str,
                                 transcription: str, file_path: str,
                                 categories: str, keywords: str):
    """
    Inserts a new transcription record into 'transcriptions',
    including multi-categories and keywords.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            current_time = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO transcriptions (
                    user_id, message_id, timestamp, transcription, file_path, categories, keywords
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, message_id, current_time, transcription, file_path, categories, keywords))
            conn.commit()
            logging.info("Inserted transcription + AI data (multi-category) into DB.")
    except Exception as e:
        logging.error(f"Error inserting transcription: {e}")