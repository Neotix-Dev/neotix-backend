import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, Response

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.api_auth import generate_api_key, check_api_key, require_api_key, require_admin_key
from models.api_key import APIKeyPermission, APIKey

class TestGenerateApiKey:
    """Tests for the API key generation function"""
    
    def test_generates_unique_keys(self):
        """Test that generate_api_key creates unique keys"""
        key1 = generate_api_key()
        key2 = generate_api_key()
        key3 = generate_api_key()
        
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
    
    def test_key_format(self):
        """Test that generated keys have expected format/length"""
        key = generate_api_key()
        
        # Should be a string
        assert isinstance(key, str)
        
        # Should be URL-safe (no special chars)
        import re
        assert re.match(r'^[A-Za-z0-9_-]+$', key) is not None
        
        # Should be reasonably long (at least 32 chars for secrets.token_urlsafe(32))
        assert len(key) >= 32

class TestApiKeyDecorator:
    """Tests for the API key checking decorator"""
    
    @pytest.fixture
    def mock_app(self):
        """Create a test Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/test')
        def test_route():
            return jsonify({"success": True})
            
        @app.route('/protected')
        @require_api_key
        def protected_route():
            return jsonify({"success": True})
            
        @app.route('/admin')
        @require_admin_key
        def admin_route():
            return jsonify({"success": True})
            
        @app.route('/custom')
        @check_api_key(APIKeyPermission.READ)
        def custom_route():
            return jsonify({"success": True})
        
        return app
    
    @pytest.fixture
    def mock_db(self):
        """Mock the database session"""
        with patch('utils.api_auth.db') as mock_db:
            yield mock_db
    
    @pytest.fixture
    def mock_api_key_model(self):
        """Mock the APIKey model"""
        with patch('utils.api_auth.APIKey') as mock_model:
            # Set up query mock chain
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_first = MagicMock()
            
            mock_model.query = mock_query
            mock_query.filter_by = mock_filter
            mock_filter.first = mock_first
            mock_first.return_value = None  # Default to no key found
            
            yield mock_model
    
    @pytest.fixture
    def valid_api_key(self):
        """Create a valid API key record"""
        key = MagicMock()
        key.key = "valid_test_key_123"
        key.permission = APIKeyPermission.READ.value
        key.is_active = True
        key.last_used_at = None
        return key
    
    @pytest.fixture
    def admin_api_key(self):
        """Create a valid admin API key record"""
        key = MagicMock()
        key.key = "valid_admin_key_456"
        key.permission = APIKeyPermission.ADMIN.value
        key.is_active = True
        key.last_used_at = None
        return key
        
    def test_no_api_key_provided(self, mock_app, mock_api_key_model):
        """Test behavior when no API key is provided"""
        client = mock_app.test_client()
        
        # Make request without API key header
        response = client.get('/protected')
        
        # Verify response
        assert response.status_code == 401
        assert response.json['error'] == 'No API key provided'
    
    def test_invalid_api_key(self, mock_app, mock_api_key_model):
        """Test behavior with invalid API key"""
        client = mock_app.test_client()
        
        # Configure mock to return None (key not found)
        mock_api_key_model.query.filter_by().first.return_value = None
        
        # Make request with invalid key
        response = client.get('/protected', headers={"X-API-Key": "invalid_key"})
        
        # Verify response
        assert response.status_code == 401
        assert response.json['error'] == 'Invalid API key'
        
        # Verify database was queried with correct parameters
        mock_api_key_model.query.filter_by.assert_called_with(key="invalid_key", is_active=True)
    
    def test_master_key(self, mock_app, mock_api_key_model):
        """Test that master key from environment works"""
        client = mock_app.test_client()
        
        # Set up environment variable
        with patch.dict(os.environ, {"MASTER_API_KEY": "master_secret_key"}):
            # Try accessing admin endpoint with master key
            response = client.get('/admin', headers={"X-API-Key": "master_secret_key"})
            
            # Verify success
            assert response.status_code == 200
            assert response.json['success'] is True
            
            # Verify database was not queried (master key skips DB check)
            mock_api_key_model.query.filter_by.assert_not_called()
    
    def test_valid_key_with_insufficient_permissions(self, mock_app, mock_api_key_model, valid_api_key):
        """Test behavior when key has insufficient permissions"""
        client = mock_app.test_client()
        
        # Configure mock to return a READ key when trying to access admin endpoint
        mock_api_key_model.query.filter_by().first.return_value = valid_api_key
        
        # Make request to admin endpoint with READ key
        response = client.get('/admin', headers={"X-API-Key": valid_api_key.key})
        
        # Verify response
        assert response.status_code == 403
        assert response.json['error'] == 'Insufficient permissions'
        assert APIKeyPermission.ADMIN.value in response.json['message']
    
    def test_valid_key_updates_timestamp(self, mock_app, mock_api_key_model, mock_db, valid_api_key):
        """Test that last_used_at is updated on successful authentication"""
        client = mock_app.test_client()
        
        # Configure mock to return a valid key
        mock_api_key_model.query.filter_by().first.return_value = valid_api_key
        
        # Make request with valid key
        before_request = datetime.now(timezone.utc)
        response = client.get('/protected', headers={"X-API-Key": valid_api_key.key})
        
        # Verify response
        assert response.status_code == 200
        
        # Verify last_used_at was updated
        assert valid_api_key.last_used_at is not None
        assert isinstance(valid_api_key.last_used_at, datetime)
        
        # Verify database session was committed
        mock_db.session.commit.assert_called_once()
    
    def test_require_api_key_decorator(self, mock_app, mock_api_key_model, valid_api_key):
        """Test the require_api_key convenience decorator"""
        client = mock_app.test_client()
        
        # Configure mock to return a valid key
        mock_api_key_model.query.filter_by().first.return_value = valid_api_key
        
        # Make request to protected endpoint
        response = client.get('/protected', headers={"X-API-Key": valid_api_key.key})
        
        # Verify success
        assert response.status_code == 200
        assert response.json['success'] is True
    
    def test_require_admin_key_decorator(self, mock_app, mock_api_key_model, admin_api_key):
        """Test the require_admin_key convenience decorator"""
        client = mock_app.test_client()
        
        # Configure mock to return an admin key
        mock_api_key_model.query.filter_by().first.return_value = admin_api_key
        
        # Make request to admin endpoint
        response = client.get('/admin', headers={"X-API-Key": admin_api_key.key})
        
        # Verify success
        assert response.status_code == 200
        assert response.json['success'] is True
    
    def test_check_api_key_function(self, mock_app, mock_api_key_model, valid_api_key):
        """Test the check_api_key function with a specific permission"""
        client = mock_app.test_client()
        
        # Configure mock to return a valid key with READ permission
        mock_api_key_model.query.filter_by().first.return_value = valid_api_key
        
        # Make request to custom endpoint that requires READ permission
        response = client.get('/custom', headers={"X-API-Key": valid_api_key.key})
        
        # Verify success since the key has READ permission
        assert response.status_code == 200
        assert response.json['success'] is True
        
    def test_decorator_preserves_function_metadata(self):
        """Test that the decorator properly preserves function metadata"""
        @check_api_key()
        def test_function():
            """Test docstring"""
            pass
            
        # Verify the decorated function keeps its metadata
        assert test_function.__name__ == 'test_function'
        assert test_function.__doc__ == 'Test docstring'