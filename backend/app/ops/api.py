"""HTTP-Schnittstelle der Betreiber-Werkzeuge. Oeffentlich ist nur ``GET /api/site-settings``; alles unter ``/api/admin``
verlangt die Betreiber-Anmeldung (siehe ``community.admin_auth``)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from functools import wraps

from flask import Blueprint, jsonify, request

from ..community.admin_auth import AdminAuth
from . import bot_tuning
from . import system as sysinfo
from .insights import summarize_insights
from .live import NoticeError, clean_notice, live_overview
from .settings import SettingsError, validate_update

DEFAULT_CLOSE_MESSAGE = "Dieser Tisch wurde vom Betreiber beendet."


@dataclass
class OpsDeps:
    admin: AdminAuth
    settings: object            # get() / put(data) / reset()
    live: object                # tables() / close(code) / add_spectator(code)
    errors: object              # list(limit) / count_since(t) / delete(id) / clear()
    stats: object               # logs() / events()
    system: object              # callable -> {"db": {...}, "runtime": {...}}
    notify: object              # callable(code, event, payload)
    clock: object = time.time
    started_at: float = field(default_factory=time.time)
    environ: object = field(default_factory=lambda: os.environ)
    bots: object = field(default_factory=bot_tuning.MemoryBotTuning)     # get() / put(data) / reset()


def _err(message: str, status: int, code: str = "bad_request"):
    return jsonify({"error": message, "code": code}), status


def create_ops_blueprint(deps: OpsDeps) -> Blueprint:
    bp = Blueprint("ops", __name__)

    def admin_only(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not deps.admin.enabled:
                return _err("Das Betreiber-Backend ist nicht eingerichtet (ADMIN_PASSWORD fehlt).", 503, "admin_disabled")
            token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not deps.admin.verify(token):
                return _err("Bitte anmelden.", 401, "unauthorized")
            return fn(*args, **kwargs)
        return wrapper

    def body() -> dict:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    # --- Design-Einstellungen und Banner ---
    @bp.get("/site-settings")
    def public_settings():
        response = jsonify(deps.settings.get())
        response.headers["Cache-Control"] = "no-cache"
        return response

    @bp.get("/admin/site-settings")
    @admin_only
    def admin_settings():
        return jsonify(deps.settings.get())

    @bp.put("/admin/site-settings")
    @admin_only
    def admin_settings_save():
        try:
            data = validate_update(body())
        except SettingsError as exc:
            return _err(str(exc), 400, exc.code)
        return jsonify(deps.settings.put(data))

    @bp.post("/admin/site-settings/reset")
    @admin_only
    def admin_settings_reset():
        return jsonify(deps.settings.reset())

    # --- Bot-Einstellungen ---
    def bots_payload(values: dict) -> dict:
        return {"values": values, **bot_tuning.schema()}

    @bp.get("/admin/bots")
    @admin_only
    def admin_bots():
        return jsonify(bots_payload(deps.bots.get()))

    @bp.put("/admin/bots")
    @admin_only
    def admin_bots_save():
        try:
            data = bot_tuning.validate_update(body(), deps.bots.get())
        except bot_tuning.BotTuningError as exc:
            return _err(str(exc), 400, exc.code)
        saved = deps.bots.put(data)
        bot_tuning.apply(saved)                      # gilt sofort, auch fuer laufende Tische
        return jsonify(bots_payload(saved))

    @bp.post("/admin/bots/reset")
    @admin_only
    def admin_bots_reset():
        saved = deps.bots.reset()
        bot_tuning.apply(saved)
        return jsonify(bots_payload(saved))

    # --- Live-Uebersicht und Eingriffe ---
    @bp.get("/admin/live")
    @admin_only
    def admin_live():
        return jsonify(live_overview(deps.live.tables(), deps.clock()))

    @bp.post("/admin/live/<code>/message")
    @admin_only
    def admin_live_message(code):
        code = code.upper()
        if not any(t["code"] == code for t in deps.live.tables()):
            return _err("Tisch nicht gefunden.", 404, "not_found")
        try:
            message = clean_notice(body().get("message"))
        except NoticeError as exc:
            return _err(str(exc), 400)
        deps.notify(code, "room:notice", {"message": message, "closed": False})
        return jsonify({"ok": True})

    @bp.post("/admin/live/<code>/close")
    @admin_only
    def admin_live_close(code):
        code = code.upper()
        try:
            message = clean_notice(body().get("message"), required=False) or DEFAULT_CLOSE_MESSAGE
        except NoticeError as exc:
            return _err(str(exc), 400)
        if not any(t["code"] == code for t in deps.live.tables()):
            return _err("Tisch nicht gefunden.", 404, "not_found")
        deps.notify(code, "room:notice", {"message": message, "closed": True})   # erst melden, dann schliessen
        deps.live.close(code)
        return jsonify({"ok": True})

    @bp.post("/admin/live/<code>/spectate")
    @admin_only
    def admin_live_spectate(code):
        code = code.upper()
        seat = deps.live.add_spectator(code)
        if seat is None:
            return _err("Tisch nicht gefunden.", 404, "not_found")
        deps.notify(code, "room:refresh", None)         # die Anwesenheit ist fuer alle am Tisch sichtbar
        return jsonify({"code": code, **seat}), 201

    # --- Auswertungen, System, Fehler ---
    @bp.get("/admin/insights")
    @admin_only
    def admin_insights():
        return jsonify(summarize_insights(deps.stats.events(), deps.stats.logs(), deps.clock()))

    @bp.get("/admin/system")
    @admin_only
    def admin_system():
        now = deps.clock()
        extra = deps.system()
        runtime = dict(extra.get("runtime", {}))
        runtime["errors24h"] = deps.errors.count_since(now - 86400)
        return jsonify(sysinfo.snapshot(sysinfo.build_info(deps.environ), deps.started_at, now,
                                        extra.get("db", {}), runtime))

    @bp.get("/admin/errors")
    @admin_only
    def admin_errors():
        return jsonify({"errors": deps.errors.list(100)})

    @bp.delete("/admin/errors")
    @admin_only
    def admin_errors_clear():
        return jsonify({"deleted": deps.errors.clear()})

    @bp.delete("/admin/errors/<int:entry_id>")
    @admin_only
    def admin_error_delete(entry_id):
        return jsonify({"ok": True}) if deps.errors.delete(entry_id) else _err("Eintrag nicht gefunden.", 404, "not_found")

    return bp
