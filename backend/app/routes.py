"""Raum-Routen (Anlegen, Beitreten, Bereitschaft, Bots). Spielstart/-zuege: siehe ``game_api.py``."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash
from . import db, socketio
from .models import GameSnapshot, Member, Room
from .rules import RuleViolation
from .services import create_room, join_room, new_token, public_room, token_digest

api = Blueprint("api", __name__)


def error(message, status=400):
    return jsonify({"error": message}), status


def member_from_token(token):
    if not token:
        return None
    member = Member.query.filter_by(session_token_hash=token_digest(token)).first()
    return None if member is None or member.is_bot else member   # Bots handeln nur serverseitig


def broadcast_room(room):
    socketio.emit("room:state", public_room(room), to=room.code)


@api.get("/health")
def health():
    return jsonify({"status": "ok", "service": "doppelkopf-multiplayer"})


@api.post("/rooms")
def create_room_route():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:32]
    password = str(data.get("password", "")) or None
    if not name:
        return error("Bitte gib einen Spielernamen ein.")
    if password and len(password) < 4:
        return error("Das Passwort muss mindestens vier Zeichen lang sein.")
    try:
        room, member, token = create_room(name, password, data.get("settings"), bool(data.get("public", False)))
    except RuleViolation as exc:
        return error(exc.message, 400)
    from flask import current_app
    stats = current_app.extensions.get("stats")
    if stats is not None:
        stats.table_created(room.code)           # Statistik: ein Tisch mehr
    return jsonify({"room": public_room(room, member.id), "token": token, "memberId": member.id}), 201


PUBLIC_ACTIVE_SECONDS = 90      # nur Tische anzeigen, an denen sich jemand in letzter Zeit gemeldet hat
PUBLIC_LIST_LIMIT = 30


@api.get("/rooms/public")
def public_rooms():
    """Tische, die Mitspieler suchen: oeffentlich, wartend, mindestens ein freier Platz, Besitzer aktiv."""
    now = datetime.now(timezone.utc)
    items = []
    for room in Room.query.filter_by(is_public=True, status="waiting").order_by(Room.created_at.desc()).all():
        players = [m for m in room.members if m.role == "player"]
        if len(players) >= 4:
            continue
        humans = [m for m in room.members if not m.is_bot]
        if not any((now - m.last_seen_at.replace(tzinfo=timezone.utc)).total_seconds() < PUBLIC_ACTIVE_SECONDS
                   for m in humans):
            continue
        host = next((m for m in room.members if m.id == room.host_member_id), None)
        pub = public_room(room)
        items.append({"code": room.code, "host": host.name if host else "", "players": [m.name for m in players],
                      "playerCount": len(players), "hasPassword": pub["hasPassword"], "settings": pub["settings"],
                      "isOfficialDdv": pub["isOfficialDdv"], "createdAt": room.created_at.isoformat()})
        if len(items) >= PUBLIC_LIST_LIMIT:
            break
    return jsonify({"rooms": items})


@api.post("/rooms/<code>/visibility")
def set_visibility(code):
    """Host schaltet den Tisch oeffentlich (Tischliste) oder privat (nur per Link)."""
    data = request.get_json(silent=True) or {}
    token = request.headers.get("X-Session-Token", "") or str(data.get("token", ""))
    member = member_from_token(token)
    room = Room.query.filter_by(code=code.upper()).first()
    if room is None or member is None or member.room_id != room.id:
        return error("Ungültiger Raum oder ungültige Sitzung.", 403)
    if room.host_member_id != member.id:
        return error("Nur der Host kann die Sichtbarkeit ändern.", 403)
    room.is_public = bool(data.get("public", False))
    db.session.commit()
    broadcast_room(room)
    return jsonify({"room": public_room(room, member.id)})


@api.post("/rooms/<code>/join")
def join_room_route(code):
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:32]
    role = str(data.get("role", "player"))
    if not name:
        return error("Bitte gib einen Spielernamen ein.")
    try:
        room, member, token = join_room(code, name, role, data.get("password"))
    except PermissionError as exc:
        return error(str(exc), 403)
    except ValueError as exc:
        return error(str(exc), 404 if "nicht gefunden" in str(exc) else 409)
    broadcast_room(room)
    return jsonify({"room": public_room(room, member.id), "token": token, "memberId": member.id}), 201


@api.get("/rooms/<code>")
def get_room(code):
    room = Room.query.filter_by(code=code.upper()).first()
    if room is None:
        return error("Raum nicht gefunden.", 404)
    token = request.headers.get("X-Session-Token", "")
    member = member_from_token(token)
    if member and member.room_id == room.id:
        from .models import utcnow
        member.connected = True
        member.last_seen_at = utcnow()
        db.session.commit()
    return jsonify({"room": public_room(room, member.id if member and member.room_id == room.id else None)})


@api.post("/rooms/<code>/ready")
def set_ready(code):
    data = request.get_json(silent=True) or {}
    member = member_from_token(data.get("token", ""))
    room = Room.query.filter_by(code=code.upper()).first()
    if room is None or member is None or member.room_id != room.id:
        return error("Ungültiger Raum oder ungültige Sitzung.", 403)
    if member.role != "player":
        return error("Zuschauer können nicht bereit sein.", 403)
    member.ready = bool(data.get("ready", True))
    db.session.commit()
    broadcast_room(room)
    return jsonify({"room": public_room(room, member.id)})


@api.post("/rooms/<code>/bots")
def fill_with_bots(code):
    data = request.get_json(silent=True) or {}
    member = member_from_token(data.get("token", ""))
    room = Room.query.filter_by(code=code.upper()).first()
    if room is None or member is None or member.room_id != room.id:
        return error("Ungültiger Raum oder ungültige Sitzung.", 403)
    if room.host_member_id != member.id:
        return error("Nur der Host kann Bots hinzufügen.", 403)
    if room.status != "waiting":
        return error("Das Spiel wurde bereits gestartet.", 409)
    count = sum(m.role == "player" for m in room.members)
    while count < 4:
        index = count + 1
        room.members.append(Member(name=f"Bot {index}", role="player", ready=True, is_bot=True,
                                   session_token_hash=token_digest(new_token())))  # Token wird verworfen
        count += 1
    db.session.commit()
    broadcast_room(room)
    return jsonify({"room": public_room(room, member.id)})


@api.post("/rooms/<code>/leave")
def leave_room(code):
    """Tisch verlassen. Waehrend einer laufenden Runde nicht moeglich (der Sitz gehoert zum Spiel)."""
    data = request.get_json(silent=True) or {}
    token = request.headers.get("X-Session-Token", "") or str(data.get("token", ""))
    room = Room.query.filter_by(code=code.upper()).first()
    member = member_from_token(token)
    if room is None or member is None or member.room_id != room.id:
        return error("Ungültiger Raum oder ungültige Sitzung.", 403)
    if room.status == "playing" and member.role == "player":
        return error("Während einer laufenden Runde kann man den Tisch nicht verlassen.", 409)
    was_host = room.host_member_id == member.id
    room.members.remove(member)
    db.session.delete(member)
    humans = [m for m in room.members if not m.is_bot]
    if not humans:  # leerer Tisch (nur Bots uebrig) wird geschlossen
        GameSnapshot.query.filter_by(room_id=room.id).delete()
        db.session.delete(room)
        db.session.commit()
        return jsonify({"left": True, "closed": True})
    if was_host:
        players = sorted((m for m in humans if m.role == "player"), key=lambda m: (m.joined_at, m.id))
        heir = players[0] if players else sorted(humans, key=lambda m: (m.joined_at, m.id))[0]
        room.host_member_id = heir.id
        heir.ready = True
    db.session.commit()
    broadcast_room(room)
    return jsonify({"left": True, "closed": False})


@api.post("/rooms/<code>/rejoin")
def rejoin_room(code):
    """Platz zurueckholen (z. B. anderes Geraet, geloeschter Browserspeicher): Name + ggf. Passwort genuegen.

    Nur fuer Spieler, die gerade nicht verbunden sind. Das alte Token wird dadurch ungueltig.
    """
    data = request.get_json(silent=True) or {}
    room = Room.query.filter_by(code=code.upper()).first()
    if room is None:
        return error("Raum nicht gefunden.", 404)
    if room.password_hash and not check_password_hash(room.password_hash, str(data.get("password", ""))):
        return error("Das Raum-Passwort ist nicht korrekt.", 403)
    name = str(data.get("name", "")).strip().lower()
    member = next((m for m in room.members
                   if m.role == "player" and not m.is_bot and m.name.strip().lower() == name), None)
    if member is None:
        return error("An diesem Tisch sitzt kein Spieler mit diesem Namen.", 404)
    last = member.last_seen_at.replace(tzinfo=timezone.utc)
    if member.connected and (datetime.now(timezone.utc) - last).total_seconds() < 20:
        return error("Dieser Spieler ist gerade verbunden.", 409)
    token = new_token()
    member.session_token_hash = token_digest(token)
    db.session.commit()
    return jsonify({"room": public_room(room, member.id), "token": token, "memberId": member.id})
