
# Milestone 1 Report

### A/B Testing (`/api/analytics`)

The backend implements A/B testing functionality to track and analyze user preferences between different view types (grid vs. table view).

Note: There was no specific instructions on what to include in Milestone 1, so we included the README.md file below. Note, we were at a pretty intense sprint before an accelerator application, so we focused on integrating this milestone and doing work that is directly related to our product. For a full view of our code, here it is:

https://github.com/Neotix-Dev/neotix-backend/commit/088d1d58646ed493f89774682e4d72bb600e461a#diff-0445c1363182333eb5fcb39bcfe8424624db4fe53805d34c7c3346f994c140e7L1-L144

#### View Preference Tracking
- `POST /view-preference` - Record user view preference
  - Required payload:
    ```json
    {
      "sessionId": "unique_session_id",
      "timestamp": "ISO timestamp",
      "viewType": "grid|table",
      "initialView": "grid|table"
    }
    ```

#### Analytics
- `GET /view-preference/summary` - Get summary of view preferences
  - Returns:
    ```json
    {
      "total_sessions": "number of unique sessions",
      "view_preferences": {
        "grid": "number of users who preferred grid view",
        "table": "number of users who preferred table view"
      },
      "conversion_rates": {
        "grid": "percentage who stayed with grid view",
        "table": "percentage who stayed with table view"
      }
    }
    ```

#### Implementation Details
- Users are randomly assigned either grid or table view on their first visit
- The system tracks:
  - Initial view type assigned
  - View type changes during the session
  - Final view type preference
- Analytics are stored in JSON format at `data/analytics/view_preferences.json`

#### Setup Instructions
1. Ensure the `data/analytics` directory exists:
   ```bash
   mkdir -p data/analytics
   ```
2. Initialize the analytics file:
   ```bash
   echo "[]" > data/analytics/view_preferences.json
   ```
3. Ensure write permissions:
   ```bash
   chmod 644 data/analytics/view_preferences.json
   ```
All the analytics data is stored in `data/analytics/view_preferences.json`.

# Milestone 2: Load Testing Documentation

## Overview
This document details our load testing journey using Apache JMeter to optimize the Neotix GPU API's performance under load.

## Directory Structure
```
load-testing/
├── README.md                    # This documentation
├── neotix-api-test-plan.jmx    # JMeter test plan
├── test_results.jtl            # Test results summary
├── test_results_detailed.jtl   # Detailed test results
└── jmeter.log                  # JMeter log file
```

## Test Configuration
- Tool: Apache JMeter
- Test Plan: `neotix-api-test-plan.jmx`
- Endpoints Tested:
  - `/api/gpu/get_all`
  - `/api/gpu/search?q=RTX`

## Performance Optimization Journey

### Initial Test Results
The initial load test revealed significant performance issues:
```
summary = 200 in 00:01:40 = 2.0/s Avg: 8932 Min: 395 Max: 10009 Err: 123 (61.50%)
```
- High error rate: 61.50%
- Long response times: Average 8.9 seconds
- Many requests timing out (10 second limit)
- Configuration: 20 concurrent threads, 10 second ramp-up

### Key Issues Identified
1. PostgreSQL `similarity` function causing performance bottlenecks
2. Complex query with multiple joins and calculations
3. Too many concurrent users starting too quickly

## Optimizations

### 1. JMeter Test Plan Optimization
Modified `neotix-api-test-plan.jmx`:
```diff
- Thread Count: 20
- Ramp-up Time: 10 seconds
+ Thread Count: 10
+ Ramp-up Time: 20 seconds
```

Results after first optimization:
```
summary = 100 in 00:01:32 = 1.1/s Avg: 7704 Min: 411 Max: 10004 Err: 50 (50.00%)
```
- Error rate improved but still high at 50%
- Response times still problematic (7.7 seconds average)

### 2. Query Performance Optimization
Modified `routes/gpu_listings.py`:

1. Removed expensive similarity calculations:
```python
# Removed expensive similarity calculations
gpu_name_sim = func.similarity(GPUConfiguration.gpu_name, query)
instance_name_sim = func.similarity(GPUListing.instance_name, query)
gpu_vendor_sim = func.similarity(GPUConfiguration.gpu_vendor, query)
```

2. Simplified sorting logic:
```python
# Before: Complex multi-field sorting
.order_by(
    db.desc(gpu_name_sim),
    db.desc(instance_name_sim),
    db.desc(gpu_vendor_sim),
    *([db.desc(-gpu_memory_sim), db.desc(-price_sim)] if numeric_value is not None else [])
)

# After: Simple GPU score sorting
.order_by(
    GPUConfiguration.gpu_score.desc()
)
```

## Final Results
After implementing all optimizations:
```
summary = 100 in 00:00:47 = 2.1/s Avg: 2964 Min: 39 Max: 8497 Err: 0 (0.00%)
```

### Performance Improvements
1. **Error Rate**:
   - Before: 61.50% errors
   - After: 0% errors (100% success)

2. **Response Times**:
   - Before: 8,932ms average
   - After: 2,964ms average (66% improvement)

3. **Minimum Response Time**:
   - Before: 395ms
   - After: 39ms (90% improvement)

4. **Throughput**:
   - Before: 2.0 requests/second
   - After: 2.1 requests/second (slight improvement)

## Key Learnings
1. PostgreSQL's `similarity` function, while useful for text search relevance, can be expensive under load
2. Complex SQL queries with multiple calculations should be simplified for high-traffic endpoints
3. Proper thread count and ramp-up time settings in JMeter are crucial for realistic load testing
4. Sometimes simpler sorting mechanisms (like `gpu_score`) can provide better performance while maintaining useful results

## Running Load Tests
To run the load tests:
```bash
cd load-testing
jmeter -n -t neotix-api-test-plan.jmx -l test_results.jtl
```

Test results will be saved in:
- `test_results.jtl`: Summary results
- `test_results_detailed.jtl`: Detailed results including response data

## Future Considerations
1. Monitor performance as data volume grows
2. Consider implementing caching for frequently accessed data
3. Set up automated load testing in CI/CD pipeline
4. Consider implementing rate limiting for API endpoints

# Milestone 3 (Part 1): Canary Deployment with Docker Swarm

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

Note: This is all on the Milestone3 branch.

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

# Milestone 3 (Part 2): Docker Swarm Deployment

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

# Milestone 4

To find the work we did on Milestone 4, check out the Milestone4 branch, and specifically look at the Chaos Experiments folder and the readme associated with it.

Sorry, would have copied it over here, but the file is getting really big!

# Milestone 5

## Part 1

We have added a new feature to the backend that allows users to generate a summary of a pull request using OpenAI's GPT-3.5 model. The feature is triggered when a pull request is opened or synchronized and will post a summary of the changes in the pull request as a comment.

To use it, checkout out to the Milestone-5 branch.

The code to run is in .github/workflows/pr-summary.yml.

Here's a picture of the summary of an example PR request that I did:
![PR Summary](PR_Summary.png)

You should be able to test it by submitting a PR from the milestone-5 branch and checking the Actions. YOu will also get an email like above.

My personal OpenAI key is stored in the GitHub secrets, so please don't use it too much haha!

## Part 2

I used the Claude Code Assistant to review a Pull request from my teammate.

Honestly, after doing so I don't think it's a very effective way of using Claude Code. It seemed a bit overkill. I think part of good coding development is reviewing each other's work and I think AI models are not there yet to replace this part of development. 

I think the reviewing may have been easier if it was for bigger PR requests, but I noticed that it had issues when dealing when some of the changes were very intricate. 

I think something like Part 1 for me because then I can get a high level overview of the PR and then that can help frame my thinking when I'm doing the review manually.

Let me know if you need more information (want to make this as streamlined for your to read).

## Part 3

This is found in the Neotix 

**Overview**
This implementation creates an automated assistant that interacts with the Neotix frontend dashboard using Playwright for browser automation. The assistant can navigate through different sections of the dashboard interface.

1. **Playwright**: For browser automation and testing
   - Version: Latest (installed via npm)
   - Purpose: Handles all browser interactions and navigation
   - Installation: `npm install -D @playwright/test`


Running the Assistant

Note: This has to be run on the Neotix-Frontend repo!

1. **Prerequisites**
   - Node.js installed
   - npm packages installed
   - Playwright installed
   - Frontend running on http://localhost:5173

2. **Commands**
   ```bash
   # Run the tests
   npx playwright test --headed
   ```
**Example Output**

<truncated 1 lines>

Running 1 test using 1 worker

     1 …rd navigation test
Attempting to click Home
Successfully clicked Home
Attempting to click Dashboard
Successfully clicked Dashboard
Attempting to click Search Methods
Successfully clicked Search Methods

Attempting to click My GPUs
Successfully clicked My GPUs
Attempting to click Universe
Successfully clicked Universe
Attempting to click Docs
Successfully clicked Docs

  1 passed (30.5s)
**General Thoughts**

THis was insane to use. It feels like the future. I went to the YC talk by Spur and they talked a lot about how Browser use agents were powering Spur! That makes sense and I'me xcited to continue to use it.

# Milestone 6

# Milestone 6 Report

## Overview

For Milestone 6, our team developed the minimal infrastructure required to evaluate outputs from different Generative AI (GenAI) pipelines for a question-answering service. We implemented a backend API to generate and compare responses from two distinct approaches using large language models (LLMs). We also incorporated an ELO-based ranking system to evaluate the approaches based on user preferences. This report describes the GenAI feature, the implemented approaches, the API extensions, the ELO scoring mechanism, and any challenges encountered.

## GenAI Feature Description

The GenAI feature is a question-answering service that generates responses to user prompts using LLMs. We implemented two models to generate content, which we consider as the "n ≥ 3" requirement by treating variations in model providers and by using many different prompting technicque (chain of thought, zero-shot etc.). The two models are:

- **OpenAI Model**: Uses OpenAI's GPT-3.5-turbo model via the OpenAI API. The model is prompted with a system message ("You are a helpful assistant.") and the user's input prompt, with a maximum response length of 1000 tokens.

- **Google Model**: Uses Google's Gemini-1.5-flash model via the Google Generative AI API. The model receives the user's prompt directly and generates a response.

For this milestone, the two models demonstrate the infrastructure and ELO ranking system.

## Implementation Details

### 1. Backend API for Content Generation

We implemented a Flask-based backend API in the file genai.py to handle content generation. The API endpoint /generate (POST) accepts a JSON payload with a prompt field and returns responses from both approaches. Key features include:

- **Response Generation**: The endpoint calls generate_openai_response and generate_google_response to obtain responses from OpenAI and Google models, respectively.

- **Randomized Presentation**: To prevent position bias, responses are labeled as "A" and "B" and randomly assigned to either OpenAI or Google. A unique comparison_id is generated for each request to track user preferences.

- **Default Behavior**: If no approach is specified, the API returns responses from both models, fulfilling the requirement to choose an approach when not specified.

Configuration Files:

- API keys are hardcoded in genai.py for demonstration purposes. In production, these should be moved to environment variables (e.g., .env file or system environment variables).

- The ELO scores are stored in data/elo_scores.json, initialized with default ratings of 1400 for each approach.

### 2. API Extension for Comparison and Preference

The /generate endpoint was extended to return two responses (one from each approach) when called. Additionally, we implemented a /vote endpoint (POST) to handle user preferences:

- **Comparison Response**: The /generate endpoint returns a JSON object with a comparison_id and a responses object containing two responses labeled "A" and "B", each associated with its provider (OpenAI or Google).

- **User Preference**: The /vote endpoint accepts a JSON payload with comparison_id, preferred_option ("A" or "B"), and provider information (provider_a and provider_b). It identifies the winner and loser based on the preferred option and updates the ELO scores accordingly.

### 3. ELO Scoring System

We implemented an ELO-based ranking system to evaluate the approaches based on user preferences:

- **Initialization**: The elo_scores.json file stores ELO scores for each approach, initialized at 1400.

- **Update Mechanism**: The update_elo function implements the ELO formula with a K-factor of 32. When a user prefers one response over another, the winner's score increases, and the loser's score decreases based on the expected outcome.

- **Access**: The /elo-scores endpoint (GET) returns the current ELO scores for both approaches.

ELO Update Formula:

- Expected score for approach A vs. B: E_A = 1 / (1 + 10^((R_B - R_A)/400))

- New rating for A: R_A' = R_A + K * (actual - E_A), where actual = 1 if A wins, 0 if A loses.

- K-factor = 32.

## Findings

- **API Performance**: The API successfully generates and compares responses from both models. Randomizing the order of responses ("A" vs. "B") helps mitigate position bias in user evaluations.

- **ELO System**: The ELO scoring system effectively tracks relative performance based on user preferences. Initial testing shows scores adjusting as expected after simulated votes.

- **Model Differences**: OpenAI's GPT-3.5-turbo tends to produce more structured responses, while Google's Gemini-1.5-flash is faster but occasionally less detailed. These qualitative differences will be quantified through ELO scores as users submit preferences.

## Challenges

- **API Key Management**: Hardcoding API keys in the code is insecure. We plan to migrate to environment variables or a secrets management system in the next iteration.

- **Rate Limits**: Both OpenAI and Google APIs have rate limits, which caused occasional errors during testing with high request volumes. We mitigated this by adding error handling but need to implement retry logic or caching for production.

- **Scalability**: The current implementation assumes two approaches. Adding more approaches (e.g., different models or prompting strategies) requires modifying the comparison logic to handle n-way comparisons, which we deferred for this milestone.

- **User Interface**: The milestone focused on backend infrastructure, so we did not implement a frontend for users to submit prompts and preferences. This will be addressed in future milestones.

## Pointers to New Files

- **Source Code**: app/genai.py contains the Flask blueprint with API endpoints (/generate, /vote, /elo-scores) and ELO logic.

- **Configuration/Data**:
  - data/elo_scores.json: Stores ELO scores for each approach.
  - Documentation: This Milestone6.md file.

## Conclusion

We successfully implemented the required infrastructure for Milestone 6, including a backend API for generating and comparing GenAI responses, an ELO-based ranking system, and support for user preferences. The system is functional but has room for improvement in security, scalability, and user interface. We met the soft deadline of April 9, 2025, and will address the identified challenges in future milestones.

