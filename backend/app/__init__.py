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
    app.register_blueprint(create_community_blueprint(CommunityDeps(
        suggestions=SuggestionService(SqlSuggestions()), phrases=PhraseService(SqlPhrases()), stats=stats,
        tables=SqlTableOverview(), admin=AdminAuth(admin_password, app.config["SECRET_KEY"]),
        captcha=CaptchaGuard(app.config["SECRET_KEY"]), secret=app.config["SECRET_KEY"],
        trust_proxy=bool(app.config.get("TRUST_PROXY")))), url_prefix="/api")

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


def _ensure_columns():
    """Entwicklungs-Datenbanken aus Meilenstein 0-1 um neue Spalten ergaenzen (kein Alembic noetig)."""
    from sqlalchemy import inspect, text
    wanted = {"room": [("settings_json", "TEXT NOT NULL DEFAULT '{}'"), ("is_public", "BOOLEAN NOT NULL DEFAULT 0"),
                      ("takeover_seconds", "INTEGER NOT NULL DEFAULT 180")],
              "game_snapshot": [("schema_version", "INTEGER NOT NULL DEFAULT 1")]}
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

    @socketio.on("disconnect")
    def socket_disconnected(reason=None):
        from . import db
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
