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
import sqlite3
from dateutil.relativedelta import relativedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, 
    CallbackContext, CallbackQueryHandler
)

# Whisper import
import whisper

# Database imports
from database import initialize_db, insert_transcription_with_ai #delete_last_entry, generate_daily_summary, generate_weekly_summary

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
# 2) AUTHORIZATION FUNCTION
# -------------------------------------------------------------------
def is_authorized(user_id: int) -> bool:
    """
    Check if a user is authorized to use the bot.
    """
    config = configparser.ConfigParser()
    config.read('config.ini')
    authorized_users = json.loads(config.get('Auth', 'authorized_users', fallback='[]'))
    return str(user_id) in authorized_users

# -------------------------------------------------------------------
# 3) TRANSCRIBE AUDIO FUNCTION
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
# 4) AI CATEGORIZE & EXTRACT (MULTIPLE CATEGORIES) WITH GPT-4
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
# 5) PROCESS TEXT AND SAVE TO DB
# -------------------------------------------------------------------
def process_and_save_text(text: str, user_id: str, message_id: str) -> str:
    """
    Common function to process text input (from voice or direct text):
    1. Categorize and extract keywords
    2. Save to database
    3. Return formatted response
    """
    try:
        # 1) Categorize & Extract
        categories_str, keywords_str = categorize_and_extract(text)

        # 2) Save to DB
        insert_transcription_with_ai(
            user_id=user_id,
            message_id=message_id,
            transcription=text,
            file_path="text_input",  # For text messages, no file path needed
            categories=categories_str,
            keywords=keywords_str
        )

        # 3) Format response
        response = (
            "Message received and processed!\n\n"
            f"**Text**:\n{text}\n\n"
            f"**Categories**: {categories_str}\n"
            f"**Keywords**: {keywords_str}"
        )
        return response

    except Exception as e:
        logging.error(f"Error processing text: {e}")
        return "Sorry, I couldn't process that message."

# -------------------------------------------------------------------
# 6) COMMAND HANDLER: /start
# -------------------------------------------------------------------
def start(update: Update, context: CallbackContext) -> None:
    if not is_authorized(update.effective_user.id):
        update.message.reply_text("Sorry, you are not authorized to use this bot. Please contact the bot owner.")
        return
    
    welcome_message = (
        "Hello, I'm your AI Journaling Bot!\n"
        "You can:\n"
        "1. Send me a voice note\n"
        "2. Type your journal entry directly\n\n"
        "I'll analyze it using GPT-4 and save it to your journal."
    )
    keyboard = get_start_keyboard()
    update.message.reply_text(welcome_message, reply_markup=keyboard)

# -------------------------------------------------------------------
# 7) TEXT MESSAGE HANDLER
# -------------------------------------------------------------------
def text_handler(update: Update, context: CallbackContext) -> None:
    if not is_authorized(update.effective_user.id):
        update.message.reply_text("Sorry, you are not authorized to use this bot. Please contact the bot owner.")
        return
        
    try:
        text = update.message.text.strip()
        
        # Skip empty messages or commands
        if not text or text.startswith('/'):
            return
            
        # Process the text and get response
        response = process_and_save_text(
            text=text,
            user_id=str(update.message.from_user.id),
            message_id=str(update.message.message_id)
        )
        
        keyboard = get_entry_keyboard()
        update.message.reply_text(response, reply_markup=keyboard)
        
    except Exception as e:
        logging.error(f"Error handling text message: {e}")
        update.message.reply_text("Sorry, I couldn't process that message.")

# -------------------------------------------------------------------
# 8) VOICE HANDLER
# -------------------------------------------------------------------
def voice_handler(update: Update, context: CallbackContext) -> None:
    if not is_authorized(update.effective_user.id):
        update.message.reply_text("Sorry, you are not authorized to use this bot. Please contact the bot owner.")
        return

    try:
        # 7.1) Download
        voice_file = update.message.voice.get_file()
        file_path = f"voice_{update.message.from_user.id}_{update.message.message_id}.ogg"
        voice_file.download(file_path)
        logging.info(f"Voice note saved locally as: {file_path}")

        # 7.2) Transcribe
        transcribed_text = transcribe_audio(file_path)
        if transcribed_text:
            # 7.3) Process text and get response
            response = process_and_save_text(
                text=transcribed_text,
                user_id=str(update.message.from_user.id),
                message_id=str(update.message.message_id)
            )
            keyboard = get_entry_keyboard()
            update.message.reply_text(response, reply_markup=keyboard)
        else:
            update.message.reply_text("Voice note saved, but I couldn't transcribe it.")

        # 7.4) Delete file
        try:
            os.remove(file_path)
            logging.info(f"Deleted local file: {file_path}")
        except Exception as e:
            logging.error(f"Could not delete file: {file_path} - {e}")

    except Exception as e:
        logging.error(f"Error handling voice note: {e}")
        update.message.reply_text("Sorry, I couldn't process that voice note.")

# -------------------------------------------------------------------
# 9) KEYBOARD MARKUP HELPERS
# -------------------------------------------------------------------
def get_start_keyboard():
    """Creates the main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("📊 Summaries", callback_data='view_summaries')],
        [
            InlineKeyboardButton("📅 Daily", callback_data='summary_daily'),
            InlineKeyboardButton("📈 Weekly", callback_data='summary_weekly'),
            InlineKeyboardButton("📋 Monthly", callback_data='summary_monthly')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_entry_keyboard():
    """Creates the keyboard shown after a new entry."""
    keyboard = [
        [
            InlineKeyboardButton("❌ Delete Entry", callback_data='delete_last'),
            InlineKeyboardButton("📊 View Summaries", callback_data='view_summaries')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard():
    """Creates a confirmation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, delete it", callback_data='confirm_delete'),
            InlineKeyboardButton("❌ No, keep it", callback_data='cancel_delete')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_summary_keyboard():
    """Creates the summary selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("📊 Summaries", callback_data='view_summaries')],
        [
            InlineKeyboardButton("📅 Daily", callback_data='summary_daily'),
            InlineKeyboardButton("📈 Weekly", callback_data='summary_weekly'),
            InlineKeyboardButton("📋 Monthly", callback_data='summary_monthly')
        ],
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data='start')]
    ]
    return InlineKeyboardMarkup(keyboard)

# -------------------------------------------------------------------
# 10) SUMMARY HANDLERS
# -------------------------------------------------------------------
def generate_monthly_summary():
    """Generates a monthly summary of journal entries."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            
            # Get entries from the last 30 days
            thirty_days_ago = (datetime.now() - relativedelta(months=1)).isoformat()
            cursor.execute("""
                SELECT categories, transcription, timestamp 
                FROM transcriptions 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            """, (thirty_days_ago,))
            
            entries = cursor.fetchall()
            if not entries:
                return {"No Entries": "No journal entries found in the last 30 days."}
            
            # Group entries by category
            summary = {}
            for entry in entries:
                categories = entry[0].split(", ") if entry[0] else ["Uncategorized"]
                entry_date = datetime.fromisoformat(entry[2]).strftime("%Y-%m-%d")
                entry_preview = entry[1][:100] + "..." if len(entry[1]) > 100 else entry[1]
                
                for category in categories:
                    if category not in summary:
                        summary[category] = []
                    summary[category].append(f"• {entry_date}: {entry_preview}")
            
            # Format each category's entries
            formatted_summary = {}
            for category, entries in summary.items():
                formatted_summary[category] = "\n".join(entries[-5:])  # Show last 5 entries per category
            
            return formatted_summary
            
    except Exception as e:
        logging.error(f"Error generating monthly summary: {e}")
        return {"Error": "Could not generate monthly summary."}

def send_summary(update: Update, context: CallbackContext, summary_type: str):
    """Sends a summary (daily, weekly, or monthly) with proper formatting."""
    try:
        # Send loading message
        if hasattr(update, 'callback_query'):
            loading_message = update.callback_query.message.reply_text(
                f"🔄 Analyzing your {summary_type} journal entries... This may take a minute."
            )
        else:
            loading_message = update.message.reply_text(
                f"🔄 Analyzing your {summary_type} journal entries... This may take a minute."
            )
        
        # Generate appropriate summary
        if summary_type == 'daily':
            summary = generate_daily_summary()
            title = "📅 *Your Day in Review*"
        elif summary_type == 'weekly':
            summary = generate_weekly_summary()
            title = "📈 *Your Week in Review*"
        else:  # monthly
            summary = generate_monthly_summary()
            title = "📋 *Your Month in Review*"
        
        # Format the summary as a nice message
        message = f"{title}\n\n"
        
        if "Error" in summary:
            message = f"❌ {summary['Error']}"
            if "Details" in summary:
                logging.error(f"GPT Analysis Error: {summary['Details']}")
        else:
            # Add overview
            if "Overview" in summary:
                message += f"*Overview*\n{summary['Overview']}\n\n"
            
            # Add themes
            if "Themes" in summary:
                message += f"*Key Themes*\n{summary['Themes']}\n\n"
            
            # Add category analysis
            if "Categories" in summary:
                message += "*Category Analysis*\n"
                for category, analysis in summary["Categories"].items():
                    message += f"*{category}*\n{analysis}\n\n"
            
            # Add insights
            if "Insights" in summary:
                message += f"*Insights & Suggestions*\n{summary['Insights']}"
        
        # Delete loading message
        loading_message.delete()
        
        # Send with summary keyboard
        keyboard = get_summary_keyboard()
        if hasattr(update, 'callback_query'):
            update.callback_query.message.edit_text(
                message, 
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
    except Exception as e:
        logging.error(f"Error generating {summary_type} summary: {e}")
        error_msg = f"Sorry, I couldn't generate the {summary_type} summary. Please try again later."
        if hasattr(update, 'callback_query'):
            update.callback_query.message.edit_text(
                error_msg,
                reply_markup=get_summary_keyboard()
            )
        else:
            update.message.reply_text(error_msg)

# -------------------------------------------------------------------
# 11) CALLBACK QUERY HANDLER
# -------------------------------------------------------------------
def handle_button(update: Update, context: CallbackContext) -> None:
    """Handles callback queries from inline keyboard buttons."""
    query = update.callback_query
    query.answer()  # Acknowledge the button press to Telegram
    
    try:
        if query.data == 'start':
            # Show start menu
            welcome_message = (
                "Hello, I'm your AI Journaling Bot!\n"
                "You can:\n"
                "1. Send me a voice note\n"
                "2. Type your journal entry directly\n\n"
                "I'll analyze it using GPT-4 and save it to your journal."
            )
            keyboard = get_start_keyboard()
            query.message.edit_text(welcome_message, reply_markup=keyboard)
            
        elif query.data == 'delete_last':
            # Show delete confirmation
            message = "❗ Are you sure you want to delete your last entry? This cannot be undone."
            keyboard = get_confirmation_keyboard()
            query.message.edit_text(message, reply_markup=keyboard)
            
        elif query.data == 'confirm_delete':
            # Actually delete the entry
            success, message = delete_last_entry(str(query.from_user.id))
            if success:
                keyboard = get_start_keyboard()
                query.message.edit_text(f"✅ {message}", reply_markup=keyboard)
            else:
                keyboard = get_start_keyboard()
                query.message.edit_text(f"❌ {message}", reply_markup=keyboard)
                
        elif query.data == 'cancel_delete':
            # Cancel deletion
            keyboard = get_start_keyboard()
            query.message.edit_text("✅ Entry kept safe!", reply_markup=keyboard)
            
        elif query.data == 'view_summaries':
            # Show summary options
            message = "📊 Choose a summary type:"
            keyboard = get_summary_keyboard()
            query.message.edit_text(message, reply_markup=keyboard)
            
        elif query.data.startswith('summary_'):
            # Generate and show appropriate summary
            summary_type = query.data.split('_')[1]  # daily, weekly, or monthly
            send_summary(update, context, summary_type)
            
    except Exception as e:
        logging.error(f"Error handling button press: {e}")
        query.message.edit_text(
            "Sorry, something went wrong. Please try again.",
            reply_markup=get_start_keyboard()
        )

# -------------------------------------------------------------------
# 12) MAIN
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

    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("daily", lambda u, c: send_summary(u, c, 'daily')))
    dp.add_handler(CommandHandler("weekly", lambda u, c: send_summary(u, c, 'weekly')))
    dp.add_handler(CommandHandler("monthly", lambda u, c: send_summary(u, c, 'monthly')))
    dp.add_handler(CommandHandler("delete_last", lambda u, c: handle_button(u._get_callback(), c)))
    dp.add_handler(CallbackQueryHandler(handle_button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))
    dp.add_handler(MessageHandler(Filters.voice, voice_handler))

    updater.start_polling()
    logging.info("Bot is running... Press Ctrl+C to stop.")
    updater.idle()

if __name__ == "__main__":
    main()