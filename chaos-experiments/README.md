# Chaos Engineering Experiments for Neotix Backend

This directory contains chaos engineering experiments for the Neotix backend services running in Docker Swarm. These experiments are designed to test the resilience and reliability of our system under various failure conditions.

## Experiments

1. **Container Failure Test (`experiment-1-container-failure.sh`)**: 
   - Tests Docker Swarm's self-healing capability by killing a canary container
   - Verifies that Swarm reschedules the container and the service recovers

2. **Resource Starvation - CPU Limit (`experiment-2-resource-starvation.sh`)**: 
   - Limits CPU resources for the GCP API canary service to test performance degradation
   - Monitors service health and response times under CPU constraints

3. **Resource Starvation - Memory Limit (`experiment-3-memory-limit.sh`)**: 
   - Tests how the main API canary service behaves under severe memory constraints
   - May trigger OOM (Out of Memory) conditions to test Swarm's recovery behavior

## Running the Experiments

1. Make the scripts executable:
   ```
   chmod +x experiment-*.sh
   ```

2. Run the desired experiment:
   ```
   ./experiment-1-container-failure.sh
   ```

3. Monitor the results in:
   - Terminal output
   - Grafana dashboards
   - Prometheus metrics
   - Docker service logs

## Important Notes

- These experiments intentionally introduce failures and should be run in controlled environments
- Always monitor the experiments closely to prevent unintended impact
- Have access to monitoring dashboards during experiments
- Document findings and lessons learned after each experiment
- Be prepared to manually intervene if services don't recover as expected

## Extending the Experiments

Future experiments could include:
- Network latency injection (requires additional tools like Pumba)
- Database connection failures
- Multiple simultaneous failures
- Load testing during failure conditions
