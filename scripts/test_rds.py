#!/usr/bin/env python3
from flask import Flask
from models.gpu_listing import GPUListing
from models.host import Host
from flask_sqlalchemy import SQLAlchemy
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def test_rds_connection():
    """Test RDS connection and data operations"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db = SQLAlchemy(app)
    
    with app.app_context():
        try:
            # Test 1: Verify connection
            print("1. Testing database connection...")
            db.engine.connect()
            print("✅ Database connection successful!")
            
            # Test 2: Verify tables exist
            print("\n2. Verifying tables exist...")
            tables = db.engine.table_names()
            required_tables = ['gpu_listings', 'hosts']
            for table in required_tables:
                if table in tables:
                    print(f"✅ Table '{table}' exists")
                else:
                    print(f"❌ Table '{table}' is missing")
            
            # Test 3: Insert sample data
            print("\n3. Inserting sample data...")
            
            # Create host if not exists
            vultr_host = Host.query.filter_by(name='vultr').first()
            if not vultr_host:
                vultr_host = Host(name='vultr')
                db.session.add(vultr_host)
                db.session.commit()
                print("✅ Created 'vultr' host")
            
            # Sample GPU data
            sample_gpu = {
                "cpu": 2,
                "current_price": 0.059,
                "disk_size": 50,
                "gpu_count": 1,
                "gpu_memory": 2,
                "gpu_name": "A16",
                "gpu_score": 73.6,
                "gpu_vendor": "nvidia",
                "instance_name": "vcg-a16-2c-8g-2vram",
                "memory": 8
            }
            
            # Create GPU listing
            new_gpu = GPUListing(
                instance_name=sample_gpu['instance_name'],
                gpu_name=sample_gpu['gpu_name'],
                gpu_vendor=sample_gpu['gpu_vendor'],
                gpu_count=sample_gpu['gpu_count'],
                gpu_memory=sample_gpu['gpu_memory'],
                current_price=sample_gpu['current_price'],
                cpu=sample_gpu['cpu'],
                memory=sample_gpu['memory'],
                disk_size=sample_gpu['disk_size'],
                host_id=vultr_host.id
            )
            db.session.add(new_gpu)
            db.session.commit()
            print("✅ Inserted sample GPU listing")
            
            # Test 4: Query data
            print("\n4. Querying inserted data...")
            gpu = GPUListing.query.filter_by(instance_name=sample_gpu['instance_name']).first()
            if gpu:
                print("✅ Successfully retrieved GPU data:")
                print(f"Instance: {gpu.instance_name}")
                print(f"GPU: {gpu.gpu_name}")
                print(f"Price: ${gpu.current_price}")
                print(f"Provider: {gpu.host.name}")
            else:
                print("❌ Failed to retrieve GPU data")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            raise e

if __name__ == "__main__":
    test_rds_connection()
