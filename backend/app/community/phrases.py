"""Klassiker-Sprueche fuer den Chat: vom Betreiber pflegbar (hinzufuegen, bearbeiten, loeschen, sortieren)."""
from __future__ import annotations

import threading
from typing import Protocol

from .text import ValidationError, clean

PHRASE_MAX = 200          # so lang darf eine Chatnachricht sein
MAX_PHRASES = 200

DEFAULT_PHRASES = (
    "Den mach ich fett.",
    "... und den hab ich auch noch!",
    "Kleinvieh macht auch Mist.",
    "Hinten sind die Enten fett.",
    "Pikus der Waldspecht",
    "Butter bei die Fische!",
    "Kann gehen, muss aber nicht.",
    "Karte oder Stück Holz",
)


class PhraseStore(Protocol):
    def list(self) -> list[dict]:
        """``[{id, text}]`` in Anzeigereihenfolge."""
    def add(self, text: str) -> dict: ...
    def update(self, phrase_id: int, text: str) -> bool: ...
    def delete(self, phrase_id: int) -> bool: ...
    def reorder(self, ordered_ids: list[int]) -> None: ...


class PhraseService:
    def __init__(self, store: PhraseStore) -> None:
        self.store = store

    @staticmethod
    def _clean(text: object) -> str:
        return clean(text, "Spruch", 1, PHRASE_MAX, allow_links=True)

    def _ensure_unique(self, text: str, own_id: int | None = None) -> None:
        if any(p["text"].casefold() == text.casefold() and p["id"] != own_id for p in self.store.list()):
            raise ValidationError("Diesen Spruch gibt es schon.", "duplicate")

    def list(self) -> list[dict]:
        return self.store.list()

    def add(self, text: object) -> dict:
        text = self._clean(text)
        if len(self.store.list()) >= MAX_PHRASES:
            raise ValidationError(f"Es sind höchstens {MAX_PHRASES} Sprüche möglich.", "too_many")
        self._ensure_unique(text)
        return self.store.add(text)

    def update(self, phrase_id: int, text: object) -> bool:
        text = self._clean(text)
        self._ensure_unique(text, phrase_id)
        return self.store.update(phrase_id, text)

    def delete(self, phrase_id: int) -> bool:
        return self.store.delete(phrase_id)

    def move(self, phrase_id: int, direction: object) -> bool:
        if direction not in ("up", "down"):
            raise ValidationError("direction muss 'up' oder 'down' sein.")
        ids = [p["id"] for p in self.store.list()]
        if phrase_id not in ids:
            return False
        i = ids.index(phrase_id)
        j = i - 1 if direction == "up" else i + 1
        if 0 <= j < len(ids):
            ids[i], ids[j] = ids[j], ids[i]
            self.store.reorder(ids)
        return True


class MemoryPhrases:
    def __init__(self, texts=()) -> None:
        self._items: list[dict] = []
        self._next = 1
        self._lock = threading.Lock()
        for t in texts:
            self.add(t)

    def list(self):
        with self._lock:
            return [dict(p) for p in self._items]

    def add(self, text):
        with self._lock:
            item = {"id": self._next, "text": text}
            self._next += 1
            self._items.append(item)
            return dict(item)

    def update(self, phrase_id, text):
        with self._lock:
            for p in self._items:
                if p["id"] == phrase_id:
                    p["text"] = text
                    return True
            return False

    def delete(self, phrase_id):
        with self._lock:
            n = len(self._items)
            self._items = [p for p in self._items if p["id"] != phrase_id]
            return len(self._items) != n

    def reorder(self, ordered_ids):
        with self._lock:
            by_id = {p["id"]: p for p in self._items}
            self._items = [by_id[i] for i in ordered_ids if i in by_id]
