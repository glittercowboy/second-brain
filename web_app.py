from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('journal.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)
