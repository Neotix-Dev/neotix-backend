import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

@pytest.mark.unit_tests
def test_rented_gpu_creation(db_fixture, isolated_user_preference_models):
    """Test creating a RentedGPU with all required and optional fields"""
    mock_db = db_fixture
    TestRentedGPU, _, _, _ = isolated_user_preference_models
    
    # Create a RentedGPU
    rental_start = datetime(2023, 5, 15, tzinfo=timezone.utc)
    rental_end = datetime(2023, 5, 16, tzinfo=timezone.utc)
    
    rented_gpu = TestRentedGPU(
        gpu_id=1,
        is_active=True,
        rental_start=rental_start,
        rental_end=rental_end
    )
    
    # Test attributes
    assert rented_gpu.gpu_id == 1
    assert rented_gpu.is_active is True
    assert rented_gpu.rental_start == rental_start
    assert rented_gpu.rental_end == rental_end
    
    # Save to mock database
    mock_db.session.add(rented_gpu)
    mock_db.session.commit()
    mock_db.session.refresh(rented_gpu)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(rented_gpu)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_rented_gpu_to_dict(isolated_user_preference_models):
    """Test the to_dict method returns correct data for RentedGPU"""
    TestRentedGPU, _, _, _ = isolated_user_preference_models
    
    # Create mock GPU
    mock_gpu = MagicMock()
    mock_gpu.id = 1
    mock_gpu.name = "Test GPU"
    
    # Create RentedGPU
    rental_start = datetime(2023, 5, 15, tzinfo=timezone.utc)
    rental_end = datetime(2023, 5, 16, tzinfo=timezone.utc)
    
    rented_gpu = TestRentedGPU(
        gpu_id=1,
        is_active=True,
        rental_start=rental_start,
        rental_end=rental_end
    )
    rented_gpu.gpu = mock_gpu  # Set relationship manually
    
    # Call to_dict method
    rented_gpu_dict = rented_gpu.to_dict()
    
    # Verify returned dictionary
    assert rented_gpu_dict["id"] == 1
    assert rented_gpu_dict["name"] == "Test GPU"
    assert rented_gpu_dict["isActive"] is True
    assert rented_gpu_dict["rentalStart"] == rental_start.isoformat()
    assert rented_gpu_dict["rentalEnd"] == rental_end.isoformat()

@pytest.mark.unit_tests
def test_price_alert_specific_gpu(db_fixture, isolated_user_preference_models):
    """Test creating a PriceAlert for a specific GPU"""
    mock_db = db_fixture
    _, TestPriceAlert, _, _ = isolated_user_preference_models
    
    # Create a PriceAlert for specific GPU
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    price_alert = TestPriceAlert(
        gpu_id=1,
        target_price=500.0,
        is_type_alert=False,
        created_at=created_at
    )
    
    # Test attributes
    assert price_alert.gpu_id == 1
    assert price_alert.target_price == 500.0
    assert price_alert.is_type_alert is False
    assert price_alert.created_at == created_at
    
    # Save to mock database
    mock_db.session.add(price_alert)
    mock_db.session.commit()
    mock_db.session.refresh(price_alert)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(price_alert)
    mock_db.session.commit.assert_called_once()
    
    # Test to_dict method
    alert_dict = price_alert.to_dict()
    assert "1" in alert_dict
    assert alert_dict["1"]["targetPrice"] == 500.0
    assert alert_dict["1"]["isTypeAlert"] is False
    assert alert_dict["1"]["gpuType"] is None
    assert alert_dict["1"]["createdAt"] == created_at.isoformat()

@pytest.mark.unit_tests
def test_price_alert_gpu_type(db_fixture, isolated_user_preference_models):
    """Test creating a PriceAlert for a GPU type"""
    mock_db = db_fixture
    _, TestPriceAlert, _, _ = isolated_user_preference_models
    
    # Create a PriceAlert for GPU type
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    price_alert = TestPriceAlert(
        gpu_type="RTX 3090",
        target_price=450.0,
        is_type_alert=True,
        created_at=created_at
    )
    
    # Test attributes
    assert price_alert.gpu_id is None
    assert price_alert.gpu_type == "RTX 3090"
    assert price_alert.target_price == 450.0
    assert price_alert.is_type_alert is True
    assert price_alert.created_at == created_at
    
    # Save to mock database
    mock_db.session.add(price_alert)
    mock_db.session.commit()
    mock_db.session.refresh(price_alert)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(price_alert)
    mock_db.session.commit.assert_called_once()
    
    # Test to_dict method
    alert_dict = price_alert.to_dict()
    assert "type_RTX 3090" in alert_dict
    assert alert_dict["type_RTX 3090"]["targetPrice"] == 450.0
    assert alert_dict["type_RTX 3090"]["isTypeAlert"] is True
    assert alert_dict["type_RTX 3090"]["gpuType"] == "RTX 3090"
    assert alert_dict["type_RTX 3090"]["createdAt"] == created_at.isoformat()

@pytest.mark.unit_tests
def test_selected_gpu_creation(db_fixture, isolated_user_preference_models):
    """Test creating a SelectedGPU"""
    mock_db = db_fixture
    _, _, TestSelectedGPU, _ = isolated_user_preference_models
    
    # Create a SelectedGPU
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    selected_gpu = TestSelectedGPU(
        gpu_id=1,
        created_at=created_at
    )
    
    # Test attributes
    assert selected_gpu.gpu_id == 1
    assert selected_gpu.created_at == created_at
    
    # Save to mock database
    mock_db.session.add(selected_gpu)
    mock_db.session.commit()
    mock_db.session.refresh(selected_gpu)
    selected_gpu.id = 1  # Simulate ID assignment
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(selected_gpu)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_selected_gpu_to_dict(isolated_user_preference_models):
    """Test the to_dict method returns correct data for SelectedGPU"""
    _, _, TestSelectedGPU, _ = isolated_user_preference_models
    
    # Create mock GPU
    mock_gpu = MagicMock()
    mock_gpu.id = 1
    mock_gpu.to_dict.return_value = {"id": 1, "name": "Test GPU"}
    
    # Create SelectedGPU
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    selected_gpu = TestSelectedGPU(
        gpu_id=1,
        created_at=created_at
    )
    selected_gpu.id = 1  # Simulate ID assignment
    selected_gpu.gpu = mock_gpu  # Set relationship manually
    
    # Call to_dict method
    selected_gpu_dict = selected_gpu.to_dict()
    
    # Verify returned dictionary
    assert selected_gpu_dict["id"] == 1
    assert selected_gpu_dict["gpu_id"] == 1
    assert selected_gpu_dict["created_at"] == created_at.isoformat()
    assert selected_gpu_dict["gpu"] == {"id": 1, "name": "Test GPU"}

@pytest.mark.unit_tests
def test_favorite_gpu_creation(db_fixture, isolated_user_preference_models):
    """Test creating a FavoriteGPU"""
    mock_db = db_fixture
    _, _, _, TestFavoriteGPU = isolated_user_preference_models
    
    # Create a FavoriteGPU
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    favorite_gpu = TestFavoriteGPU(
        gpu_id=1,
        created_at=created_at
    )
    
    # Test attributes
    assert favorite_gpu.gpu_id == 1
    assert favorite_gpu.created_at == created_at
    
    # Save to mock database
    mock_db.session.add(favorite_gpu)
    mock_db.session.commit()
    mock_db.session.refresh(favorite_gpu)
    
    # Verify database operations were called
    mock_db.session.add.assert_called_once_with(favorite_gpu)
    mock_db.session.commit.assert_called_once()

@pytest.mark.unit_tests
def test_favorite_gpu_to_dict(isolated_user_preference_models):
    """Test the to_dict method returns correct data for FavoriteGPU"""
    _, _, _, TestFavoriteGPU = isolated_user_preference_models
    
    # Create mock GPU and host
    mock_host = MagicMock()
    mock_host.name = "Test Host"
    
    mock_gpu = MagicMock()
    mock_gpu.id = 1
    mock_gpu.name = "Test GPU"
    mock_gpu.host = mock_host
    
    # Create FavoriteGPU
    created_at = datetime(2023, 5, 15, tzinfo=timezone.utc)
    favorite_gpu = TestFavoriteGPU(
        gpu_id=1,
        created_at=created_at
    )
    favorite_gpu.gpu = mock_gpu  # Set relationship manually
    
    # Call to_dict method
    favorite_gpu_dict = favorite_gpu.to_dict()
    
    # Verify returned dictionary
    assert favorite_gpu_dict["id"] == 1
    assert favorite_gpu_dict["name"] == "Test GPU"
    assert favorite_gpu_dict["host_name"] == "Test Host"

@pytest.mark.unit_tests
def test_favorite_gpu_to_dict_no_gpu(isolated_user_preference_models):
    """Test the to_dict method when gpu relationship is not set"""
    _, _, _, TestFavoriteGPU = isolated_user_preference_models
    
    # Create FavoriteGPU without setting gpu relationship
    favorite_gpu = TestFavoriteGPU(
        gpu_id=2,
        created_at=datetime(2023, 5, 15, tzinfo=timezone.utc)
    )
    
    # Call to_dict method
    favorite_gpu_dict = favorite_gpu.to_dict()
    
    # Verify returned dictionary uses fallbacks
    assert favorite_gpu_dict["id"] == 2
    assert favorite_gpu_dict["name"] == "GPU 2"
    assert favorite_gpu_dict["host_name"] is None