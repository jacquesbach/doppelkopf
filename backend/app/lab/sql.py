"""Datenbankanbindung des Test-Tisches (duenn; Logik steht in ``scenario``/``api``)."""
from __future__ import annotations

import json

from .. import db
from ..models import GameHistory, GameSnapshot, Member, Room
from ..services import new_code, new_token, token_digest

SEAT_ORDER = (Member.joined_at, Member.id)


class SqlLabAccess:
    def __init__(self, chat=None) -> None:
        self.chat = chat

    @staticmethod
    def _lab_room(code: str) -> Room | None:
        room = Room.query.filter_by(code=code).first()
        return room if room is not None and room.lab_spec_json else None

    @staticmethod
    def _members(room: Room) -> list[Member]:
        return sorted((m for m in room.members if m.role == "player"), key=lambda m: (m.joined_at, m.id))

    def create(self, scenario: dict) -> dict:
        code = new_code()
        while Room.query.filter_by(code=code).first() is not None:
            code = new_code()
        room = Room(code=code, settings_json=json.dumps(scenario["settings"]), is_public=False, status="playing",
                    takeover_seconds=0, lab_spec_json=json.dumps(scenario, ensure_ascii=False))
        db.session.add(room)
        db.session.flush()
        seats, host = [], None
        for i, spec in enumerate(scenario["seats"]):
            token = new_token()
            member = Member(room_id=room.id, name=spec["name"], role="player", ready=True, is_bot=bool(spec["bot"]),
                            session_token_hash=token_digest(token))
            db.session.add(member)
            db.session.flush()
            if host is None and not spec["bot"]:
                host = member
            seats.append({"seat": i, "memberId": member.id, "name": member.name, "isBot": member.is_bot,
                          "token": None if member.is_bot else token})
        room.host_member_id = host.id
        db.session.commit()
        return {"code": code, "seats": seats}

    def seats(self, code: str) -> list[dict] | None:
        room = self._lab_room(code)
        if room is None:
            return None
        return [{"seat": i, "memberId": m.id, "name": m.name, "isBot": m.is_bot}
                for i, m in enumerate(self._members(room))]

    def scenario(self, code: str) -> dict | None:
        room = self._lab_room(code)
        return json.loads(room.lab_spec_json) if room else None

    def set_scenario(self, code: str, scenario: dict) -> None:
        room = self._lab_room(code)
        if room is not None:
            room.lab_spec_json = json.dumps(scenario, ensure_ascii=False)
            room.settings_json = json.dumps(scenario["settings"])
            db.session.commit()

    def reissue_tokens(self, code: str) -> list[dict] | None:
        room = self._lab_room(code)
        if room is None:
            return None
        out = []
        for i, m in enumerate(self._members(room)):
            token = None
            if not m.is_bot:
                token = new_token()
                m.session_token_hash = token_digest(token)
            out.append({"seat": i, "memberId": m.id, "name": m.name, "isBot": m.is_bot, "token": token})
        db.session.commit()
        return out

    def set_status(self, code: str, status: str) -> None:
        room = Room.query.filter_by(code=code).first()
        if room is not None:
            room.status = status
            db.session.commit()

    def list(self) -> list[dict]:
        rows = []
        for room in Room.query.filter(Room.lab_spec_json.isnot(None)).order_by(Room.created_at.desc()).all():
            spec = json.loads(room.lab_spec_json)
            rows.append({"code": room.code, "title": spec.get("title", ""), "createdAt": room.created_at.isoformat(),
                         "seats": [{"name": m.name, "isBot": m.is_bot} for m in self._members(room)]})
        return rows

    def delete(self, code: str) -> bool:
        room = self._lab_room(code)
        if room is None:
            return False
        GameSnapshot.query.filter_by(room_id=room.id).delete()
        GameHistory.query.filter_by(room_code=room.code).delete()
        if self.chat is not None:
            self.chat.clear(room.code)
        db.session.delete(room)
        db.session.commit()
        return True
