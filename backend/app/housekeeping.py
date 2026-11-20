"""Aufraeumen: Tische, an denen 12 Stunden lang nichts passiert ist, werden geschlossen (geloescht).

Das ist KEINE Bot-Uebernahme (siehe ``table.service.watch_tick``), sondern nur Speicherhygiene: Ein Spiel gegen Bots
darf beliebig lange stehen bleiben, aber nicht ewig als offener Tisch herumliegen. Die Entscheidung ist als reine
Funktion (``is_idle``/``last_activity``) von der Datenbank getrennt und ohne Flask testbar.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Iterable

MAX_IDLE = timedelta(hours=12)
INTERVAL_SECONDS = 600          # alle zehn Minuten pruefen


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)   # SQLite liefert naive UTC-Zeiten


def last_activity(moments: Iterable[datetime | None]) -> datetime | None:
    """Juengster Zeitpunkt aus: Raum angelegt, Beitritte, letzte Spielzustands-Aenderung."""
    aware = [_aware(m) for m in moments if m is not None]
    return max(aware) if aware else None


def is_idle(moments: Iterable[datetime | None], now: datetime, max_idle: timedelta = MAX_IDLE) -> bool:
    latest = last_activity(moments)
    return latest is not None and _aware(now) - latest >= max_idle


def close_idle_rooms(chat=None, now: datetime | None = None, max_idle: timedelta = MAX_IDLE) -> list[str]:
    """Loescht Raeume ohne Aktivitaet samt Spielstand, Protokoll und Chat. Gibt die geschlossenen Codes zurueck."""
    from . import db
    from .models import GameHistory, GameSnapshot, Room
    now = now or datetime.now(timezone.utc)
    closed = []
    for room in Room.query.all():
        snapshot = GameSnapshot.query.filter_by(room_id=room.id).first()
        moments = [room.created_at, *(m.joined_at for m in room.members), snapshot.updated_at if snapshot else None]
        if not is_idle(moments, now, max_idle):
            continue
        GameSnapshot.query.filter_by(room_id=room.id).delete()
        GameHistory.query.filter_by(room_code=room.code).delete()
        if chat is not None:
            chat.clear(room.code)
        closed.append(room.code)
        db.session.delete(room)         # Mitglieder per cascade
    if closed:
        db.session.commit()
        logging.getLogger(__name__).info("Inaktive Tische geschlossen: %s", ", ".join(closed))
    return closed


def start_janitor(app, socketio, chat=None) -> None:
    """Hintergrundaufgabe: regelmaessig ``close_idle_rooms`` im App-Kontext."""
    hours = float(app.config.get("TABLE_MAX_IDLE_HOURS", MAX_IDLE.total_seconds() / 3600))

    def loop():
        log = logging.getLogger(__name__)
        while True:
            socketio.sleep(INTERVAL_SECONDS)
            try:
                with app.app_context():
                    close_idle_rooms(chat, max_idle=timedelta(hours=hours))
                    import time
                    from .ops.sql import SqlErrors, prune_events
                    SqlErrors().prune(time.time())           # Fehler-Log: nach 30 Tagen weg
                    prune_events(time.time())                # anonyme Spiel-Zaehler: nach 400 Tagen weg
            except Exception:  # pragma: no cover - der Hausmeister darf den Prozess nie beenden
                log.exception("Aufraeumen fehlgeschlagen")

    socketio.start_background_task(loop)
