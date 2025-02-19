import re
from datetime import datetime
import sqlite3
from bot import categorize_and_extract
from database import DB_NAME

def parse_entry(text):
    """Parse a single entry into content and timestamp."""
    # Find the timestamp at the end of the entry
    timestamp_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}(?:am|pm|AM|PM)?)\s*$', text)
    if not timestamp_match:
        return None, None
    
    # Split content and timestamp
    timestamp_str = timestamp_match.group(1)
    content = text[:timestamp_match.start()].strip()
    
    # Parse the timestamp
    try:
        timestamp = datetime.strptime(timestamp_str, '%m/%d/%Y %I:%M%p')
    except ValueError:
        try:
            timestamp = datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M')
        except ValueError:
            return None, None
    
    return content, timestamp

def import_entries(entries_text):
    """Import multiple entries from text."""
    # Split entries (they're separated by empty lines)
    raw_entries = [e.strip() for e in entries_text.split('\n\n') if e.strip()]
    
    # Connect to database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    for entry in raw_entries:
        content, timestamp = parse_entry(entry)
        if not content or not timestamp:
            print(f"Skipping entry due to parsing error: {entry[:100]}...")
            continue
            
        # Get categories and keywords using the existing system
        categories_str, keywords_str = categorize_and_extract(content)
        
        # Insert into database
        cursor.execute("""
            INSERT INTO transcriptions 
            (user_id, message_id, timestamp, transcription, file_path, categories, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            'imported_user',  # user_id
            f'import_{timestamp.strftime("%Y%m%d%H%M%S")}',  # message_id
            timestamp.isoformat(),  # timestamp
            content,  # transcription
            'imported_entry',  # file_path
            categories_str,  # categories
            keywords_str  # keywords
        ))
        print(f"Imported entry from {timestamp}")
    
    # Commit changes
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Read entries from the file
    with open('old_entries.txt', 'r') as f:
        entries_text = f.read()
    
    # Import the entries
    import_entries(entries_text)
    print("Import complete!")
