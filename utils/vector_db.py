import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import os
import logging

logger = logging.getLogger(__name__)

_client = None
_embedding_model = None
_collection = None

def get_chroma_client():
    """Initializes and returns a persistent ChromaDB client."""
    global _client
    if _client is None:
        try:
            persistent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'chroma_data'))
            if not os.path.exists(persistent_path):
                os.makedirs(persistent_path)
            logger.info(f"Initializing ChromaDB client with persistent path: {persistent_path}")
            _client = chromadb.PersistentClient(path=persistent_path, settings=Settings(anonymized_telemetry=False))
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}", exc_info=True)
            raise
    return _client

def get_embedding_model():
    """Loads and returns the Sentence Transformer model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            # Using a lightweight and effective model suitable for semantic search
            model_name = 'all-MiniLM-L6-v2'
            logger.info(f"Loading embedding model: {model_name}")
            _embedding_model = SentenceTransformer(model_name)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}", exc_info=True)
            raise
    return _embedding_model

def get_gpu_listings_collection():
    """Gets or creates the 'gpu_listings' collection in ChromaDB."""
    global _collection
    if _collection is None:
        client = get_chroma_client()
        model = get_embedding_model() # Ensure model is loaded before getting collection
        try:
            logger.info("Getting or creating 'gpu_listings' collection.")
            # The embedding function is implicitly handled by chromadb when using SentenceTransformer models > 0.4
            _collection = client.get_or_create_collection(
                name="gpu_listings",
                # The metadata ensures chromadb uses the correct embedding model settings
                metadata={"hnsw:space": "cosine"} # Using cosine distance for similarity
            )
            logger.info("'gpu_listings' collection obtained successfully.")
        except Exception as e:
            logger.error(f"Failed to get or create 'gpu_listings' collection: {e}", exc_info=True)
            raise
    return _collection

# Optional: Function to generate embeddings directly if needed outside ChromaDB's context
def generate_embedding(text):
    """Generates an embedding for the given text using the loaded model."""
    model = get_embedding_model()
    if not model:
        raise RuntimeError("Embedding model not loaded.")
    try:
        embedding = model.encode(text, convert_to_numpy=True) # Chroma prefers numpy arrays
        return embedding.tolist() # Convert to list for easier handling/storage if needed outside chroma
    except Exception as e:
        logger.error(f"Failed to generate embedding for text: '{text[:50]}...': {e}", exc_info=True)
        raise

# Consider adding a shutdown hook or similar mechanism if running in a long-lived application
# to properly clean up resources if necessary, though PersistentClient is generally robust.
