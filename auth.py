"""
Authentication Module for AgriSense AI
Handles user registration, login, password reset, OTP verification
"""

import os
import sqlite3
import hashlib
import secrets
import smtplib
import requests
import re
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, jsonify

# Database setup
DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def init_db():
    """Initialize the users database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            name TEXT,
            username_slug TEXT,
            google_id TEXT UNIQUE,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Add username_slug column if it doesn't exist (migration for old databases)
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN username_slug TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # OTP table for password reset
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp_code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0
        )
    ''')
    
    # Forum posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            image_url TEXT,
            tags TEXT,
            poll_data TEXT,
            location TEXT,
            mentioned_users TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Forum likes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id),
            FOREIGN KEY (post_id) REFERENCES forum_posts (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Forum comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES forum_posts (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # User photos table (profile photos, cover photos, uploaded photos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            photo_url TEXT NOT NULL,
            photo_type TEXT NOT NULL,
            caption TEXT,
            source_post_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (source_post_id) REFERENCES forum_posts (id)
        )
    ''')
    
    # Photo likes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photo_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(photo_id, user_id),
            FOREIGN KEY (photo_id) REFERENCES user_photos (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Photo comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photo_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (photo_id) REFERENCES user_photos (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Friends table
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
    
    # Add bio column to users table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            bio TEXT,
            cover_photo_url TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Migration: Add missing columns to forum_posts if they don't exist
    try:
        cursor.execute('ALTER TABLE forum_posts ADD COLUMN poll_data TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE forum_posts ADD COLUMN location TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE forum_posts ADD COLUMN mentioned_users TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Migration: Add source_post_id to user_photos
    try:
        cursor.execute('ALTER TABLE user_photos ADD COLUMN source_post_id INTEGER')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Migration: Fix forum_poll_votes UNIQUE constraint for multiple choice polls
    try:
        # Check if old unique constraint exists by trying to insert a duplicate
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forum_poll_votes_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                option_index INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id, option_index),
                FOREIGN KEY (post_id) REFERENCES forum_posts (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Try to copy data from old table if it exists
        try:
            cursor.execute('INSERT INTO forum_poll_votes_new SELECT * FROM forum_poll_votes')
            cursor.execute('DROP TABLE forum_poll_votes')
            cursor.execute('ALTER TABLE forum_poll_votes_new RENAME TO forum_poll_votes')
        except:
            # Old table doesn't exist or is already correct
            pass
    except:
        pass
    
    # Create poll votes table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forum_poll_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            option_index INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id, option_index),
            FOREIGN KEY (post_id) REFERENCES forum_posts (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Notifications table for likes/comments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            post_id INTEGER,
            photo_id INTEGER,
            comment_id INTEGER,
            content TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recipient_id) REFERENCES users (id),
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (post_id) REFERENCES forum_posts (id),
            FOREIGN KEY (photo_id) REFERENCES user_photos (id),
            FOREIGN KEY (comment_id) REFERENCES forum_comments (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on import
init_db()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_username_slug(name, email, user_id=None):
    """
    Create a unique username slug from name/email
    Format: lowercase letters/numbers only + 6-digit random number
    Example: nhatquang.576789
    """
    # Use name if available, otherwise use email username part
    base_name = name if name else email.split('@')[0]
    
    # Remove Vietnamese accents and special characters
    accent_map = {
        'à': 'a', 'á': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'è': 'e', 'é': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ề': 'e', 'ế': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'ì': 'i', 'í': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ò': 'o', 'ó': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ù': 'u', 'ú': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ỳ': 'y', 'ý': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y',
        'đ': 'd',
        ' ': '', '.': '', '_': '', '-': ''
    }
    
    # Convert to lowercase and replace accents
    slug_base = base_name.lower()
    for acc, replacement in accent_map.items():
        slug_base = slug_base.replace(acc, replacement)
    
    # Remove any remaining non-alphanumeric characters
    slug_base = re.sub(r'[^a-z0-9]', '', slug_base)
    
    # Limit to first 20 characters
    slug_base = slug_base[:20]
    
    # Generate 6-digit random number
    random_suffix = random.randint(100000, 999999)
    
    # Combine: username.123456
    username_slug = f"{slug_base}.{random_suffix}"
    
    return username_slug

def generate_unique_username_slug(name, email, conn=None):
    """Generate a unique username slug (check for duplicates)"""
    should_close = False
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        should_close = True
    
    cursor = conn.cursor()
    
    # Try up to 10 times to generate unique slug
    for _ in range(10):
        slug = create_username_slug(name, email)
        cursor.execute('SELECT id FROM users WHERE username_slug = ?', (slug,))
        if not cursor.fetchone():
            if should_close:
                conn.close()
            return slug
    
    # If all attempts fail, add timestamp
    slug_base = create_username_slug(name, email).split('.')[0]
    timestamp_suffix = str(int(datetime.now().timestamp()))[-6:]
    final_slug = f"{slug_base}.{timestamp_suffix}"
    
    if should_close:
        conn.close()
    return final_slug

def generate_otp():
    """Generate a 6-digit OTP code"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

def send_otp_email(email, otp_code):
    """Send OTP code via email"""
    # Print to console for debugging
    print(f"\n{'='*50}")
    print(f"📧 SENDING OTP TO {email}")
    print(f"🔑 OTP CODE: {otp_code}")
    print(f"{'='*50}\n")
    
    try:
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_email = os.getenv('SMTP_EMAIL')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        # If SMTP not configured, just return True for testing
        if not smtp_email or not smtp_password:
            print("⚠️ SMTP not configured. Check terminal for OTP code above.")
            return True
        
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = email
        msg['Subject'] = 'AgriSense AI - Mã OTP xác thực'
        
        body = f'''
Xin chào,

Mã OTP của bạn là: {otp_code}

Mã này có hiệu lực trong 10 phút.

Nếu bạn không yêu cầu mã này, vui lòng bỏ qua email này.

Trân trọng,
AgriSense AI Team
        '''
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)
        
        print("✅ Email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        print("⚠️ OTP will still work if you use the code printed above.")
        return True  # Return True anyway so OTP flow continues

# Authentication Functions

def register_user_init(email, password, name=None):
    """Initialize registration - validate and send OTP"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return {'success': False, 'message': 'Email đã được đăng ký'}
        
        conn.close()
        
        # Generate and send OTP
        otp_code = generate_otp()
        if not send_otp_email(email, otp_code):
            return {'success': False, 'message': 'Không thể gửi mã OTP'}
        
        # Save OTP to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO otp_codes (email, otp_code, expires_at) VALUES (?, ?, datetime("now", "+10 minutes"))',
            (email, otp_code)
        )
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Mã OTP đã được gửi đến email của bạn',
            'email': email
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def register_user_complete(email, otp_code, password, name=None):
    """Complete registration after OTP verification"""
    try:
        # Verify OTP
        if not verify_otp(email, otp_code):
            return {'success': False, 'message': 'Mã OTP không hợp lệ hoặc đã hết hạn'}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if email already exists (double check)
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if cursor.fetchone():
            conn.close()
            return {'success': False, 'message': 'Email đã được đăng ký'}
        
        # Generate unique username slug
        username_slug = generate_unique_username_slug(name, email, conn)
        
        # Hash password and insert user
        password_hash = hash_password(password) if password else None
        cursor.execute(
            'INSERT INTO users (email, password_hash, name, username_slug) VALUES (?, ?, ?, ?)',
            (email, password_hash, name, username_slug)
        )
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return {
            'success': True,
            'message': 'Đăng ký thành công',
            'user': {
                'id': user_id,
                'email': email,
                'name': name,
                'username_slug': username_slug
            }
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def login_user_init(email, password):
    """Verify credentials and send OTP for manual login"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get user by email
        cursor.execute(
            'SELECT id, email, password_hash, name, is_active FROM users WHERE email = ?',
            (email,)
        )
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {'success': False, 'message': 'Email hoặc mật khẩu không đúng'}
        
        user_id, user_email, password_hash, name, is_active = user
        
        # Check if account is active
        if not is_active:
            conn.close()
            return {'success': False, 'message': 'Tài khoản đã bị vô hiệu hóa'}
        
        # Check if user has password (not Google-only account)
        if not password_hash:
            conn.close()
            return {'success': False, 'message': 'Tài khoản này đăng ký bằng Google. Vui lòng đăng nhập bằng Google.'}
        
        # Verify password
        if hash_password(password) != password_hash:
            conn.close()
            return {'success': False, 'message': 'Email hoặc mật khẩu không đúng'}
        
        conn.close()
        
        # Generate and send OTP
        otp_code = generate_otp()
        if not send_otp_email(email, otp_code):
            return {'success': False, 'message': 'Không thể gửi mã OTP'}
        
        # Save OTP to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO otp_codes (email, otp_code, expires_at) VALUES (?, ?, datetime("now", "+10 minutes"))',
            (email, otp_code)
        )
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Mã OTP đã được gửi đến email của bạn',
            'email': email
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def login_user_complete(email, otp_code):
    """Complete login after OTP verification"""
    try:
        # Verify OTP
        if not verify_otp(email, otp_code):
            return {'success': False, 'message': 'Mã OTP không hợp lệ hoặc đã hết hạn'}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute(
            'SELECT id, email, name FROM users WHERE email = ?',
            (email,)
        )
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {'success': False, 'message': 'Không tìm thấy người dùng'}
        
        user_id, user_email, name = user
        
        # Update last login
        cursor.execute(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
            (user_id,)
        )
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message': 'Đăng nhập thành công',
            'user': {
                'id': user_id,
                'email': user_email,
                'name': name
            }
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def request_password_reset(email):
    """Generate and send OTP for password reset"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if email exists
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        if not cursor.fetchone():
            conn.close()
            return {'success': False, 'message': 'Email không tồn tại'}
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = datetime.now() + timedelta(minutes=10)
        
        # Store OTP
        cursor.execute(
            'INSERT INTO otp_codes (email, otp_code, expires_at) VALUES (?, ?, ?)',
            (email, otp_code, expires_at)
        )
        conn.commit()
        conn.close()
        
        # Send OTP via email
        if send_otp_email(email, otp_code):
            return {'success': True, 'message': 'Mã OTP đã được gửi đến email của bạn'}
        else:
            return {'success': False, 'message': 'Không thể gửi email. Vui lòng thử lại'}
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def verify_otp(email, otp_code):
    """Verify OTP code"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get latest unused OTP for this email
        cursor.execute('''
            SELECT id, expires_at FROM otp_codes 
            WHERE email = ? AND otp_code = ? AND used = 0
            ORDER BY created_at DESC LIMIT 1
        ''', (email, otp_code))
        
        otp = cursor.fetchone()
        
        if not otp:
            conn.close()
            return {'success': False, 'message': 'Mã OTP không đúng'}
        
        otp_id, expires_at = otp
        
        # Check if OTP has expired
        if datetime.now() > datetime.fromisoformat(expires_at):
            conn.close()
            return {'success': False, 'message': 'Mã OTP đã hết hạn'}
        
        # Mark OTP as used
        cursor.execute('UPDATE otp_codes SET used = 1 WHERE id = ?', (otp_id,))
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Xác thực OTP thành công'}
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def reset_password(email, new_password):
    """Reset user password after OTP verification"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update password
        password_hash = hash_password(new_password)
        cursor.execute(
            'UPDATE users SET password_hash = ? WHERE email = ?',
            (password_hash, email)
        )
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Đổi mật khẩu thành công'}
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def get_user_profile(user_id):
    """Get user profile information"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, email, name, avatar_url, created_at, last_login, username_slug FROM users WHERE id = ?',
            (user_id,)
        )
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return {'success': False, 'message': 'Người dùng không tồn tại'}
        
        return {
            'success': True,
            'user': {
                'id': user[0],
                'email': user[1],
                'name': user[2],
                'avatar_url': user[3],
                'created_at': user[4],
                'last_login': user[5],
                'username_slug': user[6]
            }
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def update_user_profile(user_id, name=None, avatar_url=None):
    """Update user profile information"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if name:
            cursor.execute('UPDATE users SET name = ? WHERE id = ?', (name, user_id))
        
        if avatar_url:
            cursor.execute('UPDATE users SET avatar_url = ? WHERE id = ?', (avatar_url, user_id))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Cập nhật thông tin thành công'}
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

def change_password(user_id, old_password, new_password):
    """Change user password"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verify old password
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        
        if not result or hash_password(old_password) != result[0]:
            conn.close()
            return {'success': False, 'message': 'Mật khẩu cũ không đúng'}
        
        # Update password
        password_hash = hash_password(new_password)
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        
        conn.commit()
        conn.close()
        
        return {'success': True, 'message': 'Đổi mật khẩu thành công'}
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}

# Flask Decorators

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged in user from session"""
    if 'user_id' in session:
        result = get_user_profile(session['user_id'])
        if result['success']:
            return result['user']
    return None

def verify_google_token(credential):
    """Verify Google ID token and extract user info"""
    try:
        # Google's tokeninfo endpoint
        url = f'https://oauth2.googleapis.com/tokeninfo?id_token={credential}'
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return None
        
        user_info = response.json()
        
        # Verify audience (client ID)
        if user_info.get('aud') != '101632487017-bvc6csfrngsmvh4o8urkhrrtp92qvsok.apps.googleusercontent.com':
            return None
        
        return {
            'google_id': user_info.get('sub'),
            'email': user_info.get('email'),
            'name': user_info.get('name'),
            'picture': user_info.get('picture'),
            'email_verified': user_info.get('email_verified')
        }
    except Exception as e:
        print(f"Error verifying Google token: {e}")
        return None

def google_login(credential):
    """Login or register user with Google - No OTP required"""
    try:
        # Verify Google token
        user_info = verify_google_token(credential)
        
        if not user_info:
            return {'success': False, 'message': 'Token Google không hợp lệ'}
        
        if not user_info.get('email_verified'):
            return {'success': False, 'message': 'Email chưa được xác thực bởi Google'}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if user exists by Google ID or email
        cursor.execute(
            'SELECT id, email, name FROM users WHERE google_id = ? OR email = ?',
            (user_info['google_id'], user_info['email'])
        )
        user = cursor.fetchone()
        
        if user:
            # Update Google ID and avatar if not set
            user_id, email, name = user
            cursor.execute(
                'UPDATE users SET google_id = ?, avatar_url = ?, last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user_info['google_id'], user_info.get('picture'), user_id)
            )
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': 'Đăng nhập thành công',
                'user': {
                    'id': user_id,
                    'email': email,
                    'name': name
                }
            }
        else:
            # Create new user with username slug
            username_slug = generate_unique_username_slug(user_info['name'], user_info['email'], conn)
            
            cursor.execute(
                'INSERT INTO users (email, google_id, name, avatar_url, password_hash, username_slug) VALUES (?, ?, ?, ?, ?, ?)',
                (user_info['email'], user_info['google_id'], user_info['name'], user_info.get('picture'), None, username_slug)
            )
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            return {
                'success': True,
                'message': 'Đăng ký thành công',
                'user': {
                    'id': user_id,
                    'email': user_info['email'],
                    'name': user_info['name'],
                    'username_slug': username_slug
                }
            }
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}
