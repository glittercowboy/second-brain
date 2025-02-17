# bot.py
"""
Phase 5 (Modified): Telegram Bot + Whisper + SQLite + Multi-Category
-------------------------------------------------------------------
- Uses OPENAI_API_KEY from environment variable
- Allows multiple categories (health, work, purpose, relationships)
- Stores categories as a comma-separated string in SQLite
- Still deletes local .ogg file after processing
"""

import os
import logging
import json

import configparser  # only if you still use config for other stuff; otherwise remove
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
    try:
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        return result["text"].strip()
    except Exception as e:
        logging.error(f"Error transcribing audio: {e}")
        return None

# -------------------------------------------------------------------
# 3) AI CATEGORIZE & EXTRACT (MULTIPLE CATEGORIES)
# -------------------------------------------------------------------
def categorize_and_extract(text: str) -> (str, str):
    """
    Sends 'text' to OpenAI to:
      1) Possibly assign multiple categories from: health, work, purpose, relationships
      2) Extract keywords
    Returns (comma-separated categories, comma-separated keywords).
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful assistant that categorizes text and extracts keywords."
                },
                {
                    "role": "user", 
                    "content": f"""
                    Analyze this text:
                    \"\"\"{text}\"\"\"

                    1) Categorize it into any subset of [health, work, purpose, relationships].
                       For example, if it touches on both work and health, list both.
                    2) Extract a few relevant keywords.

                    Respond ONLY with a valid JSON in this format:
                    {{
                      "categories": ["...","..."],
                      "keywords": ["...","..."]
                    }}
                    """
                }
            ],
            temperature=0.3,
            max_tokens=150
        )

        # Extract the response text
        raw_text = response.choices[0].message.content.strip()
        data = json.loads(raw_text)

        # Convert arrays to comma-separated strings
        cat_list = data.get("categories", [])
        categories_str = ", ".join([c.strip().lower() for c in cat_list])

        kw_list = data.get("keywords", [])
        keywords_str = ", ".join([k.strip().lower() for k in kw_list])

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
        "Send me a voice note and I'll transcribe it with multiple possible categories."
    )
    update.message.reply_text(welcome_message)

# -------------------------------------------------------------------
# 5) VOICE HANDLER
# -------------------------------------------------------------------
def voice_handler(update: Update, context: CallbackContext) -> None:
    """
    - Downloads the voice file
    - Transcribes with Whisper
    - Calls categorize_and_extract for multi-categories + keywords
    - Inserts into SQLite
    - Deletes local file
    """
    try:
        # Download
        voice_file = update.message.voice.get_file()
        file_path = f"voice_{update.message.from_user.id}_{update.message.message_id}.ogg"
        voice_file.download(file_path)
        logging.info(f"Voice note saved locally as: {file_path}")

        # Transcribe
        transcribed_text = transcribe_audio(file_path)
        if transcribed_text:
            # Categorize & Extract
            categories_str, keywords_str = categorize_and_extract(transcribed_text)

            # Reply
            response = (
                "Voice note received!\n\n"
                f"**Transcription**:\n{transcribed_text}\n\n"
                f"**Categories**: {categories_str}\n"
                f"**Keywords**: {keywords_str}"
            )
            update.message.reply_text(response)

            # Insert into DB
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

        # Delete file
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
    # If you still need config.ini for Telegram token, keep this block;
    # otherwise you can remove config usage entirely.
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