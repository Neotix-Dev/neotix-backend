import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models.gpu_listing import Host, GPUListing
from utils.database import db
from datetime import datetime


def load_json_data(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def populate_db():
    app = create_app()

    # Override the database URI for local population
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")

    with app.app_context():
        print("Starting database population...")

        # Clear existing data
        print("Clearing existing data...")
        db.session.query(GPUListing).delete()
        db.session.query(Host).delete()
        db.session.commit()
        print("Data cleared successfully")

        # Add hosts (unique providers from the JSON)
        print("Loading JSON data...")
        json_data = load_json_data(
            f"scripts/web-scrapping/normalized/normalized_gpu_data_20241120.json"
        )
        print(f"Loaded {len(json_data)} GPU entries from JSON")

        unique_providers = set(item["provider"] for item in json_data)
        print(f"Found {len(unique_providers)} unique providers")

        hosts = []
        for provider in unique_providers:
            host_data = {"name": provider, "description": f"{provider} GPU Provider"}
            host = Host(**host_data)
            db.session.add(host)
            hosts.append(host)
        db.session.commit()
        print(f"Added {len(hosts)} hosts to database")

        # Create a mapping of provider names to host IDs
        host_mapping = {host.name: host.id for host in hosts}
        print("Created host mapping")

        # Add GPU listings
        gpu_listings = []
        for item in json_data:
            try:
                gpu_data = {
                    "name": item["name"],
                    "current_price": round(float(item["pricing"]["amount"]), 2),
                    "price_metric": f"/{item['pricing']['unit']}",
                    "price_change": round(
                        float(item["pricing"]["price_change"] or 0.0), 2
                    ),
                    "reliability": round(
                        float(item["specifications"]["reliability"] or 0.0), 2
                    ),
                    "flops": round(float(item["specifications"]["flops"] or 0.0), 2),
                    "vram": round(float(item["specifications"]["vram"] or 0.0), 2),
                    "description": f"{item['name']} from {item['provider']}",
                    "image_url": "",
                    "host_id": host_mapping[item["provider"]],
                    "number_of_gpus": round(
                        float(item["specifications"]["number_of_gpus"] or 0.0), 2
                    ),
                }
                gpu = GPUListing(**gpu_data)
                db.session.add(gpu)
                gpu_listings.append(gpu)
            except Exception as e:
                print(f"Error adding GPU {item['name']}: {str(e)}")
                continue
        db.session.commit()
        print(f"Database populated successfully with {len(gpu_listings)} GPU listings!")


if __name__ == "__main__":
    populate_db()
