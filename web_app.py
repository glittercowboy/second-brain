# web_app.py

from flask import Flask, render_template, jsonify, request, Response, stream_with_context
import sqlite3
from datetime import datetime, timedelta
import google.generativeai as genai
import os
import configparser
import json
import logging

# Import your database helpers
from database import (
    initialize_db,
    get_db_connection,
    create_chat_conversation,
    add_chat_message,
    get_chat_messages
)

# Load config
config = configparser.ConfigParser()
config.read('config.ini')

# Configure Gemini
genai.configure(api_key=config['gemini']['GEMINI_API_KEY'])

app = Flask(__name__)

# Call initialize_db() so that all tables (transcriptions, chat_conversations, chat_messages) exist
initialize_db()

def is_question(user_input: str) -> bool:
    """
    A simple heuristic to detect if the user is asking a question.
    1. Check if it ends with a question mark.
    2. Or starts with who/what/when/where/why/how.
    You can refine this logic as needed.
    """
    stripped = user_input.strip().lower()
    if stripped.endswith('?'):
        return True
    question_words = ["who", "what", "when", "where", "why", "how"]
    return any(stripped.startswith(word + " ") for word in question_words)

def get_all_entries():
    """
    Retrieves all journal entries from the database and formats them as a single string.
    Used for providing context to the AI if the user asks a question.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, transcription FROM transcriptions ORDER BY timestamp DESC')
    entries = cursor.fetchall()
    conn.close()
    
    entries_text = ""
    for entry in entries:
        timestamp = entry[0]
        content = entry[1]
        entries_text += f"\nDate: {timestamp}\n{content}\n---"
    return entries_text

def stream_chat_response(message, conversation_id):
    """
    Streams the response from Gemini, deciding whether to give a short or detailed answer.
    - If user_input is recognized as a question, provide more detailed context from the journal.
    - If it's a statement, respond briefly and store new info.
    """
    try:
        # 1) Retrieve conversation history from DB
        conversation_history = get_chat_messages(conversation_id)
        
        # Build conversation context string
        conversation_context = ""
        for msg in conversation_history:
            role_name = "User" if msg['role'] == 'user' else "Assistant"
            conversation_context += f"{role_name}: {msg['message']}\n"

        # 2) Decide prompt based on whether it's a question or statement
        if is_question(message):
            # Longer, more detailed response with entire journal context
            journal_entries = get_all_entries()
            prompt = f"""You are a helpful AI assistant that references the user's journal and chat history.

Here are the journal entries:
{journal_entries}

Below is the conversation history:
{conversation_context}

The user's last message is a question:
User: {message}
Assistant:"""
        else:
            # Shorter response prompt for statements
            prompt = f"""You are a helpful but concise AI assistant.
The user is making a statement, not asking a question.
Respond with a brief acknowledgment or relevant comment, storing any new info about them, but do not provide an overly detailed reply.

Conversation so far:
{conversation_context}
User: {message}
Assistant:"""

        # 3) Set up Gemini model
        model = genai.GenerativeModel('gemini-1.5-pro')

        # 4) Generate streaming response
        response = model.generate_content(prompt, stream=True)
        full_response_text = ""

        for chunk in response:
            if chunk.text:
                yield chunk.text
                full_response_text += chunk.text

        # 5) After streaming, store the assistant's message in DB
        add_chat_message(conversation_id, "assistant", full_response_text)

    except Exception as e:
        logging.error(f"Error in stream_chat_response: {e}")
        yield f"Error: {str(e)}"

@app.route('/')
def journal():
    return render_template('journal.html')

@app.route('/patterns')
def patterns():
    return render_template('patterns.html')

@app.route('/questions')
def questions():
    return render_template('questions.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

# ---------------------------------------------
# Chat API Endpoint
# ---------------------------------------------
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Endpoint for chat messages.
    Accepts JSON with 'message' and optionally 'conversation_id'.
    If no conversation_id is provided, creates a new conversation.
    Stores the user message, then streams the assistant's response.
    """
    try:
        data = request.get_json()
        message = data.get('message')
        conversation_id = data.get('conversation_id')

        if not message:
            return jsonify({'error': 'No message provided'}), 400
        
        # If no conversation ID, create a new conversation
        if not conversation_id:
            conversation_name = f"Chat - {message[:20]}..."
            conversation_id = create_chat_conversation(conversation_name)

        # Store the user's message
        add_chat_message(conversation_id, "user", message)

        # Stream the assistant's response
        response = Response(
            stream_with_context(stream_chat_response(message, conversation_id)),
            content_type='text/plain'
        )
        # Return conversation ID so the front end can continue the same chat
        response.headers['X-Conversation-Id'] = str(conversation_id)
        return response

    except Exception as e:
        logging.error(f"Error in /api/chat: {e}")
        return jsonify({'error': str(e)}), 500

# ---------------------------------------------
# Existing API Endpoints for categories, entries, etc.
# ---------------------------------------------
@app.route('/api/categories')
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT categories FROM transcriptions WHERE categories IS NOT NULL')
    categories = set()
    for row in cursor.fetchall():
        if row[0]:
            categories.update(cat.strip().capitalize() for cat in row[0].split(','))
    conn.close()
    return jsonify(sorted(list(categories)))

@app.route('/api/entries')
def get_entries():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    category = request.args.get('category', 'all')
    search = request.args.get('search', '').strip()
    
    offset = (page - 1) * per_page
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT id, transcription as content, timestamp as date, categories, keywords
        FROM transcriptions
        WHERE 1=1
    '''
    params = []
    
    if category != 'all':
        query += " AND LOWER(categories) LIKE LOWER(?)"
        params.append(f'%{category}%')
    
    if search:
        query += ' AND transcription LIKE ?'
        params.append(f'%{search}%')
    
    query += '''
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    '''
    params.extend([per_page, offset])
    
    cursor.execute(query, params)
    entries = []
    for row in cursor.fetchall():
        categories = row[3]
        if categories:
            categories = ','.join(cat.strip().capitalize() for cat in categories.split(','))
        entries.append({
            'id': row[0],
            'content': row[1],
            'date': row[2],
            'category': categories,
            'keywords': row[4]
        })
    
    conn.close()
    return jsonify(entries)

@app.route('/api/entries/<int:entry_id>', methods=['PUT'])
def update_entry(entry_id):
    content = request.json.get('content')
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE transcriptions SET transcription = ? WHERE id = ?',
        (content, entry_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transcriptions WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ---------------------------------------------
# Reports / Patterns / Stats Endpoints
# ---------------------------------------------
@app.route('/patterns/data')
def patterns_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM patterns')
    patterns = cursor.fetchall()
    conn.close()
    return jsonify(patterns)

@app.route('/reports/data')
def reports_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reports')
    reports = cursor.fetchall()
    conn.close()
    return jsonify(reports)

@app.route('/api/journal_stats')
def journal_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    
    if not start_date:
        cursor.execute('SELECT DATE(MIN(timestamp)) FROM transcriptions')
        start_date = cursor.fetchone()[0]
    
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM transcriptions
        WHERE DATE(timestamp) >= ? AND DATE(timestamp) <= ?
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', (start_date, end_date))
    entries_data = cursor.fetchall()
    
    cursor.execute('''
        SELECT DATE(timestamp) as date, 
               AVG(LENGTH(transcription) - LENGTH(REPLACE(transcription, ' ', '')) + 1) as avg_words
        FROM transcriptions
        WHERE DATE(timestamp) >= ? AND DATE(timestamp) <= ?
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', (start_date, end_date))
    words_data = cursor.fetchall()
    
    cursor.execute('SELECT DATE(MIN(timestamp)) FROM transcriptions')
    first_entry_date = cursor.fetchone()[0]
    
    conn.close()
    
    dates = []
    entries_per_day = []
    words_per_entry = []
    
    from datetime import datetime
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    entries_dict = {row[0]: row[1] for row in entries_data}
    words_dict = {row[0]: int(row[1]) for row in words_data if row[1] is not None}
    
    while current.date() <= end.date():
        date_str = current.strftime('%Y-%m-%d')
        dates.append(date_str)
        entries_per_day.append(entries_dict.get(date_str, 0))
        words_per_entry.append(words_dict.get(date_str, 0))
        current += timedelta(days=1)
    
    return jsonify({
        'dates': dates,
        'entries_per_day': entries_per_day,
        'words_per_entry': words_per_entry,
        'first_entry_date': first_entry_date
    })

@app.route('/api/get_report')
def get_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        time_range = request.args.get('time_range')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT content, generated_at
            FROM reports
            WHERE category = ? 
            AND time_range = ?
            AND start_date = ?
            AND end_date = ?
        ''', (category, time_range, start_date, end_date))
        report = cursor.fetchone()
        conn.close()

        if report:
            return jsonify({
                'content': report[0],
                'generated_at': report[1]
            })
        return jsonify(None)

    except Exception as e:
        logging.error(f"Error getting report: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_report')
def generate_report():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        time_range = request.args.get('time_range')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, transcription, tags
            FROM transcriptions
            WHERE DATE(timestamp) >= ? AND DATE(timestamp) <= ?
            ORDER BY timestamp
        ''', (start_date, end_date))
        entries = cursor.fetchall()

        if not entries:
            return jsonify({
                'content': '<p>No journal entries found for this time period.</p>',
                'generated_at': datetime.now().isoformat()
            })

        formatted_entries = []
        for timestamp, text, tags in entries:
            if tags:
                tag_list = [t.strip() for t in tags.split(',')]
            else:
                tag_list = []
            if category in tag_list:
                formatted_entries.append({
                    'date': timestamp,
                    'text': text,
                    'tags': tag_list
                })

        if not formatted_entries:
            return jsonify({
                'content': f'<p>No entries tagged with "{category}" found for this time period.</p>',
                'generated_at': datetime.now().isoformat()
            })

        prompt = f'''You are analyzing journal entries for a personal development report. Focus on entries tagged with "{category}" from {start_date} to {end_date}.

Here are the relevant entries:
{json.dumps(formatted_entries, indent=2)}

Please generate a detailed {time_range}ly report that:
1. Identifies key themes, patterns, and insights specific to the {category} category
2. Highlights significant developments or changes over this period
3. Notes any challenges faced and how they were addressed
4. Suggests potential areas for growth or improvement
5. Provides actionable insights based on the journal entries

Important guidelines:
- Focus ONLY on content relevant to the {category} category
- Ignore parts of entries that don't relate to {category}, even if they're in tagged entries
- Be specific and reference actual events/thoughts from the entries
- Format the response in clean HTML with appropriate headings and lists
- Keep the tone analytical but personal
- Don't include the dates of entries in the report unless particularly significant

Structure the report with these sections:
- Overview
- Key Themes
- Notable Progress
- Challenges & Solutions
- Recommendations
'''

        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        formatted_response = response.text.replace('\n', '<br>')
        generated_at = datetime.now().isoformat()

        cursor.execute('''
            INSERT OR REPLACE INTO reports 
            (category, time_range, start_date, end_date, content, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (category, time_range, start_date, end_date, formatted_response, generated_at))
        conn.commit()
        conn.close()
        
        return jsonify({
            'content': formatted_response,
            'generated_at': generated_at
        })

    except Exception as e:
        logging.error(f"Error generating report: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)