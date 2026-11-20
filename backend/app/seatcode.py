"""Platz-Code: Nachweis, dass jemand den Sitz am Tisch schon vorher hatte (flask-frei).

Der Code wird aus dem geheimen Serverschluessel, dem Tisch-Code und den Daten des Sitzes **berechnet** und nirgends
gespeichert. Mit dem Code kann man den Sitz auf einem anderen Geraet zurueckholen (``/rejoin``). Der Host kann die Codes
der Spieler seines Tisches abrufen und einer Person weitergeben, die ihren Code verloren hat. Wechselt der Serverschluessel,
sind alle Codes ungueltig (die laufenden Sitzungen mit Token bleiben davon unberuehrt).
"""
from __future__ import annotations

import hashlib
import hmac

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"      # 32 Zeichen = 5 Bit je Zeichen
LENGTH = 8


def seat_code(secret: str, room_code: str, member_id: int, joined_at) -> str:
    """8 Zeichen (40 Bit), angezeigt als ``ABCD-EFGH``. ``joined_at``: Zeitpunkt des Beitritts (datetime oder Text)."""
    stamp = joined_at.replace(tzinfo=None).isoformat() if hasattr(joined_at, "replace") else str(joined_at)
    digest = hmac.new(secret.encode(), f"seat:{room_code}:{member_id}:{stamp}".encode(), hashlib.sha256).digest()
    value = int.from_bytes(digest[:5], "big")
    return "".join(ALPHABET[(value >> (5 * (LENGTH - 1 - i))) & 31] for i in range(LENGTH))


def parse(value: object) -> str | None:
    """Eingabe (mit Bindestrich, Leerzeichen, Kleinbuchstaben) -> 8 Zeichen oder ``None``."""
    text = str(value or "").strip().upper().replace("-", "").replace(" ", "")
    return text if len(text) == LENGTH and all(ch in ALPHABET for ch in text) else None


def display(code: str) -> str:
    return f"{code[:4]}-{code[4:]}"


def matches(expected: str, given: object) -> bool:
    parsed = parse(given)
    return parsed is not None and hmac.compare_digest(expected, parsed)
