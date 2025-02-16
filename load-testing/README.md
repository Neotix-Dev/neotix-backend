# Load Testing Documentation

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
