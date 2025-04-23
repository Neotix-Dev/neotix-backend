#!/bin/bash

echo "Testing Neotix services deployed on Docker Swarm"
echo "==============================================="

# Check if the services are running
echo "Checking if services are running..."
sudo docker service ls | grep -E 'neotix_neotix-api|neotix_gcp-deployment-api'

# Test the main Neotix API
echo -e "\nTesting the main Neotix API..."
curl -s -w "\nStatus Code: %{http_code}\n" http://localhost:5000/api/health || echo "Failed to connect to main API"

# Generate a token for the GCP deployment API
echo -e "\nGenerating JWT token for GCP deployment API..."
TOKEN=$(sudo docker exec $(sudo docker ps --filter name=neotix_gcp-deployment-api -q) python -c "
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from datetime import timedelta
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'default-secret-key')
jwt = JWTManager(app)

with app.app_context():
    token = create_access_token(identity='1', expires_delta=timedelta(days=1))
    print(token)
" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo "Failed to generate token. Make sure the GCP deployment service is running."
else
    echo "Token generated successfully."
    
    # Test the GCP deployment API
    echo -e "\nTesting the GCP deployment API..."
    curl -s -w "\nStatus Code: %{http_code}\n" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        http://localhost:5001/api/instances || echo "Failed to connect to GCP deployment API"
fi

echo -e "\nTests completed."
