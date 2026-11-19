"""Speicherschnittstelle fuer Tische + Speicher-Implementierung (Tests, Einzelprozess-Entwicklung)."""
from __future__ import annotations

import copy
import json
import threading
from dataclasses import dataclass
from typing import Protocol

from ..rules import VersionConflict
from .state import TableState


@dataclass
class Stored:
    table: TableState
    version: int


class TableStore(Protocol):
    def load(self, code: str) -> Stored | None: ...

    def create(self, code: str, table: TableState) -> int:
        """Legt den Tisch an (Version 1). Existiert schon einer, wird er ersetzt (Version + 1)."""

    def save(self, code: str, table: TableState, expected_version: int, summaries: list[dict]) -> int:
        """Optimistisch speichern; wirft ``VersionConflict``, wenn der gespeicherte Stand abweicht."""

    def history(self, code: str) -> list[dict]:
        """Zusammenfassungen aller beendeten Spiele dieses Raums (aelteste zuerst)."""


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[str, int]] = {}
        self._history: dict[str, list[dict]] = {}
        self._lock = threading.Lock()

    def load(self, code: str) -> Stored | None:
        with self._lock:
            entry = self._data.get(code)
        return None if entry is None else Stored(TableState.from_dict(json.loads(entry[0])), entry[1])

    def create(self, code: str, table: TableState) -> int:
        with self._lock:
            version = self._data[code][1] + 1 if code in self._data else 1
            self._data[code] = (json.dumps(table.to_dict(), ensure_ascii=False), version)
            self._history.setdefault(code, [])      # Historie bleibt ueber Runden eines Raums erhalten
            return version

    def save(self, code: str, table: TableState, expected_version: int, summaries: list[dict]) -> int:
        with self._lock:
            current = self._data[code][1]
            if current != expected_version:
                raise VersionConflict(expected_version, current)
            self._data[code] = (json.dumps(table.to_dict(), ensure_ascii=False), current + 1)
            self._history[code].extend(copy.deepcopy(summaries))
            return current + 1

    def history(self, code: str) -> list[dict]:
        with self._lock:
            return copy.deepcopy(self._history.get(code, []))
