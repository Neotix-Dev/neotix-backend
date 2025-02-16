# GPU Listings Backend

A simple Flask backend for fetching and managing GPU listings from various providers.

## Quick Setup

1. Create a virtual environment and activate it:
```bash
python -m venv .startup
source .startup/bin/activate
```

2. Install dependencies from requirements.txt:
```bash
pip install -r requirements.txt
```

3. Install PostgreSQL if not already installed
```bash
sudo pacman -S postgresql
```

Note: These are for linux, if on mac, pacman will not work. You will have to use brew.



4. Create a `.env` file in the root directory:
```bash
DATABASE_URI=postgresql://postgres:postgres@localhost:5432/neotix
```
5. Now run the script 'setup_postgres.py' in the scripts folder.
   

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
flask run
```

7. Fetch GPU data:
```bash
flask fetch-gpu-data
```

## API Documentation

### Authentication
Most endpoints require Firebase authentication token in the `Authorization` header.

### GPU Endpoints (`/api/gpu`)us
- `GET /get_all` - Get all GPU listingsUS national
- `GET /get_gpus/<page_number>` - Get paginated list of GPUs, start from page 1. Contains more info on the GPUs, better to use this endpoint as it pulls 200 GPUs at a time
- `GET /<id>` - Get specific GPU by ID
- `GET /search?q=<query>` - Search GPUs by name/specs with fuzzy matching
- `GET /filtered` - Get filtered GPUs with pagination
  - Query params: gpu_name, gpu_vendor, min/max_gpu_count, min/max_gpu_memory, min/max_cpu, min/max_memory, min/max_price, min/max_gpu_score, provider, sort_by, sort_order, page, per_page
- `GET /<gpu_id>/price-points` - Get current price points for a GPU
- `GET /<gpu_id>/price-history` - Get price history with optional date range
- `GET /vendors` - List all GPU vendors
- `GET /hosts` - List all GPU providers

### User Management (`/api/user`)
- `POST /register` - Register new user with Firebase
  - Required: email, password, first_name, last_name, organization, experience_level
- `POST /sync` - Sync Firebase user with backend
- `GET /profile` - Get user profile and preferences
- `PUT /profile` - Update user profile
- `POST /update` - Update user data
- `DELETE /` - Delete user account

### Projects (`/api/projects`)
- `GET /` - Get user's projects
- `POST /` - Create new project (requires: name)
- `PUT /<project_id>` - Update project details
- `DELETE /<project_id>` - Delete project
- `POST /<project_id>/gpus` - Add GPU to project
- `DELETE /<project_id>/gpus/<gpu_id>` - Remove GPU from project

### User Preferences (`/api/preferences`)
#### Selected GPUs
- `GET /selected-gpus` - Get selected GPUs
- `POST /selected-gpus` - Add GPU to selection
- `DELETE /selected-gpus/<gpu_id>` - Remove GPU from selection

#### Favorite GPUs  
- `GET /favorite-gpus` - Get favorite GPUs
- `POST /favorite-gpus` - Add GPU to favorites
- `DELETE /favorite-gpus/<gpu_id>` - Remove from favorites

#### Rented GPUs
- `GET /rented-gpus` - Get active rentals
- `POST /rented-gpus` - Add rented GPU
- `DELETE /rented-gpus/<gpu_id>` - End GPU rental

#### Price Alerts
- `GET /price-alerts` - Get price alerts
- `POST /price-alerts` - Create price alert
  - Required: gpuId/gpuType, targetPrice, isTypeAlert
- `DELETE /price-alerts/<alert_id>` - Remove price alert

### A/B Testing (`/api/analytics`)

The backend implements A/B testing functionality to track and analyze user preferences between different view types (grid vs. table view).

#### View Preference Tracking
- `POST /view-preference` - Record user view preference
  - Required payload:
    ```json
    {
      "sessionId": "unique_session_id",
      "timestamp": "ISO timestamp",
      "viewType": "grid|table",
      "initialView": "grid|table"
    }
    ```

#### Analytics
- `GET /view-preference/summary` - Get summary of view preferences
  - Returns:
    ```json
    {
      "total_sessions": "number of unique sessions",
      "view_preferences": {
        "grid": "number of users who preferred grid view",
        "table": "number of users who preferred table view"
      },
      "conversion_rates": {
        "grid": "percentage who stayed with grid view",
        "table": "percentage who stayed with table view"
      }
    }
    ```

#### Implementation Details
- Users are randomly assigned either grid or table view on their first visit
- The system tracks:
  - Initial view type assigned
  - View type changes during the session
  - Final view type preference
- Analytics are stored in JSON format at `data/analytics/view_preferences.json`

#### Setup Instructions
1. Ensure the `data/analytics` directory exists:
   ```bash
   mkdir -p data/analytics
   ```
2. Initialize the analytics file:
   ```bash
   echo "[]" > data/analytics/view_preferences.json
   ```
3. Ensure write permissions:
   ```bash
   chmod 644 data/analytics/view_preferences.json
   ```
All the analytics data is stored in `data/analytics/view_preferences.json`.

### Response Format
All endpoints return JSON with standard structure:
- Success: `{ data: [result] }`
- Error: `{ error: "error message" }`

### Status Codes
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Server Error
# Test change
