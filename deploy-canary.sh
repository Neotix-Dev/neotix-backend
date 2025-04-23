#!/bin/bash

# Exit on error
set -e

# Check if Docker Swarm is initialized
if ! sudo docker info | grep -q "Swarm: active"; then
  echo "Initializing Docker Swarm mode..."
  sudo docker swarm init
else
  echo "Docker Swarm is already active."
fi

# Make sure networks are properly set up
echo "Checking Docker networks..."
if ! sudo docker network ls | grep -q "neotix-network"; then
  echo "Creating Neotix overlay network..."
  sudo docker network create --driver overlay --attachable neotix-network
else
  echo "Neotix overlay network exists."
fi

# Build stable images if they don't exist
if ! sudo docker image ls | grep -q "neotix/main-api.*stable"; then
  echo "Building stable images first..."
  ./build-images.sh stable
fi

# Build canary images
echo "Building canary images..."
./build-images.sh canary

# Deploy the stack using docker stack deploy
echo "Deploying the Neotix stack with canary services..."
sudo docker stack deploy -c docker-compose.canary.yml neotix

echo "Canary deployment completed!"
echo "Access the services at:"
echo "  - Main API: http://api.localhost/api"
echo "  - GCP Deployment API: http://api.localhost/gcp"
echo "  - Traefik Dashboard: http://traefik.localhost"
echo "  - Prometheus: http://prometheus.localhost"
echo "  - Grafana: http://grafana.localhost (admin/admin)"
echo
echo "To test the canary version specifically, use:"
echo "  curl -H 'X-Canary: true' http://api.localhost/api/health"
echo
echo "To check service status: sudo docker service ls"
echo "To view logs: sudo docker service logs neotix_neotix-api-canary"
