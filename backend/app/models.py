from datetime import datetime, timezone
from . import db


def utcnow():
    return datetime.now(timezone.utc)


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    status = db.Column(db.String(20), default="waiting", nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    host_member_id = db.Column(db.Integer, nullable=True)
    settings_json = db.Column(db.Text, nullable=False, default="{}", server_default="{}")  # Regeloptionen + Deck
    is_public = db.Column(db.Boolean, nullable=False, default=False, server_default="0")   # in der Tischliste sichtbar
    takeover_seconds = db.Column(db.Integer, nullable=False, default=180, server_default="180")  # Bot-Uebernahme; 0 = nie
    lab_spec_json = db.Column(db.Text, nullable=True)   # nur Test-Tische des Betreibers: Szenario (JSON); sonst NULL
    members = db.relationship("Member", backref="room", cascade="all, delete-orphan", lazy=True)


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False, index=True)
    name = db.Column(db.String(32), nullable=False)
    role = db.Column(db.String(16), default="player", nullable=False)  # player | spectator
    ready = db.Column(db.Boolean, default=False, nullable=False)
    is_bot = db.Column(db.Boolean, default=False, nullable=False)
    connected = db.Column(db.Boolean, default=True, nullable=False)
    last_seen_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    session_token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    joined_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(8), nullable=False, index=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    result_json = db.Column(db.Text, nullable=True)



class GameSnapshot(db.Model):
    """Latest authoritative game state; private hands are stored only server-side."""
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), unique=True, nullable=False, index=True)
    history_id = db.Column(db.Integer, db.ForeignKey("game_history.id"), nullable=True)
    state_json = db.Column(db.Text, nullable=False)  # komplettes TableState-JSON
    schema_version = db.Column(db.Integer, default=2, nullable=False, server_default="1")  # 1 = Altformat (ignoriert)
    version = db.Column(db.Integer, default=1, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Suggestion(db.Model):
    """Verbesserungsvorschlag eines Besuchers (Moderation: status = visible | hidden)."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(10), nullable=False, default="visible", server_default="visible", index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class SuggestionVote(db.Model):
    """Ein Daumen. ``voter`` ist ein Hash der zufaelligen Browser-Kennung (kein Klarname, keine IP)."""
    __table_args__ = (db.UniqueConstraint("suggestion_id", "voter", name="uq_vote_once"),)
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey("suggestion.id"), nullable=False, index=True)
    voter = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Phrase(db.Model):
    """Klassiker-Spruch fuer den Chat (vom Betreiber gepflegt)."""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0, index=True)


class Setting(db.Model):
    """Kleine Schluessel-Wert-Ablage des Betreibers (z. B. 'phrases_seeded')."""
    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")


class TableLog(db.Model):
    """Statistik je angelegtem Tisch; bleibt bestehen, auch wenn der Raum spaeter geloescht wird."""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_activity_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    humans = db.Column(db.Integer, nullable=False, default=0)
    bots = db.Column(db.Integer, nullable=False, default=0)
    games = db.Column(db.Integer, nullable=False, default=0)
    rounds = db.Column(db.Integer, nullable=False, default=0)
    rounds_finished = db.Column(db.Integer, nullable=False, default=0, server_default="0")


class GameEvent(db.Model):
    """Anonymes Zaehlereignis: ein beendetes Spiel (Zeitpunkt, Dauer, Zahl der Menschen). Keine Namen, kein Tisch-Code."""
    id = db.Column(db.Integer, primary_key=True)
    at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    duration_s = db.Column(db.Integer, nullable=True)
    humans = db.Column(db.Integer, nullable=False, default=0)


class ErrorEntry(db.Model):
    """Technischer Fehler des Servers fuer das Betreiber-Dashboard (gleiche Fehler werden zusammengezaehlt)."""
    id = db.Column(db.Integer, primary_key=True)
    sig = db.Column(db.String(40), nullable=False, index=True)
    source = db.Column(db.String(16), nullable=False, default="server")
    origin = db.Column(db.String(120), nullable=False, default="")
    kind = db.Column(db.String(80), nullable=False, default="")
    message = db.Column(db.Text, nullable=False, default="")
    trace = db.Column(db.Text, nullable=False, default="")
    count = db.Column(db.Integer, nullable=False, default=1)
    first_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    last_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
