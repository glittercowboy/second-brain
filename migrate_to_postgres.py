import sqlite3
import psycopg2
import configparser
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

def get_postgres_connection():
    config = configparser.ConfigParser()
    config.read('database_config.ini')
    
    return psycopg2.connect(
        host=config['PostgreSQL']['host'],
        database=config['PostgreSQL']['database'],
        user=config['PostgreSQL']['user'],
        password=config['PostgreSQL']['password'],
        port=config['PostgreSQL']['port']
    )

def migrate_data():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('journal.db')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Connect to PostgreSQL
    pg_conn = get_postgres_connection()
    pg_cur = pg_conn.cursor()

    try:
        # Migrate transcriptions
        logging.info("Migrating transcriptions...")
        sqlite_cur.execute("SELECT * FROM transcriptions")
        rows = sqlite_cur.fetchall()
        
        for row in rows:
            pg_cur.execute("""
                INSERT INTO transcriptions (
                    user_id, message_id, timestamp, transcription, 
                    file_path, categories, keywords
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                row['user_id'], 
                row['message_id'],
                row['timestamp'],
                row['transcription'],
                row['file_path'],
                row['categories'],
                row['keywords']
            ))

        # Migrate chat_conversations
        logging.info("Migrating chat conversations...")
        sqlite_cur.execute("SELECT * FROM chat_conversations")
        rows = sqlite_cur.fetchall()
        
        for row in rows:
            pg_cur.execute("""
                INSERT INTO chat_conversations (
                    id, name, created_at, updated_at
                ) VALUES (%s, %s, %s, %s)
            """, (
                row['id'],
                row['name'],
                row['created_at'],
                row['updated_at']
            ))

        # Migrate chat_messages
        logging.info("Migrating chat messages...")
        sqlite_cur.execute("SELECT * FROM chat_messages")
        rows = sqlite_cur.fetchall()
        
        for row in rows:
            pg_cur.execute("""
                INSERT INTO chat_messages (
                    conversation_id, role, message, timestamp
                ) VALUES (%s, %s, %s, %s)
            """, (
                row['conversation_id'],
                row['role'],
                row['message'],
                row['timestamp']
            ))

        # Commit the transaction
        pg_conn.commit()
        logging.info("Migration completed successfully!")

    except Exception as e:
        pg_conn.rollback()
        logging.error(f"Error during migration: {e}")
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    migrate_data()
