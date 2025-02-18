import sys
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth
from dotenv import load_dotenv
from flask import Flask

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db
from models.user import User
from models.cluster import Cluster
from models.rental_gpu import RentalGPU
from models.transaction import Transaction

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/neotix")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        if not firebase_admin._apps:
            cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "firebaseKey.json")
            if not os.path.exists(cred_path):
                raise FileNotFoundError(f"Firebase credentials file not found at {cred_path}")
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized successfully")
    except Exception as e:
        print(f"Error initializing Firebase: {str(e)}")
        sys.exit(1)

def get_firebase_users():
    """Retrieve all users from Firebase"""
    try:
        result = auth.list_users()
        return result.users
    except Exception as e:
        print(f"Error fetching Firebase users: {str(e)}")
        return []

def sync_users():
    """Sync Firebase users with local database"""
    with app.app_context():
        try:
            print("Starting user synchronization...")
            
            # Initialize Firebase
            initialize_firebase()
            
            # Get Firebase users
            firebase_users = get_firebase_users()
            print(f"Found {len(firebase_users)} users in Firebase")
            
            # Track sync statistics
            stats = {"created": 0, "updated": 0, "errors": 0}
            
            # Process each Firebase user
            for fb_user in firebase_users:
                try:
                    # Check if user exists in database
                    db_user = User.query.filter_by(firebase_uid=fb_user.uid).first()
                    
                    if not db_user:
                        # Create new user
                        names = (fb_user.display_name or "").split(" ", 1)
                        first_name = names[0] if names else ""
                        last_name = names[1] if len(names) > 1 else ""
                        
                        db_user = User(
                            firebase_uid=fb_user.uid,
                            email=fb_user.email or "",
                            first_name=first_name,
                            last_name=last_name,
                            email_verified=fb_user.email_verified,
                            disabled=fb_user.disabled,
                            created_at=datetime.utcfromtimestamp(
                                fb_user.user_metadata.creation_timestamp / 1000
                            ),
                            last_login=datetime.utcfromtimestamp(
                                fb_user.user_metadata.last_sign_in_timestamp / 1000
                            ) if fb_user.user_metadata.last_sign_in_timestamp else None,
                            experience_level="beginner"  # Default value
                        )
                        db.session.add(db_user)
                        stats["created"] += 1
                        print(f"Created user: {fb_user.email}")
                        
                    else:
                        # Update existing user
                        names = (fb_user.display_name or "").split(" ", 1)
                        if names:
                            db_user.first_name = names[0]
                            if len(names) > 1:
                                db_user.last_name = names[1]
                        
                        db_user.email = fb_user.email or db_user.email
                        db_user.email_verified = fb_user.email_verified
                        db_user.disabled = fb_user.disabled
                        
                        if fb_user.user_metadata.last_sign_in_timestamp:
                            db_user.last_login = datetime.utcfromtimestamp(
                                fb_user.user_metadata.last_sign_in_timestamp / 1000
                            )
                        
                        stats["updated"] += 1
                        print(f"Updated user: {fb_user.email}")
                    
                except Exception as e:
                    print(f"Error processing user {fb_user.email}: {str(e)}")
                    stats["errors"] += 1
                    continue
            
            # Commit all changes
            db.session.commit()
            
            print("\nSync completed!")
            print(f"Created: {stats['created']}")
            print(f"Updated: {stats['updated']}")
            print(f"Errors: {stats['errors']}")
            
        except Exception as e:
            print(f"Error during sync: {str(e)}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    sync_users()
