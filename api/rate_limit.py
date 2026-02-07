"""
Rate limiting module with Redis backend for distributed rate limiting.
Falls back to in-memory rate limiting if Redis is not available.
"""

import time
import logging
from typing import Optional, Dict
from config import settings

logger = logging.getLogger("valohub")

# Redis client (initialized lazily)
_redis_client = None
_redis_available: Optional[bool] = None

# In-memory fallback cache
_memory_cache: Dict[str, int] = {}


async def get_redis_client():
    """Get or create the Redis client."""
    global _redis_client, _redis_available

    if _redis_available is False:
        return None

    if _redis_client is not None:
        return _redis_client

    if not settings.redis_url:
        _redis_available = False
        logger.info("Redis URL not configured, using in-memory rate limiting")
        return None

    try:
        import redis.asyncio as redis

        _redis_client = redis.from_url(
            settings.redis_url, encoding="utf-8", decode_responses=True
        )
        # Test connection
        await _redis_client.ping()
        _redis_available = True
        logger.info("Connected to Redis for rate limiting")
        return _redis_client
    except Exception as e:
        _redis_available = False
        logger.warning(f"Failed to connect to Redis, falling back to in-memory: {e}")
        return None


async def close_redis():
    """Close Redis connection."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        _redis_available = None
        logger.info("Redis connection closed")


async def check_rate_limit(
    key: str, limit: int = None, period: int = None
) -> tuple[bool, int]:
    """
    Check if a request should be rate limited.

    Args:
        key: Unique identifier for the rate limit bucket (e.g., IP address)
        limit: Maximum requests allowed per period (defaults to settings.rate_limit)
        period: Time period in seconds (defaults to settings.rate_period)

    Returns:
        Tuple of (allowed: bool, current_count: int)
    """
    if limit is None:
        limit = settings.rate_limit
    if period is None:
        period = settings.rate_period

    now = int(time.time())
    window = now // period
    rate_key = f"rate:{key}:{window}"

    redis = await get_redis_client()

    if redis is not None:
        # Use Redis for distributed rate limiting
        try:
            pipe = redis.pipeline()
            pipe.incr(rate_key)
            pipe.expire(rate_key, period)
            results = await pipe.execute()
            count = results[0]

            if count > limit:
                return False, count
            return True, count
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fall through to in-memory

    # In-memory fallback
    # Clean old entries periodically
    if len(_memory_cache) > 10000:
        current_window = now // period
        keys_to_delete = [
            k for k in _memory_cache.keys() if not k.endswith(f":{current_window}")
        ]
        for k in keys_to_delete:
            del _memory_cache[k]

    count = _memory_cache.get(rate_key, 0) + 1
    _memory_cache[rate_key] = count

    if count > limit:
        return False, count
    return True, count


async def get_rate_limit_remaining(
    key: str, limit: int = None, period: int = None
) -> int:
    """Get the remaining requests allowed for a key."""
    if limit is None:
        limit = settings.rate_limit
    if period is None:
        period = settings.rate_period

    now = int(time.time())
    window = now // period
    rate_key = f"rate:{key}:{window}"

    redis = await get_redis_client()

    if redis is not None:
        try:
            count = await redis.get(rate_key)
            count = int(count) if count else 0
            return max(0, limit - count)
        except Exception:
            pass

    count = _memory_cache.get(rate_key, 0)
    return max(0, limit - count)
