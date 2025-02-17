# scheduler.py
"""
This module uses APScheduler to automatically run summary generation tasks.
It schedules:
  - A daily summary (runs every day at 9:00 AM)
  - A weekly summary (runs every Monday at 9:00 AM)
  - A monthly summary (runs on the 1st of each month at 9:00 AM)

Generated summaries are saved as JSON files with a timestamp in the filename.
  
Dependencies:
  - APScheduler (installed via APScheduler==3.6.3)
  - Functions from summaries.py
  - time and logging (standard library)
"""

import time
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from summaries import generate_daily_summary, generate_weekly_summary, generate_monthly_summary, save_summary_to_file

# Configure logging to see scheduler output.
logging.basicConfig(level=logging.INFO)

def schedule_daily_summary():
    """Generates the daily summary and saves it to a file."""
    daily = generate_daily_summary()
    filename = f"daily_summary_{datetime.now().strftime('%Y%m%d')}.json"
    save_summary_to_file(daily, filename)
    logging.info("Daily summary generated and saved.")

def schedule_weekly_summary():
    """Generates the weekly summary and saves it to a file."""
    weekly = generate_weekly_summary()
    filename = f"weekly_summary_{datetime.now().strftime('%Y%m%d')}.json"
    save_summary_to_file(weekly, filename)
    logging.info("Weekly summary generated and saved.")

def schedule_monthly_summary():
    """Generates the monthly summary and saves it to a file."""
    monthly = generate_monthly_summary()
    filename = f"monthly_summary_{datetime.now().strftime('%Y%m%d')}.json"
    save_summary_to_file(monthly, filename)
    logging.info("Monthly summary generated and saved.")

if __name__ == "__main__":
    # Initialize the APScheduler BackgroundScheduler
    scheduler = BackgroundScheduler()

    # Schedule the daily summary to run every day at 9:00 AM.
    scheduler.add_job(schedule_daily_summary, 'cron', hour=9, minute=0)
    
    # Schedule the weekly summary to run every Monday at 9:00 AM.
    scheduler.add_job(schedule_weekly_summary, 'cron', day_of_week='mon', hour=9, minute=0)
    
    # Schedule the monthly summary to run on the 1st of every month at 9:00 AM.
    scheduler.add_job(schedule_monthly_summary, 'cron', day=1, hour=9, minute=0)
    
    # Start the scheduler.
    scheduler.start()
    logging.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        # Keep the script running.
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler shut down.")