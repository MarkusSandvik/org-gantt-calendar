import time
from collections import defaultdict, deque


class InMemorySlidingWindowRateLimiter:
    """A minimal sliding-window limiter, keyed by an arbitrary string (e.g.
    client IP). Good enough for local development and a small single-process
    deployment; a production deployment behind multiple worker processes
    should swap this for a Redis-backed limiter without changing call
    sites — every caller only sees `hit(key) -> bool`."""

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str) -> bool:
        """Records an attempt for `key` and returns whether it's allowed
        (i.e. the caller has not exceeded max_attempts within the window)."""
        now = time.monotonic()
        window = self._hits[key]
        while window and now - window[0] > self._window_seconds:
            window.popleft()
        if len(window) >= self._max_attempts:
            return False
        window.append(now)
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def reset_all(self) -> None:
        self._hits.clear()
