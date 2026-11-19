"""Betreiber-Anmeldung: ein Passwort aus der Umgebung (``ADMIN_PASSWORD``), danach ein signiertes, befristetes Token."""
from __future__ import annotations

import hashlib
import hmac
import time

from .ratelimit import RateLimiter

TOKEN_TTL = 8 * 3600
MAX_FAILURES = 5
FAILURE_WINDOW = 600
MIN_PASSWORD_PRODUCTION = 10


class TooManyAttempts(Exception):
    pass


class AdminAuth:
    def __init__(self, password: str | None, secret: str, ttl: int = TOKEN_TTL, clock=time.time,
                 limiter: RateLimiter | None = None) -> None:
        self._password = (password or "").encode()
        self.secret, self.ttl, self.clock = secret, ttl, clock
        self.limiter = limiter or RateLimiter()

    @property
    def enabled(self) -> bool:
        return bool(self._password)

    def _sign(self, exp: int) -> str:
        return hmac.new(self.secret.encode(), f"admin:{exp}".encode(), hashlib.sha256).hexdigest()[:40]

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
        exp = int(self.clock() + self.ttl)
        return f"{exp}.{self._sign(exp)}"

    def verify(self, token: object) -> bool:
        if not self.enabled:
            return False
        exp, _, sig = str(token or "").partition(".")
        if not exp.isdigit() or not hmac.compare_digest(sig, self._sign(int(exp))):
            return False
        return self.clock() < int(exp)
