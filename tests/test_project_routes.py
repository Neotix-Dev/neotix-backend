import pytest
from models.project import Project

@pytest.mark.usefixtures("mock_firebase")
def test_get_user_projects(client, auth_headers, test_user, test_project):
    """Test getting all projects for a user."""
    response = client.get(
        "/api/projects/",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['name'] == test_project.name
    assert data[0]['description'] == test_project.description

@pytest.mark.usefixtures("mock_firebase")
def test_create_project(client, auth_headers, test_user):
    """Test creating a new project."""
    project_data = {
        "name": "New Project",
        "description": "New Description"
    }
    response = client.post(
        "/api/projects/",
        headers=auth_headers,
        json=project_data
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == project_data['name']
    assert data['description'] == project_data['description']
    assert data['user_id'] == test_user.id

@pytest.mark.usefixtures("mock_firebase")
def test_update_project(client, auth_headers, test_project):
    """Test updating an existing project."""
    update_data = {
        "name": "Updated Project",
        "description": "Updated Description"
    }
    response = client.put(
        f"/api/projects/{test_project.id}",
        headers=auth_headers,
        json=update_data
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == update_data['name']
    assert data['description'] == update_data['description']

@pytest.mark.usefixtures("mock_firebase")
def test_delete_project(client, auth_headers, test_project):
    """Test deleting a project."""
    response = client.delete(
        f"/api/projects/{test_project.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Project deleted successfully'

@pytest.mark.usefixtures("mock_firebase")
def test_add_gpu_to_project(client, auth_headers, test_project, test_gpu):
    """Test adding a GPU to a project."""
    response = client.post(
        f"/api/projects/{test_project.id}/gpus",
        headers=auth_headers,
        json={"gpu_id": test_gpu.id}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert test_gpu.id in [gpu['id'] for gpu in data['gpus']]

@pytest.mark.usefixtures("mock_firebase")
def test_remove_gpu_from_project(client, auth_headers, test_project, test_gpu):
    """Test removing a GPU from a project."""
    # First add the GPU
    client.post(
        f"/api/projects/{test_project.id}/gpus",
        headers=auth_headers,
        json={"gpu_id": test_gpu.id}
    )
    
    # Then remove it
    response = client.delete(
        f"/api/projects/{test_project.id}/gpus/{test_gpu.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert test_gpu.id not in [gpu['id'] for gpu in data['gpus']]

@pytest.mark.usefixtures("mock_firebase")
def test_project_not_found(client, auth_headers):
    """Test accessing a non-existent project."""
    response = client.get(
        "/api/projects/999",
        headers=auth_headers
    )
    assert response.status_code == 404

@pytest.mark.usefixtures("mock_firebase")
def test_unauthorized_access(client, test_project):
    """Test accessing endpoints without authentication."""
    # Test GET endpoints
    response = client.get("/api/projects/")
    assert response.status_code == 401
    
    response = client.get(f"/api/projects/{test_project.id}")
    assert response.status_code == 401
    
    # Test POST endpoints
    response = client.post("/api/projects/", json={})
    assert response.status_code == 401
    
    # Test PUT endpoints
    response = client.put(f"/api/projects/{test_project.id}", json={})
    assert response.status_code == 401
    
    # Test DELETE endpoints
    response = client.delete(f"/api/projects/{test_project.id}")
    assert response.status_code == 401

@pytest.mark.usefixtures("mock_firebase")
def test_project_validation(client, auth_headers, test_user):
    """Test project creation with invalid data."""
    invalid_data = {
        "description": "Missing name field"
    }
    response = client.post(
        "/api/projects/",
        headers=auth_headers,
        json=invalid_data
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
