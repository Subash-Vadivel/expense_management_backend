from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    """In-process sliding-window limiter.

    State lives in this process only (per worker, reset on restart). Swap for a
    Redis-backed implementation with the same interface when one is available.
    """

    def __init__(self, max_hits: int, window_seconds: int) -> None:
        self.max_hits = max_hits
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        if not hits:
            del self._hits[key]
            return deque()
        return hits

    def hit(self, key: str) -> bool:
        """Record an attempt. Returns False (and records nothing) when over the limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._prune(key, now)
            if len(hits) >= self.max_hits:
                return False
            self._hits[key].append(now)
            return True

    def remaining(self, key: str) -> int:
        with self._lock:
            return max(0, self.max_hits - len(self._prune(key, time.monotonic())))

    def retry_after_seconds(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            hits = self._prune(key, now)
            if len(hits) < self.max_hits:
                return 0
            return max(1, int(hits[0] + self.window_seconds - now))


DAY_SECONDS = 24 * 60 * 60

verification_resend_limiter = SlidingWindowLimiter(max_hits=3, window_seconds=DAY_SECONDS)
password_reset_limiter = SlidingWindowLimiter(max_hits=3, window_seconds=DAY_SECONDS)
