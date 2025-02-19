import sys
import os
from flask import Flask
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db
from models.gpu_listing import GPUListing, Host, GPUConfiguration
from models.user import User
from models.project import Project
from models.transaction import Transaction

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:postgres@localhost:5432/neotix"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    try:
        # Drop all tables forcefully with CASCADE
        db.session.execute(text("DROP SCHEMA public CASCADE;"))
        db.session.execute(text("CREATE SCHEMA public;"))
        db.session.commit()

        # Recreate all tables
        db.create_all()
        print("Database schema has been reset successfully.")
    except Exception as e:
        print(f"Error resetting database: {str(e)}")
        db.session.rollback()
