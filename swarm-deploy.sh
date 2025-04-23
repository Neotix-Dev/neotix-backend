#!/bin/bash

# Exit on error
set -e

# Initialize Docker Swarm if not already initialized
if ! sudo docker info | grep -q "Swarm: active"; then
  echo "Initializing Docker Swarm mode..."
  sudo docker swarm init
else
  echo "Docker Swarm is already active."
fi

# Make sure Docker networks are properly set up
echo "Checking Docker networks..."
if ! sudo docker network ls | grep -q "bridge"; then
  echo "Creating Docker bridge network..."
  sudo docker network create bridge
else
  echo "Docker bridge network exists."
fi

if ! sudo docker network ls | grep -q "neotix-network"; then
  echo "Creating Neotix overlay network..."
  sudo docker network create --driver overlay --attachable neotix-network
else
  echo "Neotix overlay network exists."
fi

# Build the Docker images separately instead of using docker-compose build
echo "Building Docker images individually..."

echo "Building neotix-api image..."
sudo docker build -t neotix/main-api:latest --network=host .

echo "Building gcp-deployment-api image..."
sudo docker build -t neotix/gcp-deployment-api:latest --network=host ./gcp_deployment_handler

# Deploy the stack using docker stack deploy
echo "Deploying the Neotix stack to Docker Swarm..."
sudo docker stack deploy -c docker-compose.yml neotix

echo "Stack deployed!"
echo "To check service status: sudo docker service ls"
echo "To check running containers: sudo docker ps"
echo "To view logs: sudo docker service logs neotix_neotix-api or sudo docker service logs neotix_gcp-deployment-api"
