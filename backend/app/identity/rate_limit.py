"""Rate limiting for authentication endpoints.

An interface plus one in-process implementation, the same "in_memory is
enough for a single-process deployment, swap the interface later" pattern
``MemoryStore`` and ``ArtifactStore`` already use elsewhere in this codebase.
Nothing here defends against abuse spread across multiple processes; that
needs a shared backend (Redis, for example) behind the same ``RateLimiter``
contract -- this module does not need to change for that to happen.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque

#: (max attempts, window in seconds) per action. Two independent buckets are
#: checked per sensitive request -- caller IP and the identifier being acted
#: on (email or user id) -- so neither a single account nor a single address
#: can be brute-forced by varying the other.
RATE_LIMITS: dict[str, tuple[int, float]] = {
    "register": (5, 60.0),
    "login": (10, 60.0),
    "forgot_password": (5, 60.0),
    "reset_password": (10, 60.0),
    "verify_resend": (5, 60.0),
    "change_password": (10, 60.0),
    "verify_confirm": (10, 60.0),
}


class RateLimitExceededError(Exception):
    def __init__(self, *, action: str, retry_after_seconds: float) -> None:
        super().__init__(f"Rate limit exceeded for {action}.")
        self.action = action
        self.retry_after_seconds = retry_after_seconds


class RateLimiter(ABC):
    @abstractmethod
    async def check(self, *, action: str, key: str, limit: int, window_seconds: float) -> None:
        """Raise RateLimitExceededError once ``key`` has hit ``limit`` within the window."""


class InMemoryRateLimiter(RateLimiter):
    """Sliding-window counter per (action, key), safe under concurrent requests."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, *, action: str, key: str, limit: int, window_seconds: float) -> None:
        bucket = f"{action}:{key}"
        now = time.monotonic()
        async with self._lock:
            hits = self._hits[bucket]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                raise RateLimitExceededError(
                    action=action, retry_after_seconds=max(window_seconds - (now - hits[0]), 0.0)
                )
            hits.append(now)


async def enforce_rate_limit(limiter: RateLimiter, action: str, *keys: str) -> None:
    """Check every key's bucket for ``action``, raising on the first that is over limit."""

    limit, window_seconds = RATE_LIMITS[action]
    for key in keys:
        await limiter.check(action=action, key=key, limit=limit, window_seconds=window_seconds)
