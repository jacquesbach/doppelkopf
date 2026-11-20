"""Flask application factory for the Doppelkopf multiplayer backend."""
import os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
socketio = SocketIO(async_mode="threading")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY="dev-only-change-me",
        SQLALCHEMY_DATABASE_URI="sqlite:///doppelkopf.sqlite3",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        CORS_ORIGINS=["http://localhost:5173"],
    )
    if test_config:
        app.config.update(test_config)
    if os.environ.get("APP_ENV") == "production" and app.config["SECRET_KEY"] == "dev-only-change-me":
        raise RuntimeError("In Produktion muss SECRET_KEY gesetzt sein.")

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    # Socket.IO prueft den Origin-Header strikt. Hinter einem Reverse-Proxy auf anderem Host/Port als erwartet wuerde
    # die Verbindung sonst still scheitern (Tisch zeigt dauerhaft "Offline"). "*" ist unkritisch: die Sitzung haengt am
    # Token im Ereignis, nicht an Cookies.
    origins = app.config["CORS_ORIGINS"]
    socketio.init_app(app, cors_allowed_origins="*" if "*" in origins else origins)

    from . import models  # noqa: F401
    from .db_access import SocketNotifier, SqlRoomAccess, SqlStore
    from .game_api import Publisher, create_game_blueprint
    from .routes import api
    from .table import BotRunner, TableService
    import logging
    logging.basicConfig(level=logging.INFO)   # Docker-Logs: Bot-Schleife sichtbar machen
    paced = app.config.get("PACED_BOTS", True)
    service = TableService(SqlStore(), paced=paced)
    app.extensions["table_service"] = service
    access, notifier = SqlRoomAccess(), SocketNotifier()
    from .community.admin_auth import AdminAuth, MIN_PASSWORD_PRODUCTION
    from .community.api import CommunityDeps, create_community_blueprint
    from .community.captcha import CaptchaGuard
    from .community.phrases import PhraseService
    from .community.sql import SqlPhrases, SqlStats, SqlSuggestions, SqlTableOverview
    from .community.suggestions import SuggestionService
    admin_password = app.config.get("ADMIN_PASSWORD") or ""
    if os.environ.get("APP_ENV") == "production" and admin_password and len(admin_password) < MIN_PASSWORD_PRODUCTION:
        raise RuntimeError(f"ADMIN_PASSWORD muss in Produktion mindestens {MIN_PASSWORD_PRODUCTION} Zeichen lang sein.")
    stats = SqlStats()
    app.extensions["stats"] = stats
    publisher = Publisher(service, access, notifier, stats)
    from .table.chat import ChatLog
    chat = ChatLog()
    app.extensions["chat_log"] = chat

    def spawn(fn, *args):  # Hintergrundaufgabe mit eigenem App-Kontext (DB-Sitzung)
        def run():
            with app.app_context():
                fn(*args)
        socketio.start_background_task(run)

    runner = BotRunner(service, publisher.step, spawn=spawn, sleep=socketio.sleep,
                       refresh=db.session.remove) if paced else None
    app.extensions["bot_runner"] = runner
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(create_game_blueprint(service, access, notifier, chat=chat,
                                                     runner=runner, publisher=publisher, stats=stats),
                           url_prefix="/api")
    from .lab.api import create_lab_blueprint
    from .lab.sql import SqlLabAccess
    admin_auth = AdminAuth(admin_password, app.config["SECRET_KEY"])
    app.register_blueprint(create_lab_blueprint(service, SqlLabAccess(chat), publisher, admin_auth, runner),
                           url_prefix="/api")
    app.register_blueprint(create_community_blueprint(CommunityDeps(
        suggestions=SuggestionService(SqlSuggestions()), phrases=PhraseService(SqlPhrases()), stats=stats,
        tables=SqlTableOverview(), admin=admin_auth,
        captcha=CaptchaGuard(app.config["SECRET_KEY"]), secret=app.config["SECRET_KEY"],
        trust_proxy=bool(app.config.get("TRUST_PROXY")))), url_prefix="/api")

    _register_ops(app, service, runner, chat, admin_auth, stats)

    with app.app_context():
        db.create_all()
        _ensure_columns()
        from .community.sql import seed_default_phrases
        seed_default_phrases()

    register_socket_handlers()
    if paced and not app.config.get("TESTING"):
        from .housekeeping import start_janitor
        start_janitor(app, socketio, chat)   # Tische ohne Aktivitaet nach 12 Stunden schliessen
    return app


def _register_ops(app, service, runner, chat, admin_auth, stats):
    """Betreiber-Werkzeuge: Design-Einstellungen/Banner, Live-Uebersicht, Auswertungen, Fehler-Log, Systemstatus."""
    import logging
    import time
    from .models import Room
    from .ops.api import OpsDeps, create_ops_blueprint
    from .ops.errors import LogHandler
    from .ops.sql import SqlErrors, SqlLive, SqlSettings, SqlSystem
    from .presence import PresenceRegistry
    from .services import public_room

    settings, errors, system = SqlSettings(), SqlErrors(), SqlSystem()
    presence = PresenceRegistry()
    app.extensions.update(site_settings=settings, error_log=errors, presence=presence)
    db_path = app.config["SQLALCHEMY_DATABASE_URI"].removeprefix("sqlite:///") if \
        app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///") else None

    def notify(code, event, payload):
        if event == "room:refresh":
            room = Room.query.filter_by(code=code).first()
            if room:
                socketio.emit("room:state", public_room(room), to=code)
        else:
            socketio.emit(event, payload, to=code)

    def runtime():
        import os
        disk_dir = os.path.dirname(os.path.abspath(db_path)) if db_path else app.instance_path
        return {"db": system.db_info(),
                "runtime": {"botLoops": len(getattr(runner, "_running", ()) or ()),
                            "socketConnections": len(_socket_members), "presenceOnline": presence.online_count(),
                            "disk": system.disk(disk_dir)}}

    app.register_blueprint(create_ops_blueprint(OpsDeps(
        admin=admin_auth, settings=settings, live=SqlLive(chat), errors=errors, stats=stats, system=runtime,
        notify=notify, started_at=time.time())), url_prefix="/api")

    if not app.config.get("TESTING"):
        # Alle ERROR-Eintraege mit Ausnahme (auch aus der Bot-Schleife) landen im Fehler-Log des Dashboards.
        logging.getLogger().addHandler(LogHandler(errors))

    from flask import jsonify
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(Exception)
    def unexpected(exc):
        if isinstance(exc, HTTPException):
            return exc
        import sys
        from flask import request
        try:
            db.session.rollback()          # eine offene Schreibsperre darf das Protokollieren nicht blockieren
        except Exception:  # pragma: no cover
            pass
        # Docker-Log UND Fehler-Log des Dashboards (LogHandler liest ``path`` aus dem Eintrag)
        logging.getLogger("doppelkopf.http").error("Unerwarteter Fehler bei %s", request.path,
                                                   exc_info=sys.exc_info(), extra={"path": request.path})
        return jsonify({"error": "Interner Fehler. Bitte versuche es später noch einmal."}), 500


def _ensure_columns():
    """Entwicklungs-Datenbanken aus Meilenstein 0-1 um neue Spalten ergaenzen (kein Alembic noetig)."""
    from sqlalchemy import inspect, text
    wanted = {"room": [("settings_json", "TEXT NOT NULL DEFAULT '{}'"), ("is_public", "BOOLEAN NOT NULL DEFAULT 0"),
                      ("takeover_seconds", "INTEGER NOT NULL DEFAULT 180"), ("lab_spec_json", "TEXT")],
              "game_snapshot": [("schema_version", "INTEGER NOT NULL DEFAULT 1")],
              "table_log": [("rounds_finished", "INTEGER NOT NULL DEFAULT 0")]}
    inspector = inspect(db.engine)
    with db.engine.begin() as conn:
        for table, columns in wanted.items():
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns:
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def register_socket_handlers():
    """Register room presence and member-scoped game-state events."""
    from flask import request
    from flask_socketio import emit, join_room
    from .models import Member, Room
    from .services import public_room, token_digest

    @socketio.on("room:watch")
    def watch_room(payload):
        payload = payload or {}
        code = str(payload.get("code", "")).upper()
        token = str(payload.get("token", ""))
        member = Member.query.filter_by(session_token_hash=token_digest(token)).first() if token else None
        room = Room.query.filter_by(code=code).first()
        if room is None or member is None or member.room_id != room.id or member.is_bot:
            emit("room:error", {"message": "Ungültiger Raum oder ungültige Sitzung."})
            return
        existing_member_id = _socket_members.get(request.sid)
        if existing_member_id is not None and existing_member_id != member.id:
            emit("room:error", {"message": "Diese Socket-Verbindung ist bereits einer anderen Sitzung zugeordnet."})
            return
        join_room(code)
        join_room(f"member:{member.id}")
        _socket_members[request.sid] = member.id
        from .models import utcnow
        member.connected = True
        member.last_seen_at = utcnow()
        from . import db
        db.session.commit()
        emit("room:state", public_room(room, viewer_id=member.id))
        from flask import current_app
        view = current_app.extensions["table_service"].view(room.code, member.id)
        if view is not None:  # personalisierte Sicht, nie die der anderen
            emit("game:state", view, to=f"member:{member.id}")

    # --- Freiwilliger Online-Status (ohne Konto, nur im Arbeitsspeicher; siehe presence.py) ---
    def _presence():
        from flask import current_app
        return current_app.extensions["presence"]

    def _friends_allowed() -> bool:
        from flask import current_app
        return bool(current_app.extensions["site_settings"].get().get("friendsEnabled", True))

    def _announce(code, online, name=""):
        socketio.emit("presence:update", {"code": code, "online": online, "name": name}, to=f"watch:{code}")

    @socketio.on("presence:hello")
    def presence_hello(payload):
        payload = payload if isinstance(payload, dict) else {}
        if not _friends_allowed():
            emit("presence:error", {"message": "Die Freunde-Funktion ist gerade ausgeschaltet."})
            return
        registry = _presence()
        try:
            code, came_online = registry.hello(request.sid, payload.get("code"), payload.get("name"))
        except ValueError as exc:
            emit("presence:error", {"message": str(exc)})
            return
        join_room(f"fc:{code}")
        emit("presence:ready", {"code": code})
        if came_online:
            _announce(code, True, registry.name_of(code) or "")

    @socketio.on("presence:watch")
    def presence_watch(payload):
        from flask_socketio import leave_room as _leave
        payload = payload if isinstance(payload, dict) else {}
        registry = _presence()
        try:
            old, new = registry.watch(request.sid, payload.get("codes"))
        except ValueError as exc:
            emit("presence:error", {"message": str(exc)})
            return
        for code in old - new:
            _leave(f"watch:{code}")
        for code in new:
            join_room(f"watch:{code}")
        emit("presence:state", {"friends": registry.status(new)})

    @socketio.on("presence:goodbye")
    def presence_goodbye(payload=None):
        from flask_socketio import leave_room as _leave
        code, offline = _presence().goodbye(request.sid)
        if code:
            _leave(f"fc:{code}")
        if offline:
            _announce(code, False)

    @socketio.on("presence:invite")
    def presence_invite(payload):
        from .presence import valid_code, valid_table
        payload = payload if isinstance(payload, dict) else {}
        registry = _presence()
        sender = registry.code_of(request.sid)
        target, table = valid_code(payload.get("to")), valid_table(payload.get("table"))
        if sender is None or target is None or table is None:
            emit("presence:error", {"message": "Einladung nicht möglich."})
            return
        token = str(payload.get("token", ""))
        member = Member.query.filter_by(session_token_hash=token_digest(token)).first() if token else None
        room = Room.query.filter_by(code=table).first()
        if room is None or member is None or member.room_id != room.id or member.is_bot:
            emit("presence:error", {"message": "Du kannst nur zu deinem eigenen Tisch einladen."})
            return
        if not registry.allow_invite(request.sid):
            emit("presence:error", {"message": "Zu viele Einladungen. Bitte warte kurz."})
            return
        delivered = registry.is_online(target)
        if delivered:
            socketio.emit("presence:invite", {"from": registry.name_of(sender) or "Jemand", "table": table,
                                              "hasPassword": bool(room.password_hash)}, to=f"fc:{target}")
        emit("presence:invited", {"to": target, "delivered": delivered})

    @socketio.on_error_default
    def socket_error(exc):
        import logging
        logging.getLogger("doppelkopf.socket").error("Fehler in einem Socket-Ereignis", exc_info=(type(exc), exc, exc.__traceback__))

    @socketio.on("disconnect")
    def socket_disconnected(reason=None):
        from . import db
        code, offline = _presence().goodbye(request.sid)
        if offline:
            _announce(code, False)
        member_id = _socket_members.pop(request.sid, None)
        if member_id and member_id not in _socket_members.values():
            member = db.session.get(Member, member_id)
            if member:
                member.connected = False
                db.session.commit()
                room = db.session.get(Room, member.room_id)
                if room:
                    socketio.emit("room:state", public_room(room), to=room.code)


_socket_members = {}
