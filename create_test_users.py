import sqlite3
import hashlib

DB_PATH = 'database.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Helper function
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# Create test users
test_users = [
    ('user1@test.com', 'user1_test', 'User One'),
    ('user2@test.com', 'user2_test', 'User Two'),
]

for email, username, name in test_users:
    try:
        cursor.execute('''
            INSERT INTO users (email, password_hash, username_slug, name)
            VALUES (?, ?, ?, ?)
        ''', (email, hash_password('password123'), username, name))
        print(f"✅ Created user: {name}")
    except sqlite3.IntegrityError:
        print(f"⚠️ User {email} already exists")

conn.commit()

# Show users
cursor.execute("SELECT id, email, name FROM users")
users = cursor.fetchall()
print("\n📋 All users:")
for user_id, email, name in users:
    print(f"  ID={user_id}: {email} ({name})")

# Test block: user 1 blocks user 2
cursor.execute('''
    INSERT OR IGNORE INTO blocked_users (blocker_id, blocked_id)
    VALUES (1, 2)
''')
conn.commit()

# Check block
cursor.execute("SELECT * FROM blocked_users")
blocks = cursor.fetchall()
print("\n🚫 Blocked relationships:")
for block in blocks:
    print(f"  {block}")

conn.close()
