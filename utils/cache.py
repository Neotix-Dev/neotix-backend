import time
from functools import wraps

# Simple in-memory cache dictionary
_cache = {}

# Default cache expiration time in seconds
DEFAULT_EXPIRATION = 60

def cache_key(func, args, kwargs):
    """Generate a cache key based on function name and arguments."""
    key = f"{func.__name__}:{args}:{kwargs}"
    return key

def memory_cache(expiration=DEFAULT_EXPIRATION):
    """Decorator to cache function results in memory."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = cache_key(func, args, kwargs)
            current_time = time.time()

            # Check if the key is in the cache and not expired
            if key in _cache:
                result, timestamp = _cache[key]
                if current_time - timestamp < expiration:
                    return result

            # Call the function and cache the result
            result = func(*args, **kwargs)
            _cache[key] = (result, current_time)
            return result

        return wrapper
    return decorator

def invalidate_cache():
    """Clear the entire cache."""
    _cache.clear()
