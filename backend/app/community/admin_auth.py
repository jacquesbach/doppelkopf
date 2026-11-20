"""Betreiber-Anmeldung: ein Passwort aus der Umgebung (``ADMIN_PASSWORD``), danach eine befristete Sitzung.

Das Token ist eine zufaellige Zeichenfolge ohne Inhalt. Der Server merkt sich nur den Hash des Tokens mit Ablaufzeit,
ausschliesslich im Arbeitsspeicher (kein Datenbankeintrag, keine IP-Adresse). Dadurch laesst sich jede Sitzung widerrufen
(``logout``, ``logout_all``), und ein Neustart des Servers beendet alle Sitzungen.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time

from .ratelimit import RateLimiter

TOKEN_TTL = 2 * 3600
MAX_SESSIONS = 20
MAX_FAILURES = 5
FAILURE_WINDOW = 600
MIN_PASSWORD_PRODUCTION = 10


class TooManyAttempts(Exception):
    pass


def _digest(token: object) -> str:
    return hashlib.sha256(str(token or "").encode()).hexdigest()


class AdminAuth:
    def __init__(self, password: str | None, secret: str, ttl: int = TOKEN_TTL, clock=time.time,
                 limiter: RateLimiter | None = None) -> None:
        self._password = (password or "").encode()
        self.secret, self.ttl, self.clock = secret, ttl, clock
        self.limiter = RateLimiter() if limiter is None else limiter
        self._sessions: dict[str, float] = {}          # Hash des Tokens -> Ablaufzeit
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self._password)

    def _expire(self, now: float) -> None:
        for key in [k for k, exp in self._sessions.items() if exp <= now]:
            del self._sessions[key]

    def login(self, password: object, ip: str) -> str | None:
        """Token bei richtigem Passwort, sonst ``None``; nach zu vielen Fehlversuchen ``TooManyAttempts``."""
        if not self.enabled:
            return None
        key = f"admin-login:{ip}"
        if not self.limiter.allow(key, MAX_FAILURES, FAILURE_WINDOW):
            raise TooManyAttempts()
        given = hashlib.sha256(str(password or "").encode()).digest()
        wanted = hashlib.sha256(self._password).digest()
        if not hmac.compare_digest(given, wanted):
            return None
        self.limiter.reset(key)
        token = secrets.token_urlsafe(32)
        now = self.clock()
        with self._lock:
            self._expire(now)
            while len(self._sessions) >= MAX_SESSIONS:                 # aelteste Sitzung weicht
                del self._sessions[min(self._sessions, key=self._sessions.get)]
            self._sessions[_digest(token)] = now + self.ttl
        return token

    def verify(self, token: object) -> bool:
        if not self.enabled or not token:
            return False
        now = self.clock()
        with self._lock:
            self._expire(now)
            return _digest(token) in self._sessions

    def logout(self, token: object) -> bool:
        """Diese eine Sitzung beenden."""
        with self._lock:
            return self._sessions.pop(_digest(token), None) is not None

    def logout_all(self) -> int:
        """Alle Sitzungen beenden (z. B. nach Passwortwechsel oder bei Verdacht). Gibt die Zahl der beendeten zurueck."""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            return count

    def session_count(self) -> int:
        with self._lock:
            self._expire(self.clock())
            return len(self._sessions)
