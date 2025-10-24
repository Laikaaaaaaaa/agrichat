#!/usr/bin/env python3
"""Test script to verify block functionality"""

import sqlite3
import os

DB_PATH = 'users.db'

def test_blocked_users_table():
    """Check if blocked_users table exists and has data"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='blocked_users'")
        if not cursor.fetchone():
            print("❌ blocked_users table does not exist!")
            conn.close()
            return
        
        print("✅ blocked_users table exists")
        
        # Get all blocked records
        cursor.execute("SELECT blocker_id, blocked_id, created_at FROM blocked_users")
        records = cursor.fetchall()
        
        if not records:
            print("⚠️  No blocked records found in database")
        else:
            print(f"📊 Found {len(records)} blocked record(s):")
            for blocker_id, blocked_id, created_at in records:
                print(f"   - User {blocker_id} blocked User {blocked_id} (created: {created_at})")
        
        # Get user info for better understanding
        cursor.execute("SELECT id, name, email FROM users LIMIT 5")
        users = cursor.fetchall()
        print("\n📝 Sample users in database:")
        for uid, name, email in users:
            print(f"   - ID: {uid}, Name: {name}, Email: {email}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    print("🔍 Testing block functionality...\n")
    test_blocked_users_table()
