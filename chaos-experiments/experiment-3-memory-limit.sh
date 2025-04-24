#!/bin/bash
# Experiment 3: Memory Limit Test
# This experiment limits memory for the main API canary service to test OOM behavior

echo "==== CHAOS EXPERIMENT 3: MEMORY LIMIT TEST ===="
echo "Starting experiment at $(date)"
echo

# Define the target service
TARGET_SERVICE="neotix_neotix-api-canary"
echo "Target service: $TARGET_SERVICE"

# Check current service state and configuration before the experiment
echo "Current service configuration:"
CURRENT_MEMORY_LIMIT=$(sudo docker service inspect --format "{{.Spec.TaskTemplate.Resources.Limits.MemoryBytes}}" $TARGET_SERVICE)

# Convert from bytes to human-readable format
if [ -z "$CURRENT_MEMORY_LIMIT" ] || [ "$CURRENT_MEMORY_LIMIT" = "<no value>" ]; then
    CURRENT_MEMORY_LIMIT_HUMAN="unlimited"
else
    # Convert bytes to MB
    CURRENT_MEMORY_LIMIT_HUMAN=$(echo "scale=2; $CURRENT_MEMORY_LIMIT / 1048576" | bc)
    CURRENT_MEMORY_LIMIT_HUMAN="${CURRENT_MEMORY_LIMIT_HUMAN}MB"
fi

echo "Current memory limit: $CURRENT_MEMORY_LIMIT_HUMAN"

# Get current containers for the service
CONTAINER_IDS=$(sudo docker ps --filter name=$TARGET_SERVICE --format "{{.ID}}")
if [ -z "$CONTAINER_IDS" ]; then
    echo "Error: No containers found for service $TARGET_SERVICE"
    exit 1
fi

echo "Current containers for $TARGET_SERVICE:"
for CONTAINER_ID in $CONTAINER_IDS; do
    TASK_ID=$(sudo docker inspect --format "{{.Config.Labels.\"com.docker.swarm.task.id\"}}" $CONTAINER_ID)
    echo "Container ID: $CONTAINER_ID, Task ID: $TASK_ID"
done

# Define memory limit (50MB - intentionally small to trigger potential OOM)
MEMORY_LIMIT="50M"
echo "==== INJECTING CHAOS: Limiting memory to ${MEMORY_LIMIT} ===="
echo "Applying memory limit at $(date)"
sudo docker service update --limit-memory $MEMORY_LIMIT $TARGET_SERVICE

# Wait for the update to apply
echo "Waiting for service update to apply..."
sleep 15

# Check if service update was successful
SERVICE_STATE=$(sudo docker service inspect --format "{{.UpdateStatus.State}}" $TARGET_SERVICE)
if [ "$SERVICE_STATE" == "completed" ] || [ -z "$SERVICE_STATE" ]; then
    echo "Service update completed successfully"
else
    echo "Service update is in state: $SERVICE_STATE"
fi

# Check service state after update
echo "Service state after memory limit applied:"
sudo docker service ps $TARGET_SERVICE

# Verify the memory limit was applied
NEW_MEMORY_LIMIT=$(sudo docker service inspect --format "{{.Spec.TaskTemplate.Resources.Limits.MemoryBytes}}" $TARGET_SERVICE)

# Convert bytes to MB for display
if [ -z "$NEW_MEMORY_LIMIT" ] || [ "$NEW_MEMORY_LIMIT" = "<no value>" ]; then
    NEW_MEMORY_LIMIT_HUMAN="unlimited"
else
    NEW_MEMORY_LIMIT_HUMAN=$(echo "scale=2; $NEW_MEMORY_LIMIT / 1048576" | bc)
    NEW_MEMORY_LIMIT_HUMAN="${NEW_MEMORY_LIMIT_HUMAN}MB"
fi

echo "New memory limit: $NEW_MEMORY_LIMIT_HUMAN"

# Check if containers were replaced
echo "Checking for container replacements..."
NEW_CONTAINER_IDS=$(sudo docker ps --filter name=$TARGET_SERVICE --format "{{.ID}}")
CONTAINERS_CHANGED="false"

for CONTAINER_ID in $NEW_CONTAINER_IDS; do
    FOUND="false"
    for OLD_ID in $CONTAINER_IDS; do
        if [ "$CONTAINER_ID" == "$OLD_ID" ]; then
            FOUND="true"
            break
        fi
    done
    if [ "$FOUND" == "false" ]; then
        CONTAINERS_CHANGED="true"
        break
    fi
done

if [ "$CONTAINERS_CHANGED" == "true" ]; then
    echo "Containers were replaced during the update"
else
    echo "Containers were not replaced (update done in-place)"
fi

# Show memory usage of the container
echo "Container memory stats with new limit:"
sudo docker stats --no-stream $(sudo docker ps --filter name=$TARGET_SERVICE --format "{{.ID}}")

# Monitor for OOM kills
echo "Monitoring for OOM events for 30 seconds..."
echo "This will generate some load on the service to potentially trigger OOM..."

# Create a background job to monitor for OOM messages
sudo dmesg -T -w | grep -i "out of memory" &
DMESG_PID=$!

# Generate some load to potentially hit the memory limit (background)
for i in {1..15}; do
    # Generate load in the background
    sudo docker exec $(sudo docker ps --filter name=$TARGET_SERVICE --format "{{.ID}}" | head -n 1) python3 -c "import numpy as np; a = np.random.rand(100, 100); b = np.random.rand(100, 100); c = a @ b" &
    # Space out the requests slightly
    sleep 1
done

# Wait and observe
echo "Waiting 30 seconds to observe behavior under memory limit..."
sleep 30

# Kill the dmesg monitoring process
kill $DMESG_PID 2>/dev/null

# Check service state again to see if any containers restarted due to OOM
echo "Service state after load generation:"
sudo docker service ps $TARGET_SERVICE | grep -i "out of memory" || echo "No explicit OOM failures detected in service list"

# Restore normal operation
echo
echo "==== RESTORING NORMAL OPERATION ===="
echo "Removing memory limit at $(date)"

# If there was a previous memory limit, restore it, otherwise remove the limit
if [ "$CURRENT_MEMORY_LIMIT_HUMAN" == "unlimited" ]; then
    sudo docker service update --limit-memory 0 $TARGET_SERVICE
else
    # Need to convert back to the format Docker expects (number + unit)
    sudo docker service update --limit-memory $CURRENT_MEMORY_LIMIT_HUMAN $TARGET_SERVICE
fi

# Wait for the update to apply
echo "Waiting for service update to complete..."
sleep 15

# Check service state after recovery
echo "Service state after memory limit removed:"
sudo docker service ps $TARGET_SERVICE

# Verify memory limit was restored
FINAL_MEMORY_LIMIT=$(sudo docker service inspect --format "{{.Spec.TaskTemplate.Resources.Limits.MemoryBytes}}" $TARGET_SERVICE)

if [ -z "$FINAL_MEMORY_LIMIT" ] || [ "$FINAL_MEMORY_LIMIT" = "<no value>" ]; then
    FINAL_MEMORY_LIMIT_HUMAN="unlimited"
else
    FINAL_MEMORY_LIMIT_HUMAN=$(echo "scale=2; $FINAL_MEMORY_LIMIT / 1048576" | bc)
    FINAL_MEMORY_LIMIT_HUMAN="${FINAL_MEMORY_LIMIT_HUMAN}MB"
fi

echo "Final memory limit: $FINAL_MEMORY_LIMIT_HUMAN"

echo
echo "==== EXPERIMENT COMPLETE ===="
echo "Experiment ended at $(date)"
echo
echo "Summary:"
echo "1. Initial memory limit: $CURRENT_MEMORY_LIMIT_HUMAN"
echo "2. Applied memory limit: $NEW_MEMORY_LIMIT_HUMAN"
echo "3. Final memory limit: $FINAL_MEMORY_LIMIT_HUMAN"
echo "4. Container replacement: $CONTAINERS_CHANGED"
echo "5. Check service history for OOM events"
echo
echo "Check Prometheus/Grafana for detailed metrics on memory usage during the experiment"
