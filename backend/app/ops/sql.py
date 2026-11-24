"""SQLAlchemy-Umsetzung der Betreiber-Werkzeuge (duenn: die Logik steht in den flask-freien Nachbarmodulen)."""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import db
from ..models import (ErrorEntry, GameEvent, GameHistory, GameSnapshot, Member, Phrase, Room, Setting, Suggestion,
                      TableLog, utcnow)
from ..services import new_token, token_digest
from . import errors as errlog
from . import bot_tuning
from . import settings as site

SETTINGS_KEY = "site_settings"
BOTS_KEY = "bot_tuning"
SPECTATOR_NAME = "Betreiber"


def _ts(moment: datetime | None) -> float | None:
    if moment is None:
        return None
    return (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).timestamp()


def _dt(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, timezone.utc)


class SqlSettings:
    def get(self) -> dict:
        row = db.session.get(Setting, SETTINGS_KEY)
        return site.loads(row.value if row else None)

    def put(self, data: dict) -> dict:
        data = site.normalize(data)
        row = db.session.get(Setting, SETTINGS_KEY)
        if row is None:
            db.session.add(Setting(key=SETTINGS_KEY, value=site.dumps(data)))
        else:
            row.value = site.dumps(data)
        db.session.commit()
        return data

    def reset(self) -> dict:
        return self.put({})


class SqlBotTuning:
    """Bot-Einstellungen des Betreibers (eigener Schluessel, nie Teil der oeffentlichen ``site_settings``)."""

    def saved(self) -> dict | None:
        """Gespeicherter Stand oder ``None``, wenn der Betreiber nie gespeichert hat."""
        row = db.session.get(Setting, BOTS_KEY)
        return bot_tuning.loads(row.value if row else None)

    def get(self) -> dict:
        return self.saved() or bot_tuning.normalize({})

    def put(self, data: dict) -> dict:
        data = bot_tuning.normalize(data)
        row = db.session.get(Setting, BOTS_KEY)
        if row is None:
            db.session.add(Setting(key=BOTS_KEY, value=bot_tuning.dumps(data)))
        else:
            row.value = bot_tuning.dumps(data)
        db.session.commit()
        return data

    def reset(self) -> dict:
        return self.put({})


class SqlErrors:
    """Fehler-Log in der Datenbank. Schreibt ueber eine eigene Verbindung, damit eine kaputte Sitzung nicht stoert."""

    def record(self, entry: dict) -> None:
        now = _dt(time.time())
        with Session(db.engine) as session:                 # eigene Sitzung/Verbindung
            row = session.query(ErrorEntry).filter_by(sig=entry["sig"]).first()
            if row is not None:
                row.count += 1
                row.last_at = now
            else:
                session.add(ErrorEntry(sig=entry["sig"], source=entry["source"], origin=entry["where"], kind=entry["kind"],
                                       message=entry["message"], trace=entry["trace"], count=1, first_at=now, last_at=now))
            session.flush()
            keep = [r[0] for r in session.query(ErrorEntry.id).order_by(ErrorEntry.last_at.desc()).limit(errlog.MAX_ENTRIES)]
            session.query(ErrorEntry).filter(ErrorEntry.id.notin_(keep)).delete(synchronize_session=False)
            session.commit()

    def list(self, limit: int = 100) -> list[dict]:
        rows = ErrorEntry.query.order_by(ErrorEntry.last_at.desc()).limit(limit).all()
        return [{"id": r.id, "source": r.source, "where": r.origin, "kind": r.kind, "message": r.message,
                 "trace": r.trace, "count": r.count, "firstAt": _ts(r.first_at), "lastAt": _ts(r.last_at)} for r in rows]

    def count_since(self, since: float) -> int:
        total = db.session.query(func.coalesce(func.sum(ErrorEntry.count), 0)).filter(
            ErrorEntry.last_at >= _dt(since)).scalar()
        return int(total or 0)

    def delete(self, entry_id: int) -> bool:
        row = db.session.get(ErrorEntry, entry_id)
        if row is None:
            return False
        db.session.delete(row)
        db.session.commit()
        return True

    def clear(self) -> int:
        n = ErrorEntry.query.delete()
        db.session.commit()
        return n

    def prune(self, now: float, max_age_days: int = errlog.MAX_AGE_DAYS) -> int:
        n = ErrorEntry.query.filter(ErrorEntry.last_at < _dt(now - max_age_days * 86400)).delete()
        db.session.commit()
        return n


def prune_events(now: float, keep_days: int = 400) -> int:
    n = GameEvent.query.filter(GameEvent.at < _dt(now - keep_days * 86400)).delete()
    db.session.commit()
    return n


class SqlLive:
    """Offene Tische mit Sitzbesetzung (fuer die Live-Uebersicht) und die Eingriffe des Betreibers."""
    CONNECTED_WITHIN = 20

    def __init__(self, chat=None) -> None:
        self.chat = chat

    def tables(self) -> list[dict]:
        now = time.time()
        rows = []
        for room in Room.query.order_by(Room.created_at).all():
            snap = GameSnapshot.query.filter_by(room_id=room.id).first()
            log = TableLog.query.filter_by(code=room.code).order_by(TableLog.id.desc()).first()
            members = sorted(room.members, key=lambda m: (m.role != "player", m.joined_at, m.id))
            players = [{"name": m.name, "isBot": m.is_bot, "isHost": m.id == room.host_member_id,
                        "connected": bool(m.is_bot) or bool(m.connected and now - _ts(m.last_seen_at) < self.CONNECTED_WITHIN)}
                       for m in members if m.role == "player"]
            moments = [_ts(room.created_at)] + [_ts(m.joined_at) for m in room.members]
            if snap is not None:
                moments.append(_ts(snap.updated_at))
            if log is not None:
                moments.append(_ts(log.last_activity_at))
            game = None
            if snap is not None:
                try:
                    state = json.loads(snap.state_json)
                    g = state.get("game", {})
                    game = {"number": state.get("gameNumber"), "phase": g.get("phase"),
                            "tricks": len(g.get("tricks", [])),
                            "normalGamesPlayed": state.get("round", {}).get("normalGamesPlayed")}
                except (ValueError, AttributeError):
                    game = None
            rows.append({
                "code": room.code, "status": room.status, "isPublic": bool(room.is_public),
                "hasPassword": bool(room.password_hash), "isLab": bool(room.lab_spec_json),
                "createdAt": _ts(room.created_at), "startedAt": _ts(log.started_at) if log else None,
                "lastActivityAt": max(m for m in moments if m), "players": players,
                "spectators": sum(m.role == "spectator" for m in room.members), "game": game})
        return rows

    def close(self, code: str) -> bool:
        room = Room.query.filter_by(code=code).first()
        if room is None:
            return False
        GameSnapshot.query.filter_by(room_id=room.id).delete()
        GameHistory.query.filter_by(room_code=room.code).delete()
        if self.chat is not None:
            self.chat.clear(room.code)
        db.session.delete(room)
        db.session.commit()
        return True

    def add_spectator(self, code: str) -> dict | None:
        """Betreiber als sichtbaren Zuschauer „Betreiber“ an den Tisch setzen (alle sehen ihn in der Liste)."""
        room = Room.query.filter_by(code=code).first()
        if room is None:
            return None
        token = new_token()
        member = Member(room_id=room.id, name=SPECTATOR_NAME, role="spectator", ready=True,
                        session_token_hash=token_digest(token))
        db.session.add(member)
        db.session.commit()
        return {"memberId": member.id, "token": token}


class SqlSystem:
    def db_info(self) -> dict:
        info = {"kind": db.engine.dialect.name, "bytes": None, "rows": {}}
        try:
            if db.engine.dialect.name == "sqlite":
                pages = db.session.execute(text("PRAGMA page_count")).scalar()
                size = db.session.execute(text("PRAGMA page_size")).scalar()
                info["bytes"] = int(pages) * int(size)
        except Exception:  # pragma: no cover
            logging.getLogger(__name__).exception("Datenbankgroesse nicht lesbar")
        for label, model in (("tables", Room), ("games", GameHistory), ("tableLogs", TableLog), ("gameEvents", GameEvent),
                             ("suggestions", Suggestion), ("phrases", Phrase), ("errors", ErrorEntry)):
            info["rows"][label] = db.session.query(func.count(model.id)).scalar() or 0
        return info

    @staticmethod
    def disk(path: str) -> dict | None:
        try:
            usage = shutil.disk_usage(path)
            return {"total": usage.total, "free": usage.free}
        except OSError:
            return None
