# Chaos Engineering Experiment Findings

## Experiment 1: Container Failure Test

**Date:** April 23, 2025  
**Target Service:** `neotix_neotix-api-canary`

### Procedure:
1. Identified the running container for the canary API service: `9fe3562aee72`
2. Manually killed the container using `docker kill`
3. Observed Docker Swarm's response

### Observations:
- Docker Swarm immediately detected the container failure
- A new task was created within seconds to replace the failed container
- The new container moved from "Ready" to "Running" state in approximately 12 seconds
- The service maintained its desired replica count (1)
- The history of previous container failures was preserved in the service task list

### Findings:
- Self-healing mechanism in Docker Swarm works as expected
- Recovery time is quick (under 15 seconds)
- Previous container failures are properly tracked in the service history
- The service maintains the configuration (CPU limits, etc.) when recreating containers

### Recommendations:
- Consider implementing health checks in the Dockerfile to improve failure detection
- Add more detailed monitoring for container restarts in Prometheus/Grafana
- Implement graceful shutdown handling in the application to prevent data loss during container terminations
- Consider adjusting the update config for faster parallelism during recovery

## Experiment 2: Resource Limitation Test (CPU)

**Date:** April 23, 2025  
**Target Service:** `neotix_neotix-api-canary`

### Procedure:
1. Changed CPU limit from 0.3 cores to 0.2 cores (33% reduction)
2. Observed service behavior
3. Restored original CPU limit

### Observations:
- Docker Swarm successfully applied the new CPU limit
- Service update resulted in a container restart rather than an in-place update
- The resource constraint was properly applied (visible in `docker stats` output)
- CPU usage was around 20.24% during the test, indicating the limit was working
- The container continued to function despite the reduced CPU allocation

### Findings:
- Docker Swarm resource constraints work as expected
- Service updates for resource limits trigger container restarts
- The application remains functional under CPU constraints, though likely with reduced performance
- Docker Swarm maintains a clean history of service updates and configuration changes

### Recommendations:
- Implement better resource monitoring in the application
- Add degradation handling logic for CPU-constrained scenarios
- Configure appropriate resource requests and limits based on actual usage patterns
- Monitor application performance metrics under various CPU limits to establish optimal values

## Experiment 3: Memory Limitation Test (OOM)

**Date:** April 23, 2025  
**Target Service:** `neotix_neotix-api-canary`

### Procedure:
1. Changed memory limit from 384MB to a very restrictive 50MB
2. Generated memory load with NumPy operations to trigger OOM conditions
3. Monitored system logs for OOM kill events
4. Observed Docker Swarm's behavior in response to OOM kills

### Observations:
- Docker Swarm successfully applied the strict memory limit
- When the container tried to use more memory, Linux kernel's OOM killer terminated processes
- Multiple OOM kill events were observed in system logs
- Docker Swarm detected these crashes and restarted the container
- The container was killed and restarted multiple times during the test
- After restoring normal memory limits, the service stabilized

### Findings:
- Memory limits are strictly enforced by the container runtime
- OOM kills are properly logged in system logs (`dmesg`)
- Docker Swarm can detect and recover from OOM failures, but repeated failures can destabilize the service
- The application has no protection against OOM conditions
- Under memory pressure, critical processes like Gunicorn workers were terminated

### Recommendations:
- Implement memory usage monitoring and alerting
- Add memory-aware code to gracefully degrade service when under memory pressure
- Set appropriate memory limits based on actual application requirements
- Consider implementing circuit breakers for memory-intensive operations
- Add memory utilization to health checks to provide early warning of potential issues

## Summary of Docker Swarm Resilience

Based on these experiments, Docker Swarm has demonstrated good resilience capabilities:

1. **Self-healing**: Quick detection and recovery from container failures
2. **Resource Management**: Proper enforcement of CPU and memory limits
3. **Service Continuity**: Maintenance of desired replica counts despite failures
4. **Configuration Persistence**: Preservation of service configuration during restarts
5. **Failure Tracking**: Good visibility into service history and failure causes

The main area for improvement is in application-level resilience, particularly:

1. Better handling of resource constraints
2. Graceful degradation under pressure
3. Protection against OOM conditions
4. Improved health checking

These findings provide a foundation for enhancing the resilience of both the infrastructure and application components of the Neotix backend services.

## Next Steps

1. Implement additional chaos experiments:
   - Network latency and packet loss
   - Database connection failures
   - Multiple simultaneous failures
   - Extended CPU/memory pressure

2. Add resilience patterns to the application code:
   - Circuit breakers
   - Graceful degradation
   - Retry mechanisms
   - Better error handling

3. Enhance monitoring:
   - Add Prometheus metrics for failure detection and recovery
   - Create specific Grafana dashboards for resilience monitoring
   - Set up alerting for cascading failures
   - Track recovery times and failure rates
