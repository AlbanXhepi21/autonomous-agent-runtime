"""InMemoryRateLimiter: allows within budget, blocks over budget, per bucket."""

import pytest

from app.identity.rate_limit import InMemoryRateLimiter, RateLimitExceededError


@pytest.mark.asyncio
async def test_allows_requests_within_the_limit() -> None:
    limiter = InMemoryRateLimiter()

    for _ in range(3):
        await limiter.check(action="login", key="1.2.3.4", limit=3, window_seconds=60)


@pytest.mark.asyncio
async def test_raises_once_the_limit_is_exceeded() -> None:
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        await limiter.check(action="login", key="1.2.3.4", limit=3, window_seconds=60)

    with pytest.raises(RateLimitExceededError) as excinfo:
        await limiter.check(action="login", key="1.2.3.4", limit=3, window_seconds=60)

    assert excinfo.value.action == "login"
    assert excinfo.value.retry_after_seconds > 0


@pytest.mark.asyncio
async def test_buckets_are_independent_per_key() -> None:
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        await limiter.check(action="login", key="1.2.3.4", limit=3, window_seconds=60)

    # A different key must not be blocked by another key's exhausted bucket.
    await limiter.check(action="login", key="5.6.7.8", limit=3, window_seconds=60)


@pytest.mark.asyncio
async def test_buckets_are_independent_per_action() -> None:
    limiter = InMemoryRateLimiter()
    for _ in range(3):
        await limiter.check(action="login", key="1.2.3.4", limit=3, window_seconds=60)

    await limiter.check(action="register", key="1.2.3.4", limit=3, window_seconds=60)
