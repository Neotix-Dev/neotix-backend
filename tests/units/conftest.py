import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

@pytest.fixture
def db_fixture():
    """Mock database fixture for unit testing"""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.session = mock_session

    # Configure mock session to behave like a real session
    def mock_refresh(obj):
        # Only set timestamps if they don't exist or are None
        if not hasattr(obj, 'created_at') or obj.created_at is None:
            obj.created_at = datetime.now(timezone.utc)
        if not hasattr(obj, 'updated_at') or obj.updated_at is None:
            obj.updated_at = datetime.now(timezone.utc)
        if not hasattr(obj, 'last_used_at') or obj.last_used_at is None:
            obj.last_used_at = datetime.now(timezone.utc)                
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
        if hasattr(obj, 'status') and obj.status is None:
            obj.status = "pending"
        if hasattr(obj, 'is_active') and obj.is_active is None:
            obj.is_active = True  # Fixed the typo here
            
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

@pytest.fixture
def isolated_user_preference_models():
    """Get user preference models completely isolated from SQLAlchemy"""
    # Create isolated test classes directly instead of patching modules
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
            
            # Create a vendor object with .value attribute to mimic enum behavior
            if gpu_vendor is None:
                self.gpu_vendor = None
            elif isinstance(gpu_vendor, mock_gpu_vendor):
                # If already a mock vendor, use it directly
                self.gpu_vendor = gpu_vendor
            else:
                # Create new mock vendor
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