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
    print(f"\n=== GPU Data Fetching Report ===")
    print(f"Found {len(offers)} total offers from all providers")
    filtered_offers = [offer for offer in offers if (offer.provider == 'gcp' or not offer.gpu_count or offer.gpu_count < 1)]
    print(f"Filtering out {len(filtered_offers)} offers (GCP or invalid GPU count)")
    valid_offers = [offer for offer in offers if offer.provider != 'gcp' and offer.gpu_count and offer.gpu_count >= 1]
    print(f"Processing {len(valid_offers)} valid offers\n")
    print(f"Found {len(existing_listings)} existing listings in database\n")
    
    new_listings = 0
    updated_listings = 0
    skipped_listings = 0
    processed_offers = set()
    unique_listings = set()  # Track unique instance configurations
    
    # Dictionary to track lowest prices per instance
    lowest_prices = {}
    
    # First pass: Find lowest price for each instance across all locations
    for offer in offers:
        if offer.provider == "gcp" or not offer.gpu_count or offer.gpu_count < 1:
            continue
            
        listing_key = f"{offer.instance_name}:{offer.gpu_name}:{offer.gpu_count}:{offer.gpu_memory}:{offer.cpu}:{offer.memory}:{offer.disk_size}:{offer.provider}"
        offer_key = f"{listing_key}:{offer.location}"
        
        if offer_key in processed_offers:
            continue
            
        processed_offers.add(offer_key)
        unique_listings.add(listing_key)
        
        if listing_key not in lowest_prices or offer.price < lowest_prices[listing_key]:
            lowest_prices[listing_key] = offer.price
    
    # Second pass: Create or update listings with lowest prices
    processed_offers.clear()  # Reset for second pass
    
    for offer in offers:
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
            
        listing_key = f"{offer.instance_name}:{offer.gpu_name}:{offer.gpu_count}:{offer.gpu_memory}:{offer.cpu}:{offer.memory}:{offer.disk_size}:{offer.provider}"
        offer_key = f"{listing_key}:{offer.location}"
        
        # Skip if we've already processed this exact offer
        if offer_key in processed_offers:
            skipped_listings += 1
            continue
        processed_offers.add(offer_key)
        
        # Only create/update if this is the lowest price for this instance
        if offer.price == lowest_prices[listing_key]:
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
                    updated_listings += 1
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
                new_listings += 1
        
        # Update or create price point
        price_point = GPUPricePoint.query.filter_by(
            gpu_listing_id=gpu_listing.id if 'gpu_listing' in locals() else None,
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
                gpu_listing_id=gpu_listing.id if 'gpu_listing' in locals() else None,
                price=offer.price,
                location=offer.location,
                spot=offer.spot,
                last_updated=current_time
            )
            db.session.add(price_point)
        
        # Add historical price record
        history = GPUPriceHistory(
            gpu_listing_id=gpu_listing.id if 'gpu_listing' in locals() else None,
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
    
    print(f"\n=== Summary ===")
    print(f"Added {new_listings} new listings")
    print(f"Updated {updated_listings} existing listings")
    print(f"Skipped {skipped_listings} duplicate offers")
    print(f"Total unique instance configurations: {len(unique_listings)}")
    print(f"Total unique offers (including locations): {len(processed_offers)}\n")