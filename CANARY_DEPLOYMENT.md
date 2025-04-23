# Canary Deployment with Docker Swarm

This document explains how to use canary deployments for the Neotix backend services.

## What is a Canary Deployment?

A canary deployment is a technique where you gradually roll out changes to a small subset of users before rolling it out to the entire infrastructure. This allows you to test new features or fixes in a production-like environment with real users, while limiting the impact of potential issues.

## Architecture

Our canary deployment setup consists of:

1. **Traefik**: Acts as a load balancer and router, directing traffic between stable and canary versions.
2. **Stable Services**: Running the current production version (80% of traffic).
3. **Canary Services**: Running the new version (20% of traffic).
4. **Monitoring**: Prometheus and Grafana for tracking metrics and performance.

## Deployment Process

### 1. Initial Deployment

Deploy the entire stack with both stable and canary services:

```bash
./deploy-canary.sh
```

This script:
- Builds stable images if they don't exist
- Builds canary images
- Deploys the stack with Traefik, both service versions, and monitoring

### 2. Testing the Canary

After deployment, you can specifically test the canary version by adding an `X-Canary: true` header to your requests:

```bash
./test-canary.sh
```

This script tests both stable and canary versions of the services.

### 3. Monitoring

Monitor the performance of both versions:

- **Traefik Dashboard**: http://traefik.localhost
- **Prometheus**: http://prometheus.localhost
- **Grafana**: http://grafana.localhost (admin/admin)

### 4. Promoting the Canary

If the canary version proves stable and performant, promote it to become the new stable version:

```bash
./promote-canary.sh
```

This will:
- Tag the canary images as stable
- Update the stable services to use the new images

## Common Operations

### Build Images with Specific Tag

```bash
./build-images.sh stable
./build-images.sh canary
```

### Manually Test Services

```bash
# Test stable API
curl http://api.localhost/api/health

# Test canary API
curl -H "X-Canary: true" http://api.localhost/api/health

# Test stable GCP API
curl http://api.localhost/gcp/api/health

# Test canary GCP API
curl -H "X-Canary: true" http://api.localhost/gcp/api/health
```

### View Service Logs

```bash
sudo docker service logs neotix_neotix-api
sudo docker service logs neotix_neotix-api-canary
sudo docker service logs neotix_gcp-deployment-api
sudo docker service logs neotix_gcp-deployment-api-canary
```

## Rollback

In case of issues with the canary version, you can simply stop routing traffic to it by removing the canary services:

```bash
sudo docker service scale neotix_neotix-api-canary=0 neotix_gcp-deployment-api-canary=0
```

To re-enable the canary services:

```bash
sudo docker service scale neotix_neotix-api-canary=1 neotix_gcp-deployment-api-canary=1
```

## Traffic Distribution

By default, traffic is distributed:
- 80% to stable instances
- 20% to canary instances

This is controlled by the number of replicas for each service and the Traefik routing rules. You can modify this distribution by adjusting the replica counts in the `docker-compose.canary.yml` file.
