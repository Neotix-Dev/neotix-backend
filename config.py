import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI",
        "postgresql://postgres:postgres@localhost:5432/neotix"  # Default for local development
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
    EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "embeddings_model")
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")
