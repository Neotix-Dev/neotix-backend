from functools import wraps
from flask import request, jsonify
from models.api_key import APIKey, APIKeyPermission
from utils.database import db
from datetime import datetime
import secrets
import os
from dotenv import load_dotenv

load_dotenv()

def generate_api_key():
    """Generate a new API key using secrets module"""
    return secrets.token_urlsafe(32)

def check_api_key(required_permission=None):
    """
    Decorator factory that creates a decorator to check API key with specific permission level.
    If required_permission is None, any valid API key will work.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                return jsonify({
                    'error': 'No API key provided',
                    'message': 'Please provide your API key in the X-API-Key header'
                }), 401
                
            # Check if it's the master key from .env
            master_key = os.getenv('MASTER_API_KEY')
            if master_key and api_key == master_key:
                # Master key has all permissions
                return f(*args, **kwargs)
                
            # Check if key exists in database
            key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()
            if not key_record:
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid or has been deactivated'
                }), 401
            
            # Check permission if required
            if required_permission and key_record.permission != required_permission.value:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires {required_permission.value} permission'
                }), 403
                
            # Update last used timestamp
            key_record.last_used_at = datetime.utcnow()
            db.session.commit()
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Convenience decorators for common permission levels
require_api_key = check_api_key()  # Any valid key
require_admin_key = check_api_key(APIKeyPermission.ADMIN)  # Admin only
