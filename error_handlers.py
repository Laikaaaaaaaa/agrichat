"""🔧 Centralized error handling for AgriSense AI API"""
import logging
from functools import wraps
from flask import jsonify
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== ERROR CLASSES =====

class AgriSenseError(Exception):
    """Base error class for AgriSense"""
    def __init__(self, message, code, status_code=500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(AgriSenseError):
    """Input validation failed"""
    def __init__(self, message):
        super().__init__(message, 'VALIDATION_ERROR', 400)

class NotFoundError(AgriSenseError):
    """Resource not found"""
    def __init__(self, message):
        super().__init__(message, 'NOT_FOUND', 404)

class AuthenticationError(AgriSenseError):
    """User not authenticated"""
    def __init__(self, message="Please login"):
        super().__init__(message, 'AUTH_REQUIRED', 401)

class PermissionError(AgriSenseError):
    """User doesn't have permission"""
    def __init__(self, message="Permission denied"):
        super().__init__(message, 'PERMISSION_DENIED', 403)

class RateLimitError(AgriSenseError):
    """Too many requests"""
    def __init__(self, message="Too many requests"):
        super().__init__(message, 'RATE_LIMIT', 429)

class DatabaseError(AgriSenseError):
    """Database operation failed"""
    def __init__(self, message="Database error"):
        super().__init__(message, 'DATABASE_ERROR', 500)

class ExternalAPIError(AgriSenseError):
    """External API call failed"""
    def __init__(self, service_name, message=None):
        msg = f"{service_name} API error" + (f": {message}" if message else "")
        super().__init__(msg, f'{service_name.upper()}_ERROR', 503)

# ===== ERROR RESPONSE HANDLER =====

def error_response(error, user_id=None):
    """✅ Standardized error response"""
    if isinstance(error, AgriSenseError):
        response = {
            'success': False,
            'error': error.message,
            'code': error.code
        }
        status = error.status_code
    else:
        response = {
            'success': False,
            'error': 'Internal server error',
            'code': 'SERVER_ERROR'
        }
        status = 500
        error_msg = str(error)
    
    # Log error
    if isinstance(error, AgriSenseError):
        log_msg = f"[{user_id or 'ANON'}] {error.code}: {error.message}"
        if error.status_code >= 500:
            logger.error(log_msg)
        else:
            logger.warning(log_msg)
    else:
        logger.error(f"[{user_id or 'ANON'}] Unhandled error: {error}")
        logger.error(traceback.format_exc())
    
    return jsonify(response), status

# ===== DECORATOR FOR ENDPOINTS =====

def handle_errors(f):
    """✅ Decorator to wrap endpoint with error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AgriSenseError as e:
            # Get user_id from function if available
            user_id = None
            try:
                from flask import session
                user_id = session.get('user_id')
            except:
                pass
            return error_response(e, user_id)
        except Exception as e:
            user_id = None
            try:
                from flask import session
                user_id = session.get('user_id')
            except:
                pass
            logger.error(f"Unhandled exception in {f.__name__}: {e}")
            logger.error(traceback.format_exc())
            return error_response(AgriSenseError('Server error', 'SERVER_ERROR', 500), user_id)
    return decorated_function
