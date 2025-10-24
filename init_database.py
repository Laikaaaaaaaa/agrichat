#!/usr/bin/env python
import sqlite3
import os

DB_PATH = 'database.db'

# Delete if exists
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"✅ Deleted {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        name TEXT,
        username_slug TEXT,
        avatar_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Create blocked_users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS blocked_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blocker_id INTEGER NOT NULL,
        blocked_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(blocker_id, blocked_id),
        FOREIGN KEY (blocker_id) REFERENCES users (id),
        FOREIGN KEY (blocked_id) REFERENCES users (id)
    )
''')

# Create friendships table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS friendships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        friend_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, friend_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (friend_id) REFERENCES users (id)
    )
''')

conn.commit()
conn.close()

# Verify
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"✅ Database initialized! Tables: {tables}")
conn.close()
