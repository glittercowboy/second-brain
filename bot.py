# bot.py
"""
Phase 5 (Modified for GPT-4 + Extended Prompts + Larger Max Tokens):
--------------------------------------------------------------------
- Uses GPT-4 via ChatCompletion
- Larger max_tokens (1000)
- Multi-category classification (Work, Health, Relationships, Purpose)
- More specific instructions for categorization and keyword extraction
- Outputs in JSON only
- Deletes local .ogg file after processing
"""

import os
import logging
import json
import configparser
from datetime import datetime

# Telegram imports
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Whisper import
import whisper

# Database imports
from database import initialize_db, insert_transcription_with_ai

# OpenAI
import openai

# -------------------------------------------------------------------
# 1) LOGGING CONFIG
# -------------------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# -------------------------------------------------------------------
# 2) TRANSCRIBE AUDIO FUNCTION
# -------------------------------------------------------------------
def transcribe_audio(file_path: str) -> str:
    """
    Transcribes the given audio file using Whisper.
    Returns the transcribed text, or None if there's an error.
    """
    try:
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        return result["text"].strip()
    except Exception as e:
        logging.error(f"Error transcribing audio: {e}")
        return None

# -------------------------------------------------------------------
# 3) AI CATEGORIZE & EXTRACT (MULTIPLE CATEGORIES) WITH GPT-4
# -------------------------------------------------------------------
def categorize_and_extract(text: str) -> (str, str):
    """
    Sends 'text' to GPT-4 to:
      1) Possibly assign multiple categories from: Work, Health, Relationships, Purpose
      2) Extract the most relevant keywords
    Returns (comma-separated categories, comma-separated keywords).
    """
    try:
        # The prompt merges your categorization & keyword instructions into one.
        # We request JSON only, to parse easily.
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a classifier that categorizes diary entries into four possible buckets: "
                    "Work, Health, Relationships, and Purpose. Then you also extract the most relevant keywords. "
                    "Return your answer in valid JSON ONLY, with the format:\n\n"
                    "{\n"
                    '  "categories": ["Work", "Health"],\n'
                    '  "keywords": ["Keyword1", "Keyword2"]\n'
                    "}\n\n"
                    "No extra text or punctuation beyond valid JSON."
                )
            },
            {
                "role": "user",
                "content": f"""
Text:
\"\"\"{text}\"\"\"

Categorization Instructions:
- You can output any subset of [Work, Health, Relationships, Purpose].
- If multiple categories apply, list them all, exactly matching those category names.
- Do not explain your reasoning or add extra text.

Keyword Extraction Instructions:
- Extract the most relevant keywords from this personal journal entry.
- Focus on meaningful themes, emotions, and concepts.
- Avoid generic or filler words.
- Output them capitalized, separated by commas in JSON array form.

Return JSON ONLY, e.g.:
{{
  "categories": ["Work", "Health"],
  "keywords": ["Stress", "Deadlines", "Project"]
}}
                """
            }
        ]

        response = openai.ChatCompletion.create(
            model="gpt-4",            # Use GPT-4
            messages=messages,
            temperature=0.3,
            max_tokens=1000          # Increased token limit
        )

        # Extract the response text
        raw_text = response.choices[0].message.content.strip()

        # Parse JSON
        data = json.loads(raw_text)

        # Convert arrays to comma-separated strings
        cat_list = data.get("categories", [])
        categories_str = ", ".join([c.strip() for c in cat_list])

        kw_list = data.get("keywords", [])
        keywords_str = ", ".join([k.strip() for k in kw_list])

        return (categories_str, keywords_str)
    except Exception as e:
        logging.error(f"Error in categorize_and_extract: {e}")
        return ("", "")

# -------------------------------------------------------------------
# 4) COMMAND HANDLER: /start
# -------------------------------------------------------------------
def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "Hello, I'm your AI Journaling Bot!\n"
        "Send me a voice note and I'll transcribe it, categorize it, and extract keywords using ``GPT-4``."
    )
    update.message.reply_text(welcome_message)

# -------------------------------------------------------------------
# 5) VOICE HANDLER
# -------------------------------------------------------------------
def voice_handler(update: Update, context: CallbackContext) -> None:
    """
    - Downloads the voice file
    - Transcribes with Whisper
    - Calls categorize_and_extract for multi-categories + keywords (GPT-4)
    - Inserts into SQLite
    - Deletes local file
    """
    try:
        # 5.1) Download
        voice_file = update.message.voice.get_file()
        file_path = f"voice_{update.message.from_user.id}_{update.message.message_id}.ogg"
        voice_file.download(file_path)
        logging.info(f"Voice note saved locally as: {file_path}")

        # 5.2) Transcribe
        transcribed_text = transcribe_audio(file_path)
        if transcribed_text:
            # 5.3) Categorize & Extract
            categories_str, keywords_str = categorize_and_extract(transcribed_text)

            # 5.4) Reply
            response = (
                "Voice note received!\n\n"
                f"**Transcription**:\n{transcribed_text}\n\n"
                f"**Categories**: {categories_str}\n"
                f"**Keywords**: {keywords_str}"
            )
            update.message.reply_text(response)

            # 5.5) Insert into DB
            insert_transcription_with_ai(
                user_id=str(update.message.from_user.id),
                message_id=str(update.message.message_id),
                transcription=transcribed_text,
                file_path=file_path,
                categories=categories_str,
                keywords=keywords_str
            )
        else:
            update.message.reply_text("Voice note saved, but I couldn't transcribe it.")

        # 5.6) Delete file
        try:
            os.remove(file_path)
            logging.info(f"Deleted local file: {file_path}")
        except Exception as e:
            logging.error(f"Could not delete file: {file_path} - {e}")

    except Exception as e:
        logging.error(f"Error handling voice note: {e}")
        update.message.reply_text("Sorry, I couldn't process that voice note.")

# -------------------------------------------------------------------
# 6) MAIN
# -------------------------------------------------------------------
def main():
    config = configparser.ConfigParser()
    config.read("config.ini")
    BOT_TOKEN = config["telegram"]["BOT_TOKEN"]
    OPENAI_API_KEY = config["openai"]["OPENAI_API_KEY"]

    # Set the OpenAI API key
    openai.api_key = OPENAI_API_KEY

    if not BOT_TOKEN:
        raise ValueError("Error: BOT_TOKEN not found in config.ini.")
    if not OPENAI_API_KEY:
        raise ValueError("Error: OPENAI_API_KEY not found in config.ini.")

    # Init DB
    initialize_db()

    # Start bot
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.voice, voice_handler))

    updater.start_polling()
    logging.info("Bot is running... Press Ctrl+C to stop.")
    updater.idle()

if __name__ == "__main__":
    main()