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
            google_id TEXT UNIQUE,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
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
    
    conn.commit()
    conn.close()

# Initialize database on import
init_db()

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

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
        
        # Hash password and insert user
        password_hash = hash_password(password) if password else None
        cursor.execute(
            'INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)',
            (email, password_hash, name)
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
                'name': name
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
            'SELECT id, email, name, avatar_url, created_at, last_login FROM users WHERE id = ?',
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
                'last_login': user[5]
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
            # Create new user
            cursor.execute(
                'INSERT INTO users (email, google_id, name, avatar_url, password_hash) VALUES (?, ?, ?, ?, ?)',
                (user_info['email'], user_info['google_id'], user_info['name'], user_info.get('picture'), None)
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
                    'name': user_info['name']
                }
            }
    
    except Exception as e:
        return {'success': False, 'message': f'Lỗi: {str(e)}'}
