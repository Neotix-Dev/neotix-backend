from flask import Blueprint, request, jsonify, g
from models.user import User
from utils.database import db
from middleware.auth import require_auth
from datetime import datetime
import firebase_admin
from firebase_admin import auth as firebase_auth

bp = Blueprint("user_bp", __name__)


@bp.route("/sync", methods=["POST"])
@require_auth()
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
@require_auth()
def get_user_profile():
    """Get user profile including preferences"""
    try:
        user_id = g.user_id  # Get user ID from auth context
        user = User.query.filter_by(firebase_uid=user_id).first()
        print("user", user)
        if not user:
            return jsonify({"error": "User not found"}), 404

        profile = user.to_dict()
        # Add preference data
        print(profile)
        # profile.update(
        #     {
        #         "rented_gpus": [gpu.to_dict() for gpu in user.rented_gpus],
        #         "price_alerts": [alert.to_dict() for alert in user.price_alerts],
        #         "selected_gpus": [gpu.to_dict() for gpu in user.selected_gpus],
        #         "favorite_gpus": [gpu.to_dict() for gpu in user.favorite_gpus],
        #     }
        # )

        return jsonify(profile), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/profile", methods=["PUT"])
@require_auth()
def update_user_profile():
    """Update user profile information"""
    try:
        data = request.json
        user_id = g.user_id  # Get user ID from auth context
        user = User.query.filter_by(firebase_uid=user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Update fields if provided
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "organization" in data:
            user.organization = data["organization"]
        if "experience_level" in data:
            user.experience_level = data["experience_level"]

        db.session.commit()
        return jsonify(user.to_dict()), 200
    except Exception as e:
        print(f"Error in update_user_profile: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/", methods=["DELETE"])
@require_auth()
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
def register_user():
    """Register a new user and return a custom token"""
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        organization = data.get("organization")
        experience_level = data.get("experience_level", "beginner")
        referral_source = data.get("referral_source")

        # Create the user in Firebase
        firebase_user = firebase_auth.create_user(
            email=email, password=password, display_name=f"{first_name} {last_name}"
        )

        # Create custom token
        custom_token = firebase_auth.create_custom_token(firebase_user.uid)

        # Create user in our database
        user = User(
            firebase_uid=firebase_user.uid,
            email=email,
            first_name=first_name,
            last_name=last_name,
            organization=organization,
            experience_level=experience_level,
            email_verified=False,
            disabled=False,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow(),
            referral_source=referral_source,
        )
        db.session.add(user)
        db.session.commit()

        return (
            jsonify({"token": custom_token.decode("utf-8"), "user": user.to_dict()}),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bp.route("/update", methods=["POST"])
@require_auth()
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
