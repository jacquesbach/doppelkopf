"""HTTP-Schnittstelle: oeffentliche Routen (Vorschlaege, Captcha, Sprueche) und Betreiber-Routen (``/admin/...``)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from functools import wraps

from flask import Blueprint, current_app, jsonify, request

from .admin_auth import AdminAuth, TooManyAttempts
from .captcha import CaptchaGuard
from .phrases import PhraseService
from .ratelimit import RateLimiter
from .stats import StatsRecorder, summarize
from .suggestions import SuggestionService
from .tables import TableOverview, overview
from .text import ValidationError

HOUR = 3600
SUBMIT_PER_IP = 5          # Vorschlaege je Stunde und Adresse
SUBMIT_PER_CLIENT = 3      # ... und je Browser-Kennung
VOTES_PER_IP = 120         # Daumen-Klicks je Stunde und Adresse
_CLIENT_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@dataclass
class CommunityDeps:
    suggestions: SuggestionService
    phrases: PhraseService
    stats: StatsRecorder
    tables: TableOverview
    admin: AdminAuth
    captcha: CaptchaGuard
    secret: str
    limiter: RateLimiter = field(default_factory=RateLimiter)
    clock: callable = time.time
    trust_proxy: bool = False       # hinter nginx: letzte Adresse aus X-Forwarded-For


def _err(message: str, status: int, code: str = "bad_request"):
    return jsonify({"error": message, "code": code}), status


def create_community_blueprint(deps: CommunityDeps) -> Blueprint:
    bp = Blueprint("community", __name__)

    def client_ip() -> str:
        if deps.trust_proxy:
            forwarded = request.headers.get("X-Forwarded-For", "")
            if forwarded:
                return forwarded.split(",")[-1].strip()[:64]
        return request.remote_addr or "unknown"

    def voter_key() -> str | None:
        """Pseudonyme Nutzerkennung: Hash der zufaelligen Browser-Kennung (die Kennung selbst wird nie gespeichert)."""
        raw = request.headers.get("X-Client-Id", "")
        if not _CLIENT_ID.match(raw):
            return None
        import hashlib, hmac
        return hmac.new(deps.secret.encode(), f"voter:{raw}".encode(), hashlib.sha256).hexdigest()[:32]

    def body() -> dict:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}

    # --- oeffentlich ---
    @bp.get("/captcha")
    def captcha():
        if not deps.limiter.allow(f"captcha:{client_ip()}", 60, HOUR):
            return _err("Zu viele Anfragen. Bitte später erneut versuchen.", 429, "rate_limited")
        return jsonify(deps.captcha.challenge())

    @bp.get("/phrases")
    def phrases():
        return jsonify({"phrases": deps.phrases.list()})

    @bp.get("/suggestions")
    def suggestions():
        return jsonify({"suggestions": deps.suggestions.public_list(voter_key())})

    @bp.post("/suggestions")
    def submit():
        data = body()
        if data.get("website"):                            # Honigtopf: das Feld sieht nur ein Bot
            return _err("Eingabe abgelehnt.", 400, "rejected")
        ip, voter = client_ip(), voter_key()
        if not deps.limiter.allow(f"submit-ip:{ip}", SUBMIT_PER_IP, HOUR) or (
                voter and not deps.limiter.allow(f"submit-client:{voter}", SUBMIT_PER_CLIENT, HOUR)):
            return _err("Du hast gerade schon mehrere Vorschläge geschickt. Bitte versuche es später wieder.", 429, "rate_limited")
        try:
            title, description = deps.suggestions.validate(data.get("title"), data.get("description"))
        except ValidationError as exc:
            return _err(str(exc), 400, exc.code)
        result = deps.captcha.verify(data.get("captchaToken"), data.get("captchaAnswer"))   # erst nach der Textpruefung
        if result != "ok":
            message = {"expired": "Das Captcha ist abgelaufen. Bitte neu laden.", "used": "Dieses Captcha wurde schon benutzt."}.get(
                result, "Das Captcha stimmt nicht. Bitte versuche es mit der neuen Grafik noch einmal.")
            return _err(message, 400, "captcha_" + result)
        try:
            item = deps.suggestions.submit(title, description)
        except ValidationError as exc:
            return _err(str(exc), 409 if exc.code == "duplicate" else 400, exc.code)
        return jsonify({"suggestion": item}), 201

    @bp.post("/suggestions/<int:suggestion_id>/vote")
    def vote(suggestion_id):
        voter = voter_key()
        if voter is None:
            return _err("Kennung fehlt (X-Client-Id).", 400, "client_id_required")
        if not deps.limiter.allow(f"vote-ip:{client_ip()}", VOTES_PER_IP, HOUR):
            return _err("Zu viele Abstimmungen. Bitte später erneut versuchen.", 429, "rate_limited")
        result = deps.suggestions.vote(suggestion_id, voter)
        if result is None:
            return _err("Vorschlag nicht gefunden.", 404, "not_found")
        return jsonify(result)

    # --- Betreiber ---
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

    @bp.get("/admin/status")
    def admin_status():
        return jsonify({"enabled": deps.admin.enabled})

    @bp.post("/admin/login")
    def admin_login():
        if not deps.admin.enabled:
            return _err("Das Betreiber-Backend ist nicht eingerichtet (ADMIN_PASSWORD fehlt).", 503, "admin_disabled")
        try:
            token = deps.admin.login(body().get("password"), client_ip())
        except TooManyAttempts:
            return _err("Zu viele Versuche. Bitte warte einige Minuten.", 429, "rate_limited")
        if token is None:
            return _err("Passwort falsch.", 401, "unauthorized")
        return jsonify({"token": token, "expiresIn": deps.admin.ttl})

    @bp.post("/admin/logout")
    @admin_only
    def admin_logout():
        """Diese Sitzung serverseitig beenden (das Token ist danach wertlos)."""
        deps.admin.logout(request.headers.get("Authorization", "").removeprefix("Bearer ").strip())
        return jsonify({"ok": True})

    @bp.post("/admin/logout-all")
    @admin_only
    def admin_logout_all():
        """Alle Betreiber-Sitzungen beenden (auch diese)."""
        return jsonify({"ended": deps.admin.logout_all()})

    @bp.get("/admin/tables")
    @admin_only
    def admin_tables():
        return jsonify(overview(deps.tables.tables(), deps.clock()))

    @bp.get("/admin/stats")
    @admin_only
    def admin_stats():
        return jsonify(summarize(deps.stats.logs(), deps.clock()))

    @bp.get("/admin/phrases")
    @admin_only
    def admin_phrases():
        return jsonify({"phrases": deps.phrases.list()})

    @bp.post("/admin/phrases")
    @admin_only
    def admin_phrase_add():
        try:
            return jsonify({"phrase": deps.phrases.add(body().get("text"))}), 201
        except ValidationError as exc:
            return _err(str(exc), 409 if exc.code == "duplicate" else 400, exc.code)

    @bp.put("/admin/phrases/<int:phrase_id>")
    @admin_only
    def admin_phrase_update(phrase_id):
        try:
            found = deps.phrases.update(phrase_id, body().get("text"))
        except ValidationError as exc:
            return _err(str(exc), 409 if exc.code == "duplicate" else 400, exc.code)
        return jsonify({"ok": True}) if found else _err("Spruch nicht gefunden.", 404, "not_found")

    @bp.delete("/admin/phrases/<int:phrase_id>")
    @admin_only
    def admin_phrase_delete(phrase_id):
        return jsonify({"ok": True}) if deps.phrases.delete(phrase_id) else _err("Spruch nicht gefunden.", 404, "not_found")

    @bp.post("/admin/phrases/<int:phrase_id>/move")
    @admin_only
    def admin_phrase_move(phrase_id):
        try:
            found = deps.phrases.move(phrase_id, body().get("direction"))
        except ValidationError as exc:
            return _err(str(exc), 400, exc.code)
        return jsonify({"phrases": deps.phrases.list()}) if found else _err("Spruch nicht gefunden.", 404, "not_found")

    @bp.get("/admin/suggestions")
    @admin_only
    def admin_suggestions():
        return jsonify({"suggestions": deps.suggestions.admin_list()})

    @bp.post("/admin/suggestions/<int:suggestion_id>/status")
    @admin_only
    def admin_suggestion_status(suggestion_id):
        try:
            found = deps.suggestions.moderate(suggestion_id, body().get("status"))
        except ValidationError as exc:
            return _err(str(exc), 400, exc.code)
        return jsonify({"ok": True}) if found else _err("Vorschlag nicht gefunden.", 404, "not_found")

    @bp.put("/admin/suggestions/<int:suggestion_id>")
    @admin_only
    def admin_suggestion_edit(suggestion_id):
        data = body()
        try:
            found = deps.suggestions.edit(suggestion_id, data.get("title"), data.get("description"))
        except ValidationError as exc:
            return _err(str(exc), 400, exc.code)
        return jsonify({"ok": True}) if found else _err("Vorschlag nicht gefunden.", 404, "not_found")

    @bp.delete("/admin/suggestions/<int:suggestion_id>")
    @admin_only
    def admin_suggestion_delete(suggestion_id):
        return jsonify({"ok": True}) if deps.suggestions.delete(suggestion_id) else _err("Vorschlag nicht gefunden.", 404, "not_found")

    return bp
