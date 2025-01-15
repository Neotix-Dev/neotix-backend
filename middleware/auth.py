from functools import wraps
from flask import request, jsonify, g
from firebase_admin import auth


def require_auth():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'No authorization header'}), 401

            try:
                # Remove 'Bearer ' from token
                id_token = auth_header.split(' ')[1]
                # Verify the token
                decoded_token = auth.verify_id_token(id_token)
                # Set the user ID in flask.g
                g.user_id = decoded_token['uid']
                return f(*args, **kwargs)
            except Exception as e:
                print(f"Auth error: {str(e)}")
                return jsonify({'error': 'Invalid token'}), 401
        return decorated_function
    return decorator
