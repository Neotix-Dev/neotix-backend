#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Testing both stable and canary versions of Neotix services${NC}"
echo "=============================================================="

# Test stable version of the main API
echo -e "\n${GREEN}Testing stable version of Main API:${NC}"
curl -s http://api.localhost/api/health | jq

# Test canary version of the main API
echo -e "\n${GREEN}Testing canary version of Main API:${NC}"
curl -s -H "X-Canary: true" http://api.localhost/api/health | jq

# Generate JWT token for GCP API
echo -e "\n${GREEN}Generating JWT token for GCP API...${NC}"
token=$(curl -s -X POST http://api.localhost/api/auth/token -H "Content-Type: application/json" -d '{"user_id": 1}' | jq -r .token)

if [ -z "$token" ] || [ "$token" = "null" ]; then
    echo -e "${RED}Failed to get token. Using a mock token for testing.${NC}"
    token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwibmFtZSI6IlRlc3QgVXNlciIsImlhdCI6MTUxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
else
    echo -e "${GREEN}Successfully obtained token.${NC}"
fi

# Test stable version of the GCP API
echo -e "\n${GREEN}Testing stable version of GCP Deployment API:${NC}"
curl -s http://api.localhost/gcp/api/health -H "Authorization: Bearer $token" | jq

# Test canary version of the GCP API
echo -e "\n${GREEN}Testing canary version of GCP Deployment API:${NC}"
curl -s -H "X-Canary: true" http://api.localhost/gcp/api/health -H "Authorization: Bearer $token" | jq

echo -e "\n${GREEN}All tests completed.${NC}"
echo "=============================================================="
echo "Monitoring:"
echo "- Traefik Dashboard: http://traefik.localhost"
echo "- Prometheus: http://prometheus.localhost"
echo "- Grafana: http://grafana.localhost (admin/admin)"
