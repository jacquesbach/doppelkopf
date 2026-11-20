"""HTTP-Schnittstelle fuer Einstellungen, Spielstart und Spielzuege.

Abhaengig nur von ``TableService`` sowie den kleinen Schnittstellen ``RoomAccess`` und ``Notifier``
(SQL- bzw. Socket.IO-Umsetzung in ``db_access.py``). Dadurch ist die komplette HTTP-Schicht ohne
Datenbank testbar. Der Sitz eines Handelnden ergibt sich ausschliesslich aus dem Sitzungs-Token.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from flask import Blueprint, jsonify, request

from .rules import (RuleViolation, VersionConflict, normalize_settings, profile_from_settings, rule_schema)
from .table import AccessDenied, NoSuchTable, NullRunner, Outcome, TableService, view_for
from .table.state import TAKEOVER_CHOICES
from .table.chat import ChatLog
from .community.stats import NullStats


@dataclass(frozen=True)
class Auth:
    room_code: str
    member_id: int
    role: str          # 'player' | 'spectator'
    is_host: bool
    room_status: str   # 'waiting' | 'playing' | 'finished'
    name: str = ""     # Anzeigename (fuer den Chat)


class RoomAccess(Protocol):
    def authenticate(self, code: str, token: str) -> Auth | None: ...
    def players(self, code: str) -> list[dict]:
        """Spieler in Sitzreihenfolge: {"memberId", "name", "isBot", "ready"}."""
    def member_ids(self, code: str) -> list[int]: ...
    def settings(self, code: str) -> dict: ...
    def set_settings(self, code: str, settings: dict) -> None: ...
    def set_status(self, code: str, status: str) -> None: ...
    def touch(self, member_id: int) -> None: ...
    def takeover(self, code: str) -> int:
        """Sekunden Inaktivitaet bis ein Bot uebernimmt (0 = nie); Einstellung des Hosts."""
    def set_takeover(self, code: str, seconds: int) -> None: ...


class Notifier(Protocol):
    def game_updated(self, code: str, views: dict[int, dict]) -> None: ...
    def room_updated(self, code: str) -> None: ...
    def chat_message(self, code: str, message: dict) -> None: ...


_BAD_REQUEST_CODES = {"bad_request", "unknown_action", "unknown_option", "invalid_option_value",
                      "invalid_option_combination", "bad_seats"}


def _err(message: str, status: int, **extra):
    return jsonify({"error": message, **extra}), status


def _rule_error(exc: RuleViolation):
    status = 429 if exc.code == "rate_limited" else 400 if exc.code in _BAD_REQUEST_CODES else 409
    return _err(exc.message, status, code=exc.code)


def _duration(summary: dict) -> float | None:
    """Spieldauer in Sekunden aus den Zeitstempeln der Zusammenfassung (``None``, wenn sie fehlen oder unplausibel sind)."""
    from datetime import datetime
    try:
        seconds = (datetime.fromisoformat(summary["finishedAt"]) - datetime.fromisoformat(summary["startedAt"])).total_seconds()
    except (KeyError, TypeError, ValueError):
        return None
    return seconds if seconds >= 0 else None


class Publisher:
    """Veroeffentlicht Spielstaende: persoenliche Sichten an alle Mitglieder, Raumstatus bei Rundenende."""

    def __init__(self, service: TableService, access: RoomAccess, notifier: Notifier, stats=None) -> None:
        self.service, self.access, self.notifier = service, access, notifier
        self.stats = stats or NullStats()

    def game(self, code: str) -> None:
        stored = self.service.load(code)
        if stored is not None:
            self.notifier.game_updated(code, {mid: view_for(stored.table, mid, stored.version)
                                              for mid in self.access.member_ids(code)})

    def summaries(self, code: str, summaries: list[dict]) -> None:
        for s in summaries:
            self.stats.game_finished(code, duration=_duration(s))         # Statistik: Spiele je Tisch, Dauer
            if s.get("roundFinished"):
                self.stats.round_finished(code)
        if any(s["roundFinished"] for s in summaries):
            self.access.set_status(code, "finished")
            self.notifier.room_updated(code)

    def step(self, code: str, outcome) -> None:
        """Callback des ``BotRunner``: ein Botzug wurde gespielt."""
        self.summaries(code, outcome.summaries)
        self.game(code)


def create_game_blueprint(service: TableService, access: RoomAccess, notifier: Notifier,
                          chat: ChatLog | None = None, runner=None,
                          publisher: Publisher | None = None, stats=None) -> Blueprint:
    bp = Blueprint("game", __name__)
    chat = chat or ChatLog()
    runner = runner or NullRunner()
    stats = stats or (publisher.stats if publisher else None) or NullStats()
    publisher = publisher or Publisher(service, access, notifier, stats)

    def auth_for(code: str, data: dict | None = None) -> Auth | None:
        token = request.headers.get("X-Session-Token", "") or str((data or {}).get("token", ""))
        return access.authenticate(code.upper(), token) if token else None

    push = publisher.game
    after_summaries = publisher.summaries

    @bp.get("/rule-schema")
    def schema():
        return jsonify({"options": rule_schema()})

    @bp.post("/rooms/<code>/settings")
    def set_settings(code):
        data = request.get_json(silent=True) or {}
        auth = auth_for(code, data)
        if auth is None:
            return _err("Ungültiger Raum oder ungültige Sitzung.", 403)
        if not auth.is_host:
            return _err("Nur der Host kann die Regeln ändern.", 403)
        if auth.room_status == "playing":
            return _err("Die Regeln können während einer Runde nicht geändert werden.", 409)
        try:
            settings = normalize_settings(data.get("settings"))
        except RuleViolation as exc:
            return _rule_error(exc)
        access.set_settings(auth.room_code, settings)
        notifier.room_updated(auth.room_code)
        return jsonify({"settings": settings, "profileId": profile_from_settings(settings).id.value})

    @bp.post("/rooms/<code>/takeover")
    def set_takeover(code):
        """Host: nach wie vielen Sekunden Inaktivitaet ein Bot uebernimmt (0 = nie). Auch waehrend der Runde."""
        data = request.get_json(silent=True) or {}
        auth = auth_for(code, data)
        if auth is None:
            return _err("Ungültiger Raum oder ungültige Sitzung.", 403)
        if not auth.is_host:
            return _err("Nur der Host kann die Bot-Übernahme einstellen.", 403)
        seconds = data.get("seconds")
        if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds not in TAKEOVER_CHOICES:
            return _err("Ungültige Zeit für die Bot-Übernahme.", 400, code="bad_request")
        access.set_takeover(auth.room_code, seconds)
        try:
            outcome = service.set_takeover(auth.room_code, seconds)   # None: noch kein Spiel (Lobby)
        except RuleViolation as exc:
            return _rule_error(exc)
        notifier.room_updated(auth.room_code)
        if outcome is not None and not outcome.duplicate:
            push(auth.room_code)
            runner.kick(auth.room_code)
        return jsonify({"seconds": seconds})

    @bp.post("/rooms/<code>/start")
    def start(code):
        data = request.get_json(silent=True) or {}
        auth = auth_for(code, data)
        if auth is None:
            return _err("Ungültiger Raum oder ungültige Sitzung.", 403)
        if not auth.is_host:
            return _err("Nur der Host kann das Spiel starten.", 403)
        if auth.room_status == "playing":
            return _err("Das Spiel wurde bereits gestartet.", 409)
        players = access.players(auth.room_code)
        if len(players) != 4:
            return _err("Zum Start werden vier Spieler benötigt.", 409)
        if not all(p["ready"] for p in players):
            return _err("Noch nicht alle Spieler sind bereit.", 409)
        try:
            profile = profile_from_settings(access.settings(auth.room_code))
            version = service.start(auth.room_code, [{"memberId": p["memberId"], "name": p["name"],
                                                      "isBot": p["isBot"]} for p in players], profile,
                                    access.takeover(auth.room_code))
        except RuleViolation as exc:
            return _rule_error(exc)
        access.set_status(auth.room_code, "playing")
        stats.round_started(auth.room_code, sum(not p["isBot"] for p in players), sum(p["isBot"] for p in players))
        push(auth.room_code)
        notifier.room_updated(auth.room_code)
        runner.kick(auth.room_code)
        return jsonify({"version": version, "view": service.view(auth.room_code, auth.member_id),
                        "message": "Die Spielrunde wurde gestartet."}), 201

    @bp.get("/rooms/<code>/game")
    def game(code):
        auth = auth_for(code)
        if auth is None:
            return _err("Ungültiger Raum oder ungültige Sitzung.", 403)
        access.touch(auth.member_id)
        view = service.view(auth.room_code, auth.member_id)
        if view is None:
            return _err("Für diesen Raum läuft noch kein Spiel.", 404)
        runner.kick(auth.room_code)   # nach einem Neustart des Servers weiterspielen lassen
        return jsonify(view)

    def run(code: str, fn):
        data = request.get_json(silent=True)
        data = data if isinstance(data, dict) else {}
        auth = auth_for(code, data)
        if auth is None:
            return _err("Ungültiger Raum oder ungültige Sitzung.", 403)
        if auth.role != "player":
            return _err("Zuschauer können nicht mitspielen.", 403)
        try:
            outcome = fn(auth, data)
        except AccessDenied as exc:
            return _err(str(exc), 403)
        except NoSuchTable as exc:
            return _err(str(exc), 404)
        except VersionConflict as exc:
            return _err("Der Spielstand hat sich geändert. Bitte neu laden.", 409,
                        code="version_conflict", version=exc.actual)
        except RuleViolation as exc:
            return _rule_error(exc)
        if not outcome.duplicate:
            stats.activity(auth.room_code)
            after_summaries(auth.room_code, outcome.summaries)
            push(auth.room_code)
            runner.kick(auth.room_code)
        return jsonify({"version": outcome.version, "duplicate": outcome.duplicate,
                        "view": service.view(auth.room_code, auth.member_id)})

    @bp.post("/rooms/<code>/action")
    def action(code):
        return run(code, lambda auth, data: service.act(auth.room_code, auth.member_id, data))

    @bp.post("/rooms/<code>/next")
    def next_game(code):
        return run(code, lambda auth, data: service.next_game(auth.room_code, auth.member_id))

    @bp.post("/rooms/<code>/continue")
    def continue_game(code):
        """"Naechster Stich" im Spiel gegen Bots."""
        return run(code, lambda auth, data: service.release(auth.room_code, auth.member_id))

    @bp.post("/rooms/<code>/stay")
    def stay(code):
        """"Weiterspielen": Countdown der Bot-Uebernahme beenden; optional (`remember`) dauerhaft ablehnen/zulassen."""
        return run(code, lambda auth, data: service.stay(auth.room_code, auth.member_id, data.get("remember")))

    @bp.post("/rooms/<code>/away")
    def away(code):
        """Platz verlassen, waehrend die Runde laeuft: ein Bot spielt fuer dich weiter."""
        return run(code, lambda auth, data: service.set_away(auth.room_code, auth.member_id, True)
                   or Outcome(0, duplicate=True))

    @bp.post("/rooms/<code>/back")
    def back(code):
        """Wieder am Tisch: der Bot gibt den Platz zurueck."""
        return run(code, lambda auth, data: service.set_away(auth.room_code, auth.member_id, False)
                   or Outcome(0, duplicate=True))

    @bp.get("/rooms/<code>/history")
    def history(code):
        auth = auth_for(code)
        if auth is None:
            return _err("Ungültiger Raum oder ungültige Sitzung.", 403)
        return jsonify({"games": service.store.history(auth.room_code)})

    @bp.get("/rooms/<code>/chat")
    def chat_history(code):
        auth = auth_for(code)
        if auth is None:
            return _err("Ungültiger Raum oder ungültige Sitzung.", 403)
        return jsonify({"messages": chat.history(auth.room_code)})

    @bp.post("/rooms/<code>/chat")
    def chat_post(code):
        data = request.get_json(silent=True)
        data = data if isinstance(data, dict) else {}
        auth = auth_for(code, data)
        if auth is None:
            return _err("Ungültiger Raum oder ungültige Sitzung.", 403)
        try:
            message = chat.post(auth.room_code, auth.member_id, auth.name, data.get("text"))
        except RuleViolation as exc:
            return _rule_error(exc)
        notifier.chat_message(auth.room_code, message)
        return jsonify({"message": message}), 201

    return bp
