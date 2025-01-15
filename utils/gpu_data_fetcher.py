from datetime import datetime
import hashlib
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
    gpu_hash_map = {}  # hash -> gpu_listing
    
    # Get all offers from all providers
    offers = gpuhunt.query()
    
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
            
        # Create hash for comparison
        offer_hash = hash_gpu_listing(offer)
        
        # Skip if we've seen this exact configuration
        if offer_hash in gpu_hash_map:
            continue
            
        # Store in hash map
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
        # Set default price change
        gpu_listing.price_change = "0%"
        
        gpu_hash_map[offer_hash] = gpu_listing
        db.session.add(gpu_listing)
        db.session.flush()
        
        # Create price point
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