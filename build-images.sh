#!/bin/bash

# Exit on error
set -e

if [ $# -lt 1 ]; then
  echo "Usage: $0 <tag>"
  echo "Example: $0 stable  # builds neotix/main-api:stable and neotix/gcp-deployment-api:stable"
  echo "Example: $0 canary  # builds neotix/main-api:canary and neotix/gcp-deployment-api:canary"
  exit 1
fi

TAG=$1

# Create or update .dockerignore files to handle large contexts
cat > .dockerignore <<EOF
.git
.venv
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
gpu_listings.log
chroma_data
EOF

cat > ./gcp_deployment_handler/.dockerignore <<EOF
.git
.venv
__pycache__
*.pyc
*.pyo
*.pyd
.pytest_cache
EOF

# Build the main API image
echo "Building neotix/main-api:$TAG image..."
sudo docker build -t neotix/main-api:$TAG --network=host .

# Build the GCP deployment API image
echo "Building neotix/gcp-deployment-api:$TAG image..."
sudo docker build -t neotix/gcp-deployment-api:$TAG --network=host ./gcp_deployment_handler

echo "Images built successfully with tag: $TAG"
