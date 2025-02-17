# database.py
"""
Phase 4: SQLite Database Management
-----------------------------------
This file handles creating the database table (if it doesn't exist)
and inserting new transcriptions.
"""

import sqlite3
import logging
from datetime import datetime

# You can change the database file name if you want
DB_NAME = "journal.db"

def initialize_db():
    """
    Creates the 'transcriptions' table if it does not exist.
    Columns:
      - id (PRIMARY KEY, auto-increment)
      - user_id (TEXT)
      - message_id (TEXT)
      - timestamp (TEXT)
      - transcription (TEXT)
      - file_path (TEXT)
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
                    file_path TEXT NOT NULL
                )
            """)
            conn.commit()
            logging.info("Database initialized or already exists.")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

def insert_transcription(user_id: str, message_id: str, transcription: str, file_path: str):
    """
    Inserts a new transcription record into the 'transcriptions' table.
    Automatically generates a timestamp for when the record is inserted.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Use current datetime in ISO format for the timestamp
            current_time = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO transcriptions (user_id, message_id, timestamp, transcription, file_path)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, message_id, current_time, transcription, file_path))
            
            conn.commit()
            logging.info("Inserted transcription into the database.")
    except Exception as e:
        logging.error(f"Error inserting transcription: {e}")