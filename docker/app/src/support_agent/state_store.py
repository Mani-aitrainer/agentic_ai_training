"""Optional Redis-backed counter.

This exists purely to give the session a *second* service. Docker Compose shines
when there is more than one moving part: the agent container is stateless and can
be scaled to N replicas, while the Redis container holds the state they share.
Without it, every replica would have its own private counter.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class InMemoryStore:
    """Fallback used when REDIS_URL is unset. Per-process, so the count differs
    between containers - a nice thing to show live during the scaling demo."""

    def __init__(self) -> None:
        self._n = 0

    def increment(self) -> int:
        self._n += 1
        return self._n

    def count(self) -> int:
        return self._n

    def ping(self) -> bool:
        return True

    @property
    def kind(self) -> str:
        return "memory"


class RedisStore:
    def __init__(self, url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(url, socket_connect_timeout=2, decode_responses=True)

    def increment(self) -> int:
        return int(self._client.incr("agent:requests"))

    def count(self) -> int:
        try:
            return int(self._client.get("agent:requests") or 0)
        except Exception:  # noqa: BLE001
            return 0

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:  # noqa: BLE001
            return False

    @property
    def kind(self) -> str:
        return "redis"


def build_store(redis_url: str | None):
    if not redis_url:
        return InMemoryStore()
    try:
        store = RedisStore(redis_url)
        store.ping()
        return store
    except Exception:  # noqa: BLE001
        log.warning("Redis at %s unavailable - using in-memory store", redis_url)
        return InMemoryStore()
