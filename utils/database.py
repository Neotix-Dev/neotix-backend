from flask_sqlalchemy import SQLAlchemy
import os
import logging
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy import create_engine

db = SQLAlchemy()
logger = logging.getLogger(__name__)


def init_db(app):
    try:
        with app.app_context():
            database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
            logger.info(f"Using database at: {database_uri}")

            # Create database if it doesn't exist
            engine = create_engine(database_uri)
            if not database_exists(engine.url):
                create_database(engine.url)
                logger.info(f"Created database at: {database_uri}")

            # Create all tables
            logger.info("Creating tables...")
            db.create_all()
            logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
