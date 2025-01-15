#!/usr/bin/env python3
import subprocess
import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(command, shell=False):
    """Run a command and return its output"""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.cmd}")
        logger.error(f"Error output: {e.stderr}")
        return None

def setup_postgres():
    """Set up PostgreSQL for the Neotix project"""
    try:
        # Check if PostgreSQL is running
        logger.info("Checking PostgreSQL status...")
        status = run_command(["brew", "services", "list"])
        if "postgresql@15" not in status or "started" not in status:
            logger.info("Starting PostgreSQL...")
            run_command(["brew", "services", "start", "postgresql@15"])

        # Create postgres superuser if it doesn't exist
        logger.info("Creating postgres superuser...")
        run_command(["createuser", "-s", "postgres"])
        
        # Set password for postgres user
        logger.info("Setting password for postgres user...")
        run_command([
            "psql",
            "-d", "postgres",
            "-c", "ALTER USER postgres WITH PASSWORD 'postgres';"
        ])

        # Create neotix database if it doesn't exist
        logger.info("Creating neotix database...")
        run_command(["createdb", "neotix"])

        # Update local .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        env_content = """DATABASE_URI=postgresql://postgres:postgres@localhost:5432/neotix
MILVUS_HOST=localhost
MILVUS_PORT=19530
EMBEDDING_MODEL_PATH=sentence-transformers/all-MiniLM-L6-v2
QDRANT_HOST=localhost
QDRANT_PORT=6333"""

        with open(env_path, 'w') as f:
            f.write(env_content)
        
        logger.info("Environment file updated successfully")
        
        logger.info("""
PostgreSQL setup completed successfully!
Your database is now configured with:
- Database name: neotix
- Username: postgres
- Password: postgres
- Port: 5432

To start using the database:
1. Make sure PostgreSQL is running: brew services start postgresql@15
2. Your .env file has been updated with the correct DATABASE_URI
3. Run your Flask application to create the tables
""")

    except Exception as e:
        logger.error(f"Error setting up PostgreSQL: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    setup_postgres()
