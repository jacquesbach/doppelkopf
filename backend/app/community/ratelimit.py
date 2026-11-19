"""Gleitendes Zeitfenster pro Schluessel (im Arbeitsspeicher, thread-sicher)."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float) -> bool:
        """Zaehlt einen Versuch; ``False``, wenn in den letzten ``window`` Sekunden schon ``limit`` Versuche liefen."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            if len(self._hits) > 5000:           # Speicher begrenzen: leere Eintraege wegraeumen
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)
