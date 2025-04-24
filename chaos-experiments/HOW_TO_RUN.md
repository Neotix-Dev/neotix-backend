# How to Run Chaos Engineering Experiments

This guide explains how to run the chaos engineering experiments in this directory to test the resilience of your Docker Swarm setup.

## Prerequisites

Ensure that your Docker Swarm is initialized and running with both stable and canary services:

```bash
# Check if services are running
sudo docker service ls
```

If services aren't running, start them using:

```bash
./swarm-deploy.sh
```

## Running the Experiments

### 1. Container Failure Test

This experiment tests Docker Swarm's self-healing capabilities by killing a running container and observing how quickly and effectively Docker Swarm replaces it.

```bash
./experiment-1-container-failure.sh
```

**What to watch for:**
- How quickly Docker Swarm detects the failure
- How long it takes to create a replacement container
- Whether the task ID changes (indicating a new task was created)
- The approximate recovery time

### 2. CPU Resource Starvation Test

This experiment limits CPU resources for the main API canary service to test performance degradation under constrained resources.

```bash
./experiment-2-resource-starvation.sh
```

**What to watch for:**
- Whether the CPU limit is correctly applied
- If containers need to be replaced during the update
- CPU usage statistics during the constrained period
- Whether the service remains functional despite CPU constraints

### 3. Memory Limit Test

This experiment applies a strict memory limit to potentially trigger OOM (Out of Memory) conditions and test Docker Swarm's recovery mechanisms.

```bash
./experiment-3-memory-limit.sh
```

**What to watch for:**
- Whether memory limits are correctly applied
- If any OOM (Out of Memory) kills occur
- How Docker Swarm handles container restarts due to OOM
- Memory usage statistics during the test

## Monitoring During Experiments

While running experiments, monitor these additional sources:

1. **Prometheus/Grafana**: Check dashboards for real-time metrics
   ```
   http://grafana.localhost (admin/admin)
   ```

2. **Docker Service Logs**: Watch for errors or interesting behavior
   ```bash
   sudo docker service logs neotix_neotix-api-canary
   ```

3. **Traefik Dashboard**: Monitor routing and service health
   ```
   http://traefik.localhost
   ```

## Reviewing Results

After each experiment:

1. Check the terminal output for a summary of what happened
2. Review service history: `sudo docker service ps <service_name>`
3. Check the Grafana dashboards for performance impacts during the experiment period
4. Update the findings.md file with your observations

## Troubleshooting

If experiments don't work as expected:

- Ensure all services are running: `sudo docker service ls`
- Check if Docker Swarm is initialized properly: `sudo docker node ls`
- Verify network connectivity between services
- Check Traefik routing configuration
- Ensure environment variables are set correctly for the services
