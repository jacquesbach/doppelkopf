"""Room helpers. Tokens are only returned once and stored as SHA-256 digests."""
import hashlib
import json
import secrets
from datetime import datetime, timezone
from werkzeug.security import check_password_hash, generate_password_hash
from . import db
from .models import Member, Room
from .rules import normalize_settings, profile_from_settings

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def new_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))


def create_room(name: str, password: str | None = None, settings: dict | None = None, is_public: bool = False):
    """``settings`` = Deck + Regeloptionen (siehe ``rules.options``); ungueltige Werte werfen ``RuleViolation``."""
    normalized = normalize_settings(settings)
    code = new_code()
    while Room.query.filter_by(code=code).first() is not None:
        code = new_code()
    room = Room(code=code, password_hash=generate_password_hash(password) if password else None,
                settings_json=json.dumps(normalized), is_public=bool(is_public))
    token = new_token()
    host = Member(name=name, role="player", ready=True, session_token_hash=token_digest(token))
    room.members.append(host)
    db.session.add(room)
    db.session.flush()
    host.room_id = room.id
    db.session.add(host)
    db.session.flush()
    room.host_member_id = host.id
    db.session.commit()
    return room, host, token


def join_room(code: str, name: str, role: str, password: str | None = None):
    room = Room.query.filter_by(code=code.upper()).first()
    if room is None:
        raise ValueError("Raum nicht gefunden.")
    if room.password_hash and not check_password_hash(room.password_hash, password or ""):
        raise PermissionError("Das Raum-Passwort ist nicht korrekt.")
    if room.status != "waiting" and role != "spectator":
        raise ValueError("Dieses Spiel läuft bereits. Du kannst als Zuschauer beitreten.")
    if role not in {"player", "spectator"}:
        raise ValueError("Unbekannte Beitrittsart.")
    if role == "player" and sum(m.role == "player" for m in room.members) >= 4:
        raise ValueError("Der Spieltisch ist bereits voll. Du kannst als Zuschauer beitreten.")
    token = new_token()
    member = Member(room=room, name=name, role=role, ready=(role == "spectator"), session_token_hash=token_digest(token))
    db.session.add(member)
    db.session.commit()
    return room, member, token


def room_settings(room: Room) -> dict:
    return normalize_settings(json.loads(room.settings_json or "{}"))


def public_room(room: Room, viewer_id: int | None = None):
    members = sorted(room.members, key=lambda m: (m.role != "player", m.joined_at, m.id))
    now = datetime.now(timezone.utc)
    settings = room_settings(room)
    profile = profile_from_settings(settings)
    return {
        "settings": settings,
        "profileId": profile.id.value,
        "isOfficialDdv": profile.is_official_ddv,
        "code": room.code,
        "status": room.status,
        "hasPassword": bool(room.password_hash),
        "isPublic": bool(room.is_public),
        "botTakeover": room.takeover_seconds,
        "players": [
            {"id": m.id, "name": m.name, "role": m.role, "ready": m.ready,
             "isHost": m.id == room.host_member_id,
             "connected": m.connected and (now - m.last_seen_at.replace(tzinfo=timezone.utc)).total_seconds() < 20,
             "isBot": m.is_bot, "isMe": m.id == viewer_id}
            for m in members
        ],
        "playerCount": sum(m.role == "player" for m in members),
        "spectatorCount": sum(m.role == "spectator" for m in members),
        "canStart": room.status == "waiting" and sum(m.role == "player" for m in members) == 4,
    }
