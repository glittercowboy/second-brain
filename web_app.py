from flask import Flask, render_template, jsonify, request, Response, stream_with_context
import sqlite3
from datetime import datetime
import google.generativeai as genai
import os
import configparser
from collections import defaultdict
from datetime import datetime, timedelta

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

@app.route('/api/journal_stats')
def journal_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get date range from query params or use defaults
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    
    # Get first entry date if no start date provided
    if not start_date:
        cursor.execute('SELECT DATE(MIN(timestamp)) FROM transcriptions')
        start_date = cursor.fetchone()[0]
    
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    # Get entries per day
    cursor.execute('''
        SELECT DATE(timestamp) as date, COUNT(*) as count
        FROM transcriptions
        WHERE DATE(timestamp) >= ? AND DATE(timestamp) <= ?
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', (start_date, end_date))
    entries_data = cursor.fetchall()
    
    # Get words per entry
    cursor.execute('''
        SELECT DATE(timestamp) as date, 
               AVG(LENGTH(transcription) - LENGTH(REPLACE(transcription, ' ', '')) + 1) as avg_words
        FROM transcriptions
        WHERE DATE(timestamp) >= ? AND DATE(timestamp) <= ?
        GROUP BY DATE(timestamp)
        ORDER BY date
    ''', (start_date, end_date))
    words_data = cursor.fetchall()
    
    # Get first entry date for client
    cursor.execute('SELECT DATE(MIN(timestamp)) FROM transcriptions')
    first_entry_date = cursor.fetchone()[0]
    
    conn.close()
    
    # Format data for charts
    dates = []
    entries_per_day = []
    words_per_entry = []
    
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    entries_dict = {row[0]: row[1] for row in entries_data}
    words_dict = {row[0]: int(row[1]) for row in words_data}
    
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
        # Get parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        time_range = request.args.get('time_range')

        # Get cached report from database
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
        print(f"Error getting report: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_report')
def generate_report():
    try:
        # Get parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')
        time_range = request.args.get('time_range')

        # Get entries for the date range
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

        # Format entries for analysis
        formatted_entries = []
        for timestamp, text, tags in entries:
            entry_tags = tags.split(',') if tags else []
            if category in entry_tags:
                formatted_entries.append({
                    'date': timestamp,
                    'text': text,
                    'tags': entry_tags
                })

        if not formatted_entries:
            return jsonify({
                'content': f'<p>No entries tagged with "{category}" found for this time period.</p>',
                'generated_at': datetime.now().isoformat()
            })

        # Create prompt for Gemini
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

        # Generate report with Gemini
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        
        # Format the response
        formatted_response = response.text.replace('\n', '<br>')
        generated_at = datetime.now().isoformat()

        # Save report to database
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
        print(f"Error generating report: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
