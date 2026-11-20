"""Fehler-Log fuer den Betreiber: technische Fehler des Servers, gleiche Fehler werden zusammengezaehlt.

Gespeichert werden nur technische Angaben (Zeit, Quelle, Pfad ohne Parameter, Fehlerart, gekuerzte Meldung und Stack).
Keine IP-Adressen, keine Anfrageinhalte, keine Chat-Texte. Die Ablage ist auf ``MAX_ENTRIES`` Eintraege und
``MAX_AGE_DAYS`` Tage begrenzt.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
import traceback

MAX_ENTRIES = 300
MAX_AGE_DAYS = 30
MESSAGE_MAX = 400
TRACE_MAX = 4000


def signature(kind: str, message: str, where: str) -> str:
    first = (message or "").splitlines()[0] if message else ""
    return hashlib.sha1(f"{kind}|{where}|{first[:200]}".encode("utf-8", "replace")).hexdigest()


def describe(exc_info, where: str = "", source: str = "server") -> dict:
    """Ausnahme (``sys.exc_info()``-Tripel) -> Eintrag ohne Datenbankbezug."""
    kind, value, tb = exc_info
    message = str(value)[:MESSAGE_MAX]
    trace = "".join(traceback.format_exception(kind, value, tb))[-TRACE_MAX:]
    name = kind.__name__ if kind else "Error"
    return {"source": source, "where": where[:120], "kind": name[:80], "message": message, "trace": trace,
            "sig": signature(name, message, where)}


class MemoryErrors:
    """Fuer Tests und Betrieb ohne Datenbank."""

    def __init__(self, clock=time.time) -> None:
        self._rows: list[dict] = []
        self._next = 1
        self._clock = clock
        self._lock = threading.Lock()

    def record(self, entry: dict) -> None:
        now = self._clock()
        with self._lock:
            for row in self._rows:
                if row["sig"] == entry["sig"]:
                    row["count"] += 1
                    row["lastAt"] = now
                    return
            self._rows.append({**entry, "id": self._next, "count": 1, "firstAt": now, "lastAt": now})
            self._next += 1
            if len(self._rows) > MAX_ENTRIES:
                self._rows.sort(key=lambda r: r["lastAt"])
                del self._rows[: len(self._rows) - MAX_ENTRIES]

    def list(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = sorted(self._rows, key=lambda r: r["lastAt"], reverse=True)[:limit]
            return [{k: v for k, v in r.items() if k != "sig"} for r in rows]

    def count_since(self, since: float) -> int:
        with self._lock:
            return sum(r["count"] for r in self._rows if r["lastAt"] >= since)

    def delete(self, entry_id: int) -> bool:
        with self._lock:
            before = len(self._rows)
            self._rows = [r for r in self._rows if r["id"] != entry_id]
            return len(self._rows) != before

    def clear(self) -> int:
        with self._lock:
            n = len(self._rows)
            self._rows = []
            return n


class LogHandler(logging.Handler):
    """Schreibt jeden ``ERROR``-Logeintrag mit Ausnahme in das Fehler-Log. Selbst nie ein Grund fuer einen Absturz."""

    def __init__(self, sink, level=logging.ERROR) -> None:
        super().__init__(level)
        self.sink = sink
        self._busy = threading.local()

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(self._busy, "on", False) or record.name.startswith(("sqlalchemy", "engineio", "socketio")):
            return
        self._busy.on = True
        try:
            where = (getattr(record, "path", None) or record.name)
            source = "http" if getattr(record, "path", None) else "log"
            if record.exc_info and record.exc_info[0] is not None:
                entry = describe(record.exc_info, where=where, source=source)
            else:
                message = record.getMessage()[:MESSAGE_MAX]
                entry = {"source": source, "where": where[:120], "kind": record.levelname, "message": message,
                         "trace": "", "sig": signature(record.levelname, message, where)}
            self.sink.record(entry)
        except Exception:  # pragma: no cover - das Fehler-Log darf nie selbst Fehler ausloesen
            pass
        finally:
            self._busy.on = False
