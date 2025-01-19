#!/usr/bin/env python3
import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from flask import Flask
from models.gpu_listing import GPUListing, GPUPricePoint, GPUPriceHistory
from models.host import Host
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import MetaData

load_dotenv()

def create_tables():
    """Initialize database tables in AWS RDS"""
    app = Flask(__name__)
    
    # Configure the Flask app with AWS RDS credentials
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize SQLAlchemy with extend_existing=True
    metadata = MetaData()
    db = SQLAlchemy(app, metadata=metadata)
    
    with app.app_context():
        # Create all tables
        metadata.reflect(bind=db.engine)
        db.create_all()
        print("Successfully verified/created database tables in AWS RDS")

if __name__ == "__main__":
    create_tables()
