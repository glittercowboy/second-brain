# summaries.py
"""
This module generates summaries of your journal entries.
It includes functions to create daily, weekly, and monthly summaries.
Each summary:
  - Queries the 'transcriptions' table for entries since a given time.
  - Groups entries by exactly four categories: Work, Health, Relationships, and Purpose.
  - Uses GPT‑4 with an enhanced, dynamic prompt to produce a concise, category-specific summary.
  - Saves the summary as a JSON file.

Dependencies:
  - sqlite3, datetime, json, logging (standard library)
  - openai (for GPT‑4 summarization)
  - configparser (to load API keys from config.ini)
"""

import sqlite3
import logging
from datetime import datetime, timedelta
import json
import openai
import configparser

# Define the database file name – ensure it's in the same folder as this script.
DB_NAME = "journal.db"

# Define the allowed categories along with their detailed definitions.
ALLOWED_CATEGORIES = {
    "Work": (
        "Work encompasses your professional and productive activities – whether that's a career, "
        "business, education, or other meaningful work. This includes professional growth, accomplishments, "
        "financial stability, and the skills you develop. It's about how you contribute value and earn your livelihood."
    ),
    "Health": (
        "Health covers both physical and mental wellbeing. This means taking care of your body through exercise, "
        "nutrition, and rest, as well as maintaining emotional and psychological wellness through stress management, "
        "mindfulness, and mental health care. It's the foundation that enables everything else."
    ),
    "Relationships": (
        "Relationships refers to all your human connections – family, friends, romantic partners, and community. "
        "This includes the quality of these relationships, how you nurture them, your social support system, and your "
        "ability to form and maintain meaningful bonds with others."
    ),
    "Purpose": (
        "Purpose represents your sense of meaning and direction in life. This includes your values, beliefs, personal growth, "
        "and the impact you want to have on the world. It's about understanding why you do what you do and feeling that your "
        "life has significance beyond just daily tasks."
    )
}

# -------------------------------------------------------------------
# SECTION: Database Query Functions
# -------------------------------------------------------------------

def query_entries_since(start_time: datetime):
    """
    Queries the 'transcriptions' table for entries with a timestamp later than start_time.
    Returns a list of tuples: (transcription, categories, keywords, timestamp)
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            query = """
                SELECT transcription, categories, keywords, timestamp 
                FROM transcriptions 
                WHERE timestamp >= ?
            """
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
    # Initialize dictionary with empty lists for each allowed category.
    grouped = {category: [] for category in ALLOWED_CATEGORIES.keys()}
    
    for entry in entries:
        transcription, cats, _, _ = entry
        if cats:
            # Split the comma-separated category string and normalize each category.
            entry_categories = [cat.strip().title() for cat in cats.split(",")]
            for cat in entry_categories:
                if cat in ALLOWED_CATEGORIES:
                    grouped[cat].append(transcription)
    return grouped

# -------------------------------------------------------------------
# SECTION: GPT‑4 Summarization with Enhanced Prompt
# -------------------------------------------------------------------

def generate_summary_for_category(category, texts):
    """
    Uses GPT‑4 with an enhanced prompt to generate a summary for the provided list of texts,
    focusing exclusively on details relevant to the specified category.
    Returns the generated summary as a string.
    """
    if not texts:
        return f"No entries for {category}."
    
    # Combine all entries for this category into one text block.
    combined_text = "\n".join(texts)
    
    # Retrieve the detailed definition for the category.
    definition = ALLOWED_CATEGORIES.get(category, "No definition provided.")
    
    # Create a dynamic prompt template that injects the category definition and instructs GPT‑4.
    prompt_text = (
        f"You are a summarization assistant. For the category **{category}**, defined as:\n\n"
        f"{definition}\n\n"
        "Summarize the following diary entries by focusing exclusively on aspects relevant to this category. "
        "Ignore any information pertaining to other categories. Output your response as valid JSON with a single key 'summary'. "
        "Do not include any additional text.\n\n"
        f"Diary entries:\n{combined_text}"
    )
    
    try:
        # Prepare the messages for the ChatCompletion API call.
        messages = [
            {"role": "system", "content": "You are a helpful summarization assistant."},
            {"role": "user", "content": prompt_text}
        ]
        
        # Call the GPT‑4 API.
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.5,
            max_tokens=300
        )
        response_text = response.choices[0].message.content.strip()
        
        # Parse the JSON output from GPT‑4.
        data = json.loads(response_text)
        summary = data.get("summary", "Summary not provided in expected format.")
        return summary
    except Exception as e:
        logging.error(f"Error generating summary for {category}: {e}")
        return "Summary generation failed."

# -------------------------------------------------------------------
# SECTION: Summary Generation Functions (Daily, Weekly, Monthly)
# -------------------------------------------------------------------

def generate_daily_summary():
    """
    Generates a summary for all entries recorded today.
    Returns a dictionary with the allowed categories as keys and summaries as values.
    """
    now = datetime.now()
    # Define the start of today (local time).
    start_time = datetime(now.year, now.month, now.day)
    entries = query_entries_since(start_time)
    grouped = group_entries_by_category(entries)
    
    daily_summary = {}
    for category in ALLOWED_CATEGORIES.keys():
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
    for category in ALLOWED_CATEGORIES.keys():
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
    for category in ALLOWED_CATEGORIES.keys():
        texts = grouped.get(category, [])
        monthly_summary[category] = generate_summary_for_category(category, texts)
    return monthly_summary

# -------------------------------------------------------------------
# SECTION: Utility Function to Save Summary to File
# -------------------------------------------------------------------

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

# -------------------------------------------------------------------
# SECTION: Main (For Testing Purposes)
# -------------------------------------------------------------------

if __name__ == "__main__":
    # Load API key from config.ini.
    config = configparser.ConfigParser()
    config.read("config.ini")
    openai.api_key = config["openai"]["OPENAI_API_KEY"]
    
    # Generate and save a daily summary as an example.
    daily = generate_daily_summary()
    save_summary_to_file(daily, "daily_summary.json")
    logging.info("Daily summary generated.")