#!/bin/bash

# Remove the deployed stack
echo "Removing the Neotix stack from Docker Swarm..."
sudo docker stack rm neotix

# Wait for stack to be fully removed
echo "Waiting for stack to be completely removed..."
sleep 10

# Leave swarm mode (optional)
echo "Do you want to leave swarm mode? (y/n)"
read answer

if [ "$answer" = "y" ]; then
  echo "Leaving swarm mode..."
  sudo docker swarm leave --force
  echo "Swarm mode exited."
else
  echo "Keeping swarm mode active."
fi
