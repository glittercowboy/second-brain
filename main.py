# main.py
"""
This script tests our environment setup by importing key libraries.
If everything is set up correctly, it will print a success message.
"""

import sqlite3  # SQLite is included with Python

# Try importing the Telegram bot libraries
try:
    from telegram import Bot
    from telegram.ext import Updater, CommandHandler
except ImportError:
    print("Error: python-telegram-bot is not installed.")
    raise

# Try importing the OpenAI package
try:
    import openai
except ImportError:
    print("Error: openai package is not installed.")
    raise

# Try importing Whisper for voice transcription
try:
    import whisper
except ImportError:
    print("Error: whisper package is not installed. Ensure you installed it from GitHub.")
    raise

def main():
    """
    Main function to verify that all required modules are imported successfully.
    """
    print("Environment setup successful! All dependencies are imported correctly.")

if __name__ == "__main__":
    main()