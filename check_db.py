from flask import Flask
from models.gpu_listing import GPUListing
from utils.database import db
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
db.init_app(app)

with app.app_context():
    # Check total number of GPU listings
    total = GPUListing.query.count()
    print(f"Total GPU listings: {total}")
    
    # Check for RTX 3090 listings
    rtx_count = GPUListing.query.filter(GPUListing.gpu_name.ilike('%RTX 3090%')).count()
    print(f"RTX 3090 listings: {rtx_count}")
    
    # Print first 5 GPU names
    gpus = GPUListing.query.limit(5).all()
    print("Sample GPU names:")
    for gpu in gpus:
        print(f"- {gpu.gpu_name}")