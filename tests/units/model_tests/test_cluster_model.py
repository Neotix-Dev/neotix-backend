import pytest
from datetime import datetime, timezone

def test_cluster_creation(db_fixture, isolated_models, test_user):
    """Test creating a cluster with all required and optional fields"""
    mock_db = db_fixture
    Cluster, _ = isolated_models
    
    # Create a cluster
    cluster = Cluster(
        name="Test Cluster",
        user_id=test_user.id,
        description="Test cluster description"
    )
    
    # Test attributes
    assert cluster.name == "Test Cluster"
    assert cluster.user_id == test_user.id
    assert cluster.description == "Test cluster description"
    
    # Save to mock database
    mock_db.session.add(cluster)
    mock_db.session.commit()
    mock_db.session.refresh(cluster)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(cluster)
    mock_db.session.commit.assert_called_once()

def test_cluster_to_dict(isolated_models, test_user):
    """Test the to_dict method returns correct data"""
    Cluster, _ = isolated_models
    
    # Create cluster instance
    cluster = Cluster(
        name="Test Cluster", 
        user_id=test_user.id,
        description="Test cluster description"
    )
    
    # Set timestamps and ID for testing
    cluster.id = 456
    cluster.created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    cluster.updated_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    
    # Call to_dict method
    cluster_dict = cluster.to_dict()
    
    # Verify returned dictionary
    assert cluster_dict["id"] == 456
    assert cluster_dict["name"] == "Test Cluster"
    assert cluster_dict["user_id"] == test_user.id
    assert cluster_dict["description"] == "Test cluster description"
    assert cluster_dict["created_at"] == "2023-05-15T00:00:00+00:00"
    assert cluster_dict["updated_at"] == "2023-05-15T00:00:00+00:00"
    assert cluster_dict["rental_gpu"] is None

def test_cluster_with_rental_gpu(isolated_models, test_user):
    """Test cluster with related rental GPU"""
    Cluster, RentalGPU = isolated_models
    
    # Create cluster
    cluster = Cluster(
        name="GPU Cluster",
        user_id=test_user.id
    )
    cluster.id = 789
    
    # Create rental GPU
    rental_gpu = RentalGPU(
        name="RTX 4090",
        hourly_cost=2.5
    )
    rental_gpu.id = 101
    
    # Set up relationship
    cluster.rental_gpu = rental_gpu
    
    # Test to_dict with relationship
    cluster_dict = cluster.to_dict()
    
    assert cluster_dict["rental_gpu"]["id"] == 101
    assert cluster_dict["rental_gpu"]["name"] == "RTX 4090"
    assert cluster_dict["rental_gpu"]["hourly_cost"] == 2.5

def test_rental_gpu_creation(db_fixture, isolated_models):
    """Test creating a rental GPU with all required and optional fields"""
    mock_db = db_fixture
    _, RentalGPU = isolated_models
    
    # Create a rental GPU
    rental_gpu = RentalGPU(
        name="RTX 4090",
        hourly_cost=2.5,
        ssh_keys=["ssh-rsa AAA..."],
        email_enabled=True,
        rented=False,
        rental_start=datetime(2023, 5, 15, tzinfo=timezone.utc),
        rental_end=datetime(2023, 5, 16, tzinfo=timezone.utc)
    )
    
    # Test attributes
    assert rental_gpu.name == "RTX 4090"
    assert rental_gpu.hourly_cost == 2.5
    assert rental_gpu.ssh_keys == ["ssh-rsa AAA..."]
    assert rental_gpu.email_enabled is True
    assert rental_gpu.rented is False
    assert rental_gpu.rental_start == datetime(2023, 5, 15, tzinfo=timezone.utc)
    assert rental_gpu.rental_end == datetime(2023, 5, 16, tzinfo=timezone.utc)
    
    # Save to mock database
    mock_db.session.add(rental_gpu)
    mock_db.session.commit()
    mock_db.session.refresh(rental_gpu)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(rental_gpu)
    mock_db.session.commit.assert_called_once()

def test_rental_gpu_to_dict(isolated_models):
    """Test the to_dict method returns correct data for RentalGPU"""
    _, RentalGPU = isolated_models
    
    # Create rental GPU instance
    rental_gpu = RentalGPU(
        name="RTX 4090",
        hourly_cost=2.5,
        ssh_keys=["ssh-rsa AAA..."],
        email_enabled=True,
        rented=False,
        rental_start=datetime(2023, 5, 15, tzinfo=timezone.utc),
        rental_end=datetime(2023, 5, 16, tzinfo=timezone.utc)
    )
    
    # Set ID for testing
    rental_gpu.id = 101
    
    # Call to_dict method
    rental_gpu_dict = rental_gpu.to_dict()
    
    # Verify returned dictionary
    assert rental_gpu_dict["id"] == 101
    assert rental_gpu_dict["name"] == "RTX 4090"
    assert rental_gpu_dict["hourly_cost"] == 2.5
    assert rental_gpu_dict["ssh_keys"] == ["ssh-rsa AAA..."]
    assert rental_gpu_dict["email_enabled"] is True
    assert rental_gpu_dict["rented"] is False
    assert rental_gpu_dict["rental_start"] == "2023-05-15T00:00:00+00:00"
    assert rental_gpu_dict["rental_end"] == "2023-05-16T00:00:00+00:00"
    assert rental_gpu_dict["users_with_access"] == []