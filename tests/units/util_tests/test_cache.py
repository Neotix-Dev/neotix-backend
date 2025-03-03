import sys
import os
from pathlib import Path
import pytest
import time
from functools import wraps

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import cache functions
from utils.cache import memory_cache, invalidate_cache, _cache

@pytest.mark.unit_tests
@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the cache before and after each test"""
    invalidate_cache()
    yield
    invalidate_cache()

@pytest.mark.unit_tests
def test_cache_basic_functionality():
    """Test that the memory_cache decorator caches function results"""
    call_count = 0
    
    @memory_cache()
    def sample_function(a, b):
        nonlocal call_count
        call_count += 1
        return a + b
    
    # First call - should execute function
    assert sample_function(2, 3) == 5
    assert call_count == 1
    
    # Second call with same args - should use cache
    assert sample_function(2, 3) == 5
    assert call_count == 1  # Still 1, function not called again
    
    # Call with different args - should execute function again
    assert sample_function(3, 4) == 7
    assert call_count == 2

@pytest.mark.unit_tests
def test_cache_expiry():
    """Test that cached results expire after the specified time"""
    call_count = 0
    
    @memory_cache(expiration=0.2)  # Short expiration for testing
    def timed_function():
        nonlocal call_count
        call_count += 1
        return f"Result {call_count}"
    
    # First call
    assert timed_function() == "Result 1"
    assert call_count == 1
    
    # Call immediately - should use cache
    assert timed_function() == "Result 1"
    assert call_count == 1
    
    # Wait for cache to expire
    time.sleep(0.3)
    
    # Call after expiration - should execute function again
    assert timed_function() == "Result 2"
    assert call_count == 2

@pytest.mark.unit_tests
def test_cache_invalidation():
    """Test that invalidate_cache clears all cached results"""
    call_count = 0
    
    @memory_cache()
    def sample_function():
        nonlocal call_count
        call_count += 1
        return call_count
    
    # First call
    assert sample_function() == 1
    
    # Call again - should use cache
    assert sample_function() == 1
    assert call_count == 1
    
    # Invalidate cache
    invalidate_cache()
    
    # Call after invalidation - should execute function again
    assert sample_function() == 2
    assert call_count == 2

@pytest.mark.unit_tests
def test_different_functions_cache_independently():
    """Test that different functions get cached independently"""
    count_a = 0
    count_b = 0
    
    @memory_cache()
    def function_a():
        nonlocal count_a
        count_a += 1
        return f"A{count_a}"
    
    @memory_cache()
    def function_b():
        nonlocal count_b
        count_b += 1
        return f"B{count_b}"
    
    # Call both functions
    assert function_a() == "A1"
    assert function_b() == "B1"
    assert count_a == 1
    assert count_b == 1
    
    # Call again - should use cache
    assert function_a() == "A1"
    assert function_b() == "B1"
    assert count_a == 1
    assert count_b == 1
    
    # Invalidate and call again - both should execute
    invalidate_cache()
    assert function_a() == "A2"
    assert function_b() == "B2"
    assert count_a == 2
    assert count_b == 2

@pytest.mark.unit_tests
def test_cache_with_different_argument_types():
    """Test cache behavior with various argument types"""
    call_count = 0
    
    @memory_cache()
    def complex_args(a, b=None, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return call_count
    
    # Different calls with different argument patterns
    assert complex_args(1) == 1
    assert complex_args(1, 2) == 2
    assert complex_args(1, b=2) == 3
    assert complex_args(1, 2, 3) == 4
    assert complex_args(1, key="value") == 5
    assert call_count == 5
    
    # Repeated calls - should use cache
    assert complex_args(1) == 1  # Cached
    assert complex_args(1, 2) == 2  # Cached
    assert complex_args(1, b=2) == 3  # Cached 
    assert complex_args(1, 2, 3) == 4  # Cached
    assert complex_args(1, key="value") == 5  # Cached
    assert call_count == 5  # Still 5, no new calls

@pytest.mark.unit_tests
def test_nested_cached_functions():
    """Test behavior with nested cached functions"""
    outer_count = 0
    inner_count = 0
    
    @memory_cache()
    def inner_function(x):
        nonlocal inner_count
        inner_count += 1
        return x * 2
    
    @memory_cache()
    def outer_function(x):
        nonlocal outer_count
        outer_count += 1
        return inner_function(x) + 1
    
    # First call
    assert outer_function(5) == 11  # (5*2)+1
    assert outer_count == 1
    assert inner_count == 1
    
    # Second call - both should use cache
    assert outer_function(5) == 11
    assert outer_count == 1
    assert inner_count == 1
    
    # Call inner directly - should use cache
    assert inner_function(5) == 10
    assert inner_count == 1
    
    # Call with different value - should execute both functions
    assert outer_function(7) == 15  # (7*2)+1
    assert outer_count == 2
    assert inner_count == 2

@pytest.mark.unit_tests
def test_cache_key_generation():
    """Test that cache keys are properly generated"""
    # We can examine the _cache dictionary directly
    
    @memory_cache()
    def key_test(a, b=10):
        return a + b
    
    # Make some calls
    key_test(1)
    key_test(2, 3)
    key_test(4, b=5)
    
    # Check cache keys
    keys = list(_cache.keys())
    assert len(keys) == 3
    
    # Keys should contain function name and arguments
    assert any("key_test:(1,):{}" in key for key in keys)
    assert any("key_test:(2, 3):{}" in key for key in keys)
    assert any("key_test:(4,):{'b': 5}" in key for key in keys)