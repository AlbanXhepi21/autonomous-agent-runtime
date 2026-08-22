"""Application-scoped instance caching and teardown.

Providers decorated with ``@provider`` build one instance per process and
register it for disposal. Teardown then walks what was actually constructed,
so adding a provider does not also mean remembering to extend a shutdown
function and a list of caches to clear.
"""

import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

from app.core.logging import log_event, safe_error_message

T = TypeVar("T")

_logger = logging.getLogger(__name__)

# Providers in construction order; teardown reverses it so a resource is
# released before whatever it was built from.
_providers: list[Any] = []
_constructed: list[Any] = []


def provider(build: Callable[[], T]) -> Callable[[], T]:
    """Cache one application-scoped instance and register it for teardown."""

    cache: dict[str, T] = {}

    @wraps(build)
    def resolve() -> T:
        if "instance" not in cache:
            instance = build()
            cache["instance"] = instance
            _constructed.append(instance)
        return cache["instance"]

    def cache_clear() -> None:
        instance = cache.pop("instance", None)
        if instance is not None and instance in _constructed:
            _constructed.remove(instance)

    resolve.cache_clear = cache_clear  # type: ignore[attr-defined]
    _providers.append(resolve)
    return resolve


async def _release(instance: Any) -> None:
    """Call whichever disposal method a resource exposes, if it exposes one."""

    for name in ("close", "dispose"):
        method: Callable[[], Awaitable[None]] | None = getattr(instance, name, None)
        if method is None:
            continue
        try:
            result = method()
            if isinstance(result, Awaitable):
                await result
        except Exception as error:
            # Shutdown continues; one resource failing must not strand the rest.
            log_event(
                _logger, logging.WARNING, "resource_release_failed",
                resource=type(instance).__name__, error_type=type(error).__name__,
                error=safe_error_message(error),
            )
        return


async def shutdown() -> None:
    """Release every constructed resource and reset the process-scoped caches."""

    for instance in reversed(list(_constructed)):
        await _release(instance)
    for resolve in _providers:
        resolve.cache_clear()
    _constructed.clear()
