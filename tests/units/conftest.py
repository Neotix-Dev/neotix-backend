import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import jwt

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app import create_app
from models.user import User

# --- Flask Test Fixtures ---

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    os.environ['FLASK_ENV'] = 'testing'
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key"
    })
    yield app

@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def auth_headers(app, test_user):
    """Create authorization headers with a dummy JWT token."""
    user_id = test_user.id
    secret_key = app.config["SECRET_KEY"]
    
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

# --- Existing Mock Fixtures ---

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

    mock_filter_by.first = mock_first
    mock_query.filter_by = MagicMock(return_value=mock_filter_by)

    return mock_query, mock_filter_by, mock_first

@pytest.fixture
def isolated_models():
    """Get models completely isolated from SQLAlchemy"""
    mock_relationship = MagicMock()
    mock_user = MagicMock()
    mock_rental_gpu_users = MagicMock()
    mock_db = MagicMock()
    mock_gpu_listing = MagicMock()

    patches = [
        patch('models.cluster.GPUListing', mock_gpu_listing),
        patch('models.cluster.db', mock_db),
        patch('models.cluster.rental_gpu_users', mock_rental_gpu_users),
        patch('models.cluster.User', mock_user),
        patch('sqlalchemy.orm.relationship', mock_relationship)
    ]

    for p in patches:
        p.start()

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

    for p in patches:
        p.stop()

@pytest.fixture
def isolated_user_preference_models():
    """Get user preference models completely isolated from SQLAlchemy"""
    class TestRentedGPU:
        def __init__(self, gpu_id, is_active=True, rental_start=None, rental_end=None):
            self.id = None
            self.gpu_id = gpu_id
            self.is_active = is_active
            self.rental_start = rental_start or datetime.now(timezone.utc)
            self.rental_end = rental_end
            self.gpu = None
        
        def to_dict(self):
            return {
                'id': self.gpu.id if self.gpu else None,
                'name': self.gpu.name if self.gpu else f"GPU {self.gpu_id}",
                'isActive': self.is_active,
                'rentalStart': self.rental_start.isoformat(),
                'rentalEnd': self.rental_end.isoformat() if self.rental_end else None
            }

    class TestPriceAlert:
        def __init__(self, gpu_id=None, gpu_type=None, target_price=None, is_type_alert=False, created_at=None):
            self.id = None
            self.gpu_id = gpu_id
            self.gpu_type = gpu_type
            self.target_price = target_price
            self.is_type_alert = is_type_alert
            self.created_at = created_at or datetime.now(timezone.utc)
            self.gpu = None
            
        def to_dict(self):
            alert_id = f"type_{self.gpu_type}" if self.is_type_alert else str(self.gpu_id)
            return {
                alert_id: {
                    'targetPrice': self.target_price,
                    'isTypeAlert': self.is_type_alert,
                    'gpuType': self.gpu_type if self.is_type_alert else None,
                    'createdAt': self.created_at.isoformat()
                }
            }

    class TestSelectedGPU:
        def __init__(self, gpu_id, created_at=None):
            self.id = None
            self.gpu_id = gpu_id
            self.created_at = created_at or datetime.now(timezone.utc)
            self.gpu = None
            
        def to_dict(self):
            return {
                'id': self.id,
                'gpu_id': self.gpu_id,
                'created_at': self.created_at.isoformat(),
                'gpu': self.gpu.to_dict() if self.gpu else None
            }

    class TestFavoriteGPU:
        def __init__(self, gpu_id, created_at=None):
            self.id = None
            self.gpu_id = gpu_id
            self.created_at = created_at or datetime.now(timezone.utc)
            self.gpu = None
            
        def to_dict(self):
            if not self.gpu:
                return {
                    'id': self.gpu_id,
                    'name': f"GPU {self.gpu_id}",
                    'host_name': None
                }
            return {
                'id': self.gpu.id,
                'name': self.gpu.name,
                'host_name': self.gpu.host.name if self.gpu.host else None
            }

    yield TestRentedGPU, TestPriceAlert, TestSelectedGPU, TestFavoriteGPU

@pytest.fixture
def mock_gpu_vendor():
    """Create a mock GPU vendor enum"""
    class MockVendor:
        def __init__(self, value):
            self.value = value
            
        def __str__(self):
            return str(self.value)
            
        def __eq__(self, other):
            if isinstance(other, MockVendor):
                return self.value == other.value
            return False
    
    return MockVendor

@pytest.fixture
def mock_offer_factory(mock_gpu_vendor):
    """Factory fixture to create MockOffer instances with consistent behavior"""
    class MockOffer:
        """Mock class for gpuhunt.Offer"""
        def __init__(self, provider="test-provider", gpu_name="Test GPU", gpu_vendor="NVIDIA", gpu_count=1, 
                     gpu_memory=16, cpu=8, memory=32, disk_size=100, instance_name="test-instance",
                     price=1.0, location="us-east", spot=True):
            self.provider = provider
            self.gpu_name = gpu_name
            
            if gpu_vendor is None:
                self.gpu_vendor = None
            elif isinstance(gpu_vendor, mock_gpu_vendor):
                self.gpu_vendor = gpu_vendor
            else:
                self.gpu_vendor = mock_gpu_vendor(gpu_vendor)
                
            self.gpu_count = gpu_count
            self.gpu_memory = gpu_memory
            self.cpu = cpu
            self.memory = memory
            self.disk_size = disk_size
            self.instance_name = instance_name
            self.price = price
            self.location = location
            self.spot = spot
            
    return MockOffer

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit_tests: mark tests as unit tests to run them separately"
    )