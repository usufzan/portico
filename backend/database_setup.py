import sqlite3
import os

DB_FILE = "local_database.db"

# Delete the old database file if it exists, to start fresh
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)

# Establish a connection to the database file
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

print("Database created. Creating tables...")

# --- Create users table ---
cursor.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
print("- 'users' table created.")

# --- Create scraped_articles table ---
cursor.execute("""
CREATE TABLE scraped_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    original_url TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    publication_date TEXT,
    word_count INTEGER,
    content_markdown TEXT NOT NULL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
""")
print("- 'scraped_articles' table created.")

# --- Create site_requests table ---
cursor.execute("""
CREATE TABLE site_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    requested_domain TEXT NOT NULL,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);
""")
print("- 'site_requests' table created.")

# --- Create rate_limit_log table ---
# Note: user_id is TEXT because it can also hold 'anonymous'
cursor.execute("""
CREATE TABLE rate_limit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL
);
""")
print("- 'rate_limit_log' table created.")

# Commit the changes and close the connection
conn.commit()
conn.close()

print("\nDatabase setup complete. You can now start the FastAPI application.")