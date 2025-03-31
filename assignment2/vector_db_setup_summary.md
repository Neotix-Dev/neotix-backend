# Vector Database & Application Setup Summary

This document outlines the key steps involved in setting up the Neotix backend application environment, integrating and initializing ChromaDB for semantic search of GPU listings, and running tests.

## 1. Initial Environment Setup

1.  **Clone Repository:** (If not already done) Obtain the project code.
    ```bash
    # Example: git clone <repository-url>
    cd neotix-backend
    ```
2.  **Create Virtual Environment:** Use `uv` to create an isolated Python environment (as per project convention, located at `~/neotix-backend/.venv/`).
    ```bash
    # Ensure uv is installed: python -m pip install uv
    uv venv .venv 
    ```
3.  **Activate Environment:**
    ```bash
    source .venv/bin/activate 
    ```
4.  **Install Dependencies:** Install required Python packages using `uv` and the requirements file.
    ```bash
    uv pip install -r requirements.txt
    ```
5.  **Environment Variables:** Configure necessary environment variables (e.g., `DATABASE_URL`, `SECRET_KEY`). This is typically done by creating a `.env` file in the project root. Copy `.env.example` if it exists and fill in the values.
    ```
    # .env example content
    DATABASE_URL=postgresql://user:password@host:port/database_name
    SECRET_KEY=your_very_secret_key
    FLASK_ENV=development
    # Add other necessary variables
    ```
6.  **Database Migrations:** Apply any pending database schema changes (if using Flask-Migrate).
    ```bash
    # Ensure Flask-Migrate is initialized (usually flask db init/migrate/upgrade)
    flask db upgrade 
    ```

## 2. Vector Database Initialization (ChromaDB)

Follow these steps specifically for the vector database functionality:

*   **Dependencies:** Ensure `chromadb` and `sentence-transformers` are listed in `requirements.txt` (verified in step 1.4).
*   **Utility Module (`utils/vector_db.py`):** This module handles loading the embedding model (`all-MiniLM-L6-v2`) and managing the persistent ChromaDB client (data stored in `chroma_data/`).
*   **Data Ingestion (CRITICAL):** The vector database needs to be populated with embeddings from your PostgreSQL listings. **The semantic search endpoint will not return results until this is done.**
    1.  **Create/Locate Script:** You need a script (e.g., `scripts/populate_vector_db.py` - **this likely needs to be created**) that:
        *   Connects to the PostgreSQL database.
        *   Iterates through GPU listings.
        *   Generates text descriptions for each.
        *   Uses `utils.vector_db.get_embedding_model()` to create embeddings.
        *   Uses `utils.vector_db.get_gpu_listings_collection()` to get the ChromaDB collection.
        *   Adds the embeddings, PostgreSQL IDs, and metadata to the collection.
    2.  **Run Script:** Execute this script after setting up the environment and database.
        ```bash
        # Example command (adjust script name/path as needed)
        python scripts/populate_vector_db.py 
        ```

## 3. Running the Development Server

Once the environment is set up, the database migrated, and the vector DB populated:

1.  **Activate Environment:** (If not already active)
    ```bash
    source .venv/bin/activate
    ```
2.  **Run Application:** Start the Flask development server.
    ```bash
    python app.py
    ```
3.  **Access:** The application should now be running, typically at `http://127.0.0.1:5000`.

## 4. Running Tests

Tests verify the application's functionality, including the API endpoints.

1.  **Activate Environment:** Ensure the virtual environment with test dependencies is active.
    ```bash
    source .venv/bin/activate
    ```
2.  **Run All Tests:** Execute the test suite using `pytest` from the project root directory.
    ```bash
    pytest
    ```
3.  **Run Specific Tests:** To run only the semantic search tests:
    ```bash
    # Run tests in a specific file
    pytest tests/units/route_tests/test_gpu_listings_routes.py
    
    # Run tests within a specific class in that file
    pytest tests/units/route_tests/test_gpu_listings_routes.py::TestGPUListingsSemanticSearch
    ```
*   **Note on VectorDB Tests:** The current unit tests for the semantic search (`TestGPUListingsSemanticSearch`) *mock* the interactions with ChromaDB and the embedding model. They do **not** require the vector database to be populated or running for the unit tests themselves to pass. Integration tests (if created) might require a populated test vector database.

## 5. Semantic Search Usage

*   **Endpoint:** `POST /api/gpu/search`
*   **Authentication:** Requires a valid JWT token in the `Authorization: Bearer <token>` header.
*   **Request Body (JSON):**
    ```json
    {
      "query": "your natural language search query here",
      "limit": 10 
    }
    ```
    (`limit` is optional, defaults to 10)
*   **Response:** JSON array of matching GPU listing objects, sorted by relevance, including a `search_distance` field (lower is more relevant).
