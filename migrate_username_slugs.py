"""
Migration script to add username_slug to existing users
Run this once to update all existing users with username slugs
"""

import sqlite3
import os
from auth import create_username_slug

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def migrate_username_slugs():
    """Add username slugs to all users that don't have one"""
    print("Ensuring database schema is up to date...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Try to add the column if it doesn't exist (without UNIQUE constraint initially)
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN username_slug TEXT')
        conn.commit()
        print("✅ Added username_slug column to users table")
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e).lower():
            print("ℹ️ username_slug column already exists")
        else:
            raise e
    
    # Get all users
    cursor.execute('SELECT id, name, email, username_slug FROM users')
    users = cursor.fetchall()
    
    updated_count = 0
    for user in users:
        user_id, name, email, username_slug = user
        
        # Skip if already has a slug
        if username_slug:
            print(f"User {email} already has slug: {username_slug}")
            continue
        
        # Generate unique slug
        attempts = 0
        while attempts < 10:
            slug = create_username_slug(name, email, user_id)
            
            # Check if slug already exists
            cursor.execute('SELECT id FROM users WHERE username_slug = ?', (slug,))
            if not cursor.fetchone():
                # Slug is unique, update user
                cursor.execute('UPDATE users SET username_slug = ? WHERE id = ?', (slug, user_id))
                conn.commit()
                print(f"✅ Updated {email} -> {slug}")
                updated_count += 1
                break
            
            attempts += 1
        
        if attempts >= 10:
            print(f"❌ Failed to generate unique slug for {email}")
    
    conn.close()
    print(f"\n🎉 Migration complete! Updated {updated_count} users.")

if __name__ == '__main__':
    print("Starting username slug migration...")
    migrate_username_slugs()
