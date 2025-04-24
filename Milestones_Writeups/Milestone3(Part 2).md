# Docker Swarm Deployment

This document explains how to deploy the Neotix backend services using Docker Swarm.

Note: This is all on the Milestone3 branch.

## Services

Our Docker Swarm deployment consists of three services:

1. **neotix-api** - The main Neotix backend API (port 5000)
2. **gcp-deployment-api** - The GCP deployment handler API (port 5001)
3. **db** - PostgreSQL database with two separate databases for each service

## Prerequisites

- Docker installed
- Docker Compose installed
- Sufficient permissions to create and manage Docker Swarm

## Deployment

1. Make sure you have all the necessary environment files:
   - `.env` file in the root directory
   - `gcp_deployment_handler/.env` file

2. Run the deployment script:
   ```bash
   ./swarm-deploy.sh
   ```

3. This will:
   - Initialize Docker Swarm if not already active
   - Build the Docker images
   - Deploy the stack to the Swarm

## Verification

To verify that the services are running:

```bash
# Check service status
docker service ls

# Check running containers
docker ps

# View logs for the main API
docker service logs neotix_neotix-api

# View logs for the GCP deployment API
docker service logs neotix_gcp-deployment-api
```

## Accessing the Services

- The main Neotix API is available at: http://localhost:5000
- The GCP deployment API is available at: http://localhost:5001

## Inter-service Communication

The services can communicate with each other using their service names:

- From the GCP deployment service, the main API is accessible at: `http://neotix-api:5000`
- From the main API, the GCP deployment service is accessible at: `http://gcp-deployment-api:5001`

## Teardown

To remove the deployment:

```bash
./swarm-teardown.sh
```

This will:
- Remove the deployed stack
- Optionally exit swarm mode

## Troubleshooting

1. **Database connection issues:**
   - Ensure the database service is running: `docker service ls | grep db`
   - Check database logs: `docker service logs neotix_db`

2. **Service not starting:**
   - Check the service logs: `docker service logs <service_name>`
   - Verify environment variables are correctly set in docker-compose.yml

3. **Network connectivity issues:**
   - Verify all services are on the same network: `docker network ls`
   - Inspect the network: `docker network inspect neotix-network`
