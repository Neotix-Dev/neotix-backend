from functools import wraps
from flask import request, jsonify, g
from firebase_admin import auth
from datetime import datetime

from models.user import User
from utils.database import db

def auth_required(pass_user=True):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "No authorization token provided"}), 401
            
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Invalid token format. Use 'Bearer {token}'"}), 401

            try:
                token = auth_header.split(" ")[1]
                decoded_token = auth.verify_id_token(token)
                
                # Get user from database
                user = User.query.filter_by(firebase_uid=decoded_token["uid"]).first()
                if not user:
                    return jsonify({"error": "User not found"}), 404

                # Set both g.user_id and g.current_user
                g.user_id = decoded_token["uid"]
                g.current_user = user
                
                # Only pass current_user if requested
                if pass_user:
                    return f(current_user=user, *args, **kwargs)
                else:
                    return f(*args, **kwargs)
                
            except auth.ExpiredIdTokenError:
                return jsonify({"error": "Token expired"}), 401
            except auth.RevokedIdTokenError:
                return jsonify({"error": "Token revoked"}), 401
            except auth.InvalidIdTokenError:
                return jsonify({"error": "Invalid token"}), 401
            except Exception as e:
                print(f"Auth error: {str(e)}")
                return jsonify({"error": "Authentication failed"}), 401

        return decorated_function
    
    if callable(pass_user):
        f = pass_user
        pass_user = True
        return decorator(f)
    return decorator

def require_auth():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"error": "No authorization header"}), 401

            try:
                # Remove 'Bearer ' from token
                id_token = auth_header.split(" ")[1]
                # Verify the token with revocation check
                decoded_token = auth.verify_id_token(id_token, check_revoked=True)
                
                # Check if token is expired
                if 'exp' in decoded_token:
                    current_time = int(datetime.now().timestamp())
                    if decoded_token['exp'] < current_time:
                        return jsonify({"error": "Token has expired", "code": "token_expired"}), 401

                # Set the user ID in flask.g
                g.user_id = decoded_token["uid"]
                return f(*args, **kwargs)
            except auth.ExpiredIdTokenError:
                return jsonify({"error": "Token has expired", "code": "token_expired"}), 401
            except auth.RevokedIdTokenError:
                return jsonify({"error": "Token has been revoked", "code": "token_revoked"}), 401
            except auth.InvalidIdTokenError:
                return jsonify({"error": "Invalid token", "code": "token_invalid"}), 401
            except Exception as e:
                print(f"Auth error: {str(e)}")
                return jsonify({"error": "Invalid authorization token", "code": "token_invalid"}), 401

        return decorated_function
    return decorator