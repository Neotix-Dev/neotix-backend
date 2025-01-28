import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.database import db
from models.gpu_listing import GPUListing, Host
from flask import Flask

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///gpu_listings.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    # Drop all tables
    db.drop_all()
    # Create all tables with new schema
    db.create_all()
    print("Database schema has been reset successfully.")
