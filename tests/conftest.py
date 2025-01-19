import pytest
from app import create_app
from utils.database import db
from models.user import User
from models.project import Project
from models.gpu_listing import GPUListing, Host
from datetime import datetime
from sqlalchemy.orm import sessionmaker, scoped_session
from unittest.mock import patch, MagicMock
import jwt
import time


class MockFirebaseUser:
    """Mock Firebase user object for testing."""

    def __init__(self):
        self.uid = "test_user_id"
        self.email = "test@example.com"
        self.display_name = "Test User"
        self.email_verified = True
        self.disabled = False


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update(
        {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}
    )

    # Create tables
    with app.app_context():
        db.create_all()

    yield app

    # Clean up / reset resources
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def session(app):
    """Create a new database session for a test."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()

        # Create a session factory bound to this connection
        session_factory = sessionmaker(bind=connection)
        session = scoped_session(session_factory)

        # Override the default session with our test session
        old_session = db.session
        db.session = session

        yield session

        # Rollback the transaction and restore the default session
        transaction.rollback()
        connection.close()
        session.remove()
        db.session = old_session


@pytest.fixture
def mock_firebase():
    """Mock Firebase authentication and user data."""
    # Create a test JWT token
    token_payload = {
        "uid": "test_user_id",
        "email": "test@example.com",
        "name": "Test User",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # Token expires in 1 hour
    }
    test_token = jwt.encode(token_payload, "test_secret", algorithm="HS256")

    # Mock Firebase auth.verify_id_token
    with patch("firebase_admin.auth.verify_id_token") as mock_verify:
        mock_verify.return_value = token_payload

        # Mock Firebase auth.get_user
        with patch("firebase_admin.auth.get_user") as mock_get_user:
            mock_get_user.return_value = MockFirebaseUser()

            yield {
                "token": test_token,
                "user_id": "test_user_id",
                "verify_id_token": mock_verify,
                "get_user": mock_get_user,
            }


@pytest.fixture
def auth_headers(mock_firebase):
    """Authentication headers for test requests."""
    return {
        "Authorization": f"Bearer {mock_firebase['token']}",
        "Firebase-ID": mock_firebase["user_id"],
    }


@pytest.fixture
def test_user(session):
    """Create a test user."""
    # First clean up any existing user
    session.query(User).filter_by(firebase_uid="test_user_id").delete()
    session.commit()

    # Create new user
    user = User(
        firebase_uid="test_user_id",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        organization="Test Org",
        experience_level="intermediate",
        email_verified=True,
        disabled=False,
        created_at=datetime.utcnow(),
        last_login=datetime.utcnow(),
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def test_project(session, test_user):
    """Create a test project."""
    project = Project(
        name="Test Project", description="Test Description", user_id=test_user.id
    )
    session.add(project)
    session.commit()
    return project


@pytest.fixture
def test_host(session):
    """Create a test host."""
    host = Host(
        name="Test Host", description="Test Host Description", url="https://test.host"
    )
    session.add(host)
    session.commit()
    return host


@pytest.fixture
def test_gpu(session, test_host):
    """Create a test GPU listing."""
    gpu = GPUListing(
        instance_name="test-instance",
        gpu_name="Test GPU",
        gpu_vendor="NVIDIA",
        gpu_count=1,
        gpu_memory=8.0,
        current_price=1.0,
        cpu=8,
        memory=32.0,
        disk_size=100.0,
        host_id=test_host.id,
    )
    session.add(gpu)
    session.commit()
    return gpu
