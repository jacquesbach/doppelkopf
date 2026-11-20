"""Live-Uebersicht fuer den Betreiber (rein funktional): offene Tische, Spieler online, laufende Spiele.

Die Rohdaten je Tisch liefert ``sql.SqlLive.tables()``; hier werden sie eingeordnet und summiert. Dazu die Pruefung der
Nachricht, die der Betreiber an einen Tisch schickt.
"""
from __future__ import annotations

ACTIVE_WITHIN = 300          # Sekunden: so kurz her darf die letzte Aktion sein, damit ein Tisch "aktiv" heisst
NOTICE_MAX = 300


class NoticeError(ValueError):
    pass


def clean_notice(text: object, required: bool = True) -> str:
    """Nachricht an einen Tisch: reiner Text, ohne Steuerzeichen, hoechstens ``NOTICE_MAX`` Zeichen."""
    value = " ".join(str(text or "").split())
    if required and not value:
        raise NoticeError("Bitte gib eine Nachricht ein.")
    if len(value) > NOTICE_MAX:
        raise NoticeError(f"Die Nachricht darf höchstens {NOTICE_MAX} Zeichen lang sein.")
    return value


def classify(row: dict, now: float) -> dict:
    idle = max(0.0, now - row["lastActivityAt"])
    if row["status"] == "playing":
        state = "running" if idle <= ACTIVE_WITHIN else "idle"
    elif row["status"] == "finished":
        state = "finished" if idle <= ACTIVE_WITHIN else "idle"
    else:
        state = "waiting" if idle <= ACTIVE_WITHIN else "idle"
    humans = [p for p in row["players"] if not p["isBot"]]
    return {**row, "state": state, "idleSeconds": int(idle),
            "humans": len(humans), "bots": sum(p["isBot"] for p in row["players"]),
            "connectedHumans": sum(1 for p in humans if p["connected"]),
            "activeSince": row.get("startedAt") or row["createdAt"],
            "againstBotsOnly": len(humans) <= 1 and row["status"] != "waiting"}


def live_overview(raw: list[dict], now: float) -> dict:
    rows = [classify(r, now) for r in raw]
    order = {"running": 0, "waiting": 1, "finished": 2, "idle": 3}
    rows.sort(key=lambda r: (order[r["state"]], r["idleSeconds"]))
    real = [r for r in rows if not r.get("isLab")]
    return {
        "tables": rows,
        "count": len(rows),
        "running": sum(r["state"] == "running" for r in real),
        "waiting": sum(r["state"] == "waiting" for r in real),
        "idle": sum(r["state"] == "idle" for r in real),
        "humansOnline": sum(r["connectedHumans"] for r in real),
        "spectatorsTotal": sum(r["spectators"] for r in real),
        "playingNow": sum(r["connectedHumans"] for r in real if r["state"] == "running"),
        "botOnlyTables": sum(1 for r in real if r["state"] == "running" and r["againstBotsOnly"]),
        "serverTime": now,
    }
