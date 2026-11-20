"""Schutz des Raumzugangs vor Durchprobieren (flask-frei, nur Arbeitsspeicher).

Gezaehlt wird je Adresse (und Tisch) fuer kurze Zeit, nichts davon wird gespeichert; ein Neustart leert alles:

- Neue Tische: ``CREATE_PER_HOUR`` je Adresse und Stunde.
- Falsches Passwort / falscher Platz-Code: ``FAIL_LIMIT`` Fehlversuche je Adresse und Tisch in ``FAIL_WINDOW`` Sekunden.
- Tisch-Codes raten: ``MISS_LIMIT`` verschiedene unbekannte Codes je Adresse in ``FAIL_WINDOW`` Sekunden (derselbe
  Code zaehlt nur einmal, damit ein offen gebliebener Tab eines beendeten Tisches niemanden aussperrt).
"""
from __future__ import annotations

import ipaddress

from .community.ratelimit import RateLimiter

CREATE_PER_HOUR = 30
FAIL_LIMIT = 8
MISS_LIMIT = 20
FAIL_WINDOW = 600
HOUR = 3600

TOO_MANY = "Zu viele Versuche. Bitte warte ein paar Minuten."


def client_ip(headers, remote_addr: str | None, trust_proxy: bool) -> str:
    """Besucheradresse. Hinter dem eigenen Proxy zaehlt dessen letzter X-Forwarded-For-Eintrag (nicht faelschbar)."""
    address = remote_addr or "unknown"
    if trust_proxy:
        forwarded = (headers.get("X-Forwarded-For", "") or "").strip()
        if forwarded:
            address = forwarded.split(",")[-1].strip()[:64]
    if ":" in address:                       # IPv6: ein Anschluss hat ein ganzes /64-Netz, gezaehlt wird das Netz
        try:
            return str(ipaddress.ip_network(f"{address}/64", strict=False))
        except ValueError:
            return address
    return address


class AccessGuard:
    def __init__(self, limiter: RateLimiter | None = None, enabled: bool = True,
                 create_per_hour: int = CREATE_PER_HOUR) -> None:
        self.limiter = RateLimiter() if limiter is None else limiter
        self.enabled = enabled
        self.create_per_hour = create_per_hour

    # --- neue Tische ---
    def allow_create(self, ip: str) -> bool:
        return not self.enabled or self.limiter.allow(f"create:{ip}", self.create_per_hour, HOUR)

    # --- Passwort / Platz-Code ---
    def blocked(self, ip: str, code: str) -> bool:
        return self.enabled and self.limiter.peek(f"fail:{ip}:{code}", FAIL_LIMIT, FAIL_WINDOW)

    def failed(self, ip: str, code: str) -> None:
        if self.enabled:
            self.limiter.record(f"fail:{ip}:{code}", FAIL_WINDOW)

    def succeeded(self, ip: str, code: str) -> None:
        if self.enabled:
            self.limiter.reset(f"fail:{ip}:{code}")

    # --- Tisch-Codes raten ---
    def lookups_blocked(self, ip: str) -> bool:
        return self.enabled and self.limiter.peek(f"miss:{ip}", MISS_LIMIT, FAIL_WINDOW)

    def missed(self, ip: str, code: str) -> None:
        """Ein unbekannter Tisch-Code wurde abgefragt (je Code nur einmal pro Fenster gezaehlt)."""
        if self.enabled and self.limiter.allow(f"seen:{ip}:{code}", 1, FAIL_WINDOW):
            self.limiter.record(f"miss:{ip}", FAIL_WINDOW)
