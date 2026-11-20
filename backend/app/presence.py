"""Freiwilliger Online-Status ohne Konto (rein funktional, nur im Arbeitsspeicher).

Wer die Funktion einschaltet, meldet dem Server per Socket einen zufaelligen **Freundescode** (10 Zeichen, vom Browser erzeugt)
und einen selbst gewaehlten Anzeigenamen. Andere sehen ihn nur, wenn sie diesen Code kennen und in ihre eigene Liste
eingetragen haben (der Code ist so lang, dass man ihn nicht raten kann). Wer selbst nicht sichtbar ist, sieht auch niemanden.
Nichts davon wird gespeichert: Beim Trennen der Verbindung oder bei einem Neustart ist alles weg.
"""
from __future__ import annotations

import re
import threading
import time

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE = re.compile(r"^[A-HJ-NP-Z2-9]{10}$")
TABLE_CODE = re.compile(r"^[A-HJ-NP-Z2-9]{6}$")
NAME_MAX = 24
MAX_WATCH = 100
INVITES_PER_MINUTE = 6
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")


def valid_code(value: object) -> str | None:
    text = str(value or "").strip().upper().replace("-", "").replace(" ", "")
    return text if CODE.match(text) else None


def valid_table(value: object) -> str | None:
    text = str(value or "").strip().upper()
    return text if TABLE_CODE.match(text) else None


def clean_name(value: object) -> str:
    return _CONTROL.sub(" ", str(value or "")).strip()[:NAME_MAX]


class PresenceRegistry:
    def __init__(self, clock=time.time) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._sid_code: dict[str, str] = {}
        self._code_sids: dict[str, set[str]] = {}
        self._names: dict[str, str] = {}
        self._watch: dict[str, set[str]] = {}
        self._invites: dict[str, list[float]] = {}

    def hello(self, sid: str, code: object, name: object) -> tuple[str, bool]:
        """Anmelden. Gibt (Code, ``True`` wenn der Code dadurch neu online ist) zurueck; ungueltige Eingaben: ``ValueError``."""
        valid = valid_code(code)
        label = clean_name(name)
        if valid is None:
            raise ValueError("Ungültiger Freundescode.")
        if not label:
            raise ValueError("Bitte gib einen Anzeigenamen ein.")
        with self._lock:
            previous = self._sid_code.get(sid)
            if previous and previous != valid:
                self._drop(sid)
            was_online = valid in self._code_sids
            self._sid_code[sid] = valid
            self._code_sids.setdefault(valid, set()).add(sid)
            self._names[valid] = label
            return valid, not was_online

    def _drop(self, sid: str) -> tuple[str | None, bool]:
        code = self._sid_code.pop(sid, None)
        self._watch.pop(sid, None)
        self._invites.pop(sid, None)
        if code is None:
            return None, False
        sids = self._code_sids.get(code, set())
        sids.discard(sid)
        if sids:
            return code, False
        self._code_sids.pop(code, None)
        self._names.pop(code, None)
        return code, True

    def goodbye(self, sid: str) -> tuple[str | None, bool]:
        """Abmelden/Trennen. Gibt (Code, ``True`` wenn er dadurch offline ist) zurueck."""
        with self._lock:
            return self._drop(sid)

    def code_of(self, sid: str) -> str | None:
        with self._lock:
            return self._sid_code.get(sid)

    def name_of(self, code: str) -> str | None:
        with self._lock:
            return self._names.get(code)

    def watch(self, sid: str, codes: object) -> tuple[set[str], set[str]]:
        """Freundesliste setzen (nur fuer angemeldete Verbindungen). Gibt (alte, neue) Menge zurueck."""
        wanted = set()
        for raw in codes if isinstance(codes, (list, tuple)) else []:
            valid = valid_code(raw)
            if valid:
                wanted.add(valid)
            if len(wanted) >= MAX_WATCH:
                break
        with self._lock:
            if sid not in self._sid_code:
                raise ValueError("Bitte zuerst den Online-Status einschalten.")
            old = self._watch.get(sid, set())
            self._watch[sid] = wanted
            return set(old), set(wanted)

    def status(self, codes) -> dict[str, dict]:
        with self._lock:
            return {c: {"online": True, "name": self._names.get(c, "")} for c in codes if c in self._code_sids}

    def is_online(self, code: str) -> bool:
        with self._lock:
            return code in self._code_sids

    def allow_invite(self, sid: str) -> bool:
        now = self._clock()
        with self._lock:
            recent = [t for t in self._invites.get(sid, []) if now - t < 60]
            if len(recent) >= INVITES_PER_MINUTE:
                self._invites[sid] = recent
                return False
            recent.append(now)
            self._invites[sid] = recent
            return True

    def online_count(self) -> int:
        with self._lock:
            return len(self._code_sids)
