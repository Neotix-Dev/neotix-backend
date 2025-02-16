import pytest
from models.cluster import Cluster

@pytest.mark.usefixtures("mock_firebase")
def test_get_user_clusters(client, auth_headers, test_user, test_cluster):
    """Test getting all clusters for a user."""
    response = client.get(
        "/api/clusters/",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['name'] == test_cluster.name
    assert data[0]['description'] == test_cluster.description

@pytest.mark.usefixtures("mock_firebase")
def test_create_cluster(client, auth_headers, test_user):
    """Test creating a new cluster."""
    cluster_data = {
        "name": "New Cluster",
        "description": "New Description"
    }
    response = client.post(
        "/api/clusters/",
        headers=auth_headers,
        json=cluster_data
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == cluster_data['name']
    assert data['description'] == cluster_data['description']
    assert data['user_id'] == test_user.id

@pytest.mark.usefixtures("mock_firebase")
def test_update_cluster(client, auth_headers, test_cluster):
    """Test updating an existing cluster."""
    update_data = {
        "name": "Updated Cluster",
        "description": "Updated Description"
    }
    response = client.put(
        f"/api/clusters/{test_cluster.id}",
        headers=auth_headers,
        json=update_data
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['name'] == update_data['name']
    assert data['description'] == update_data['description']

@pytest.mark.usefixtures("mock_firebase")
def test_delete_cluster(client, auth_headers, test_cluster):
    """Test deleting a cluster."""
    response = client.delete(
        f"/api/clusters/{test_cluster.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Cluster deleted successfully'

@pytest.mark.usefixtures("mock_firebase")
def test_add_gpu_to_cluster(client, auth_headers, test_cluster, test_gpu):
    """Test adding a GPU to a cluster."""
    response = client.post(
        f"/api/clusters/{test_cluster.id}/gpus",
        headers=auth_headers,
        json={"gpu_id": test_gpu.id}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert test_gpu.id in [gpu['id'] for gpu in data['gpus']]

@pytest.mark.usefixtures("mock_firebase")
def test_remove_gpu_from_cluster(client, auth_headers, test_cluster, test_gpu):
    """Test removing a GPU from a cluster."""
    # First add the GPU
    client.post(
        f"/api/clusters/{test_cluster.id}/gpus",
        headers=auth_headers,
        json={"gpu_id": test_gpu.id}
    )
    
    # Then remove it
    response = client.delete(
        f"/api/clusters/{test_cluster.id}/gpus/{test_gpu.id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert test_gpu.id not in [gpu['id'] for gpu in data['gpus']]

@pytest.mark.usefixtures("mock_firebase")
def test_cluster_not_found(client, auth_headers):
    """Test accessing a non-existent cluster."""
    response = client.get(
        "/api/clusters/999",
        headers=auth_headers
    )
    assert response.status_code == 404

@pytest.mark.usefixtures("mock_firebase")
def test_unauthorized_access(client, test_cluster):
    """Test accessing endpoints without authentication."""
    # Test GET endpoints
    response = client.get("/api/clusters/")
    assert response.status_code == 401
    
    response = client.get(f"/api/clusters/{test_cluster.id}")
    assert response.status_code == 401
    
    # Test POST endpoints
    response = client.post("/api/clusters/", json={})
    assert response.status_code == 401
    
    # Test PUT endpoints
    response = client.put(f"/api/clusters/{test_cluster.id}", json={})
    assert response.status_code == 401
    
    # Test DELETE endpoints
    response = client.delete(f"/api/clusters/{test_cluster.id}")
    assert response.status_code == 401

@pytest.mark.usefixtures("mock_firebase")
def test_cluster_validation(client, auth_headers, test_user):
    """Test cluster creation with invalid data."""
    invalid_data = {
        "description": "Missing name field"
    }
    response = client.post(
        "/api/clusters/",
        headers=auth_headers,
        json=invalid_data
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
