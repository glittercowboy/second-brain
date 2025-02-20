"""
Phase 6: PostgreSQL Database with Multi-Category Support and Chat Conversations
-----------------------------------------------------------------------
This file now uses PostgreSQL instead of SQLite for better cloud support.
It maintains the same functionality but with improved scalability.
"""

import logging
from datetime import datetime
import os

import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """
    Establishes and returns a new PostgreSQL database connection.
    Uses environment variables for configuration.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            database=os.getenv('POSTGRES_DATABASE', 'postgres'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', ''),
            port=os.getenv('POSTGRES_PORT', '5432')
        )
        return conn
    except Exception as e:
        logging.error(f"Error connecting to PostgreSQL database: {e}")
        raise

def initialize_db():
    """
    Creates the necessary tables if they do not exist
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Existing transcriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    message_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    transcription TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    categories TEXT,
                    keywords TEXT
                )
            """)
            # Chat conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_conversations (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            # Chat messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id INTEGER REFERENCES chat_conversations(id),
                    role TEXT,
                    message TEXT,
                    timestamp TIMESTAMP
                )
            """)
            conn.commit()
            logging.info("PostgreSQL database initialized with all tables.")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
        raise

def insert_transcription_with_ai(user_id: str, message_id: str,
                               transcription: str, file_path: str,
                               categories: str, keywords: str):
    """
    Inserts a new transcription record into 'transcriptions'
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = datetime.now()
            cursor.execute("""
                INSERT INTO transcriptions (
                    user_id, message_id, timestamp, transcription, file_path, categories, keywords
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (user_id, message_id, current_time, transcription, file_path, categories, keywords))
            conn.commit()
            logging.info("Inserted transcription + AI data into PostgreSQL DB.")
    except Exception as e:
        logging.error(f"Error inserting transcription: {e}")
        raise

def create_chat_conversation(name: str) -> int:
    """
    Creates a new chat conversation with the given name.
    Returns the conversation ID.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = datetime.now()
            cursor.execute("""
                INSERT INTO chat_conversations (name, created_at, updated_at)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (name, current_time, current_time))
            conversation_id = cursor.fetchone()[0]
            conn.commit()
            logging.info(f"Created new chat conversation with ID: {conversation_id}")
            return conversation_id
    except Exception as e:
        logging.error(f"Error creating chat conversation: {e}")
        return -1

def add_chat_message(conversation_id: int, role: str, message: str):
    """
    Adds a new message to the chat_messages table
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            current_time = datetime.now()
            cursor.execute("""
                INSERT INTO chat_messages (conversation_id, role, message, timestamp)
                VALUES (%s, %s, %s, %s)
            """, (conversation_id, role, message, current_time))
            
            cursor.execute("""
                UPDATE chat_conversations
                SET updated_at = %s
                WHERE id = %s
            """, (current_time, conversation_id))
            conn.commit()
            logging.info(f"Added {role} message to conversation {conversation_id}")
    except Exception as e:
        logging.error(f"Error adding chat message: {e}")
        raise

def get_chat_messages(conversation_id: int):
    """
    Retrieves all messages for a given conversation
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT role, message, timestamp
                FROM chat_messages
                WHERE conversation_id = %s
                ORDER BY timestamp ASC
            """, (conversation_id,))
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error retrieving chat messages: {e}")
        return []

def get_all_chat_conversations():
    """
    Retrieves all chat conversations
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT id, name, created_at, updated_at
                FROM chat_conversations
                ORDER BY updated_at DESC
            """)
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error retrieving chat conversations: {e}")
        return []

def get_chat_conversation(conversation_id: int):
    """
    Retrieves details of a single chat conversation
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT id, name, created_at, updated_at
                FROM chat_conversations
                WHERE id = %s
            """, (conversation_id,))
            return cursor.fetchone()
    except Exception as e:
        logging.error(f"Error retrieving chat conversation: {e}")
        return None