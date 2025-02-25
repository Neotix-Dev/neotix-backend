import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

@pytest.fixture
def db_fixture():
    """Mock database fixture for unit testing"""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.session = mock_session

    # Configure mock session to behave like a real session
    def mock_refresh(obj):
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
        # Simulate defaults being applied on refresh
        if hasattr(obj, 'email_verified') and obj.email_verified is None:
            obj.email_verified = False
        if hasattr(obj, 'disabled') and obj.disabled is None:
            obj.disabled = False
        if hasattr(obj, 'experience_level') and obj.experience_level is None:
            obj.experience_level = "beginner"
        if hasattr(obj, 'referral_source') and obj.referral_source == "":
            obj.referral_source = None
        if hasattr(obj, 'balance') and obj.balance is None:
            obj.balance = 0.0

    mock_session.refresh = mock_refresh
    return mock_db

@pytest.fixture
def test_user():
    """Create a mock user for testing"""
    user = MagicMock()
    user.id = 123
    user.email = "test@example.com"
    return user

@pytest.fixture
def mock_user_query():
    """Fixture for mocking User.query"""
    mock_query = MagicMock()
    mock_filter_by = MagicMock()
    mock_first = MagicMock()

    # Set up the chain of mock calls
    mock_filter_by.first = mock_first
    mock_query.filter_by = MagicMock(return_value=mock_filter_by)

    return mock_query, mock_filter_by, mock_first

@pytest.fixture
def isolated_models():
    """Get models completely isolated from SQLAlchemy"""
    # Create mocks for all dependencies
    mock_relationship = MagicMock()
    mock_user = MagicMock()
    mock_rental_gpu_users = MagicMock()
    mock_db = MagicMock()
    mock_gpu_listing = MagicMock()

    # Apply patches - store them to undo later
    patches = [
        patch('models.cluster.GPUListing', mock_gpu_listing),
        patch('models.cluster.db', mock_db),
        patch('models.cluster.rental_gpu_users', mock_rental_gpu_users),
        patch('models.cluster.User', mock_user),
        patch('sqlalchemy.orm.relationship', mock_relationship)
    ]

    # Start all patches
    for p in patches:
        p.start()

    # Create a simplified Cluster class without SQLAlchemy
    class TestCluster:
        def __init__(self, name, user_id, description=None):
            self.id = None
            self.name = name
            self.description = description
            self.user_id = user_id
            self.created_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
            self._rental_gpu = None

        @property
        def rental_gpu(self):
            return self._rental_gpu

        @rental_gpu.setter
        def rental_gpu(self, value):
            self._rental_gpu = value

        def to_dict(self):
            result = {
                "id": self.id,
                "name": self.name,
                "description": self.description,
                "user_id": self.user_id,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
                "rental_gpu": self.rental_gpu.to_dict() if self.rental_gpu else None
            }
            return result

    # Create a simplified RentalGPU class
    class TestRentalGPU:
        def __init__(self, name=None, hourly_cost=None, ssh_keys=None, email_enabled=None, rented=None, rental_start=None, rental_end=None):
            self.id = None
            self.name = name
            self.hourly_cost = hourly_cost
            self.ssh_keys = ssh_keys
            self.email_enabled = email_enabled
            self.rented = rented
            self.rental_start = rental_start
            self.rental_end = rental_end

        def to_dict(self):
            return {
                "id": self.id,
                "name": self.name,
                "hourly_cost": self.hourly_cost,
                "ssh_keys": self.ssh_keys,
                "email_enabled": self.email_enabled,
                "rented": self.rented,
                "rental_start": self.rental_start.isoformat() if self.rental_start else None,
                "rental_end": self.rental_end.isoformat() if self.rental_end else None,
                "users_with_access": []
            }

    yield TestCluster, TestRentalGPU

    # Stop all patches after the test is done
    for p in patches:
        p.stop()