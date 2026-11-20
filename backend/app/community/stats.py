"""Statistik ueber Tische: Aufzeichnung (``StatsRecorder``) und Auswertung (``summarize``, rein funktional)."""
from __future__ import annotations

import statistics
import threading
import time
from datetime import datetime, timezone
from typing import Protocol

DAY = 86400.0
BUCKETS = ((0, 0, "keins"), (1, 3, "1–3"), (4, 11, "4–11"), (12, 27, "12–27"), (28, 10**9, "28+"))   # Spiele je Tisch


class StatsRecorder(Protocol):
    def table_created(self, code: str, now: float | None = None) -> None: ...
    def round_started(self, code: str, humans: int, bots: int, now: float | None = None) -> None: ...
    def game_finished(self, code: str, now: float | None = None, duration: float | None = None) -> None: ...
    def round_finished(self, code: str, now: float | None = None) -> None: ...
    def activity(self, code: str, now: float | None = None) -> None: ...
    def logs(self) -> list[dict]:
        """``[{code, createdAt, startedAt|None, lastActivityAt, humans, bots, games, rounds, roundsFinished}]`` (Unix-Zeit)."""
    def events(self) -> list[dict]:
        """Anonyme Zaehlereignisse beendeter Spiele: ``[{at, duration|None, humans}]`` (Unix-Zeit, Sekunden)."""


class NullStats:
    def table_created(self, code, now=None): pass
    def round_started(self, code, humans, bots, now=None): pass
    def game_finished(self, code, now=None, duration=None): pass
    def round_finished(self, code, now=None): pass
    def activity(self, code, now=None): pass
    def logs(self): return []
    def events(self): return []


class MemoryStats:
    def __init__(self, clock=time.time) -> None:
        self._logs: list[dict] = []
        self._events: list[dict] = []
        self._clock = clock
        self._lock = threading.Lock()

    def _latest(self, code):
        return next((l for l in reversed(self._logs) if l["code"] == code), None)

    def table_created(self, code, now=None):
        now = self._clock() if now is None else now
        with self._lock:
            self._logs.append({"code": code, "createdAt": now, "startedAt": None, "lastActivityAt": now,
                               "humans": 0, "bots": 0, "games": 0, "rounds": 0, "roundsFinished": 0})

    def round_started(self, code, humans, bots, now=None):
        now = self._clock() if now is None else now
        with self._lock:
            log = self._latest(code)
            if log is None:
                return
            log["startedAt"] = log["startedAt"] or now
            log.update(humans=humans, bots=bots, lastActivityAt=now)
            log["rounds"] += 1

    def game_finished(self, code, now=None, duration=None):
        now = self._clock() if now is None else now
        with self._lock:
            log = self._latest(code)
            if log is not None:
                log["games"] += 1
                log["lastActivityAt"] = now
                self._events.append({"at": now, "duration": duration, "humans": log["humans"]})

    def round_finished(self, code, now=None):
        now = self._clock() if now is None else now
        with self._lock:
            log = self._latest(code)
            if log is not None:
                log["roundsFinished"] += 1
                log["lastActivityAt"] = now

    def events(self):
        with self._lock:
            return [dict(e) for e in self._events]

    def activity(self, code, now=None):
        now = self._clock() if now is None else now
        with self._lock:
            log = self._latest(code)
            if log is not None and log["startedAt"]:
                log["lastActivityAt"] = now

    def logs(self):
        with self._lock:
            return [dict(l) for l in self._logs]


def _describe(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "avg": 0.0, "median": 0.0, "max": 0.0}
    return {"count": len(values), "avg": round(sum(values) / len(values), 1),
            "median": round(statistics.median(values), 1), "max": round(max(values), 1)}


def _minutes(log: dict) -> float:
    return max(0.0, (log["lastActivityAt"] - log["startedAt"]) / 60.0)


def _group(logs: list[dict]) -> dict:
    return {"tables": len(logs), "minutes": _describe([_minutes(l) for l in logs]),
            "games": _describe([float(l["games"]) for l in logs])}


def summarize(logs: list[dict], now: float, days: int = 14) -> dict:
    """Kennzahlen: Tische gesamt/gestartet, gegen Bots vs. mit Menschen, Dauer in Minuten, Spiele je Tisch, Verlauf."""
    started = [l for l in logs if l["startedAt"]]
    alone = [l for l in started if l["humans"] <= 1]
    together = [l for l in started if l["humans"] >= 2]
    per_humans = {str(n): sum(1 for l in started if l["humans"] == n) for n in (1, 2, 3, 4)}
    buckets = [{"label": label, "tables": sum(1 for l in started if lo <= l["games"] <= hi)} for lo, hi, label in BUCKETS]
    today = datetime.fromtimestamp(now, timezone.utc).date()
    per_day = []
    for back in range(days - 1, -1, -1):
        day = today.fromordinal(today.toordinal() - back)
        per_day.append({"date": day.isoformat(),
                        "tables": sum(1 for l in logs if datetime.fromtimestamp(l["createdAt"], timezone.utc).date() == day)})
    return {
        "tablesTotal": len(logs),
        "tablesStarted": len(started),
        "tablesNeverStarted": len(logs) - len(started),
        "last24h": sum(1 for l in logs if now - l["createdAt"] <= DAY),
        "last7d": sum(1 for l in logs if now - l["createdAt"] <= 7 * DAY),
        "last30d": sum(1 for l in logs if now - l["createdAt"] <= 30 * DAY),
        "againstBotsOnly": _group(alone),
        "withHumans": _group(together),
        "byHumans": per_humans,
        "minutes": _describe([_minutes(l) for l in started]),
        "games": _describe([float(l["games"]) for l in started]),
        "gamesBuckets": buckets,
        "roundsTotal": sum(l["rounds"] for l in logs),
        "gamesTotal": sum(l["games"] for l in logs),
        "perDay": per_day,
    }
