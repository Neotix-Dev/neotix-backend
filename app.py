from flask import Flask, jsonify
from flask_cors import CORS
from utils.database import db, init_db
from routes.user_preferences import bp as user_preferences_bp
from routes.gpu_listings import bp as gpu_bp
from routes.user import bp as user_bp
from routes.project import bp as project_bp
from models.user import User
from models.project import Project, ProjectGPU
from models.gpu_listing import GPUListing
from commands.fetch_gpu_data import fetch_gpu_data_command
import os
from firebase_admin import credentials
import firebase_admin
from config import Config
from dotenv import load_dotenv
from flask_migrate import Migrate

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Debug: Print environment variables
print("Current working directory:", os.getcwd())
print("Environment file path:", os.path.join(os.path.dirname(__file__), ".env"))
print("DATABASE_URI:", os.getenv("DATABASE_URI"))


def create_app(environ=None, start_response=None):
    """Create and configure the Flask application"""
    app = Flask(__name__, instance_relative_config=True)

    try:
        # Initialize Firebase Admin with your service account
        cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), "firebaseKey.json"))
        firebase_admin.initialize_app(cred)
    except ValueError:
        # Firebase already initialized, skip
        pass

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
        print(f"Warning: Could not verify instance path is writable: {e}")

    # Configure SQLite database with absolute path
    app.config.from_object(Config)

    # Debug: Print configuration
    print("Database URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
    print("Environment DATABASE_URI:", os.getenv("DATABASE_URI"))

    # Initialize database
    db.init_app(app)

    # Initialize database tables
    init_db(app)

    # Initialize flask_migrate
    migrate = Migrate(app, db)

    # Register blueprints
    app.register_blueprint(user_preferences_bp, url_prefix="/api/preferences")
    app.register_blueprint(gpu_bp, url_prefix="/api/gpu")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(project_bp, url_prefix="/api/projects")
    
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

    if environ is not None and start_response is not None:
        return app.wsgi_app(environ, start_response)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0")


#TODO: on 01/15: Improve speed of getting things inside the DB. + There are problems with some duplicates, like 10 of them in case we call the command twice 

#TODO: on 01/15: Improve DB schem for the User GPU selections. 

# TODO: Compute and add score to each GPU 


