from functools import wraps
from flask import request, jsonify
from models.api_key import APIKey, APIKeyPermission
from utils.database import db
from datetime import datetime, timezone
import secrets
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("api_auth")

# Import this here to avoid circular imports
from models.user import User

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
            logger.debug(f"Auth header X-API-Key: {api_key}")
            
            if not api_key:
                logger.warning("No API key provided")
                return jsonify({
                    'error': 'No API key provided',
                    'message': 'Please provide your API key in the X-API-Key header'
                }), 401
                
            # Check if it's the master key from .env
            master_key = os.getenv('MASTER_API_KEY')
            if master_key and api_key == master_key:
                logger.debug("Master API key matched")
                # Master key has all permissions
                return f(*args, **kwargs)
            
            logger.debug(api_key)
                
            # Check if key exists in database
            key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()
            if key_record:
                logger.debug(f"Found APIKey record id={key_record.id} permission={key_record.permission}")
            if not key_record:
                logger.warning(f"Invalid API key: {api_key}")
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid or has been deactivated'
                }), 401
            
            # Check permission if required
            if required_permission and key_record.permission != required_permission.value:
                logger.warning(f"Insufficient permissions: required={required_permission.value}, got={key_record.permission}")
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires {required_permission.value} permission'
                }), 403
            logger.debug(f"Permission OK for API key {api_key}")
            
            # Update last used timestamp
            key_record.last_used_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.debug(f"Updated last_used_at for API key {api_key}")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Convenience decorators for common permission levels
require_api_key = check_api_key()  # Any valid key
require_admin_key = check_api_key(APIKeyPermission.ADMIN)  # Admin only

def get_user_from_key(api_key):
    """
    Get a user based on their API key.
    Returns None if the key is invalid or the user doesn't exist.
    """
    # First check if it's the master key from .env
    master_key = os.getenv('MASTER_API_KEY')
    if master_key and api_key == master_key:
        # For development/testing, return the first user or create one if none exists
        user = User.query.first()
        if not user:
            user = User(username='admin', email='admin@example.com')
            user.balance = 1000.0  # Start with some funds for testing
            db.session.add(user)
            db.session.commit()
        return user
        
    # Check if key exists in database and get user
    key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()
    if not key_record:
        return None
        
    # Get user associated with this key
    # Note: Assuming there's a user_id field in the APIKey model
    user = User.query.filter_by(id=key_record.user_id).first() if hasattr(key_record, 'user_id') else None
    return user
