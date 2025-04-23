#!/bin/bash

# Exit on error
set -e

echo "Promoting canary deployments to stable..."

# Tag canary images as stable
sudo docker tag neotix/main-api:canary neotix/main-api:stable
sudo docker tag neotix/gcp-deployment-api:canary neotix/gcp-deployment-api:stable

echo "Canary images tagged as stable."

# Update the services 
echo "Updating services to use new stable images..."
sudo docker service update --image neotix/main-api:stable neotix_neotix-api
sudo docker service update --image neotix/gcp-deployment-api:stable neotix_gcp-deployment-api

echo "Promotion complete. The current canary version is now the stable version."
