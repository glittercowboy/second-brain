# bot.py
"""
Phase 4: Telegram Bot + Whisper Transcription + SQLite
------------------------------------------------------
This script connects to the Telegram Bot API, listens for voice messages,
saves them locally, transcribes them using Whisper, and stores the
transcriptions in an SQLite database.
"""

import os
import logging
import configparser

# Telegram imports
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Whisper import
import whisper

# Database imports (our new file)
from database import initialize_db, insert_transcription

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
    Uses Whisper to transcribe the given audio file.
    Returns the transcribed text or None if an error occurs.
    """
    try:
        # Load the Whisper model (tiny, base, small, medium, large)
        model = whisper.load_model("base")
        
        # Transcribe the audio
        result = model.transcribe(file_path)
        
        # Extract the text from the result dictionary
        transcribed_text = result["text"]
        
        # Return the cleaned-up text
        return transcribed_text.strip()
    except Exception as e:
        logging.error(f"Error transcribing audio: {e}")
        return None

# -------------------------------------------------------------------
# 3) COMMAND HANDLER: /start
# -------------------------------------------------------------------
def start(update: Update, context: CallbackContext) -> None:
    welcome_message = (
        "Hello, I'm your AI Journaling Bot!\n"
        "Send me a voice note and I'll transcribe it for you."
    )
    update.message.reply_text(welcome_message)

# -------------------------------------------------------------------
# 4) VOICE MESSAGE HANDLER
# -------------------------------------------------------------------
def voice_handler(update: Update, context: CallbackContext) -> None:
    """
    Handler for voice messages.
    Downloads the voice file, saves it locally, transcribes it,
    inserts the transcription into the SQLite database,
    and then deletes the local file.
    """
    try:
        # 1) Download the voice note
        voice_file = update.message.voice.get_file()
        
        # Construct a unique filename based on user ID and message ID
        file_path = f"voice_{update.message.from_user.id}_{update.message.message_id}.ogg"
        
        voice_file.download(file_path)
        logging.info(f"Voice note saved locally as: {file_path}")

        # 2) Transcribe the audio
        transcribed_text = transcribe_audio(file_path)
        
        if transcribed_text:
            # 3) Reply with the transcribed text
            response = (
                "Voice note received and saved locally!\n\n"
                f"**Transcription**:\n{transcribed_text}"
            )
            update.message.reply_text(response)
            logging.info(f"Transcription: {transcribed_text}")
            
            # 4) Insert into database
            insert_transcription(
                user_id=str(update.message.from_user.id),
                message_id=str(update.message.message_id),
                transcription=transcribed_text,
                file_path=file_path
            )
        else:
            update.message.reply_text("Voice note saved, but I couldn't transcribe it.")

        # 5) Delete the local file after transcription attempt
        import os
        try:
            os.remove(file_path)
            logging.info(f"Deleted local file: {file_path}")
        except Exception as e:
            logging.error(f"Could not delete file: {file_path} - {e}")
            
    except Exception as e:
        logging.error(f"Error handling voice note: {e}")
        update.message.reply_text("Sorry, I couldn't process that voice note.")
# -------------------------------------------------------------------
# 5) MAIN FUNCTION
# -------------------------------------------------------------------
def main():
    """
    Main function to start the bot.
    Reads the token from config.ini, initializes the database,
    and starts polling for messages.
    """
    # 5.1) Read bot token from config.ini
    config = configparser.ConfigParser()
    config.read("config.ini")
    BOT_TOKEN = config["telegram"]["BOT_TOKEN"]

    if not BOT_TOKEN:
        raise ValueError("Error: BOT_TOKEN not found in config.ini.")

    # 5.2) Initialize the SQLite database
    initialize_db()

    # 5.3) Create the Updater and pass in the bot token
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # 5.4) Register command handlers
    dp.add_handler(CommandHandler("start", start))

    # 5.5) Register the voice message handler
    dp.add_handler(MessageHandler(Filters.voice, voice_handler))

    # 5.6) Start polling for updates
    updater.start_polling()
    logging.info("Bot is running... Press Ctrl+C to stop.")

    # 5.7) Run until you press Ctrl+C
    updater.idle()

# -------------------------------------------------------------------
# 6) ENTRY POINT
# -------------------------------------------------------------------
if __name__ == "__main__":
    main()