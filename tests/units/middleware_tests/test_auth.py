import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from flask import Flask, jsonify, g
from firebase_admin import auth

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the auth_required decorator
from middleware.auth import auth_required
from models.user import User


@pytest.fixture
def app():
    """Create minimal Flask app for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def mock_user():
    """Create a mock user"""
    mock = MagicMock()
    mock.id = 123
    mock.firebase_uid = "test_uid"
    mock.email = "test@example.com"
    return mock

@pytest.mark.unit_tests
def test_no_auth_header(app):
    """Test when no authorization header is provided"""
    with app.test_request_context():
        # Create a simple test function
        @auth_required
        def test_func():
            return "Success"
            
        # Call the decorated function
        response, status_code = test_func()
        
        # Verify response
        assert status_code == 401
        assert "No authorization token provided" in response.get_json()["error"]

@pytest.mark.unit_tests
def test_invalid_token_format(app):
    """Test when token format is invalid"""
    with app.test_request_context(headers={"Authorization": "InvalidFormat"}):
        @auth_required
        def test_func():
            return "Success"
            
        response, status_code = test_func()
        
        assert status_code == 401
        assert "Invalid token format" in response.get_json()["error"]

@pytest.mark.unit_tests
def test_valid_token_user_not_found(app):
    """Test when token is valid but user is not found in database"""
    with app.test_request_context(headers={"Authorization": "Bearer valid_token"}):
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            
            # Patch at module level where auth_required uses it
            with patch('middleware.auth.User') as mock_user_class:
                # Create a mock query chain
                mock_query = MagicMock()
                mock_filter_by = MagicMock()
                mock_filter_by.first.return_value = None  # User not found
                
                # Set up the chain
                mock_query.filter_by.return_value = mock_filter_by
                mock_user_class.query = mock_query
                
                @auth_required
                def test_func():
                    return "Success"
                
                response, status_code = test_func()
                
                assert status_code == 404
                assert "User not found" in response.get_json()["error"]

@pytest.mark.unit_tests
def test_valid_token_with_user_pass_user_true(app, mock_user):
    """Test when token is valid and user is found, pass_user=True"""
    with app.test_request_context(headers={"Authorization": "Bearer valid_token"}):
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            
            # Patch at module level
            with patch('middleware.auth.User') as mock_user_class:
                # Create mock query chain
                mock_query = MagicMock()
                mock_filter_by = MagicMock()
                mock_filter_by.first.return_value = mock_user
                
                # Set up the chain
                mock_query.filter_by.return_value = mock_filter_by
                mock_user_class.query = mock_query
                
                @auth_required
                def test_func(current_user=None):
                    assert current_user is not None
                    assert current_user.id == 123
                    assert g.user_id == "test_uid"
                    return jsonify({"success": True})
                
                response = test_func()
                
                # Check that g.user_id was set
                assert g.user_id == "test_uid"

@pytest.mark.unit_tests
def test_valid_token_with_user_pass_user_false(app, mock_user):
    """Test when token is valid and user is found, pass_user=False"""
    with app.test_request_context(headers={"Authorization": "Bearer valid_token"}):
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            
            # Patch at module level
            with patch('middleware.auth.User') as mock_user_class:
                # Create mock query chain
                mock_query = MagicMock()
                mock_filter_by = MagicMock()
                mock_filter_by.first.return_value = mock_user
                
                # Set up the chain
                mock_query.filter_by.return_value = mock_filter_by
                mock_user_class.query = mock_query
                
                @auth_required(pass_user=False)
                def test_func():
                    # Should not have current_user as parameter
                    assert g.user_id == "test_uid"
                    return jsonify({"success": True})
                
                test_func()
                
                # Check that g.user_id was set
                assert g.user_id == "test_uid"

@pytest.mark.unit_tests
def test_expired_token(app):
    """Test when token is expired"""
    with app.test_request_context(headers={"Authorization": "Bearer expired_token"}):
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            # Fix: Add required 'cause' argument
            mock_verify.side_effect = auth.ExpiredIdTokenError("Token expired", None)
            
            @auth_required
            def test_func():
                return "Success"
                
            response, status_code = test_func()
            
            assert status_code == 401
            assert "Token expired" in response.get_json()["error"]

@pytest.mark.unit_tests
def test_invalid_token(app):
    """Test when token is invalid"""
    with app.test_request_context(headers={"Authorization": "Bearer invalid_token"}):
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            # Fix: Add required 'cause' argument
            mock_verify.side_effect = auth.InvalidIdTokenError("Invalid token", None)
            
            @auth_required
            def test_func():
                return "Success"
                
            response, status_code = test_func()
            
            assert status_code == 401
            assert "Invalid token" in response.get_json()["error"]

@pytest.mark.unit_tests
def test_revoked_token(app):
    """Test when token is revoked"""
    with app.test_request_context(headers={"Authorization": "Bearer revoked_token"}):
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            # Fix: Add required 'cause' argument
            mock_verify.side_effect = auth.RevokedIdTokenError("Token revoked")
            
            @auth_required
            def test_func():
                return "Success"
                
            response, status_code = test_func()
            
            assert status_code == 401
            # Match the actual response from your auth.py implementation
            assert response.get_json()["error"] == "Token revoked"

@pytest.mark.unit_tests
def test_other_exception(app):
    """Test when an unexpected exception occurs"""
    with app.test_request_context(headers={"Authorization": "Bearer token"}):
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.side_effect = Exception("Unexpected error")
            
            @auth_required
            def test_func():
                return "Success"
                
            response, status_code = test_func()
            
            assert status_code == 401
            assert "Authentication failed" in response.get_json()["error"]

@pytest.mark.unit_tests
def test_decorator_without_parentheses(app, mock_user):
    """Test decorator when used as @auth_required"""
    with app.test_request_context(headers={"Authorization": "Bearer valid_token"}):
        with patch('firebase_admin.auth.verify_id_token') as mock_verify:
            mock_verify.return_value = {"uid": "test_uid"}
            
            # Patch the User module directly instead of User.query
            with patch('middleware.auth.User') as mock_user_class:
                # Create mock query chain
                mock_query = MagicMock()
                mock_filter_by = MagicMock()
                mock_filter_by.first.return_value = mock_user
                
                # Set up the chain
                mock_query.filter_by.return_value = mock_filter_by
                mock_user_class.query = mock_query
                
                # Use decorator without parentheses
                @auth_required
                def test_func(current_user):
                    assert current_user is not None
                    return jsonify({"success": True})
                
                response = test_func()
                json_response = response.get_json()
                assert json_response["success"] is True