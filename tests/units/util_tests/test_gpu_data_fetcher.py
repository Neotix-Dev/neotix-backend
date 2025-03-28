import sys
import os
from pathlib import Path
import pytest
import hashlib
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, call

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.gpu_data_fetcher import hash_gpu_configuration, fetch_gpu_data
from models.gpu_listing import GPUListing, GPUPricePoint, GPUPriceHistory, Host, GPUConfiguration

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

@pytest.fixture
def mock_db_session():
    """Mock database session for testing"""
    with patch('utils.gpu_data_fetcher.db') as mock_db:
        # Create mock session
        mock_session = MagicMock()
        mock_db.session = mock_session
        
        # Configure mock query results
        mock_host_query = MagicMock()
        mock_config_query = MagicMock()
        mock_price_point_query = MagicMock()
        
        # Setup Host.query.filter_by().first()
        Host.query = MagicMock()
        Host.query.filter_by = MagicMock(return_value=mock_host_query)
        mock_host_query.first = MagicMock(return_value=None)
        
        # Setup GPUConfiguration.query.filter_by().first()
        GPUConfiguration.query = MagicMock()
        GPUConfiguration.query.filter_by = MagicMock(return_value=mock_config_query)
        mock_config_query.first = MagicMock(return_value=None)
        
        # Setup GPUPricePoint.query.filter_by().first()
        GPUPricePoint.query = MagicMock()
        GPUPricePoint.query.filter_by = MagicMock(return_value=mock_price_point_query)
        mock_price_point_query.first = MagicMock(return_value=None)
        
        yield mock_db

@pytest.fixture
def mock_gpuhunt():
    """Mock gpuhunt module for testing"""
    with patch('utils.gpu_data_fetcher.gpuhunt') as mock_gh:
        yield mock_gh

class TestHashGpuConfiguration:
    """Test the hash_gpu_configuration function"""
    
    def test_hash_consistency(self, mock_offer_factory):
        """Test that the hash function produces consistent results for same configs"""
        # Create two identical offers
        offer1 = mock_offer_factory(gpu_name="RTX 3090", gpu_count=1)
        offer2 = mock_offer_factory(gpu_name="RTX 3090", gpu_count=1)
        
        # Hashes should be identical
        assert hash_gpu_configuration(offer1) == hash_gpu_configuration(offer2)
        
    def test_hash_different_configs(self, mock_offer_factory):
        """Test that different configurations produce different hashes"""
        base_offer = mock_offer_factory(gpu_name="RTX 3090", gpu_count=1)
        base_hash = hash_gpu_configuration(base_offer)
        
        # Different GPU name
        diff_name = mock_offer_factory(gpu_name="RTX 4090", gpu_count=1)
        assert hash_gpu_configuration(diff_name) != base_hash
        
        # Different GPU count
        diff_count = mock_offer_factory(gpu_name="RTX 3090", gpu_count=2)
        assert hash_gpu_configuration(diff_count) != base_hash
        
        # Different memory
        diff_memory = mock_offer_factory(gpu_name="RTX 3090", gpu_count=1, gpu_memory=24)
        assert hash_gpu_configuration(diff_memory) != base_hash
        
    def test_hash_ignores_non_hardware_fields(self, mock_offer_factory, mock_gpu_vendor):
        """Test that the hash ignores non-hardware configuration fields"""
        # Create a common vendor mock to ensure it's the same object
        vendor_mock = mock_gpu_vendor("NVIDIA")
        
        # Create two offers with same hardware but different pricing/instance/location
        offer1 = mock_offer_factory(
            gpu_vendor=vendor_mock,
            price=1.0, 
            instance_name="instance1", 
            location="us-east"
        )
        offer2 = mock_offer_factory(
            gpu_vendor=vendor_mock,
            price=2.0, 
            instance_name="instance2", 
            location="us-west"
        )
        
        # Hashes should still be identical
        assert hash_gpu_configuration(offer1) == hash_gpu_configuration(offer2)
        
    def test_hash_algorithm(self, mock_offer_factory):
        """Test that the hash uses SHA-256 as expected"""
        offer = mock_offer_factory(gpu_name="RTX 3090", gpu_vendor="NVIDIA", gpu_count=1,
                          gpu_memory=16, cpu=8, memory=32, disk_size=100)
        
        # Manually create the expected hash
        config_str = f"RTX 3090:NVIDIA:1:16:8:32:100"
        expected_hash = hashlib.sha256(config_str.encode()).hexdigest()
        
        # Check against our function
        assert hash_gpu_configuration(offer) == expected_hash

class TestFetchGpuData:
    """Test the fetch_gpu_data function"""
    
    def test_empty_offer_list(self, mock_gpuhunt, mock_db_session):
        """Test behavior with an empty list of offers"""
        # Setup gpuhunt to return empty list
        mock_gpuhunt.query.return_value = []
        
        # Call the function
        fetch_gpu_data()
        
        # Verify no database operations occurred
        mock_db_session.session.add.assert_not_called()
        mock_db_session.session.commit.assert_called_once()
        
    def test_skip_offers_without_gpus(self, mock_gpuhunt, mock_db_session, mock_offer_factory):
        """Test that offers without GPUs are skipped"""
        # Offer without GPU
        no_gpu_offer = mock_offer_factory(gpu_count=0)
        # Offer with GPU
        gpu_offer = mock_offer_factory(gpu_count=1)
        
        mock_gpuhunt.query.return_value = [no_gpu_offer, gpu_offer]
        
        # Call the function
        fetch_gpu_data()
        
        # Verify only one set of database operations occurred (for the GPU offer)
        assert mock_db_session.session.add.call_count == 5 # Host, Config, Listing, History and PricePoint
        mock_db_session.session.commit.assert_called_once()
        
    def test_single_offer_processing(self, mock_gpuhunt, mock_db_session, mock_offer_factory):
        """Test processing a single GPU offer"""
        # Create test offer
        test_offer = mock_offer_factory(
            provider="aws",
            gpu_name="RTX 3090",
            gpu_count=1,
            instance_name="g4dn.xlarge"
        )
        mock_gpuhunt.query.return_value = [test_offer]
        
        # Configure mocks to return None (new records)
        Host.query.filter_by().first.return_value = None
        GPUConfiguration.query.filter_by().first.return_value = None
        GPUPricePoint.query.filter_by().first.return_value = None
        
        # Set up ID generation for created objects
        def add_side_effect(obj):
            # Simulate DB assigning IDs
            if isinstance(obj, Host):
                obj.id = 1
            elif isinstance(obj, GPUConfiguration):
                obj.id = 1
            elif isinstance(obj, GPUListing):
                obj.id = 1
        
        mock_db_session.session.add.side_effect = add_side_effect
        
        # Call the function
        fetch_gpu_data()
        
        # Verify database operations
        assert mock_db_session.session.add.call_count >= 4  # At least Host, Config, Listing, History
        mock_db_session.session.flush.assert_called()
        mock_db_session.session.commit.assert_called_once()
        
        # Check that models were created with correct data
        add_calls = mock_db_session.session.add.call_args_list
        
        # Find the Host add call
        host_calls = [call for call in add_calls if isinstance(call[0][0], Host)]
        assert len(host_calls) == 1
        assert host_calls[0][0][0].name == "aws"
        
        # Find the GPUConfiguration add call
        config_calls = [call for call in add_calls if isinstance(call[0][0], GPUConfiguration)]
        assert len(config_calls) == 1
        assert config_calls[0][0][0].gpu_name == "RTX 3090"
        assert config_calls[0][0][0].gpu_count == 1
        
        # Find the GPUListing add call
        listing_calls = [call for call in add_calls if isinstance(call[0][0], GPUListing)]
        assert len(listing_calls) == 1
        assert listing_calls[0][0][0].instance_name == "g4dn.xlarge"
        assert listing_calls[0][0][0].current_price == 1.0
        
    def test_multiple_providers(self, mock_gpuhunt, mock_db_session, mock_offer_factory):
        """Test processing offers from multiple providers"""
        # Create test offers from different providers
        aws_offer = mock_offer_factory(provider="aws", gpu_name="RTX 3090")
        gcp_offer = mock_offer_factory(provider="gcp", gpu_name="Tesla V100")
        azure_offer = mock_offer_factory(provider="azure", gpu_name="A100")
        
        mock_gpuhunt.query.return_value = [aws_offer, gcp_offer, azure_offer]
        
        # Call the function
        fetch_gpu_data()
        
        # Verify database operations for multiple hosts
        add_calls = mock_db_session.session.add.call_args_list
        host_calls = [call for call in add_calls if isinstance(call[0][0], Host)]
        
        # Should have 3 different hosts
        host_names = [call[0][0].name for call in host_calls]
        assert len(set(host_names)) == 3
        assert "aws" in host_names
        assert "gcp" in host_names
        assert "azure" in host_names
        
        # Verify commit happened once at the end
        mock_db_session.session.commit.assert_called_once()
        
    def test_existing_host_reuse(self, mock_gpuhunt, mock_db_session, mock_offer_factory):
        """Test that existing hosts are reused"""
        # Create test offer
        test_offer = mock_offer_factory(provider="aws")
        mock_gpuhunt.query.return_value = [test_offer]
        
        # Configure mock to return an existing host
        existing_host = Host(name="aws")
        existing_host.id = 42
        Host.query.filter_by().first.return_value = existing_host
        
        # Call the function
        fetch_gpu_data()
        
        # Verify no new host was added
        add_calls = mock_db_session.session.add.call_args_list
        host_calls = [call for call in add_calls if isinstance(call[0][0], Host)]
        assert len(host_calls) == 0
        
        # Verify the listing used the existing host
        listing_calls = [call for call in add_calls if isinstance(call[0][0], GPUListing)]
        assert len(listing_calls) == 1
        assert listing_calls[0][0][0].host_id == 42
        
    def test_existing_config_reuse(self, mock_gpuhunt, mock_db_session, mock_offer_factory):
        """Test that existing configurations are reused"""
        # Create test offer
        test_offer = mock_offer_factory(gpu_name="RTX 3090")
        mock_gpuhunt.query.return_value = [test_offer]
        
        # Configure mock to return existing host and config
        existing_host = Host(name=test_offer.provider)
        existing_host.id = 1
        
        # Create config with all required parameters
        existing_config = GPUConfiguration(
            hash="randomhash2025!2f",
            gpu_name="RTX 3090",
            gpu_vendor="NVIDIA",
            gpu_count=2,
            gpu_memory=24,
            cpu=8,
            memory=32,
            disk_size=512
        )
        existing_config.id = 99  # Set ID after creation
        
        Host.query.filter_by().first.return_value = existing_host
        GPUConfiguration.query.filter_by().first.return_value = existing_config
        
        # Call the function
        fetch_gpu_data()
        
        # Verify no new config was added
        add_calls = mock_db_session.session.add.call_args_list
        config_calls = [call for call in add_calls if isinstance(call[0][0], GPUConfiguration)]
        assert len(config_calls) == 0
        
        # Verify the listing used the existing config
        listing_calls = [call for call in add_calls if isinstance(call[0][0], GPUListing)]
        assert len(listing_calls) == 1
        assert listing_calls[0][0][0].configuration_id == 99
        
    def test_price_point_update(self, mock_gpuhunt, mock_db_session, mock_offer_factory):
        """Test updating an existing price point"""
        # Create test offer
        test_offer = mock_offer_factory(price=1.5, location="us-east")
        mock_gpuhunt.query.return_value = [test_offer]
        
        # Configure mocks for existing records - using actual constructors
        existing_host = Host(
            name=test_offer.provider,
            description=f"GPU provider: {test_offer.provider}",
            url=""
        )
        existing_host.id = 1
        
        # Need to provide all required parameters for GPUConfiguration
        config_hash = "test_hash_123"
        existing_config = GPUConfiguration(
            hash=config_hash,
            gpu_name=test_offer.gpu_name,
            gpu_vendor=test_offer.gpu_vendor.value if test_offer.gpu_vendor else None,
            gpu_count=test_offer.gpu_count,
            gpu_memory=test_offer.gpu_memory,
            cpu=test_offer.cpu,
            memory=test_offer.memory,
            disk_size=test_offer.disk_size
        )
        existing_config.id = 1
        
        # For GPUPricePoint, no custom __init__ so we need to set all attributes
        existing_price_point = GPUPricePoint()
        existing_price_point.id = 1
        existing_price_point.gpu_listing_id = 1
        existing_price_point.price = 1.0  # Old price
        existing_price_point.location = "us-east"
        existing_price_point.spot = True
        existing_price_point.last_updated = datetime.now(timezone.utc)
        
        # Set up mocks to return our objects
        Host.query.filter_by().first.return_value = existing_host
        GPUConfiguration.query.filter_by().first.return_value = existing_config
        
        # Set up to return existing price point when queried
        call_count = 0
        def price_point_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return existing_price_point
            return None
            
        GPUPricePoint.query.filter_by().first.side_effect = price_point_side_effect
        
        # Need to set up the gpu_listing since it's used to query price point
        def add_side_effect(obj):
            if isinstance(obj, GPUListing):
                obj.id = 1
        
        mock_db_session.session.add.side_effect = add_side_effect
        
        # Call the function
        fetch_gpu_data()
        
        # Should not add a new price point
        add_calls = mock_db_session.session.add.call_args_list
        price_point_calls = [call for call in add_calls if isinstance(call[0][0], GPUPricePoint)]
        assert len(price_point_calls) == 0
        
        # Should update the existing price point
        assert existing_price_point.price == 1.5  # Updated to new price
        
    def test_error_handling(self, mock_gpuhunt, mock_db_session, mock_offer_factory):
        """Test error handling during database operations"""
        # Create test offer
        test_offer = mock_offer_factory()
        mock_gpuhunt.query.return_value = [test_offer]
        
        # Configure commit to raise an exception
        mock_db_session.session.commit.side_effect = Exception("Test error")
        
        # Call the function - should raise the exception
        with pytest.raises(Exception, match="Test error"):
            fetch_gpu_data()
            
        # Verify rollback was called
        mock_db_session.session.rollback.assert_called_once()