"""Systemstatus (rein funktional): Version, letzter Deploy, Laufzeit, Datenbankgroesse, Auslastung."""
from __future__ import annotations

import os
import platform

DEFAULT_VERSION = "unbekannt"


def _clean(value: object, limit: int = 80) -> str:
    return "".join(ch for ch in str(value or "") if ch.isprintable())[:limit]


def build_info(environ=os.environ) -> dict:
    """Aus der Umgebung (setzt der Deploy: ``APP_VERSION`` = Git-Stand, ``DEPLOYED_AT`` = ISO-Zeit in UTC)."""
    return {"version": _clean(environ.get("APP_VERSION")) or DEFAULT_VERSION,
            "deployedAt": _clean(environ.get("DEPLOYED_AT")) or None}


def snapshot(build: dict, started_at: float, now: float, db: dict, runtime: dict) -> dict:
    return {
        **build,
        "startedAt": started_at,
        "uptimeSeconds": int(max(0, now - started_at)),
        "python": platform.python_version(),
        "db": db,
        "runtime": runtime,
        "serverTime": now,
    }
