import pytest
from datetime import datetime, timezone
from models.api_key import APIKey, APIKeyPermission

@pytest.mark.unit_tests
def test_api_key_creation(db_fixture):
    """Test creating an APIKey with all required and optional fields"""
    mock_db = db_fixture
    
    # Create an APIKey
    api_key = APIKey(
        key="test_key_123456",
        name="Test API Key",
        permission=APIKeyPermission.READ
    )

    # Save to mock database
    mock_db.session.add(api_key)
    mock_db.session.commit()
    mock_db.session.refresh(api_key)

    # Test attributes
    assert api_key.key == "test_key_123456"
    assert api_key.name == "Test API Key"
    assert api_key.permission == APIKeyPermission.READ.value
    assert api_key.is_active is True
    assert api_key.created_at is not None  # Will be set by database
    assert api_key.last_used_at is not None
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(api_key)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_api_key_with_admin_permission(db_fixture):
    """Test creating an APIKey with admin permissions"""
    mock_db = db_fixture
    
    # Create an APIKey with admin permission
    api_key = APIKey(
        key="admin_key_123456",
        name="Admin API Key",
        permission=APIKeyPermission.ADMIN
    )
    
    # Test attributes
    assert api_key.key == "admin_key_123456"
    assert api_key.name == "Admin API Key"
    assert api_key.permission == APIKeyPermission.ADMIN.value
    
    # Save to mock database
    mock_db.session.add(api_key)
    mock_db.session.commit()
    mock_db.session.refresh(api_key)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(api_key)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_api_key_to_dict():
    """Test the to_dict method returns correct data for APIKey"""
    # Create an APIKey with custom dates
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    last_used_at = datetime(2023, 5, 16, tzinfo=timezone.utc)
    
    api_key = APIKey(
        key="test_key_123456",
        name="Test API Key",
        permission=APIKeyPermission.READ
    )
    api_key.id = 1
    api_key.created_at = created_at
    api_key.last_used_at = last_used_at
    api_key.is_active = True
    
    # Call to_dict method
    api_key_dict = api_key.to_dict()
    
    # Verify returned dictionary
    assert api_key_dict["id"] == 1
    assert api_key_dict["name"] == "Test API Key"
    assert api_key_dict["key"] == "test_key_123456"
    assert api_key_dict["permission"] == APIKeyPermission.READ.value
    assert api_key_dict["created_at"] == created_at.isoformat()
    assert api_key_dict["last_used_at"] == last_used_at.isoformat()
    assert api_key_dict["is_active"] is True

@pytest.mark.unit_tests
def test_api_key_to_dict_with_null_last_used(db_fixture):
    """Test the to_dict method handles null last_used_at correctly"""
    mock_db = db_fixture
    
    # Create an APIKey with null last_used_at
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    
    api_key = APIKey(
        key="test_key_123456",
        name="Test API Key",
        permission=APIKeyPermission.READ
    )
    
    # Use the mock database operations
    mock_db.session.add(api_key)
    mock_db.session.commit()
    
    # Store a reference to the current mock_refresh function
    original_refresh = mock_db.session.refresh
    
    # Create a custom refresh function to ensure last_used_at stays None
    def custom_refresh(obj):
        original_refresh(obj)  # Call the original refresh
        obj.id = 1  # Set specific ID for testing
        obj.created_at = created_at  # Set created_at to our test date
        obj.last_used_at = None  # Ensure this stays None
    
    # Replace the refresh function temporarily
    mock_db.session.refresh = custom_refresh
    
    # Perform the refresh
    mock_db.session.refresh(api_key)
    
    # Call to_dict method
    api_key_dict = api_key.to_dict()
    
    # Verify returned dictionary
    assert api_key_dict["id"] == 1
    assert api_key_dict["name"] == "Test API Key"
    assert api_key_dict["key"] == "test_key_123456"
    assert api_key_dict["permission"] == APIKeyPermission.READ.value
    assert api_key_dict["created_at"] == created_at.isoformat()
    assert api_key_dict["last_used_at"] is None
    assert api_key_dict["is_active"] is True
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(api_key)
    mock_db.session.commit.assert_called_once()