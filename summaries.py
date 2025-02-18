# summaries.py
"""
This module generates summaries of your journal entries.
It includes functions to create daily, weekly, and monthly summaries.
Each summary:
  - Queries the 'transcriptions' table for entries since a given time.
  - Groups entries by exactly four categories: Work, Health, Relationships, and Purpose.
  - Uses GPT‑4 to produce a concise summary for each category.
  - Saves the summary as a JSON file.

Dependencies:
  - sqlite3, datetime, json, logging (standard library)
  - openai (for GPT‑4 summarization)
  - configparser (to load API keys from config.ini)

Before running, ensure that:
  - Your journal.db exists and has entries.
  - Your config.ini includes your OPENAI_API_KEY.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import json
import openai
import configparser

# Database file name – make sure it's in the same folder as this script.
DB_NAME = "journal.db"

# Define the only allowed categories.
ALLOWED_CATEGORIES = {"Work", "Health", "Relationships", "Purpose"}

def query_entries_since(start_time: datetime):
    """
    Queries the 'transcriptions' table for entries with a timestamp later than start_time.
    Returns a list of tuples: (transcription, categories, keywords, timestamp)
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            query = "SELECT transcription, categories, keywords, timestamp FROM transcriptions WHERE timestamp >= ?"
            cursor.execute(query, (start_time.isoformat(),))
            rows = cursor.fetchall()
            return rows
    except Exception as e:
        logging.error(f"Error querying entries: {e}")
        return []

def group_entries_by_category(entries):
    """
    Groups entries into exactly the allowed categories: Work, Health, Relationships, and Purpose.
    Each entry’s categories are normalized to title case.
    Returns a dictionary mapping each allowed category to a list of transcription texts.
    """
    # Initialize dictionary with empty lists for the allowed categories
    grouped = {category: [] for category in ALLOWED_CATEGORIES}
    
    for entry in entries:
        transcription, cats, _, _ = entry
        if cats:
            # Split the comma-separated category string and normalize each category.
            entry_categories = [cat.strip().title() for cat in cats.split(",")]
            for cat in entry_categories:
                if cat in ALLOWED_CATEGORIES:
                    grouped[cat].append(transcription)
    return grouped

def generate_summary_for_category(category, texts):
    """
    Uses GPT‑4 to generate a summary for the provided list of texts.
    Returns the generated summary as a string.
    """
    if not texts:
        return f"No entries for {category}."
    
    # Combine all entries for this category into one text block.
    combined_text = "\n".join(texts)
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an assistant that summarizes personal diary entries. "
                    "Generate a concise summary highlighting key events, emotions, and recurring themes."
                )
            },
            {
                "role": "user",
                "content": f"Summarize the following diary entries for the category '{category}':\n\n{combined_text}"
            }
        ]
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.5,
            max_tokens=300
        )
        summary = response.choices[0].message.content.strip()
        return summary
    except Exception as e:
        logging.error(f"Error generating summary for {category}: {e}")
        return "Summary generation failed."

def generate_daily_summary():
    """
    Generates a summary for all entries recorded today.
    Returns a dictionary with the allowed categories as keys and summaries as values.
    """
    now = datetime.now()
    # Start of today (local time)
    start_time = datetime(now.year, now.month, now.day)
    entries = query_entries_since(start_time)
    grouped = group_entries_by_category(entries)
    
    daily_summary = {}
    for category in ALLOWED_CATEGORIES:
        texts = grouped.get(category, [])
        daily_summary[category] = generate_summary_for_category(category, texts)
    return daily_summary

def generate_weekly_summary():
    """
    Generates a summary for entries from the past 7 days.
    Returns a dictionary with the allowed categories as keys and summaries as values.
    """
    now = datetime.now()
    start_time = now - timedelta(days=7)
    entries = query_entries_since(start_time)
    grouped = group_entries_by_category(entries)
    
    weekly_summary = {}
    for category in ALLOWED_CATEGORIES:
        texts = grouped.get(category, [])
        weekly_summary[category] = generate_summary_for_category(category, texts)
    return weekly_summary

def generate_monthly_summary():
    """
    Generates a summary for entries from the past 30 days.
    Returns a dictionary with the allowed categories as keys and summaries as values.
    """
    now = datetime.now()
    start_time = now - timedelta(days=30)
    entries = query_entries_since(start_time)
    grouped = group_entries_by_category(entries)
    
    monthly_summary = {}
    for category in ALLOWED_CATEGORIES:
        texts = grouped.get(category, [])
        monthly_summary[category] = generate_summary_for_category(category, texts)
    return monthly_summary

def save_summary_to_file(summary, filename):
    """
    Saves the given summary dictionary to a JSON file.
    """
    try:
        with open(filename, "w") as f:
            json.dump(summary, f, indent=4)
        logging.info(f"Summary saved to {filename}")
    except Exception as e:
        logging.error(f"Error saving summary to file: {e}")

# For testing purposes, you can run this module directly.
if __name__ == "__main__":
    # Load API key from config.ini
    config = configparser.ConfigParser()
    config.read("config.ini")
    openai.api_key = config["openai"]["OPENAI_API_KEY"]
    
    # Generate and save a daily summary as an example.
    daily = generate_daily_summary()
    save_summary_to_file(daily, "daily_summary.json")
    logging.info("Daily summary generated.")