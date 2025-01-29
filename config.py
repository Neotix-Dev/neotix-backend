import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URI",
        "postgresql://postgres.ngwmecujqmjdkepoufcp:Neotix12@aws-0-us-west-1.pooler.supabase.com:6543/postgres"  # Default for local development
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
