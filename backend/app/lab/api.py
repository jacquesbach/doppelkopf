"""Betreiber-Schnittstelle des Test-Tisches (``/api/admin/lab/...``). Nur Flask, keine Datenbank (siehe ``LabAccess``).

Der Test-Tisch ist ein ganz normaler Raum mit ganz normalem Tisch (gleicher Regelkern, gleiche Tischschicht, gleiche
Bots, gleiche Oberflaeche). Unterschiede: feste Karten, Regeln/Geber/Rundenstand frei waehlbar, keine Bot-Uebernahme, nicht
oeffentlich, keine Statistik. Menschliche Plaetze spielt der Betreiber selbst; je Platz gibt es ein eigenes Sitzungs-Token.
"""
from __future__ import annotations

from functools import wraps
from typing import Protocol

from flask import Blueprint, jsonify, request

from ..community.admin_auth import AdminAuth
from ..rules import RuleViolation
from ..table import NullRunner, TableService
from .presets import preset_list
from .scenario import build_lab_table, parse_scenario


class LabAccess(Protocol):
    def create(self, scenario: dict) -> dict:
        """Raum + vier Mitglieder anlegen: {"code", "seats": [{"seat", "memberId", "name", "isBot", "token"|None}]}."""
    def seats(self, code: str) -> list[dict] | None:
        """Sitze eines Test-Raums (ohne Token) oder ``None``, wenn es keinen Test-Raum dieses Codes gibt."""
    def scenario(self, code: str) -> dict | None: ...
    def set_scenario(self, code: str, scenario: dict) -> None: ...
    def reissue_tokens(self, code: str) -> list[dict] | None: ...
    def set_status(self, code: str, status: str) -> None: ...
    def list(self) -> list[dict]: ...
    def delete(self, code: str) -> bool: ...


def _err(message: str, status: int, code: str = "bad_request"):
    return jsonify({"error": message, "code": code}), status


def create_lab_blueprint(service: TableService, access: LabAccess, publisher, admin: AdminAuth,
                         runner=None) -> Blueprint:
    bp = Blueprint("lab", __name__)
    runner = runner or NullRunner()

    def admin_only(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not admin.enabled:
                return _err("Das Betreiber-Backend ist nicht eingerichtet (ADMIN_PASSWORD fehlt).", 503, "admin_disabled")
            token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not admin.verify(token):
                return _err("Bitte anmelden.", 401, "unauthorized")
            return fn(*args, **kwargs)
        return wrapper

    def body() -> dict:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    def table_seats(created: list[dict]) -> list[dict]:
        return [{"memberId": s["memberId"], "name": s["name"], "isBot": s["isBot"]} for s in created]

    def launch(code: str, scenario, seats: list[dict]) -> int:
        table = build_lab_table(scenario, table_seats(seats))
        version = service.install(code, table)
        access.set_status(code, "playing")
        publisher.game(code)
        publisher.notifier.room_updated(code)
        runner.kick(code)
        return version

    @bp.get("/admin/lab/presets")
    @admin_only
    def presets():
        return jsonify({"presets": preset_list()})

    @bp.get("/admin/lab/tables")
    @admin_only
    def tables():
        return jsonify({"tables": access.list()})

    @bp.post("/admin/lab/tables")
    @admin_only
    def create():
        try:
            scenario = parse_scenario(body().get("scenario"))
        except RuleViolation as exc:
            return _err(exc.message, 400, exc.code)
        created = access.create(scenario.to_dict())
        code = created["code"]
        try:
            version = launch(code, scenario, created["seats"])
        except RuleViolation as exc:
            access.delete(code)
            return _err(exc.message, 400, exc.code)
        return jsonify({"code": code, "version": version, "seats": created["seats"]}), 201

    @bp.post("/admin/lab/tables/<code>/reset")
    @admin_only
    def reset(code):
        code = code.upper()
        seats = access.seats(code)
        if seats is None:
            return _err("Test-Tisch nicht gefunden.", 404, "not_found")
        data = body().get("scenario") or access.scenario(code)
        if isinstance(data, dict):                      # die Besetzung bleibt, wie sie angelegt wurde
            data = dict(data, seats=[{"name": s["name"], "bot": s["isBot"]} for s in seats])
        try:
            scenario = parse_scenario(data)
            version = launch(code, scenario, seats)
        except RuleViolation as exc:
            return _err(exc.message, 400, exc.code)
        access.set_scenario(code, scenario.to_dict())
        return jsonify({"code": code, "version": version})

    @bp.post("/admin/lab/tables/<code>/open")
    @admin_only
    def open_table(code):
        seats = access.reissue_tokens(code.upper())
        if seats is None:
            return _err("Test-Tisch nicht gefunden.", 404, "not_found")
        return jsonify({"code": code.upper(), "seats": seats})

    @bp.delete("/admin/lab/tables/<code>")
    @admin_only
    def delete(code):
        return jsonify({"ok": True}) if access.delete(code.upper()) else _err("Test-Tisch nicht gefunden.", 404, "not_found")

    return bp
