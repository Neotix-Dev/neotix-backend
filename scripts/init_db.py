#!/usr/bin/env python3
import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from models.user import User
from models.cluster import Cluster
from models.gpu_listing import GPUListing, GPUConfiguration, Host, GPUPricePoint, GPUPriceHistory
from models.rental_gpu import RentalGPU

def init_db():
    """Initialize the database schema"""
    print("Creating database tables...")
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()
