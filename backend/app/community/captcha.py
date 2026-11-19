"""Eigenes Captcha ohne Fremddienst: serverseitig erzeugte SVG-Grafik mit verzerrten Zeichen.

Der Server speichert nichts: Das Token enthaelt Ablaufzeit und einen HMAC der richtigen Antwort und ist selbst signiert.
Jedes Token gilt genau einmal (auch bei falscher Antwort), damit eine Grafik nicht beliebig oft durchprobiert werden kann.
Ehrliche Grenze: Ein Captcha dieser Art haelt Massen-Spam ab, aber keine gezielten Angreifer mit Texterkennung.
"""
from __future__ import annotations

import hashlib
import hmac
import random
import secrets
import threading
import time

ALPHABET = "ABCDEFGHJKLMNPRSTUVWXYZ23456789"      # ohne leicht verwechselbare Zeichen (0/O, 1/I, Q)
LENGTH = 5
TTL = 600                                         # Sekunden, die ein Captcha gueltig ist
WIDTH, HEIGHT = 200, 64
_INKS = ("#000000", "#1B1B1B", "#2B3F8F", "#B3261E")
_NOISE = ("#FF6B6B", "#6CB4EE", "#FFD23F", "#000000")


def _mac(secret: str, data: str) -> str:
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()


def _normalize(answer: object) -> str:
    return "".join(str(answer or "").split()).upper()


def _svg(text: str, rng: random.Random) -> str:
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
             f'role="img" aria-label="Captcha: fuenf Zeichen">',
             f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#FFFDF5"/>']
    for _ in range(6):                             # Stoerlinien hinter den Zeichen
        y1, y2 = rng.randint(4, HEIGHT - 4), rng.randint(4, HEIGHT - 4)
        parts.append(f'<path d="M{rng.randint(0, 20)} {y1} C{rng.randint(50, 90)} {rng.randint(0, HEIGHT)} '
                     f'{rng.randint(110, 150)} {rng.randint(0, HEIGHT)} {rng.randint(180, WIDTH)} {y2}" '
                     f'stroke="{rng.choice(_NOISE)}" stroke-width="{rng.choice((1.5, 2, 2.5))}" fill="none" opacity="0.8"/>')
    step = (WIDTH - 24) / len(text)
    for i, ch in enumerate(text):
        x = 14 + i * step + rng.uniform(-2, 3)
        y = HEIGHT / 2 + 12 + rng.uniform(-6, 6)
        angle = rng.uniform(-24, 24)
        size = rng.randint(32, 40)
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="Space Mono, Courier New, monospace" font-weight="700" '
                     f'font-size="{size}" fill="{rng.choice(_INKS)}" transform="rotate({angle:.1f} {x:.1f} {y:.1f})">{ch}</text>')
    for _ in range(40):                            # Punkte darueber
        parts.append(f'<circle cx="{rng.randint(0, WIDTH)}" cy="{rng.randint(0, HEIGHT)}" r="{rng.choice((1, 1.5, 2))}" '
                     f'fill="{rng.choice(_NOISE)}" opacity="0.7"/>')
    parts.append(f'<rect x="1.5" y="1.5" width="{WIDTH - 3}" height="{HEIGHT - 3}" fill="none" stroke="#000" stroke-width="3"/>')
    parts.append("</svg>")
    return "".join(parts)


def new_challenge(secret: str, rng: random.Random | None = None, now: float | None = None) -> dict:
    """``{"token", "svg"}``: Die Grafik zeigt die Zeichen, das Token wird mit der Antwort zurueckgeschickt."""
    rng = rng or random.SystemRandom()
    now = time.time() if now is None else now
    answer = "".join(rng.choice(ALPHABET) for _ in range(LENGTH))
    nonce = secrets.token_hex(6)
    exp = int(now + TTL)
    body = f"{nonce}.{exp}.{_mac(secret, f'a:{nonce}:{answer}')[:20]}"
    return {"token": f"{body}.{_mac(secret, f't:{body}')[:24]}", "svg": _svg(answer, rng)}


def check(secret: str, token: object, answer: object, now: float | None = None) -> tuple[str, str | None]:
    """Prueft Signatur, Ablauf und Antwort. Gibt (Ergebnis, nonce) zurueck: ok | malformed | expired | wrong."""
    now = time.time() if now is None else now
    parts = str(token or "").split(".")
    if len(parts) != 4:
        return "malformed", None
    nonce, exp, answer_mac, sig = parts
    body = f"{nonce}.{exp}.{answer_mac}"
    if not hmac.compare_digest(sig, _mac(secret, f"t:{body}")[:24]) or not exp.isdigit():
        return "malformed", None
    if now > int(exp):
        return "expired", nonce
    expected = _mac(secret, f"a:{nonce}:{_normalize(answer)}")[:20]
    return ("ok" if hmac.compare_digest(answer_mac, expected) else "wrong"), nonce


class CaptchaGuard:
    """Prueft Captchas und verbraucht jedes Token (auch bei falscher Antwort)."""

    def __init__(self, secret: str, clock=time.time, rng: random.Random | None = None) -> None:
        self.secret, self.clock, self.rng = secret, clock, rng
        self._used: dict[str, float] = {}
        self._lock = threading.Lock()

    def challenge(self) -> dict:
        return new_challenge(self.secret, self.rng, self.clock())

    def verify(self, token: object, answer: object) -> str:
        """``ok`` | ``malformed`` | ``expired`` | ``wrong`` | ``used``"""
        now = self.clock()
        result, nonce = check(self.secret, token, answer, now)
        if nonce is None:
            return result
        with self._lock:
            self._used = {n: t for n, t in self._used.items() if t > now}      # Abgelaufene vergessen
            if nonce in self._used:
                return "used"
            self._used[nonce] = now + TTL + 5
        return result
