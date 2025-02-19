-- Add reports table
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    time_range TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    content TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category, time_range, start_date, end_date)
);
