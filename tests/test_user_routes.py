import pytest
import json
from models.user import User
from utils.database import db
from unittest.mock import patch

def test_sync_user(client, auth_headers, mock_firebase, session):
    """Test syncing a Firebase user with the backend database."""
    response = client.post(
        "/api/user/sync",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['firebase_uid'] == mock_firebase['user_id']
    assert data['email'] == mock_firebase['get_user'].return_value.email

def test_get_user_profile(client, auth_headers, test_user):
    """Test getting a user's profile."""
    response = client.get(
        "/api/user/profile",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['firebase_uid'] == test_user.firebase_uid
    assert data['email'] == test_user.email
    assert data['first_name'] == test_user.first_name
    assert data['last_name'] == test_user.last_name
    assert data["organization"] == "Test Org"
    assert data["experience_level"] == "intermediate"

def test_update_user_profile(client, auth_headers, test_user, session):
    """Test updating a user's profile."""
    update_data = {
        "first_name": "Updated",
        "last_name": "Name",
        "organization": "New Org",
        "experience_level": "advanced"
    }
    
    response = client.put(
        "/api/user/profile",
        headers=auth_headers,
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['first_name'] == update_data['first_name']
    assert data['last_name'] == update_data['last_name']
    assert data['organization'] == update_data['organization']
    assert data['experience_level'] == update_data['experience_level']

def test_get_nonexistent_user_profile(client, auth_headers):
    """Test getting a profile for a non-existent user."""
    # Use a different user ID that doesn't exist in the database
    with patch('firebase_admin.auth.verify_id_token') as mock_verify:
        mock_verify.return_value = {
            'uid': 'nonexistent_user_id',
            'email': 'nonexistent@example.com'
        }
        headers = {
            "Authorization": "Bearer valid_test_token",
            "Firebase-ID": "nonexistent_user_id"
        }
        
        response = client.get(
            "/api/user/profile",
            headers=headers
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data

def test_update_nonexistent_user_profile(client, auth_headers):
    """Test updating a profile for a non-existent user."""
    # Use a different user ID that doesn't exist in the database
    with patch('firebase_admin.auth.verify_id_token') as mock_verify:
        mock_verify.return_value = {
            'uid': 'nonexistent_user_id',
            'email': 'nonexistent@example.com'
        }
        headers = {
            "Authorization": "Bearer valid_test_token",
            "Firebase-ID": "nonexistent_user_id"
        }
        
        update_data = {
            "first_name": "Updated",
            "last_name": "Name"
        }
        
        response = client.put(
            "/api/user/profile",
            headers=headers,
            json=update_data
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data

def test_unauthorized_access(client):
    """Test accessing user routes without authentication."""
    # Test sync endpoint
    response = client.post("/api/user/sync")
    assert response.status_code == 401
    
    # Test profile GET endpoint
    response = client.get("/api/user/profile")
    assert response.status_code == 401
    
    # Test profile PUT endpoint
    response = client.put("/api/user/profile", json={"first_name": "Test"})
    assert response.status_code == 401

def test_invalid_update_data(client, auth_headers, test_user):
    """Test updating a user profile with invalid data."""
    # Test with empty data
    response = client.put(
        "/api/user/profile",
        headers=auth_headers,
        json={}
    )
    assert response.status_code == 200  # Empty updates are allowed
    
    # Test with invalid experience level (if implemented)
    response = client.put(
        "/api/user/profile",
        headers=auth_headers,
        json={"experience_level": "invalid_level"}
    )
    assert response.status_code == 200  # Currently no validation on experience_level
