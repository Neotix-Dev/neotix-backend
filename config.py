import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI",
        "postgresql://postgres:postgres@localhost:5432/neotix"  # Default for local development
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
