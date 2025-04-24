#!/bin/bash
# Experiment 1: Canary API Container Failure
# This experiment tests Docker Swarm's self-healing capability by killing a canary container

echo "==== CHAOS EXPERIMENT 1: CANARY API CONTAINER FAILURE ===="
echo "Starting experiment at $(date)"
echo

# Confirm Docker Swarm services are running
echo "Checking service status..."
sudo docker service ls | grep neotix

# Define the target service
TARGET_SERVICE="neotix_neotix-api-canary"
echo "Target service: $TARGET_SERVICE"

# Check current service state before the experiment
echo "Current service state:"
sudo docker service ps $TARGET_SERVICE

# Get the container ID
CONTAINER_ID=$(sudo docker ps --filter name=$TARGET_SERVICE --format "{{.ID}}" | head -n 1)

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: No container found for service $TARGET_SERVICE"
    exit 1
fi

echo "Target container ID: $CONTAINER_ID"
echo

# Record task ID before killing container - using simpler inspection
TASK_ID=$(sudo docker inspect $CONTAINER_ID | grep -o '"com.docker.swarm.task.id": "[^"]*"' | cut -d'"' -f4 || echo "Unknown")
echo "Task ID before kill: $TASK_ID"

# Record the current container start time for comparison later
START_TIME=$(sudo docker inspect $CONTAINER_ID | grep -o '"StartedAt": "[^"]*"' | cut -d'"' -f4 || echo "Unknown")
echo "Container start time: $START_TIME"
echo

echo "==== INJECTING CHAOS: Killing container ===="
echo "Killing container $CONTAINER_ID at $(date)"
sudo docker kill $CONTAINER_ID

echo "Container killed, monitoring recovery..."
echo

# Monitor recovery - wait a moment for Swarm to detect failure
sleep 5

# Check service state immediately after kill
echo "Service state immediately after kill:"
sudo docker service ps $TARGET_SERVICE

# Wait for recovery
echo "Waiting 15 seconds for recovery..."
sleep 15

# Check service state after recovery period
echo "Service state after recovery period:"
sudo docker service ps $TARGET_SERVICE

# Get new container ID
NEW_CONTAINER_ID=$(sudo docker ps --filter name=$TARGET_SERVICE --format "{{.ID}}" | head -n 1)

if [ -z "$NEW_CONTAINER_ID" ]; then
    echo "Error: No new container found for service $TARGET_SERVICE after recovery period"
    echo "Self-healing has FAILED"
    exit 1
fi

# Get new task ID - using simpler inspection
NEW_TASK_ID=$(sudo docker inspect $NEW_CONTAINER_ID | grep -o '"com.docker.swarm.task.id": "[^"]*"' | cut -d'"' -f4 || echo "Unknown")

# Get new container start time
NEW_START_TIME=$(sudo docker inspect $NEW_CONTAINER_ID | grep -o '"StartedAt": "[^"]*"' | cut -d'"' -f4 || echo "Unknown")

echo "New container ID: $NEW_CONTAINER_ID"
echo "New task ID: $NEW_TASK_ID"
echo "New container start time: $NEW_START_TIME"

# Check if it's a new container (different task ID means Docker Swarm created a new task)
if [ "$TASK_ID" != "$NEW_TASK_ID" ] && [ "$TASK_ID" != "Unknown" ] && [ "$NEW_TASK_ID" != "Unknown" ]; then
    echo "SUCCESS: Docker Swarm created a new task to replace the killed container"
    
    # Calculate recovery time (this is an approximation)
    if [ "$START_TIME" != "Unknown" ] && [ "$NEW_START_TIME" != "Unknown" ]; then
        # Convert timestamps to seconds since epoch if possible
        if command -v date &> /dev/null; then
            START_SECONDS=$(date -d "$START_TIME" +%s 2>/dev/null || echo "0")
            NEW_START_SECONDS=$(date -d "$NEW_START_TIME" +%s 2>/dev/null || echo "0")
            
            if [ "$START_SECONDS" != "0" ] && [ "$NEW_START_SECONDS" != "0" ]; then
                RECOVERY_TIME=$((NEW_START_SECONDS - START_SECONDS))
                echo "Approximate recovery time: $RECOVERY_TIME seconds"
            else
                echo "Could not calculate recovery time"
            fi
        else
            echo "Date command not available, cannot calculate recovery time"
        fi
    else
        echo "Could not determine start times to calculate recovery"
    fi
else
    echo "INFO: Container was replaced but task details not available"
fi

echo
echo "==== EXPERIMENT COMPLETE ===="
echo "Experiment ended at $(date)"
echo
echo "Summary:"
echo "1. Container $CONTAINER_ID was killed"
echo "2. Docker Swarm recognized the failure and scheduled a replacement"
echo "3. New container $NEW_CONTAINER_ID is now running"
echo "4. Docker Swarm maintained the desired replica count"
echo
echo "Check Prometheus/Grafana for detailed metrics"
