"""
Phase 6: Cloud-Ready Telegram Bot
--------------------------------------------------------------------
- Uses environment variables for configuration
- PostgreSQL database support
- GPT-4 integration
- Multi-category classification
"""

import os
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, 
    CallbackContext, CallbackQueryHandler
)

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
# 2) AUTHORIZATION FUNCTION
# -------------------------------------------------------------------
def is_authorized(user_id: int) -> bool:
    """
    Check if a user is authorized to use the bot.
    """
    authorized_users = os.getenv('AUTHORIZED_USERS', '').split(',')
    return str(user_id) in authorized_users

# -------------------------------------------------------------------
# 3) AUDIO TRANSCRIPTION
# -------------------------------------------------------------------
def transcribe_audio(file_path: str) -> str:
    """
    Transcribe audio file using Whisper
    """
    try:
        model = whisper.load_model("base")
        result = model.transcribe(file_path)
        return result["text"].strip()
    except Exception as e:
        logging.error(f"Error transcribing audio: {e}")
        return None

# -------------------------------------------------------------------
# 4) GPT-4 INTEGRATION
# -------------------------------------------------------------------
def categorize_and_extract(text: str) -> dict:
    """
    Use GPT-4 to categorize and extract key information from text
    """
    try:
        prompt = f"""
        Analyze this journal entry and provide:
        1. The main emotion/mood
        2. Key topics discussed
        3. Any action items or goals mentioned
        4. A brief, empathetic response

        Journal entry: {text}

        Format the response as a JSON with these keys:
        - emotion
        - topics (list)
        - action_items (list)
        - response
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an empathetic AI journaling assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract and parse the JSON response
        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        logging.error(f"Error in GPT-4 processing: {e}")
        return None

# -------------------------------------------------------------------
# 5) TEXT PROCESSING
# -------------------------------------------------------------------
def process_and_save_text(text: str, user_id: str, message_id: str) -> str:
    """Process text with GPT-4 and save to database"""
    try:
        # Get AI analysis
        analysis = categorize_and_extract(text)
        
        if analysis:
            # Save to database
            insert_transcription_with_ai(
                user_id=user_id,
                message_id=message_id,
                text=text,
                ai_analysis=json.dumps(analysis)
            )
            
            # Format response
            response = (
                f"✨ *Entry saved!*\n\n"
                f"*Mood:* {analysis['emotion']}\n"
                f"*Topics:* {', '.join(analysis['topics'])}\n\n"
                f"*Response:* {analysis['response']}\n\n"
                f"*Action Items:*\n" + 
                "\n".join([f"• {item}" for item in analysis['action_items']])
            )
            
            return response
        else:
            return "Sorry, I couldn't analyze that entry properly. But I've saved it!"
            
    except Exception as e:
        logging.error(f"Error processing text: {e}")
        return "Sorry, I couldn't process that message."

# -------------------------------------------------------------------
# 6) COMMAND HANDLER: /start
# -------------------------------------------------------------------
def start(update: Update, context: CallbackContext) -> None:
    if not is_authorized(update.effective_user.id):
        update.message.reply_text("Sorry, you are not authorized to use this bot.")
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
        update.message.reply_text("Sorry, you are not authorized to use this bot.")
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
        update.message.reply_text(response, reply_markup=keyboard, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Error handling text message: {e}")
        update.message.reply_text("Sorry, I couldn't process that message.")

# -------------------------------------------------------------------
# 8) VOICE HANDLER
# -------------------------------------------------------------------
def voice_handler(update: Update, context: CallbackContext) -> None:
    if not is_authorized(update.effective_user.id):
        update.message.reply_text("Sorry, you are not authorized to use this bot.")
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
            update.message.reply_text(response, reply_markup=keyboard, parse_mode='Markdown')
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
        [
            InlineKeyboardButton("📝 New Entry", callback_data='new_entry'),
            InlineKeyboardButton("🎙 Voice Note", callback_data='voice_note')
        ],
        [
            InlineKeyboardButton("📊 Daily Summary", callback_data='daily'),
            InlineKeyboardButton("📈 Weekly Summary", callback_data='weekly')
        ],
        [
            InlineKeyboardButton("📋 Monthly Summary", callback_data='monthly'),
            InlineKeyboardButton("⚙️ Settings", callback_data='settings')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_entry_keyboard():
    """Creates the keyboard shown after an entry is saved."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Daily Summary", callback_data='daily'),
            InlineKeyboardButton("📈 Weekly Summary", callback_data='weekly'),
            InlineKeyboardButton("📋 Monthly", callback_data='monthly')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_summary_keyboard():
    """Creates the keyboard shown with summaries."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data='refresh'),
            InlineKeyboardButton("📝 New Entry", callback_data='new_entry')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# -------------------------------------------------------------------
# 10) SUMMARY HANDLERS
# -------------------------------------------------------------------
def generate_monthly_summary():
    """Generates a monthly summary of journal entries."""
    try:
        # TODO: Implement monthly summary generation
        pass
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
        
        # Get summary based on type
        if summary_type == "daily":
            summary = generate_daily_summary()
        elif summary_type == "weekly":
            summary = generate_weekly_summary()
        else:  # monthly
            summary = generate_monthly_summary()
        
        # Format message
        if "Error" in summary:
            message = f"❌ {summary['Error']}"
        else:
            message = f"*{summary_type.title()} Summary*\n\n"
            
            if "Mood" in summary:
                message += f"*Overall Mood*\n{summary['Mood']}\n\n"
            
            if "Topics" in summary:
                message += "*Key Topics*\n"
                for topic in summary['Topics']:
                    message += f"• {topic}\n"
                message += "\n"
            
            if "Progress" in summary:
                message += f"*Progress*\n{summary['Progress']}\n\n"
            
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
            
    except Exception as e:
        logging.error(f"Error in button handler: {e}")
        query.message.edit_text("❌ Sorry, something went wrong.")

# -------------------------------------------------------------------
# 12) MAIN
# -------------------------------------------------------------------
def main():
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Set the OpenAI API key
    openai.api_key = OPENAI_API_KEY

    if not BOT_TOKEN:
        raise ValueError("Error: BOT_TOKEN not found in environment variables.")
    if not OPENAI_API_KEY:
        raise ValueError("Error: OPENAI_API_KEY not found in environment variables.")

    # Init DB
    initialize_db()

    # Start bot
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))
    dp.add_handler(MessageHandler(Filters.voice, voice_handler))

    updater.start_polling()
    logging.info("Bot is running... Press Ctrl+C to stop.")
    updater.idle()

if __name__ == "__main__":
    main()