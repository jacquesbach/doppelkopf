"""Verbesserungsvorschlaege: pruefen, speichern, bewerten (ein Daumen pro Nutzer und Vorschlag)."""
from __future__ import annotations

import threading
import time
from typing import Protocol

from .text import ValidationError, clean

TITLE_MIN, TITLE_MAX = 4, 80
DESC_MIN, DESC_MAX = 10, 500
STATUSES = ("visible", "hidden")


class SuggestionStore(Protocol):
    def add(self, title: str, description: str, now: float) -> dict: ...
    def list(self, include_hidden: bool, voter: str | None) -> list[dict]:
        """Eintraege ``{id, title, description, createdAt, status, votes, voted}`` (unsortiert)."""
    def toggle_vote(self, suggestion_id: int, voter: str) -> dict | None:
        """``{"votes", "voted"}`` oder ``None``, wenn es den (sichtbaren) Vorschlag nicht gibt."""
    def set_status(self, suggestion_id: int, status: str) -> bool: ...
    def update(self, suggestion_id: int, title: str, description: str) -> bool: ...
    def delete(self, suggestion_id: int) -> bool: ...


def ranked(items: list[dict]) -> list[dict]:
    """Beliebteste zuerst; bei gleich vielen Daumen der aeltere Vorschlag zuerst."""
    return sorted(items, key=lambda s: (-s["votes"], s["createdAt"], s["id"]))


class SuggestionService:
    def __init__(self, store: SuggestionStore, clock=time.time) -> None:
        self.store, self.clock = store, clock

    @staticmethod
    def validate(title: object, description: object) -> tuple[str, str]:
        return (clean(title, "Titel", TITLE_MIN, TITLE_MAX),
                clean(description, "Beschreibung", DESC_MIN, DESC_MAX, multiline=True))

    def submit(self, title: object, description: object) -> dict:
        title, description = self.validate(title, description)
        known = {s["title"].casefold() for s in self.store.list(True, None)}
        if title.casefold() in known:
            raise ValidationError("Diesen Vorschlag gibt es schon – gib ihm lieber einen Daumen hoch.", "duplicate")
        return self.store.add(title, description, self.clock())

    def public_list(self, voter: str | None) -> list[dict]:
        return ranked(self.store.list(False, voter))

    def admin_list(self) -> list[dict]:
        return ranked(self.store.list(True, None))

    def vote(self, suggestion_id: int, voter: str) -> dict | None:
        return self.store.toggle_vote(suggestion_id, voter)

    def moderate(self, suggestion_id: int, status: str) -> bool:
        if status not in STATUSES:
            raise ValidationError("Status muss 'visible' oder 'hidden' sein.")
        return self.store.set_status(suggestion_id, status)

    def edit(self, suggestion_id: int, title: object, description: object) -> bool:
        title, description = self.validate(title, description)
        return self.store.update(suggestion_id, title, description)

    def delete(self, suggestion_id: int) -> bool:
        return self.store.delete(suggestion_id)


class MemorySuggestions:
    """Speicher fuer Tests und Entwicklung ohne Datenbank."""

    def __init__(self) -> None:
        self._items: dict[int, dict] = {}
        self._votes: dict[int, set[str]] = {}
        self._next = 1
        self._lock = threading.Lock()

    def add(self, title, description, now):
        with self._lock:
            item = {"id": self._next, "title": title, "description": description, "createdAt": now, "status": "visible"}
            self._items[self._next] = item
            self._votes[self._next] = set()
            self._next += 1
            return {**item, "votes": 0, "voted": False}

    def list(self, include_hidden, voter):
        with self._lock:
            return [{**i, "votes": len(self._votes[i["id"]]), "voted": bool(voter) and voter in self._votes[i["id"]]}
                    for i in self._items.values() if include_hidden or i["status"] == "visible"]

    def toggle_vote(self, suggestion_id, voter):
        with self._lock:
            item = self._items.get(suggestion_id)
            if item is None or item["status"] != "visible":
                return None
            votes = self._votes[suggestion_id]
            if voter in votes:
                votes.discard(voter)
            else:
                votes.add(voter)
            return {"votes": len(votes), "voted": voter in votes}

    def set_status(self, suggestion_id, status):
        with self._lock:
            if suggestion_id not in self._items:
                return False
            self._items[suggestion_id]["status"] = status
            return True

    def update(self, suggestion_id, title, description):
        with self._lock:
            if suggestion_id not in self._items:
                return False
            self._items[suggestion_id].update(title=title, description=description)
            return True

    def delete(self, suggestion_id):
        with self._lock:
            self._votes.pop(suggestion_id, None)
            return self._items.pop(suggestion_id, None) is not None
