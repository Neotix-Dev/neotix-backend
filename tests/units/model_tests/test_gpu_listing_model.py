import pytest
from datetime import datetime, timezone
from models.gpu_listing import Host, GPUConfiguration, GPUListing, GPUPricePoint, GPUPriceHistory

@pytest.mark.unit_tests
def test_host_creation(db_fixture):
    """Test creating a Host with all required and optional fields"""
    mock_db = db_fixture
    
    # Create a host
    host = Host(
        name="Test Host",
        description="Test host description",
        url="http://testhost.com"
    )
    
    # Test attributes
    assert host.name == "Test Host"
    assert host.description == "Test host description"
    assert host.url == "http://testhost.com"
    
    # Save to mock database
    mock_db.session.add(host)
    mock_db.session.commit()
    mock_db.session.refresh(host)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(host)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_gpu_configuration_creation(db_fixture):
    """Test creating a GPUConfiguration with all required and optional fields"""
    mock_db = db_fixture
    
    # Create a GPU configuration
    gpu_config = GPUConfiguration(
        hash="testhash",
        gpu_name="RTX 3090",
        gpu_vendor="NVIDIA",
        gpu_count=2,
        gpu_memory=24.0,
        cpu=16,
        memory=64.0,
        disk_size=1024.0
    )
    
    # Test attributes
    assert gpu_config.hash == "testhash"
    assert gpu_config.gpu_name == "RTX 3090"
    assert gpu_config.gpu_vendor == "NVIDIA"
    assert gpu_config.gpu_count == 2
    assert gpu_config.gpu_memory == 24.0
    assert gpu_config.cpu == 16
    assert gpu_config.memory == 64.0
    assert gpu_config.disk_size == 1024.0
    assert gpu_config.gpu_score is not None
    
    # Save to mock database
    mock_db.session.add(gpu_config)
    mock_db.session.commit()
    mock_db.session.refresh(gpu_config)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(gpu_config)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_gpu_listing_creation(db_fixture):
    """Test creating a GPUListing with all required and optional fields"""
    mock_db = db_fixture
    
    # Create a GPU listing
    gpu_listing = GPUListing(
        instance_name="Test Instance",
        configuration_id=1,
        current_price=3.5,
        host_id=1
    )
    # Test attributes
    assert gpu_listing.instance_name == "Test Instance"
    assert gpu_listing.configuration_id == 1
    assert gpu_listing.current_price == 3.5
    assert gpu_listing.host_id == 1
    assert gpu_listing.last_updated is not None
    
    # Save to mock database
    mock_db.session.add(gpu_listing)
    mock_db.session.commit()
    mock_db.session.refresh(gpu_listing)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(gpu_listing)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_gpu_price_point_creation(db_fixture):
    """Test creating a GPUPricePoint with all required and optional fields"""
    mock_db = db_fixture
    
    # Create a GPU price point
    price_point = GPUPricePoint(
        gpu_listing_id=1,
        price=2.5,
        location="us-west-1",
        spot=True,
        last_updated=datetime.now(timezone.utc)  # Explicitly set last_updated
    )
    
    # Test attributes
    assert price_point.gpu_listing_id == 1
    assert price_point.price == 2.5
    assert price_point.location == "us-west-1"
    assert price_point.spot is True
    assert price_point.last_updated is not None
    
    # Save to mock database
    mock_db.session.add(price_point)
    mock_db.session.commit()
    mock_db.session.refresh(price_point)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(price_point)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_gpu_price_history_creation(db_fixture):
    """Test creating a GPUPriceHistory with all required and optional fields"""
    mock_db = db_fixture
    
    # Create a GPU price history
    price_history = GPUPriceHistory(
        configuration_id=1,
        price=2.5,
        location="us-west-1",
        spot=True,
        date=datetime.now(timezone.utc)  # Explicitly set date
    )
    
    # Test attributes
    assert price_history.configuration_id == 1
    assert price_history.price == 2.5
    assert price_history.location == "us-west-1"
    assert price_history.spot is True
    assert price_history.date is not None
    
    # Save to mock database
    mock_db.session.add(price_history)
    mock_db.session.commit()
    mock_db.session.refresh(price_history)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(price_history)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_gpu_listing_to_dict(db_fixture):
    """Test the to_dict method returns correct data for GPUListing"""
    mock_db = db_fixture
    
    # Create a GPU configuration
    gpu_config = GPUConfiguration(
        hash="testhash",
        gpu_name="RTX 3090",
        gpu_vendor="NVIDIA",
        gpu_count=2,
        gpu_memory=24.0,
        cpu=16,
        memory=64.0,
        disk_size=1024.0
    )
    
    # Save to mock database to generate ID
    mock_db.session.add(gpu_config)
    mock_db.session.commit()
    mock_db.session.refresh(gpu_config)
    
    # Create a host
    host = Host(
        name="Test Host",
        description="Test host description"
    )
    
    # Save to mock database to generate ID
    mock_db.session.add(host)
    mock_db.session.commit()
    mock_db.session.refresh(host)
    
    # Create a GPU listing
    gpu_listing = GPUListing(
        instance_name="Test Instance",
        configuration_id=gpu_config.id,
        current_price=3.5,
        host_id=host.id
    )
    
    # Save to mock database
    mock_db.session.add(gpu_listing)
    mock_db.session.commit()
    mock_db.session.refresh(gpu_listing)
    
    # Manually set up the relationships because mocks don't do this automatically
    gpu_listing.configuration = gpu_config
    gpu_listing.host = host
    
    # Call to_dict method
    gpu_listing_dict = gpu_listing.to_dict()
    
    # Verify returned dictionary
    assert gpu_listing_dict["id"] == gpu_listing.id
    assert gpu_listing_dict["instance_name"] == "Test Instance"
    assert gpu_listing_dict["gpu_name"] == "RTX 3090"
    assert gpu_listing_dict["gpu_vendor"] == "NVIDIA"
    assert gpu_listing_dict["gpu_count"] == 2
    assert gpu_listing_dict["gpu_memory"] == 24.0
    assert gpu_listing_dict["current_price"] == 3.5
    assert gpu_listing_dict["gpu_score"] == gpu_config.gpu_score
    assert "price_change" in gpu_listing_dict
    assert gpu_listing_dict["cpu"] == 16
    assert gpu_listing_dict["memory"] == 64.0
    assert gpu_listing_dict["disk_size"] == 1024.0
    assert gpu_listing_dict["provider"] == "Test Host"
    assert gpu_listing_dict["last_updated"] is not None