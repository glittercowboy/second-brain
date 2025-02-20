# database.py
"""
Phase 5 (Modified): SQLite Database with Multi-Category Support and Chat Conversations
-----------------------------------------------------------------------
This file creates the 'transcriptions' table (if it doesn't exist) and also creates tables for chat conversations:
- chat_conversations: Stores conversation metadata (id, name, created_at, updated_at)
- chat_messages: Stores individual messages (user or assistant) linked to a conversation
It also provides helper functions for database operations.
"""

import sqlite3
import logging
from datetime import datetime

DB_NAME = "journal.db"

def get_db_connection():
    """
    Establishes and returns a new database connection.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    """
    Creates the necessary tables if they do not exist:
    - transcriptions
    - chat_conversations
    - chat_messages
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Existing transcriptions table
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
            # New table: chat_conversations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            # New table: chat_messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER,
                    role TEXT,  -- 'user' or 'assistant'
                    message TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id)
                )
            """)
            conn.commit()
            logging.info("Database initialized with transcriptions and chat tables.")
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
        with get_db_connection() as conn:
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

# -------------------------------
# New functions for chat conversations
# -------------------------------

def create_chat_conversation(name: str) -> int:
    """
    Creates a new chat conversation with the given name.
    Returns the conversation ID.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO chat_conversations (name, created_at, updated_at)
                VALUES (?, ?, ?)
            """, (name, current_time, current_time))
            conn.commit()
            conversation_id = cursor.lastrowid
            logging.info(f"Created new chat conversation with ID: {conversation_id}")
            return conversation_id
    except Exception as e:
        logging.error(f"Error creating chat conversation: {e}")
        return -1

def add_chat_message(conversation_id: int, role: str, message: str):
    """
    Adds a new message to the chat_messages table for a given conversation.
    Role should be 'user' or 'assistant'.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO chat_messages (conversation_id, role, message, timestamp)
                VALUES (?, ?, ?, ?)
            """, (conversation_id, role, message, current_time))
            # Update conversation's updated_at
            cursor.execute("""
                UPDATE chat_conversations
                SET updated_at = ?
                WHERE id = ?
            """, (current_time, conversation_id))
            conn.commit()
            logging.info(f"Added {role} message to conversation {conversation_id}.")
    except Exception as e:
        logging.error(f"Error adding chat message: {e}")

def get_chat_messages(conversation_id: int):
    """
    Retrieves all messages for a given conversation, ordered by timestamp.
    Returns a list of dictionaries.
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, message, timestamp
                FROM chat_messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            """, (conversation_id,))
            messages = [dict(row) for row in cursor.fetchall()]
            return messages
    except Exception as e:
        logging.error(f"Error retrieving chat messages: {e}")
        return []

def get_all_chat_conversations():
    """
    Retrieves all chat conversations.
    Returns a list of dictionaries.
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, created_at, updated_at
                FROM chat_conversations
                ORDER BY updated_at DESC
            """)
            conversations = [dict(row) for row in cursor.fetchall()]
            return conversations
    except Exception as e:
        logging.error(f"Error retrieving chat conversations: {e}")
        return []

def get_chat_conversation(conversation_id: int):
    """
    Retrieves details of a single chat conversation by ID.
    Returns a dictionary or None if not found.
    """
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, created_at, updated_at
                FROM chat_conversations
                WHERE id = ?
            """, (conversation_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            else:
                return None
    except Exception as e:
        logging.error(f"Error retrieving chat conversation: {e}")
        return None