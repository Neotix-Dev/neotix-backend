#!/bin/bash
# Experiment 2: Canary GCP API Resource Starvation (CPU Limit)
# This experiment limits CPU resources for the API canary service to test degradation

echo "==== CHAOS EXPERIMENT 2: RESOURCE STARVATION (CPU LIMIT) ===="
echo "Starting experiment at $(date)"
echo

# Define the target service
TARGET_SERVICE="neotix_neotix-api-canary"
echo "Target service: $TARGET_SERVICE"

# Check current service state and configuration before the experiment
echo "Current service configuration:"
CURRENT_CPU_LIMIT=$(sudo docker service inspect --format "{{.Spec.TaskTemplate.Resources.Limits.NanoCPUs}}" $TARGET_SERVICE)

# Convert from nano CPUs (billionths) to standard CPU units
if [ -z "$CURRENT_CPU_LIMIT" ] || [ "$CURRENT_CPU_LIMIT" = "<no value>" ]; then
    CURRENT_CPU_LIMIT_HUMAN="unlimited"
else
    # Convert nano CPUs to standard CPU units (divide by 1 billion)
    CURRENT_CPU_LIMIT_HUMAN=$(echo "scale=2; $CURRENT_CPU_LIMIT / 1000000000" | bc)
fi

echo "Current CPU limit: $CURRENT_CPU_LIMIT_HUMAN cores"

# Get current container IDs and task IDs for the service
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

# Define CPU limit (20% of one core)
CPU_LIMIT="0.2"
CPU_LIMIT_NANO=$(echo "$CPU_LIMIT * 1000000000 / 1" | bc)

echo "==== INJECTING CHAOS: Limiting CPU to ${CPU_LIMIT} cores ===="
echo "Applying CPU limit at $(date)"
sudo docker service update --limit-cpu $CPU_LIMIT $TARGET_SERVICE

# Wait for the update to apply
echo "Waiting for service update to apply..."
sleep 10

# Check if service update was successful
SERVICE_STATE=$(sudo docker service inspect --format "{{.UpdateStatus.State}}" $TARGET_SERVICE)
if [ "$SERVICE_STATE" == "completed" ] || [ -z "$SERVICE_STATE" ]; then
    echo "Service update completed successfully"
else
    echo "Service update is in state: $SERVICE_STATE"
fi

# Check service state after update
echo "Service state after CPU limit applied:"
sudo docker service ps $TARGET_SERVICE

# Verify the CPU limit was applied
NEW_CPU_LIMIT=$(sudo docker service inspect --format "{{.Spec.TaskTemplate.Resources.Limits.NanoCPUs}}" $TARGET_SERVICE)
NEW_CPU_LIMIT_HUMAN=$(echo "scale=2; $NEW_CPU_LIMIT / 1000000000" | bc)
echo "New CPU limit: $NEW_CPU_LIMIT_HUMAN cores"

if [ "$NEW_CPU_LIMIT" == "$CPU_LIMIT_NANO" ]; then
    echo "CPU limit was applied successfully"
else
    echo "WARNING: CPU limit doesn't match expected value"
    echo "Expected: $CPU_LIMIT_NANO, Got: $NEW_CPU_LIMIT"
fi

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

echo "Monitoring service for 30 seconds under CPU constraint..."
echo "Container stats (CPU usage) with new limit:"
sudo docker stats --no-stream $(sudo docker ps --filter name=$TARGET_SERVICE --format "{{.ID}}")

# Wait and monitor
echo "Waiting 30 seconds to observe behavior under CPU limit..."
sleep 30

# Restore normal operation
echo
echo "==== RESTORING NORMAL OPERATION ===="
echo "Removing CPU limit at $(date)"

# If there was a previous CPU limit, restore it, otherwise remove the limit
if [ "$CURRENT_CPU_LIMIT_HUMAN" == "unlimited" ]; then
    sudo docker service update --limit-cpu 0 $TARGET_SERVICE
else
    # Convert back to standard CPU format for docker update command
    sudo docker service update --limit-cpu $CURRENT_CPU_LIMIT_HUMAN $TARGET_SERVICE
fi

# Wait for the update to apply
echo "Waiting for service update to complete..."
sleep 10

# Check service state after recovery
echo "Service state after CPU limit removed:"
sudo docker service ps $TARGET_SERVICE

# Verify CPU limit was restored
FINAL_CPU_LIMIT=$(sudo docker service inspect --format "{{.Spec.TaskTemplate.Resources.Limits.NanoCPUs}}" $TARGET_SERVICE)

if [ -z "$FINAL_CPU_LIMIT" ] || [ "$FINAL_CPU_LIMIT" = "<no value>" ]; then
    FINAL_CPU_LIMIT_HUMAN="unlimited"
else
    FINAL_CPU_LIMIT_HUMAN=$(echo "scale=2; $FINAL_CPU_LIMIT / 1000000000" | bc)
fi

echo "Final CPU limit: $FINAL_CPU_LIMIT_HUMAN cores"

echo
echo "==== EXPERIMENT COMPLETE ===="
echo "Experiment ended at $(date)"
echo
echo "Summary:"
echo "1. Initial CPU limit: $CURRENT_CPU_LIMIT_HUMAN cores"
echo "2. Applied CPU limit: $NEW_CPU_LIMIT_HUMAN cores"
echo "3. Final CPU limit: $FINAL_CPU_LIMIT_HUMAN cores"
echo "4. Container replacement: $CONTAINERS_CHANGED"
echo
echo "Check Prometheus/Grafana for detailed metrics on performance degradation during the experiment"
