import pytest
from app import create_app
import json
import asyncio

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_preferences_selected_gpus_get(client):
    response = client.get("/api/preferences/selected-gpus")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_user_preferences_rented_gpus_get(client):
    response = client.get("/api/preferences/rented-gpus")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_user_preferences_price_alerts_get(client):
    response = client.get("/api/preferences/price-alerts")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, dict)

def test_user_preferences_favorite_gpus_get(client):
    response = client.get("/api/preferences/favorite-gpus")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_gpu_routes_get_all_get(client):
    response = client.get("/api/gpu/get_all")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_gpu_routes_search_get(client):
    response = client.get("/api/gpu/search?q=RTX")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_gpu_routes_search_numeric_get(client):
    response = client.get("/api/gpu/search?q=16")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_gpu_routes_search_empty_get(client):
    response = client.get("/api/gpu/search?q=")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 0

def test_gpu_routes_hosts_get(client):
    response = client.get("/api/gpu/hosts")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_gpu_routes_get_paginated_get(client):
    response = client.get("/api/gpu/get_gpus/1")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, dict)
    assert "gpus" in data
    assert isinstance(data["gpus"], list)
    assert "current_page" in data
    assert "total_pages" in data
    assert "total_gpus" in data
    assert "gpus_per_page" in data

def test_gpu_routes_filtered_get(client):
    response = client.get("/api/gpu/filtered?gpu_name=RTX&min_gpu_memory=16")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, dict)
    assert "gpus" in data
    assert isinstance(data["gpus"], list)
    assert "current_page" in data
    assert "total_pages" in data
    assert "total_items" in data
    assert "items_per_page" in data

def test_gpu_routes_vendors_get(client):
    response = client.get("/api/gpu/vendors")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_gpu_routes_price_history_get(client):
    response = client.get("/api/gpu/1/price-history")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_gpu_routes_price_points_get(client):
    response = client.get("/api/gpu/1/price-points")
    assert response.status_code == 200
    assert response.content_type == "application/json"
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_gpu_routes_get_by_id_get(client):
    response = client.get("/api/gpu/get_all")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    if data:
        first_gpu_id = data[0]["id"]
        response = client.get(f"/api/gpu/{first_gpu_id}")
        assert response.status_code == 200
        assert response.content_type == "application/json"
        data = json.loads(response.data)
        assert isinstance(data, dict)

def test_user_routes_get(client):
    response = client.get("/api/user/")
    assert response.status_code == 405

def test_project_routes_get(client):
    response = client.get("/api/projects/")
    assert response.status_code == 401