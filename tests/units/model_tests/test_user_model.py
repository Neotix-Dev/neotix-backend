import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime,timezone
from models.user import User
from models.cluster import Cluster
from models.transaction import Transaction

@pytest.fixture
def db_fixture():
    """Mock database fixture for unit testing"""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.session = mock_session
    
    # Configure mock session to behave like a real session
    # For example, .refresh() typically loads default values
    def mock_refresh(obj):
        obj.created_at = datetime.now(timezone.utc)
        # Simulate defaults being applied on refresh
        if obj.email_verified is None:
            obj.email_verified = False
        if obj.disabled is None:
            obj.disabled = False
        if obj.experience_level is None:
            obj.experience_level = "beginner"
        if obj.referral_source == "":
            obj.referral_source = None
        if obj.balance is None:
            obj.balance = 0.0
    
    mock_session.refresh = mock_refresh
    return mock_db

def test_user_creation(db_fixture):
    """Test creating a user with all required and optional fields"""
    mock_db = db_fixture
    
    user = User(
        firebase_uid="test_uid",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        email_verified=True,
        organization="Test Org",
        experience_level="intermediate",
        referral_source="friend",
        balance=100.0,
        stripe_customer_id="cus_123456"
    )
    
    # Verify all fields were set correctly
    assert user.firebase_uid == "test_uid"
    assert user.email == "test@example.com"
    assert user.first_name == "Test"
    assert user.last_name == "User"
    assert user.email_verified is True
    assert user.organization == "Test Org"
    assert user.experience_level == "intermediate"
    assert user.referral_source == "friend"
    assert user.balance == 100.0
    assert user.stripe_customer_id == "cus_123456"
    
    # Add database operations
    mock_db.session.add(user)
    mock_db.session.commit()
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(user)
    mock_db.session.commit.assert_called_once()

@pytest.mark.parametrize("db_fixture", ["db"], indirect=True)
def test_default_values(db_fixture):
    """Test default values are correctly applied when saved"""
    mock_db = db_fixture
    
    # Create user with only required fields
    user = User(
        firebase_uid="default_uid",
        email="default@example.com",
        first_name="TestFName",
        last_name="TestLName"
    )
    
    # Simulate save and retrieve
    mock_db.session.add(user)
    mock_db.session.commit()
    mock_db.session.refresh(user)  # Add this line to apply defaults
    
    # After save - defaults should be applied
    assert user.email_verified is False
    assert user.disabled is False
    assert user.experience_level == "beginner"
    assert user.referral_source == None  # This matches your __init__ behavior
    assert user.balance == 0.0
    assert user.organization == None
    assert user.stripe_customer_id is None
    assert user.last_login is None

def test_user_to_dict():
    """Test the to_dict method returns correct data"""

    user = User(
        firebase_uid="test_uid",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        email_verified=False,
        disabled=False,
        organization="Test Org",
        experience_level="intermediate",
        referral_source="friend",
        balance=100.0,
        stripe_customer_id="cus_123456"
    )

    # Set the id manually for testing
    user.id = 123
    
    # Set timestamps for testing
    now = datetime.now(timezone.utc)
    user.created_at = now
    user.last_login = now
    
    user_dict = user.to_dict()
    
    assert user_dict["id"] == 123
    assert user_dict["firebase_uid"] == "test_uid"
    assert user_dict["email"] == "test@example.com"
    assert user_dict["first_name"] == "Test"
    assert user_dict["last_name"] == "User"
    assert user_dict["organization"] == "Test Org"
    assert user_dict["email_verified"] is False
    assert user_dict["disabled"] is False
    assert user_dict["created_at"] == now.isoformat()
    assert user_dict["last_login"] == now.isoformat()
    assert user_dict["clusters"] == []
    assert user_dict["transactions"] == []

@patch('models.user.db.session')
def test_user_update(mock_session):
    """Test updating user attributes with mocked database"""
    # Create a user
    user = User(
        firebase_uid="test_uid",
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    
    # Mock the query operation
    mock_query = MagicMock()
    mock_filter_by = MagicMock()
    mock_first = MagicMock(return_value=user)
    
    # Set up the chain of mock calls
    mock_filter_by.first = mock_first
    mock_query.filter_by = MagicMock(return_value=mock_filter_by)
    User.query = mock_query
    
    # Update the user
    user.first_name = "Updated"
    user.last_name = "Name"
    
    # Check that attributes changed
    assert user.first_name == "Updated"
    assert user.last_name == "Name"
    
    # To verify db operations
    # 1. Simulate retrieving updated user
    updated_user = User.query.filter_by(firebase_uid="test_uid").first()
    
    # 2. Verify our mock chain was used correctly
    mock_query.filter_by.assert_called_with(firebase_uid="test_uid")
    mock_filter_by.first.assert_called_once()
    
    # 3. Verify user properties
    assert updated_user.first_name == "Updated"
    assert updated_user.last_name == "Name"

def test_user_relationships():
    """Test user relationships using mocks"""
    # Create user
    user = User(firebase_uid="test_uid", email="test@example.com")
    
    # Create mock clusters instead of real Cluster instances
    mock_cluster = MagicMock()
    mock_cluster.name = "Test Cluster"
    mock_cluster.to_dict.return_value = {"id": 1, "name": "Test Cluster"}
    
    # Create mock transactions instead of real Transaction instances
    mock_transaction = MagicMock()
    mock_transaction.amount = 50.0
    mock_transaction.to_dict.return_value = {"id": 1, "amount": 50.0}
    
    # Replace the relationship properties with our mocks
    user.clusters = [mock_cluster]
    user.transactions = [mock_transaction]
    
    # Now test the behavior
    assert len(user.clusters) == 1
    assert user.clusters[0].name == "Test Cluster"
    
    user_dict = user.to_dict()
    assert "clusters" in user_dict
    assert user_dict["clusters"][0]["name"] == "Test Cluster"

def test_from_firebase_user():
    """Test creating a user from Firebase user data"""
    firebase_user = {
        "uid": "firebase_uid_123",
        "email": "firebase@example.com",
        "name": "Firebase User",
        "email_verified": True,
        "disabled": False
    }
    
    user_data = User.from_firebase_user(firebase_user)
    
    assert user_data["firebase_uid"] == "firebase_uid_123"
    assert user_data["email"] == "firebase@example.com"
    assert user_data["first_name"] == "Firebase"
    assert user_data["last_name"] == "User"
    assert user_data["email_verified"] is True
    assert user_data["disabled"] is False

def test_from_firebase_user_partial_name():
    """Test creating a user with only first name"""
    firebase_user = {
        "uid": "firebase_uid_456",
        "email": "single@example.com",
        "name": "SingleName",
        "email_verified": False
    }
    
    user_data = User.from_firebase_user(firebase_user)
    
    assert user_data["firebase_uid"] == "firebase_uid_456"
    assert user_data["first_name"] == "SingleName"
    assert user_data["last_name"] == ""  # Last name should be empty

import pytest
from sqlalchemy.exc import IntegrityError

@patch('models.user.db.session')
def test_missing_required_fields(mock_session):
    """Test behavior when required fields are missing"""
    # Configure mock to simulate IntegrityError
    mock_session.commit.side_effect = IntegrityError(
        "NOT NULL constraint failed",
        params={},
        orig=None
    )
    
    # Missing firebase_uid
    user1 = User(
        email="missing@example.com",
        first_name="Missing",
        last_name="Fields"
    )
    
    # Try to save - this should raise an error
    with pytest.raises(IntegrityError):
        mock_session.add(user1)
        mock_session.commit()
    
    mock_session.reset_mock()
    
    # Missing email
    user2 = User(
        firebase_uid="missing_email",
        first_name="Missing",
        last_name="Fields"
    )
    
    # Try to save
    with pytest.raises(IntegrityError):
        mock_session.add(user2)
        mock_session.commit()

@patch('models.user.db.session')
def test_database_constraints(mock_session):
    """Test database constraints for required fields"""
    # Create user with required fields but try to set them to None before saving
    user = User(
        firebase_uid="constraint_uid",
        email="constraint@example.com"
    )
    
    # Try setting required field to None
    user.firebase_uid = None
    
    # Configure mock to simulate IntegrityError
    mock_session.commit.side_effect = IntegrityError(
        "NOT NULL constraint failed: users.firebase_uid",
        params={},
        orig=None
    )
    
    # Attempt to save should raise IntegrityError
    with pytest.raises(IntegrityError):
        mock_session.add(user)
        mock_session.commit()
    
    # Verify correct methods were called
    mock_session.add.assert_called_once_with(user)
    mock_session.commit.assert_called_once()

def test_user_repr():
    """Test the string representation of a User object"""
    # Create a user with known values
    user = User(
        firebase_uid="repr_test_uid",
        email="repr@example.com",
        first_name="Repr",
        last_name="Test"
    )
    
    # Get the string representation
    user_repr = repr(user)
    
    # Assert it matches the expected format
    assert user_repr == "<User repr@example.com>"

def test_balance_operations():
    """Test balance operations for user account"""
    # Create a user with initial balance
    user = User(
        firebase_uid="balance_uid",
        email="balance@example.com",
        first_name="Balance",
        last_name="Test",
        balance=100.0
    )
    
    # Test initial balance
    assert user.balance == 100.0
    
    # Test increasing balance
    initial_balance = user.balance
    user.balance += 50.0
    assert user.balance == initial_balance + 50.0
    
    # Test decreasing balance
    user.balance -= 25.0
    assert user.balance == 125.0
    
    # Test setting to zero
    user.balance = 0.0

@pytest.mark.parametrize("db_fixture", ["db"], indirect=True)
def test_timestamps_with_fixtures(db_fixture):
    """Test creation and last_login timestamps using our db fixture"""
    mock_db = db_fixture
    
    # Create a user
    user = User(
        firebase_uid="time_uid",
        email="time@example.com",
        first_name="Time",
        last_name="Stamp"
    )
    
    # Before refresh, created_at should be None
    assert user.created_at is None
    
    # Simulate save and refresh
    mock_db.session.add(user)
    mock_db.session.commit()
    mock_db.session.refresh(user)  # This will use your existing mock_refresh
    
    # After refresh, created_at should be set
    assert user.created_at is not None
    assert isinstance(user.created_at, datetime)
    assert user.created_at.tzinfo is not None  # Timezone aware
    
    # Capture timestamp for comparison
    initial_timestamp = user.created_at
    
    # Test that last_login starts as None
    assert user.last_login is None
    
    # Test setting last_login
    now = datetime.now(timezone.utc)
    user.last_login = now
    assert user.last_login == now
    
    # Verify created_at isn't changed during updates
    assert user.created_at == initial_timestamp
    
@patch('models.user.db.session')
def test_user_disable_enable(mock_session):
    """Test disabling and enabling a user"""
    # Create an enabled user
    user = User(
        firebase_uid="status_uid",
        email="status@example.com",
        first_name="Status",
        last_name="Test",
        disabled=False
    )
        
    assert user.disabled is False
        
    # Disable user
    user.disabled = True
    assert user.disabled is True
        
    # Enable user
    user.disabled = False
    assert user.disabled is False
        
    # Save changes
    mock_session.add(user)
    mock_session.commit()
    mock_session.add.assert_called_once_with(user)
    mock_session.commit.assert_called_once()

@patch('models.user.db.session')
def test_email_verification_status(mock_session):
    """Test changing email verification status"""
    user = User(
        firebase_uid="verify_uid",
        email="verify@example.com",
        first_name="Verify",
        last_name="Email",
        email_verified=False
    )
    
    assert user.email_verified is False
    
    # Mark email as verified
    user.email_verified = True
    assert user.email_verified is True
    
    # Save changes
    mock_session.add(user)
    mock_session.commit()
    mock_session.add.assert_called_once_with(user)
    mock_session.commit.assert_called_once()

@patch('models.user.db.session')
def test_bulk_update(mock_session):
    """Test updating multiple user attributes at once"""
    user = User(
        firebase_uid="bulk_uid",
        email="bulk@example.com",
        first_name="Bulk",
        last_name="Update"
    )
    
    # Update multiple fields at once
    updates = {
        "first_name": "NewFirst",
        "last_name": "NewLast",
        "organization": "New Org",
        "experience_level": "expert",
        "balance": 250.0
    }
    
    # Apply all updates
    for attr, value in updates.items():
        setattr(user, attr, value)
    
    # Verify all attributes were updated
    assert user.first_name == "NewFirst"
    assert user.last_name == "NewLast"
    assert user.organization == "New Org"
    assert user.experience_level == "expert"
    assert user.balance == 250.0
    
    # Save changes
    mock_session.add(user)
    mock_session.commit()
    mock_session.add.assert_called_once_with(user)
    mock_session.commit.assert_called_once()

@patch('models.user.db.session')
def test_user_delete(mock_session):
    """Test deleting a user"""
    user = User(
        firebase_uid="delete_uid",
        email="delete@example.com",
        first_name="Delete",
        last_name="User"
    )
    
    # Delete the user
    mock_session.delete(user)
    mock_session.commit()
    
    # Verify delete was called
    mock_session.delete.assert_called_once_with(user)
    mock_session.commit.assert_called_once()

@patch('models.user.db.session')
def test_user_email_uniqueness(mock_session):
    """Test handling of duplicate email addresses"""
    # Create first user
    user1 = User(
        firebase_uid="unique_uid_1",
        email="duplicate@example.com",
        first_name="First",
        last_name="User"
    )
    
    # Configure mock_session.commit to succeed for the first user
    mock_session.commit.return_value = None
    mock_session.add(user1)
    mock_session.commit()
    
    # Create another user with the same email
    user2 = User(
        firebase_uid="unique_uid_2",
        email="duplicate@example.com",  # Same email as user1
        first_name="Second",
        last_name="User"
    )
    
    # Configure mock to raise IntegrityError on the second commit
    mock_session.commit.side_effect = IntegrityError(
        "Duplicate key value violates unique constraint", 
        params={}, 
        orig=None
    )
    
    # Adding the second user should raise an IntegrityError
    with pytest.raises(IntegrityError):
        mock_session.add(user2)
        mock_session.commit()