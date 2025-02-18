import sys
import os
from datetime import datetime
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Add gpuhunt submodule to Python path
gpuhunt_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gpuhunt', 'src')
sys.path.insert(0, gpuhunt_path)

import gpuhunt
from models.gpu_listing import GPUListing, GPUPricePoint, GPUPriceHistory, Host, GPUConfiguration
from utils.database import db

def hash_gpu_configuration(offer):
    """
    Creates a unique hash of a GPU configuration for comparison
    """
    # Only use hardware configuration fields, ignore provider/instance specific ones
    config_str = f"{offer.gpu_name}:{offer.gpu_vendor}:{offer.gpu_count}:{offer.gpu_memory}:{offer.cpu}:{offer.memory}:{offer.disk_size}"
    return hashlib.sha256(config_str.encode()).hexdigest()

def fetch_gpu_data():
    """
    Fetches GPU data from all providers using gpuhunt and updates the database
    """
    current_time = datetime.utcnow()
    
    # Get all offers from all providers
    logger.info("Starting GPU data fetch from all providers...")
    offers = gpuhunt.query()
    
    # Log unique providers at the start
    providers = set(offer.provider for offer in offers if offer.gpu_count and offer.gpu_count >= 1)
    logger.info(f"Found providers: {', '.join(providers)}")
    logger.info(f"Total number of offers received: {len(offers)}")
    
    current_provider = None
    processed_gpus = 0
    active_providers = set()
    
    for offer in offers:
        # Skip offers without GPUs
        if not offer.gpu_count or offer.gpu_count < 1:
            continue
            
        # Log when switching to a new provider
        # if current_provider != offer.provider:
        #     current_provider = offer.provider
        #     # logger.info(f"Processing provider: {current_provider}")
            
        # Get or create host
        host = Host.query.filter_by(name=offer.provider).first()
        if not host:
            # logger.info(f"Creating new host entry for provider: {offer.provider}")
            host = Host(
                name=offer.provider,
                description=f"GPU provider: {offer.provider}",
                url=""
            )
            db.session.add(host)
            db.session.flush()
            # logger.info(f"Created host with ID: {host.id}")
        
        active_providers.add(host.name)
        
        # Get or create configuration
        config_hash = hash_gpu_configuration(offer)
        config = GPUConfiguration.query.filter_by(hash=config_hash).first()
        if not config:
            # logger.info(f"Creating new GPU configuration for {offer.gpu_name} (Count: {offer.gpu_count})")
            config = GPUConfiguration(
                hash=config_hash,
                gpu_name=offer.gpu_name,
                gpu_vendor=offer.gpu_vendor.value if offer.gpu_vendor else None,
                gpu_count=offer.gpu_count,
                gpu_memory=offer.gpu_memory,
                cpu=offer.cpu,
                memory=offer.memory,
                disk_size=offer.disk_size
            )
            db.session.add(config)
            db.session.flush()
            # logger.info(f"Created configuration with ID: {config.id}")
        
        # Create new listing
        gpu_listing = GPUListing(
            instance_name=offer.instance_name,
            configuration_id=config.id,
            current_price=offer.price,
            host_id=host.id
        )
        gpu_listing.price_change = "N/A"
        db.session.add(gpu_listing)
        db.session.flush()
        # logger.info(f"Created GPU listing with ID: {gpu_listing.id} for instance {offer.instance_name}")
        
        # Update or create price point
        price_point = GPUPricePoint.query.filter_by(
            gpu_listing_id=gpu_listing.id,
            location=offer.location,
            spot=offer.spot
        ).first()
        
        if price_point:
            # logger.info(f"Updating existing price point for listing {gpu_listing.id}")
            price_point.price = offer.price
            price_point.last_updated = current_time
        else:
            # logger.info(f"Creating new price point for listing {gpu_listing.id}")
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
            configuration_id=config.id,
            price=offer.price,
            date=current_time,
            location=offer.location,
            spot=offer.spot
        )
        db.session.add(history)
        
        # Increment processed GPUs counter and log progress
        processed_gpus += 1
        if processed_gpus % 1000 == 0:  
            logger.info(f"Processed {processed_gpus} GPUs...")
            # Add periodic flush to ensure data is being written
            db.session.flush()
    
    # Log completion with provider summary
    logger.info(f"GPU data fetch completed. Total GPUs processed: {processed_gpus}")
    logger.info(f"Active providers in database: {', '.join(active_providers)}")
    
    # Commit all changes
    try:
        logger.info("Attempting to commit all changes to database...")
        db.session.commit()
        logger.info("Successfully committed all GPU data to database")
        logger.info("Database URI: %s", db.engine.url)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving GPU data to database: {str(e)}")
        logger.error(f"Database URI: {db.engine.url}")
        raise e
