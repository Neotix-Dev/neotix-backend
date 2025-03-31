import pytest
import json
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

# Assuming conftest.py provides 'client' and 'auth_headers' fixtures
# Adjust imports based on your actual project structure if needed
from models.gpu_listing import GPUListing, GPUConfiguration, Host


@pytest.mark.usefixtures("client", "auth_headers")
class TestGPUListingsSemanticSearch:

    @pytest.fixture
    def mock_chroma_query_results(self):
        """Fixture for sample ChromaDB query results."""
        return {
            "ids": [["gpu_1", "gpu_2"]],
            "metadatas": [[{"postgres_id": 1, "gpu_name": "RTX 4090"}, {"postgres_id": 2, "gpu_name": "A100"}]],
            "distances": [[0.1, 0.2]],
            "embeddings": None, # Not usually needed for response processing
            "documents": None # Not usually needed for response processing
        }
    
    @pytest.fixture
    def mock_empty_chroma_query_results(self):
         """Fixture for empty ChromaDB query results."""
         return {"ids": [[]], "metadatas": [[]], "distances": [[]]}


    @pytest.fixture
    def mock_db_listings(self):
        """Fixture for sample GPUListing objects from DB."""
        # Create mock objects that mimic SQLAlchemy models with necessary attributes/methods
        mock_host1 = MagicMock(spec=Host)
        mock_host1.name = "Provider A"
        mock_config1 = MagicMock(spec=GPUConfiguration)
        mock_config1.gpu_name = "RTX 4090"
        mock_config1.gpu_vendor = "NVIDIA"
        mock_config1.gpu_count = 1
        mock_config1.gpu_memory = 24
        mock_config1.cpu = 16
        mock_config1.memory = 64
        mock_config1.disk_size = 1000
        mock_config1.gpu_score = 95.5
        mock_listing1 = MagicMock(spec=GPUListing)
        mock_listing1.id = 1
        mock_listing1.instance_name = "Instance A"
        mock_listing1.current_price = 1.50
        mock_listing1.configuration = mock_config1
        mock_listing1.host = mock_host1
        mock_listing1.to_dict.return_value = { # Simulate the to_dict output
            "id": 1, "instance_name": "Instance A", "gpu_name": "RTX 4090", "current_price": 1.50,
            # Add other fields matching your actual to_dict output
        }
        
        mock_host2 = MagicMock(spec=Host)
        mock_host2.name = "Provider B"
        mock_config2 = MagicMock(spec=GPUConfiguration)
        mock_config2.gpu_name = "A100"
        mock_config2.gpu_vendor = "NVIDIA"
        mock_config2.gpu_count = 1
        mock_config2.gpu_memory = 80
        mock_config2.cpu = 32
        mock_config2.memory = 256
        mock_config2.disk_size = 2000
        mock_config2.gpu_score = 99.0
        mock_listing2 = MagicMock(spec=GPUListing)
        mock_listing2.id = 2
        mock_listing2.instance_name = "Instance B"
        mock_listing2.current_price = 4.10
        mock_listing2.configuration = mock_config2
        mock_listing2.host = mock_host2
        mock_listing2.to_dict.return_value = {
            "id": 2, "instance_name": "Instance B", "gpu_name": "A100", "current_price": 4.10,
        }

        return [mock_listing1, mock_listing2]

    @patch('routes.gpu_listings.get_gpu_listings_collection')
    @patch('routes.gpu_listings.get_embedding_model')
    @patch('routes.gpu_listings.db.session.query')
    def test_semantic_search_success(self, mock_db_query, mock_get_model, mock_get_collection, client, auth_headers, mock_chroma_query_results, mock_db_listings):
        """Test successful semantic vector search."""
        # Mock ChromaDB collection query
        mock_collection = MagicMock()
        mock_collection.query.return_value = mock_chroma_query_results
        mock_get_collection.return_value = mock_collection

        # Mock embedding model
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384) # Example embedding
        mock_get_model.return_value = mock_model

        # Mock database query to return listings based on IDs from Chroma
        mock_query_obj = MagicMock()
        mock_query_obj.options.return_value = mock_query_obj # Chain options call
        mock_query_obj.filter.return_value = mock_query_obj # Chain filter call
        mock_query_obj.all.return_value = mock_db_listings # Return our mock listings
        mock_db_query.return_value = mock_query_obj

        search_payload = {"query": "powerful gpu for training", "limit": 5}
        response = client.post("/gpu_listings/search", headers=auth_headers, json=search_payload)
        data = response.get_json()

        assert response.status_code == 200
        assert isinstance(data, list)
        assert len(data) == 2
        # Check if results are sorted by distance (listing with id 1 should be first)
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2
        assert "search_distance" in data[0]
        assert data[0]["search_distance"] == 0.1
        assert data[1]["search_distance"] == 0.2

        mock_get_model.return_value.encode.assert_called_once_with(search_payload["query"], convert_to_numpy=True)
        mock_collection.query.assert_called_once()
        # Check that the filter was called with the correct IDs from Chroma results
        mock_query_obj.filter.assert_called_once()
        filter_args, _ = mock_query_obj.filter.call_args
        assert str(filter_args[0]) == str(GPUListing.id.in_([1, 2])) # Ensure correct IDs used

    def test_semantic_search_missing_query(self, client, auth_headers):
        """Test search request with missing query parameter."""
        response = client.post("/gpu_listings/search", headers=auth_headers, json={})
        assert response.status_code == 400
        assert "Missing 'query'" in response.get_json()["error"]

    def test_semantic_search_empty_query(self, client, auth_headers):
        """Test search request with empty query string."""
        response = client.post("/gpu_listings/search", headers=auth_headers, json={"query": "  "})
        assert response.status_code == 400
        assert "must be a non-empty string" in response.get_json()["error"]
        
    def test_semantic_search_invalid_limit(self, client, auth_headers):
        """Test search request with invalid limit."""
        response = client.post("/gpu_listings/search", headers=auth_headers, json={"query": "test", "limit": 0})
        assert response.status_code == 400
        assert "must be a positive integer" in response.get_json()["error"]
        
        response = client.post("/gpu_listings/search", headers=auth_headers, json={"query": "test", "limit": "abc"})
        assert response.status_code == 400
        assert "must be a positive integer" in response.get_json()["error"]

    @patch('routes.gpu_listings.get_gpu_listings_collection')
    @patch('routes.gpu_listings.get_embedding_model')
    def test_semantic_search_no_results(self, mock_get_model, mock_get_collection, client, auth_headers, mock_empty_chroma_query_results):
        """Test search where ChromaDB returns no results."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = mock_empty_chroma_query_results
        mock_get_collection.return_value = mock_collection

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
        mock_get_model.return_value = mock_model

        response = client.post("/gpu_listings/search", headers=auth_headers, json={"query": "obscure gpu"})
        assert response.status_code == 404
        assert "No matching GPU listings found" in response.get_json()["message"]
    
    @patch('routes.gpu_listings.get_gpu_listings_collection')
    @patch('routes.gpu_listings.get_embedding_model')
    @patch('routes.gpu_listings.db.session.query')
    def test_semantic_search_db_error(self, mock_db_query, mock_get_model, mock_get_collection, client, auth_headers, mock_chroma_query_results):
        """Test search encountering a database error during listing fetch."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = mock_chroma_query_results
        mock_get_collection.return_value = mock_collection

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1] * 384)
        mock_get_model.return_value = mock_model

        # Mock database query to raise an error
        mock_query_obj = MagicMock()
        mock_query_obj.options.side_effect = SQLAlchemyError("DB connection failed")
        mock_db_query.return_value = mock_query_obj

        response = client.post("/gpu_listings/search", headers=auth_headers, json={"query": "test"})
        assert response.status_code == 500
        assert "Database error occurred" in response.get_json()["error"]

    @patch('routes.gpu_listings.get_gpu_listings_collection')
    @patch('routes.gpu_listings.get_embedding_model')
    def test_semantic_search_generic_error(self, mock_get_model, mock_get_collection, client, auth_headers):
        """Test search encountering a generic error."""
        # Mock embedding model to raise a generic exception
        mock_get_model.side_effect = Exception("Something unexpected broke")

        # Need to mock collection as well, even though it might not be reached
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection 

        response = client.post("/gpu_listings/search", headers=auth_headers, json={"query": "test"})
        assert response.status_code == 500
        assert "An unexpected error occurred" in response.get_json()["error"]

# You might need to adjust mock object details (e.g., to_dict output) 
# based on the exact structure of your GPUListing, GPUConfiguration, and Host models.
