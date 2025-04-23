from flask import Flask, jsonify
from flask_cors import CORS
from utils.database import db, init_db
from routes.user_preferences import bp as user_preferences_bp
from routes.gpu_listings import bp as gpu_bp
from routes.user import bp as user_bp
from routes.api import bp as api_bp
from routes.cluster import bp as cluster_bp
from routes.transactions import bp as transactions_bp
from routes.analytics import bp as analytics_bp
from models.user import User
from models.cluster import Cluster
from models.rental_gpu import RentalGPU
from models.gpu_listing import GPUListing
from models.transaction import Transaction
from commands.fetch_gpu_data import fetch_gpu_data_command
import os
from firebase_admin import credentials
import firebase_admin
from config import Config
from dotenv import load_dotenv
from flask_migrate import Migrate
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Debug: Print environment variables
logger.info("Current working directory: %s", os.getcwd())
logger.info(
    "Environment file path: %s", os.path.join(os.path.dirname(__file__), ".env")
)
logger.info("DATABASE_URI: %s", os.getenv("DATABASE_URI"))


def create_app(environ=None, start_response=None):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)

    try:
        # Initialize Firebase Admin with your service account
        cred = credentials.Certificate(
            os.path.join(os.path.dirname(__file__), "firebaseKey.json")
        )
        firebase_admin.initialize_app(cred)
    except ValueError:
        # Firebase already initialized, skip
        pass

    # Enable Flask's logging
    app.logger.setLevel(logging.INFO)

    # Configure CORS - Allow specific origins
    app.config["CORS_HEADERS"] = "Content-Type"
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-Requested-With",
                    "Accept",
                    "Origin",
                ],
                "expose_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True,
            }
        },
    )

    # Ensure the instance folder exists and is writable
    try:
        instance_path = app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        # Test if directory is writable
        test_file = os.path.join(instance_path, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        logger.warning(f"Could not verify instance path is writable: {e}")

    # Configure database
    app.config.from_object(Config)
    # Override the database URI directly
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:postgres@localhost:5432/neotix"

    # Debug: Print configuration
    logger.info("Database URI: %s", app.config.get("SQLALCHEMY_DATABASE_URI"))

    # Initialize database
    db.init_app(app)

    # Initialize database tables
    init_db(app)

    # Initialize flask_migrate
    migrate = Migrate(app, db)

    # Register blueprints
    app.register_blueprint(user_preferences_bp, url_prefix="/api/user-preferences")
    app.register_blueprint(gpu_bp, url_prefix="/api/gpu")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(api_bp, url_prefix="/api")
    
    app.register_blueprint(cluster_bp, url_prefix="/api/clusters")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

    # Register CLI commands
    app.cli.add_command(fetch_gpu_data_command)

    # Add CORS headers to all responses
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    # Add health endpoint for monitoring
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "neotix-backend",
            "version": "1.0.0"
        }), 200

    if environ is not None and start_response is not None:
        return app.wsgi_app(environ, start_response)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0")


# TODO: on 01/15: Improve speed of getting things inside the DB. + There are problems with some duplicates, like 10 of them in case we call the command twice

# TODO: on 01/15: Improve DB schem for the User GPU selections.

# TODO: Compute and add score to each GPU

# TODO: AWS Copilot

# TODO: Supabase

# TODO: frontend using Vercel!

# TODO:
