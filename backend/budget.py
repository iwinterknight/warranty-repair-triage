"""Rate + budget guard (locked #4 / ADR-0002).

Two free-tier limits: ~20 req/min (throttle — in-process sliding window) and 50 req/day (a durable ledger
in S3 so the cap survives restarts). ``check_daily()`` gates *before* a call; ``record_call()`` increments
*after* a real call. The per-minute limiter is per-process — at scale it becomes reserved worker
concurrency / a distributed limiter (README scaling note).
"""
from __future__ import annotations

import time
from collections import deque

from .config import get_settings
from .store_s3 import S3Store


class BudgetExceeded(RuntimeError):
    """Daily LLM budget reached — the caller routes the note to needs_review instead of calling."""


class BudgetGuard:
    def __init__(self, store: S3Store) -> None:
        s = get_settings()
        self._store = store
        self._per_min = s.max_requests_per_min
        self._per_day = s.max_requests_per_day
        self._recent: deque[float] = deque()

    def check_daily(self) -> None:
        used = self._store.get_budget_used()
        if used >= self._per_day:
            raise BudgetExceeded(f"daily LLM budget reached ({used}/{self._per_day})")

    def throttle(self) -> None:
        """Block until under the per-minute cap (sliding 60s window)."""
        now = time.monotonic()
        while self._recent and now - self._recent[0] > 60:
            self._recent.popleft()
        if len(self._recent) >= self._per_min:
            time.sleep(max(0.0, 60 - (now - self._recent[0])))
            if self._recent:
                self._recent.popleft()
        self._recent.append(time.monotonic())

    def record_call(self) -> int:
        return self._store.incr_budget(1)
