import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database connection details from environment
DATABASE_URI = os.getenv("DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/neotix")

def reset_database():
    try:
        # Create database engine
        engine = create_engine(DATABASE_URI)
        
        with engine.connect() as connection:
            print("Starting database reset...")
            
            # Start a transaction
            trans = connection.begin()
            try:
                # Disable foreign key checks during reset
                connection.execute(text("SET session_replication_role = 'replica';"))
                
                # Drop the entire public schema and recreate it
                print("Dropping public schema...")
                connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
                connection.execute(text("CREATE SCHEMA public;"))
                
                # Reset the search path
                connection.execute(text("SET search_path TO public;"))
                
                # Re-enable foreign key checks
                connection.execute(text("SET session_replication_role = 'origin';"))
                
                # Commit the transaction
                trans.commit()
                print("Database schema has been reset successfully.")
                
            except Exception as e:
                # Rollback in case of error
                trans.rollback()
                print(f"Error during schema reset: {str(e)}")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    reset_database()
