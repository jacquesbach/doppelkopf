"""Uebersicht ueber offene Tische fuer den Betreiber (Auswertung rein funktional; Daten liefert ``sql.py``)."""
from __future__ import annotations

from typing import Protocol

ACTIVE_WITHIN = 300          # Sekunden: so kurz her darf die letzte Aktion sein, damit ein Tisch "aktiv" heisst


class TableOverview(Protocol):
    def tables(self) -> list[dict]:
        """Rohdaten je offenem Tisch (Unix-Zeit): code, status, isPublic, hasPassword, createdAt, startedAt|None,
        lastActivityAt, humans, bots, spectators, connectedHumans, game ({number, phase, normalGamesPlayed}|None)."""


def describe(info: dict, now: float) -> dict:
    idle = max(0.0, now - info["lastActivityAt"])
    state = "active" if idle <= ACTIVE_WITHIN else "idle"
    return {**info, "state": state, "idleSeconds": int(idle),
            "activeSince": info["startedAt"] or info["createdAt"],
            "againstBotsOnly": info["humans"] <= 1 and info["status"] != "waiting"}


def overview(raw: list[dict], now: float) -> dict:
    rows = [describe(r, now) for r in raw]
    rows.sort(key=lambda r: (r["state"] != "active", r["idleSeconds"]))        # aktive zuerst, dann nach Leerlauf
    return {"tables": rows, "count": len(rows),
            "activeCount": sum(r["state"] == "active" for r in rows),
            "humansTotal": sum(r["humans"] for r in rows),
            "connectedTotal": sum(r["connectedHumans"] for r in rows)}


class MemoryTables:
    def __init__(self, rows=()) -> None:
        self.rows = list(rows)

    def tables(self):
        return [dict(r) for r in self.rows]
