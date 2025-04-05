from flask import Blueprint, request, jsonify, g
from utils.database import db
from models.user import User
from middleware.auth import auth_required
import traceback
from datetime import datetime
import firebase_admin
from firebase_admin import auth as firebase_auth

bp = Blueprint("user", __name__, url_prefix="/api/users")


@bp.route("/sync", methods=["POST"])
@auth_required
def sync_user():
    """Sync Firebase user with backend database"""
    try:
        # Check if user already exists
        user = User.query.filter_by(firebase_uid=g.user_id).first()

        # Get user data from Firebase
        firebase_user = firebase_auth.get_user(g.user_id)
        if user:
            # Update existing user
            user.last_login = datetime.utcnow()
            print("updated user", user)
        else:
            # Create new user
            name_parts = (
                firebase_user.display_name.split()
                if firebase_user.display_name
                else ["", ""]
            )
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            user = User(
                firebase_uid=g.user_id,  # Use the verified UID from the token
                email=firebase_user.email,
                first_name=first_name,
                last_name=last_name,
                email_verified=firebase_user.email_verified,
                disabled=firebase_user.disabled,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow(),
            )
            print("created user", user)
            db.session.add(user)

        db.session.commit()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        print(f"Error in sync_user: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/profile", methods=["GET"])
@auth_required
def get_profile(current_user):
    """Get user profile"""
    try:
        # User is passed as current_user parameter
        return jsonify(current_user.to_dict()), 200
    except Exception as e:
        print(f"Error in get_profile: {str(e)}")
        traceback.print_exc()  # More detailed error logging
        return jsonify({"error": "Failed to retrieve user profile", "details": str(e)}), 500


@bp.route("/profile", methods=["PUT"])
@auth_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        user = g.current_user
        
        # Update user fields
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "profile_pic_url" in data:
            user.profile_pic_url = data["profile_pic_url"]
            
        try:
            # Also update Firebase user if applicable
            firebase_auth = auth.Client()
            firebase_auth.update_user(
                g.user_id, 
                display_name=f"{user.first_name} {user.last_name}"
            )
        except Exception as e:
            # Log Firebase error but don't fail the request
            print(f"Failed to update Firebase display name: {str(e)}")
            
        db.session.commit()
        return jsonify({"message": "Profile updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error in update_profile: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Failed to update profile", "details": str(e)}), 500


@bp.route("/", methods=["DELETE"])
@auth_required
def delete_user():
    """Delete user and all associated preferences"""
    try:
        firebase_user = request.user
        user = User.query.filter_by(firebase_uid=firebase_user["uid"]).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/register", methods=["POST"])
def register():
    """Register a new user"""
    try:
        data = request.get_json()

        # Check for required fields
        required_fields = ["firebase_uid", "email"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if user already exists
        existing_user = User.query.filter_by(firebase_uid=data["firebase_uid"]).first()
        if existing_user:
            return jsonify({"error": "User already exists"}), 409

        # Create new user
        new_user = User(
            firebase_uid=data["firebase_uid"],
            email=data["email"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            profile_pic_url=data.get("profile_pic_url", ""),
        )

        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "User registered successfully", "user_id": new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error in register: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/update", methods=["POST"])
@auth_required
def update_user_data():
    """Update authenticated user's data"""
    try:
        data = request.get_json()
        user_id = g.user_id  # Get user ID from auth context

        print(f"Updating user data for user_id: {user_id}")  # Debug log
        print(f"Request data: {data}")  # Debug log

        # Get required fields
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        organization = data.get("organization")
        experience_level = data.get("experience_level")
        referral_source = data.get("referral_source")

        # Update user data in database

        if not all([first_name, last_name, organization, experience_level]):
            missing = [
                f
                for f, v in [
                    ("first_name", first_name),
                    ("last_name", last_name),
                    ("organization", organization),
                    ("experience_level", experience_level),
                ]
                if not v
            ]
            return (
                jsonify({"error": f"Missing required fields: {', '.join(missing)}"}),
                400,
            )

        try:
            # Try to get Firebase user first to validate the ID
            firebase_user = firebase_auth.get_user(user_id)
            print(f"Firebase user found: {firebase_user.uid}")  # Debug log
        except Exception as e:
            print(f"Error getting Firebase user: {str(e)}")  # Debug log
            return jsonify({"error": "Invalid user ID"}), 400

        # Update user in database
        user = User.query.filter_by(firebase_uid=user_id).first()
        if not user:
            print(f"Creating new user for Firebase ID: {user_id}")  # Debug log
            # Create user if they don't exist (for social auth)
            user = User(
                firebase_uid=user_id,
                email=firebase_user.email,
                first_name=first_name,
                last_name=last_name,
                organization=organization,
                experience_level=experience_level,
                referral_source=referral_source,
                email_verified=firebase_user.email_verified,
                disabled=firebase_user.disabled,
                created_at=firebase_user.metadata.get("createdAt"),
                last_login=datetime.utcnow(),
            )
            db.session.add(user)
        else:
            print(f"Updating existing user: {user.id}")  # Debug log
            # Update existing user
            user.first_name = first_name
            user.last_name = last_name
            user.organization = organization
            user.experience_level = experience_level
            user.referral_source = referral_source

        # Update Firebase display name
        try:
            firebase_auth.update_user(user_id, display_name=f"{first_name} {last_name}")
            print(f"Updated Firebase display name for user: {user_id}")  # Debug log
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Failed to update Firebase display name: {str(e)}")

        db.session.commit()
        print(f"Successfully updated user data in database")  # Debug log

        return jsonify({"message": "User data updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating user data: {str(e)}")
        return jsonify({"error": str(e)}), 500
