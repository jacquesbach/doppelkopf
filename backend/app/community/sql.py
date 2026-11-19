"""SQLAlchemy-Umsetzung der Schnittstellen aus ``suggestions``, ``phrases``, ``stats`` und ``tables``.

Bewusst duenn (keine Fachlogik): Validierung, Sortierung und Auswertung stehen in den flask-freien Modulen.
"""
from __future__ import annotations

import json
import time
import functools
import logging
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .. import db
from ..models import GameSnapshot, Phrase, Room, Setting, Suggestion, SuggestionVote, TableLog
from .phrases import DEFAULT_PHRASES


def _ts(moment: datetime | None) -> float | None:
    if moment is None:
        return None
    return (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).timestamp()


def _dt(epoch: float) -> datetime:
    return datetime.fromtimestamp(epoch, timezone.utc)


def _never_break_the_game(fn):
    """Statistik darf das Spiel nie stoeren: Fehler werden protokolliert, die Sitzung zurueckgerollt."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            db.session.rollback()
            logging.getLogger(__name__).exception("Statistik konnte nicht geschrieben werden")
    return wrapper


class SqlSuggestions:
    @staticmethod
    def _dict(row: Suggestion, votes: int, voted: bool) -> dict:
        return {"id": row.id, "title": row.title, "description": row.description, "createdAt": _ts(row.created_at),
                "status": row.status, "votes": votes, "voted": voted}

    def add(self, title, description, now):
        row = Suggestion(title=title, description=description, created_at=_dt(now))
        db.session.add(row)
        db.session.commit()
        return self._dict(row, 0, False)

    def list(self, include_hidden, voter):
        query = (db.session.query(Suggestion, func.count(SuggestionVote.id))
                 .outerjoin(SuggestionVote, SuggestionVote.suggestion_id == Suggestion.id).group_by(Suggestion.id))
        if not include_hidden:
            query = query.filter(Suggestion.status == "visible")
        mine = set()
        if voter:
            mine = {r[0] for r in db.session.query(SuggestionVote.suggestion_id).filter_by(voter=voter)}
        return [self._dict(row, votes, row.id in mine) for row, votes in query.all()]

    def toggle_vote(self, suggestion_id, voter):
        row = db.session.get(Suggestion, suggestion_id)
        if row is None or row.status != "visible":
            return None
        existing = SuggestionVote.query.filter_by(suggestion_id=suggestion_id, voter=voter).first()
        if existing:
            db.session.delete(existing)
            voted = False
        else:
            db.session.add(SuggestionVote(suggestion_id=suggestion_id, voter=voter))
            voted = True
        try:
            db.session.commit()
        except IntegrityError:               # zwei gleichzeitige Klicks: der Daumen gilt trotzdem nur einmal
            db.session.rollback()
            voted = True
        votes = SuggestionVote.query.filter_by(suggestion_id=suggestion_id).count()
        return {"votes": votes, "voted": voted}

    def set_status(self, suggestion_id, status):
        row = db.session.get(Suggestion, suggestion_id)
        if row is None:
            return False
        row.status = status
        db.session.commit()
        return True

    def update(self, suggestion_id, title, description):
        row = db.session.get(Suggestion, suggestion_id)
        if row is None:
            return False
        row.title, row.description = title, description
        db.session.commit()
        return True

    def delete(self, suggestion_id):
        row = db.session.get(Suggestion, suggestion_id)
        if row is None:
            return False
        SuggestionVote.query.filter_by(suggestion_id=suggestion_id).delete()
        db.session.delete(row)
        db.session.commit()
        return True


class SqlPhrases:
    def list(self):
        return [{"id": p.id, "text": p.text} for p in Phrase.query.order_by(Phrase.position, Phrase.id).all()]

    def add(self, text):
        top = db.session.query(func.max(Phrase.position)).scalar()
        row = Phrase(text=text, position=(top if top is not None else -1) + 1)
        db.session.add(row)
        db.session.commit()
        return {"id": row.id, "text": row.text}

    def update(self, phrase_id, text):
        row = db.session.get(Phrase, phrase_id)
        if row is None:
            return False
        row.text = text
        db.session.commit()
        return True

    def delete(self, phrase_id):
        row = db.session.get(Phrase, phrase_id)
        if row is None:
            return False
        db.session.delete(row)
        db.session.commit()
        return True

    def reorder(self, ordered_ids):
        for position, phrase_id in enumerate(ordered_ids):
            Phrase.query.filter_by(id=phrase_id).update({"position": position})
        db.session.commit()


def seed_default_phrases() -> None:
    """Beim ersten Start die mitgelieferten Sprueche eintragen - einmalig: Wer alle loescht, bekommt sie nicht zurueck."""
    if db.session.get(Setting, "phrases_seeded") is not None:
        return
    if Phrase.query.count() == 0:
        for position, text in enumerate(DEFAULT_PHRASES):
            db.session.add(Phrase(text=text, position=position))
    db.session.add(Setting(key="phrases_seeded", value="1"))
    db.session.commit()


class SqlStats:
    @staticmethod
    def _latest(code: str) -> TableLog | None:
        return TableLog.query.filter_by(code=code).order_by(TableLog.id.desc()).first()

    @_never_break_the_game
    def table_created(self, code, now=None):
        moment = _dt(time.time() if now is None else now)
        db.session.add(TableLog(code=code, created_at=moment, last_activity_at=moment))
        db.session.commit()

    @_never_break_the_game
    def round_started(self, code, humans, bots, now=None):
        log = self._latest(code)
        if log is None:
            return
        moment = _dt(time.time() if now is None else now)
        log.started_at = log.started_at or moment
        log.humans, log.bots, log.last_activity_at = humans, bots, moment
        log.rounds += 1
        db.session.commit()

    @_never_break_the_game
    def game_finished(self, code, now=None):
        log = self._latest(code)
        if log is not None:
            log.games += 1
            log.last_activity_at = _dt(time.time() if now is None else now)
            db.session.commit()

    @_never_break_the_game
    def activity(self, code, now=None):
        log = self._latest(code)
        if log is not None and log.started_at is not None:
            log.last_activity_at = _dt(time.time() if now is None else now)
            db.session.commit()

    def logs(self):
        return [{"code": l.code, "createdAt": _ts(l.created_at), "startedAt": _ts(l.started_at),
                 "lastActivityAt": _ts(l.last_activity_at), "humans": l.humans, "bots": l.bots,
                 "games": l.games, "rounds": l.rounds} for l in TableLog.query.order_by(TableLog.id).all()]


class SqlTableOverview:
    CONNECTED_WITHIN = 20          # Sekunden, wie in der Raumsicht

    def tables(self):
        now = time.time()
        rows = []
        for room in Room.query.order_by(Room.created_at).all():
            snap = GameSnapshot.query.filter_by(room_id=room.id).first()
            log = TableLog.query.filter_by(code=room.code).order_by(TableLog.id.desc()).first()
            humans = [m for m in room.members if m.role == "player" and not m.is_bot]
            moments = [_ts(room.created_at)] + [_ts(m.joined_at) for m in room.members]
            if snap is not None:
                moments.append(_ts(snap.updated_at))
            if log is not None:
                moments.append(_ts(log.last_activity_at))
            game = None
            if snap is not None:
                try:
                    state = json.loads(snap.state_json)
                    game = {"number": state.get("gameNumber"), "phase": state.get("game", {}).get("phase"),
                            "normalGamesPlayed": state.get("round", {}).get("normalGamesPlayed")}
                except (ValueError, AttributeError):
                    game = None
            rows.append({
                "code": room.code, "status": room.status, "isPublic": bool(room.is_public),
                "hasPassword": bool(room.password_hash), "isLab": bool(room.lab_spec_json), "createdAt": _ts(room.created_at),
                "startedAt": _ts(log.started_at) if log else None, "lastActivityAt": max(m for m in moments if m),
                "humans": len(humans), "bots": sum(m.is_bot for m in room.members),
                "spectators": sum(m.role == "spectator" for m in room.members),
                "connectedHumans": sum(1 for m in humans if m.connected and now - _ts(m.last_seen_at) < self.CONNECTED_WITHIN),
                "game": game})
        return rows
