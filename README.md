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

3. Set up PostgreSQL database:
```bash
# Install PostgreSQL if not already installed
sudo pacman -S postgresql

# Create database
sudo -u postgres psql
postgres=# CREATE DATABASE neotix;
postgres=# \q
```

4. Create a `.env` file in the root directory:
```bash
DATABASE_URI=postgresql://postgres:postgres@localhost:5432/neotix
```

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
# Test change
