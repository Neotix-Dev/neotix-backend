# scripts/migrate_to_chroma.py
import sys
import os
import logging

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app import create_app # Assuming your Flask app factory is in app.py
from models.gpu_listing import GPUListing, GPUConfiguration, Host
from utils.vector_db import get_gpu_listings_collection, get_embedding_model
from utils.database import db
from sqlalchemy.orm import joinedload

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_listing_description(listing: GPUListing) -> str:
    """Creates a descriptive text string for a GPUListing object."""
    config = listing.configuration
    host = listing.host
    
    parts = [
        f"Instance: {listing.instance_name}",
        f"Provider: {host.name if host else 'Unknown'}",
        f"GPU: {config.gpu_count}x {config.gpu_vendor or ''} {config.gpu_name or ''}",
        f"VRAM: {config.gpu_memory} GB" if config.gpu_memory else None,
        f"CPU Cores: {config.cpu}" if config.cpu else None,
        f"RAM: {config.memory} GB" if config.memory else None,
        f"Disk: {config.disk_size} GB" if config.disk_size else None,
        f"Price: ${listing.current_price:.2f}/hour",
        f"GPU Score: {config.gpu_score}" if config.gpu_score else None
    ]
    
    return ", ".join(filter(None, parts))

def migrate_listings_to_chroma(batch_size=100):
    """Fetches GPU listings from PostgreSQL and migrates them to ChromaDB."""
    app = create_app()
    with app.app_context():
        logger.info("Starting migration of GPU listings to ChromaDB...")
        
        try:
            collection = get_gpu_listings_collection()
            embedding_model = get_embedding_model()
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB or embedding model: {e}")
            return

        try:
            logger.info("Fetching GPU listings from PostgreSQL...")
            # Eager load related data to avoid N+1 queries
            listings = db.session.query(GPUListing).options(
                joinedload(GPUListing.configuration),
                joinedload(GPUListing.host)
            ).all()
            logger.info(f"Found {len(listings)} GPU listings to migrate.")

            if not listings:
                logger.warning("No GPU listings found in the database. Migration skipped.")
                return

            all_ids = []
            all_embeddings = []
            all_metadatas = []
            all_documents = []

            for i, listing in enumerate(listings):
                if not listing.configuration or not listing.host:
                    logger.warning(f"Skipping listing ID {listing.id} due to missing configuration or host.")
                    continue

                description = create_listing_description(listing)
                
                # Store relevant data in metadata for filtering/retrieval later
                metadata = {
                    "instance_name": listing.instance_name,
                    "host_name": listing.host.name,
                    "gpu_name": listing.configuration.gpu_name,
                    "gpu_vendor": listing.configuration.gpu_vendor,
                    "gpu_count": listing.configuration.gpu_count,
                    "gpu_memory": listing.configuration.gpu_memory,
                    "cpu": listing.configuration.cpu,
                    "memory": listing.configuration.memory,
                    "disk_size": listing.configuration.disk_size,
                    "current_price": listing.current_price,
                    "gpu_score": listing.configuration.gpu_score,
                    "postgres_id": listing.id # Keep track of original ID
                }
                # Ensure all metadata values are ChromaDB compatible types (str, int, float, bool)
                metadata = {k: v for k, v in metadata.items() if v is not None and type(v) in [str, int, float, bool]}
                
                all_ids.append(f"gpu_{listing.id}") # Chroma IDs must be strings
                all_documents.append(description)
                all_metadatas.append(metadata)

                # Generate embeddings in batches
                if (i + 1) % batch_size == 0 or (i + 1) == len(listings):
                    # Process the current batch of documents
                    batch_documents = all_documents[-(i % batch_size + 1):]
                    logger.info(f"Generating embeddings for batch {i // batch_size + 1} (size {len(batch_documents)})...")
                    batch_embeddings = embedding_model.encode(batch_documents, convert_to_numpy=True).tolist()
                    all_embeddings.extend(batch_embeddings)
                    
                    # Add the completed batch to ChromaDB
                    logger.info(f"Adding batch {i // batch_size + 1} to ChromaDB...")
                    current_batch_ids = all_ids[-(i % batch_size + 1):]
                    current_batch_embeddings = all_embeddings[-(i % batch_size + 1):]
                    current_batch_metadatas = all_metadatas[-(i % batch_size + 1):]
                    current_batch_documents_final = all_documents[-(i % batch_size + 1):]
                    
                    try:
                        collection.add(
                            ids=current_batch_ids,
                            embeddings=current_batch_embeddings,
                            metadatas=current_batch_metadatas,
                            documents=current_batch_documents_final
                        )
                        logger.info(f"Successfully added batch {i // batch_size + 1} ({len(current_batch_ids)} items). Total processed: {i + 1}")
                    except Exception as e:
                         logger.error(f"Error adding batch {i // batch_size + 1} to ChromaDB: {e}", exc_info=True)
                         # Decide if you want to stop or continue on batch error
                         # For now, we log and continue with the next batch

            logger.info("Migration process completed.")
            logger.info(f"Total listings processed: {len(all_ids)}")
            logger.info(f"Total embeddings generated: {len(all_embeddings)}")
            logger.info(f"ChromaDB collection '{collection.name}' now contains {collection.count()} items.")

        except Exception as e:
            logger.error(f"An error occurred during migration: {e}", exc_info=True)

if __name__ == "__main__":
    migrate_listings_to_chroma()
