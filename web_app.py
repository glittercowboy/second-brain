from flask import Flask, render_template, jsonify, request, Response, stream_with_context
import sqlite3
from datetime import datetime
import google.generativeai as genai
import os
import configparser

# Load config
config = configparser.ConfigParser()
config.read('config.ini')

# Configure Gemini
genai.configure(api_key=config['gemini']['GEMINI_API_KEY'])

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('journal.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def journal():
    return render_template('journal.html')

@app.route('/api/categories')
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT categories FROM transcriptions WHERE categories IS NOT NULL')
    # Split the comma-separated categories and create a unique set
    categories = set()
    for row in cursor.fetchall():
        if row[0]:
            # Split by comma, strip whitespace, capitalize first letter, and add to set
            categories.update(cat.strip().capitalize() for cat in row[0].split(','))
    conn.close()
    # Sort the categories alphabetically
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
        # Make the category search case-insensitive
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
        categories = row['categories']
        if categories:
            # Capitalize each category in the list
            categories = ','.join(cat.strip().capitalize() for cat in categories.split(','))
        
        entries.append({
            'id': row['id'],
            'content': row['content'],
            'date': row['date'],
            'category': categories,
            'keywords': row['keywords']
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

@app.route('/patterns')
def patterns():
    return render_template('patterns.html')

@app.route('/questions')
def questions():
    return render_template('questions.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/patterns/data')
def patterns_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM patterns')
    patterns = cursor.fetchall()
    conn.close()
    return jsonify(patterns)

@app.route('/questions/data')
def questions_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM questions')
    questions = cursor.fetchall()
    conn.close()
    return jsonify(questions)

@app.route('/reports/data')
def reports_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reports')
    reports = cursor.fetchall()
    conn.close()
    return jsonify(reports)

def get_all_entries():
    print("Getting all entries from database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, transcription FROM transcriptions ORDER BY timestamp DESC')
    entries = cursor.fetchall()
    conn.close()
    
    # Format entries into a nice string
    entries_text = ""
    for entry in entries:
        timestamp = entry[0]
        content = entry[1]
        entries_text += f"\nDate: {timestamp}\n{content}\n---"
    
    print(f"Retrieved {len(entries)} entries")
    return entries_text

def stream_chat_response(message):
    try:
        print(f"Processing chat message: {message}")
        
        # Get your journal entries as context
        journal_entries = get_all_entries()
        
        print("Setting up Gemini model...")
        # Set up the model
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Create the prompt with context
        prompt = f"""You are a helpful AI assistant analyzing someone's personal journal entries. 
        Your task is to help them understand patterns, insights, and answer questions about their life based on their journal entries.
        
        IMPORTANT: Do not use markdown formatting (no **, __, or other markup) in your responses. Use plain text only.
        
        Here are all their journal entries:
        {journal_entries}
        
        Their question is: {message}
        
        Please provide a thoughtful, empathetic response based on the actual content of their journal entries.
        If you can't find relevant information in the entries to answer their question, be honest about it.
        Remember to use plain text without any markdown formatting."""
        
        print("Generating response from Gemini...")
        # Stream the response
        response = model.generate_content(prompt, stream=True)
        
        print("Starting to stream response...")
        for chunk in response:
            if chunk.text:
                print(f"Streaming chunk: {chunk.text[:50]}...")
                yield chunk.text
    except Exception as e:
        print(f"Error in stream_chat_response: {str(e)}")
        yield f"Error: {str(e)}"

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        print("Received chat request")
        message = request.json.get('message')
        if not message:
            print("No message provided")
            return jsonify({'error': 'No message provided'}), 400
            
        print(f"Processing message: {message}")
        return Response(
            stream_with_context(stream_chat_response(message)),
            content_type='text/plain'
        )
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
