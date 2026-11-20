"""SQL- und Socket.IO-Umsetzung der Schnittstellen aus ``table`` und ``game_api``.

Bewusst duenn: keinerlei Spiellogik. Die Logik ist in ``app.rules``/``app.table`` und dort ohne
Datenbank getestet; diese Datei verbindet sie nur mit SQLAlchemy und Socket.IO.
"""
from __future__ import annotations

import json
from datetime import datetime

from . import db, socketio
from .game_api import Auth
from .models import GameHistory, GameSnapshot, Member, Room, utcnow
from .rules import VersionConflict
from .services import public_room, token_digest
from .table import Stored, TableState

SCHEMA_VERSION = 2


class SqlStore:
    """Tisch pro Raum in ``GameSnapshot``; optimistische Sperre ueber die Spalte ``version``."""

    def _room(self, code: str) -> Room | None:
        return Room.query.filter_by(code=code).first()

    def _snapshot(self, room: Room | None) -> GameSnapshot | None:
        return GameSnapshot.query.filter_by(room_id=room.id).first() if room else None

    def load(self, code: str) -> Stored | None:
        snap = self._snapshot(self._room(code))
        if snap is None or snap.schema_version != SCHEMA_VERSION:
            return None  # Altformat (schema_version 1) wird ignoriert
        return Stored(TableState.from_dict(json.loads(snap.state_json)), snap.version)

    def create(self, code: str, table: TableState) -> int:
        room = self._room(code)
        snap = self._snapshot(room)
        data = json.dumps(table.to_dict(), ensure_ascii=False)
        if snap is None:
            snap = GameSnapshot(room_id=room.id, state_json=data, version=1, schema_version=SCHEMA_VERSION)
            db.session.add(snap)
        else:
            snap.state_json, snap.schema_version, snap.version = data, SCHEMA_VERSION, snap.version + 1
        db.session.commit()
        return snap.version

    def save(self, code: str, table: TableState, expected_version: int, summaries: list[dict]) -> int:
        room = self._room(code)
        snap = self._snapshot(room)
        data = json.dumps(table.to_dict(), ensure_ascii=False)
        changed = GameSnapshot.query.filter_by(id=snap.id, version=expected_version).update(
            {"state_json": data, "version": expected_version + 1}, synchronize_session=False)
        if changed != 1:  # jemand war schneller (z. B. anderer Prozess)
            db.session.rollback()
            current = db.session.get(GameSnapshot, snap.id)
            raise VersionConflict(expected_version, current.version if current else -1)
        for s in summaries:
            db.session.add(GameHistory(room_code=code, started_at=datetime.fromisoformat(s["startedAt"]),
                                       finished_at=datetime.fromisoformat(s["finishedAt"]),
                                       result_json=json.dumps(s, ensure_ascii=False)))
        db.session.commit()
        return expected_version + 1

    def history(self, code: str) -> list[dict]:
        rows = GameHistory.query.filter_by(room_code=code).order_by(GameHistory.id).all()
        return [json.loads(r.result_json) for r in rows if r.result_json]


class SqlRoomAccess:
    def _room(self, code: str) -> Room | None:
        return Room.query.filter_by(code=code).first()

    def authenticate(self, code: str, token: str) -> Auth | None:
        room = self._room(code)
        member = Member.query.filter_by(session_token_hash=token_digest(token)).first() if token else None
        # Bots authentifizieren sich nie ueber HTTP: sie handeln ausschliesslich serverseitig.
        if room is None or member is None or member.room_id != room.id or member.is_bot:
            return None
        return Auth(room.code, member.id, member.role, room.host_member_id == member.id, room.status, member.name)

    def players(self, code: str) -> list[dict]:
        room = self._room(code)
        players = sorted((m for m in room.members if m.role == "player"), key=lambda m: (m.joined_at, m.id))
        return [{"memberId": m.id, "name": m.name, "isBot": m.is_bot, "ready": m.ready} for m in players]

    def member_ids(self, code: str) -> list[int]:
        return [m.id for m in self._room(code).members if not m.is_bot]

    def settings(self, code: str) -> dict:
        return json.loads(self._room(code).settings_json or "{}")

    def set_settings(self, code: str, settings: dict) -> None:
        self._room(code).settings_json = json.dumps(settings)
        db.session.commit()

    def set_status(self, code: str, status: str) -> None:
        self._room(code).status = status
        db.session.commit()

    def takeover(self, code: str) -> int:
        return self._room(code).takeover_seconds

    def set_takeover(self, code: str, seconds: int) -> None:
        self._room(code).takeover_seconds = seconds
        db.session.commit()

    def touch(self, member_id: int) -> None:
        member = db.session.get(Member, member_id)
        if member:
            member.connected, member.last_seen_at = True, utcnow()
            db.session.commit()


class SocketNotifier:
    """Jedes Mitglied bekommt nur seine eigene Sicht (Socket-Raum ``member:<id>``)."""

    def game_updated(self, code: str, views: dict[int, dict]) -> None:
        for member_id, view in views.items():
            socketio.emit("game:state", view, to=f"member:{member_id}")

    def chat_message(self, code: str, message: dict) -> None:
        socketio.emit("chat:message", message, to=code)

    def room_updated(self, code: str) -> None:
        room = Room.query.filter_by(code=code).first()
        if room:
            socketio.emit("room:state", public_room(room), to=room.code)
