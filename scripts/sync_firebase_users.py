import firebase_admin
from firebase_admin import credentials, auth
from datetime import datetime
import sys
import os

# Add the parent directory to sys.path to import app-level modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.user import User
from utils.database import db

def initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        cred = credentials.Certificate('firebaseKey.json')
        firebase_admin.initialize_app(cred)

def get_all_firebase_users():
    """Retrieve all users from Firebase."""
    users = []
    page = None
    while True:
        try:
            result = auth.list_users(page_token=page)
            users.extend(result.users)
            if not result.page_token:
                break
            page = result.page_token
        except Exception as e:
            print(f"Error fetching Firebase users: {e}")
            break
    return users

def sync_users():
    """Sync Firebase users with database users."""
    print("Starting user sync...")
    
    # Get all Firebase users
    firebase_users = get_all_firebase_users()
    firebase_uids = {user.uid for user in firebase_users}
    
    # Get all database users
    db_users = User.query.all()
    db_uids = {user.firebase_uid for user in db_users}
    
    # Track statistics
    stats = {
        'created': 0,
        'updated': 0,
        'disabled': 0,
        'errors': 0
    }
    
    # Process Firebase users
    for firebase_user in firebase_users:
        try:
            db_user = User.query.filter_by(firebase_uid=firebase_user.uid).first()
            
            if not db_user:
                # Create new user
                new_user = User(
                    firebase_uid=firebase_user.uid,
                    email=firebase_user.email or '',
                    email_verified=firebase_user.email_verified,
                    disabled=firebase_user.disabled,
                    first_name=firebase_user.display_name.split()[0] if firebase_user.display_name else '',
                    last_name=' '.join(firebase_user.display_name.split()[1:]) if firebase_user.display_name and len(firebase_user.display_name.split()) > 1 else '',
                    created_at=datetime.utcfromtimestamp(firebase_user.user_metadata.creation_timestamp / 1000),
                    last_login=datetime.utcfromtimestamp(firebase_user.user_metadata.last_sign_in_timestamp / 1000) if firebase_user.user_metadata.last_sign_in_timestamp else None
                )
                db.session.add(new_user)
                stats['created'] += 1
                print(f"Created user: {firebase_user.email}")
            else:
                # Update existing user
                db_user.email = firebase_user.email or db_user.email
                db_user.email_verified = firebase_user.email_verified
                db_user.disabled = firebase_user.disabled
                if firebase_user.display_name:
                    db_user.first_name = firebase_user.display_name.split()[0]
                    db_user.last_name = ' '.join(firebase_user.display_name.split()[1:]) if len(firebase_user.display_name.split()) > 1 else ''
                if firebase_user.user_metadata.last_sign_in_timestamp:
                    db_user.last_login = datetime.utcfromtimestamp(firebase_user.user_metadata.last_sign_in_timestamp / 1000)
                stats['updated'] += 1
                print(f"Updated user: {firebase_user.email}")
        
        except Exception as e:
            print(f"Error processing user {firebase_user.uid}: {str(e)}")
            stats['errors'] += 1
            continue
    
    # Disable users that exist in database but not in Firebase
    for db_user in db_users:
        if db_user.firebase_uid not in firebase_uids and not db_user.disabled:
            db_user.disabled = True
            stats['disabled'] += 1
            print(f"Disabled user: {db_user.email}")
    
    # Commit all changes
    try:
        db.session.commit()
        print("\nSync completed successfully!")
        print(f"Created: {stats['created']}")
        print(f"Updated: {stats['updated']}")
        print(f"Disabled: {stats['disabled']}")
        print(f"Errors: {stats['errors']}")
    except Exception as e:
        print(f"Error committing changes to database: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        initialize_firebase()
        sync_users()
