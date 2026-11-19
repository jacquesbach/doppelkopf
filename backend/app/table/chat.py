"""Tisch-Chat: fluechtig (nur im Arbeitsspeicher), begrenzt und ratenbegrenzt. Flask-frei."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from ..rules import RuleViolation

MAX_LENGTH = 200
KEEP = 100
MIN_INTERVAL = 0.8  # Sekunden zwischen zwei Nachrichten desselben Mitglieds


class ChatLog:
    def __init__(self, clock=time.monotonic, wall=time.time) -> None:
        self._messages: dict[str, deque] = defaultdict(lambda: deque(maxlen=KEEP))
        self._last: dict[tuple[str, int], float] = {}
        self._counter: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()
        self._clock, self._wall = clock, wall

    def post(self, code: str, member_id: int, name: str, text: object) -> dict:
        if not isinstance(text, str):
            raise RuleViolation("bad_request", "Nachricht muss Text sein.")
        text = " ".join(text.split())  # Zeilenumbrueche/Mehrfach-Leerzeichen glaetten
        if not text:
            raise RuleViolation("bad_request", "Nachricht ist leer.")
        if len(text) > MAX_LENGTH:
            raise RuleViolation("bad_request", f"Nachricht ist zu lang (max. {MAX_LENGTH} Zeichen).")
        with self._lock:
            now = self._clock()
            if now - self._last.get((code, member_id), -1e9) < MIN_INTERVAL:
                raise RuleViolation("rate_limited", "Bitte etwas langsamer schreiben.")
            self._last[(code, member_id)] = now
            self._counter[code] += 1
            message = {"id": self._counter[code], "memberId": member_id, "name": name[:32], "text": text,
                       "ts": int(self._wall())}
            self._messages[code].append(message)
            return message

    def history(self, code: str) -> list[dict]:
        with self._lock:
            return list(self._messages.get(code, []))

    def clear(self, code: str) -> None:
        with self._lock:
            self._messages.pop(code, None)
