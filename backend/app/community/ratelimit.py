"""Gleitendes Zeitfenster pro Schluessel (im Arbeitsspeicher, thread-sicher).

Der Speicher bleibt begrenzt: Schluessel, deren letzter Treffer laenger als ihr Fenster zurueckliegt, werden laufend
entfernt (auch wenn sie nie wieder benutzt werden), und es gibt eine harte Obergrenze (``max_keys``). Ist sie erreicht,
fliegt der am laengsten unbenutzte Schluessel raus. Es wird nichts auf Platte geschrieben; ein Neustart leert alles.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque

MAX_KEYS = 20000
SWEEP_EVERY = 30.0       # Sekunden zwischen zwei Aufraeumdurchlaeufen


class RateLimiter:
    def __init__(self, clock=time.monotonic, max_keys: int = MAX_KEYS) -> None:
        self._clock = clock
        self._max_keys = max_keys
        self._hits: OrderedDict[str, list] = OrderedDict()   # Schluessel -> [Treffer (deque), Fenster]; vorn = am laengsten unbenutzt
        self._lock = threading.Lock()
        self._last_sweep = clock()

    def __len__(self) -> int:
        return len(self._hits)

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < SWEEP_EVERY:
            return
        self._last_sweep = now
        for key in [k for k, (hits, window) in self._hits.items() if not hits or now - hits[-1] >= window]:
            del self._hits[key]

    def _entry(self, key: str, window: float, now: float) -> deque:
        item = self._hits.get(key)
        if item is None:
            item = self._hits[key] = [deque(), window]
            while len(self._hits) > self._max_keys:
                self._hits.popitem(last=False)
        else:
            self._hits.move_to_end(key)
            item[1] = window
        hits = item[0]
        while hits and now - hits[0] >= window:
            hits.popleft()
        return hits

    def peek(self, key: str, limit: int, window: float) -> bool:
        """``True``, wenn das Limit gerade erreicht ist (zaehlt nichts mit)."""
        now = self._clock()
        with self._lock:
            self._sweep(now)
            if key not in self._hits:
                return limit <= 0
            return len(self._entry(key, window, now)) >= limit

    def record(self, key: str, window: float) -> None:
        """Einen Treffer eintragen, ohne zu pruefen (z. B. fuer Fehlversuche)."""
        now = self._clock()
        with self._lock:
            self._sweep(now)
            self._entry(key, window, now).append(now)

    def allow(self, key: str, limit: int, window: float) -> bool:
        """Zaehlt einen Versuch; ``False``, wenn in den letzten ``window`` Sekunden schon ``limit`` Versuche liefen."""
        now = self._clock()
        with self._lock:
            self._sweep(now)
            hits = self._entry(key, window, now)
            if len(hits) >= limit:
                if not hits:
                    del self._hits[key]
                return False
            hits.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)
