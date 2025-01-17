import sys
import os
from datetime import datetime
import hashlib

# Add gpuhunt submodule to Python path
gpuhunt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gpuhunt', 'src')
sys.path.insert(0, gpuhunt_path)

import gpuhunt
from models.gpu_listing import GPUListing, GPUPricePoint, GPUPriceHistory, Host
from utils.database import db

def hash_gpu_listing(offer):
    """
    Creates a unique hash of a GPU listing for comparison
    """
    # Create a deterministic string of all relevant fields
    listing_str = f"{offer.instance_name}:{offer.gpu_name}:{offer.gpu_count}:{offer.gpu_memory}:{offer.cpu}:{offer.memory}:{offer.disk_size}:{offer.provider}:{offer.location}:{offer.spot}"
    
    # Create SHA-256 hash
    return hashlib.sha256(listing_str.encode()).hexdigest()

def fetch_gpu_data():
    """
    Fetches GPU data from all providers using gpuhunt and updates the database
    """
    current_time = datetime.utcnow()
    
    # Get all offers from all providers
    offers = gpuhunt.query()
    
    # Get all existing listings for deduplication
    existing_listings = {}
    for listing in GPUListing.query.all():
        # Create a unique key for each listing
        key = f"{listing.instance_name}:{listing.gpu_name}:{listing.gpu_count}:{listing.gpu_memory}:{listing.cpu}:{listing.memory}:{listing.disk_size}:{listing.host.name}"
        existing_listings[key] = listing
    
    for offer in offers:
        # Skip GCP offers and those without GPUs
        if offer.provider == "gcp" or not offer.gpu_count or offer.gpu_count < 1:
            continue
            
        # Get or create host
        host = Host.query.filter_by(name=offer.provider).first()
        if not host:
            host = Host(
                name=offer.provider,
                description=f"GPU provider: {offer.provider}",
                url=""
            )
            db.session.add(host)
            db.session.flush()
            
        # Create key for deduplication
        listing_key = f"{offer.instance_name}:{offer.gpu_name}:{offer.gpu_count}:{offer.gpu_memory}:{offer.cpu}:{offer.memory}:{offer.disk_size}:{offer.provider}"
        
        if listing_key in existing_listings:
            # Update existing listing
            gpu_listing = existing_listings[listing_key]
            if gpu_listing.current_price != offer.price:
                # Calculate price change percentage
                price_change = ((offer.price - gpu_listing.current_price) / gpu_listing.current_price) * 100
                gpu_listing.price_change = f"{price_change:+.1f}%"
            gpu_listing.current_price = offer.price
            gpu_listing.last_updated = current_time
            gpu_listing.update_gpu_score()
        else:
            # Create new listing
            gpu_listing = GPUListing(
                instance_name=offer.instance_name,
                gpu_name=offer.gpu_name,
                gpu_vendor=offer.gpu_vendor.value if offer.gpu_vendor else None,
                gpu_count=offer.gpu_count,
                gpu_memory=offer.gpu_memory,
                current_price=offer.price,
                cpu=offer.cpu,
                memory=offer.memory,
                disk_size=offer.disk_size,
                host_id=host.id
            )
            gpu_listing.price_change = "0%"
            db.session.add(gpu_listing)
            db.session.flush()
            existing_listings[listing_key] = gpu_listing
        
        # Update or create price point
        price_point = GPUPricePoint.query.filter_by(
            gpu_listing_id=gpu_listing.id,
            location=offer.location,
            spot=offer.spot
        ).first()
        
        if price_point:
            # Update existing price point
            price_point.price = offer.price
            price_point.last_updated = current_time
        else:
            # Create new price point
            price_point = GPUPricePoint(
                gpu_listing_id=gpu_listing.id,
                price=offer.price,
                location=offer.location,
                spot=offer.spot,
                last_updated=current_time
            )
            db.session.add(price_point)
        
        # Add historical price record
        history = GPUPriceHistory(
            gpu_listing_id=gpu_listing.id,
            price=offer.price,
            date=current_time,
            location=offer.location,
            spot=offer.spot
        )
        db.session.add(history)
    
    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e