"""Design- und Betriebseinstellungen der Website (vom Betreiber im Dashboard gepflegt).

Gespeichert wird ein einziges JSON-Dokument. ``normalize`` ist tolerant (fuer gespeicherte Werte: Unbrauchbares faellt auf den
Standard zurueck), ``validate_update`` ist streng (fuer Eingaben des Betreibers: Fehler werden gemeldet). Farben sind
ausschliesslich ``#RRGGBB``; der Bannertext ist reiner Text (die Oberflaeche setzt nie HTML ein).
"""
from __future__ import annotations

import copy
import json
import re
import threading

COLOR_KEYS = ("bg", "paper", "yellow", "coral", "blue", "green", "lavender", "orange")
DEFAULT_COLORS = {"bg": "#fffdf5", "paper": "#f4f1e6", "yellow": "#ffd23f", "coral": "#ff6b6b", "blue": "#74b9ff",
                  "green": "#88d498", "lavender": "#b8a9fa", "orange": "#ffa552"}
TONES = ("info", "warn", "alert")
TABLE_THEMES = ("light", "dark")
BANNER_MAX = 280
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")

DEFAULTS = {
    "colors": dict(DEFAULT_COLORS),
    "banner": {"enabled": False, "text": "", "tone": "info", "dismissible": True},
    "tableTheme": "light",          # Vorgabe fuer Besucher, die noch nichts gewaehlt haben
    "friendsEnabled": True,         # Freunde-/Online-Funktion insgesamt erlaubt
}


class SettingsError(ValueError):
    def __init__(self, message: str, code: str = "bad_settings") -> None:
        super().__init__(message)
        self.code = code


def _clean_text(value: object) -> str:
    return " ".join(_CONTROL.sub(" ", str(value or "")).split())


def normalize(raw: object) -> dict:
    """Gespeicherte/unvollstaendige Einstellungen -> vollstaendiges, gueltiges Dokument (Unbrauchbares = Standard)."""
    data = raw if isinstance(raw, dict) else {}
    out = copy.deepcopy(DEFAULTS)
    colors = data.get("colors") if isinstance(data.get("colors"), dict) else {}
    for key in COLOR_KEYS:
        value = colors.get(key)
        if isinstance(value, str) and _HEX.match(value):
            out["colors"][key] = value.lower()
    banner = data.get("banner") if isinstance(data.get("banner"), dict) else {}
    out["banner"]["enabled"] = bool(banner.get("enabled", False))
    out["banner"]["text"] = _clean_text(banner.get("text"))[:BANNER_MAX]
    out["banner"]["tone"] = banner.get("tone") if banner.get("tone") in TONES else "info"
    out["banner"]["dismissible"] = bool(banner.get("dismissible", True))
    if not out["banner"]["text"]:
        out["banner"]["enabled"] = False
    out["tableTheme"] = data.get("tableTheme") if data.get("tableTheme") in TABLE_THEMES else "light"
    out["friendsEnabled"] = bool(data.get("friendsEnabled", True))
    return out


def validate_update(raw: object) -> dict:
    """Eingabe des Betreibers pruefen; bei Fehlern ``SettingsError`` mit verstaendlicher Meldung."""
    if not isinstance(raw, dict):
        raise SettingsError("Ungültige Einstellungen.")
    colors = raw.get("colors", {})
    if not isinstance(colors, dict):
        raise SettingsError("Farben müssen als Liste von Name und Wert übergeben werden.")
    for key, value in colors.items():
        if key not in COLOR_KEYS:
            raise SettingsError(f"Unbekannte Farbe „{key}“.")
        if not isinstance(value, str) or not _HEX.match(value):
            raise SettingsError(f"Die Farbe „{key}“ muss die Form #RRGGBB haben.")
    banner = raw.get("banner", {})
    if not isinstance(banner, dict):
        raise SettingsError("Ungültiger Banner.")
    text = _clean_text(banner.get("text"))
    if len(text) > BANNER_MAX:
        raise SettingsError(f"Der Bannertext darf höchstens {BANNER_MAX} Zeichen lang sein.")
    if banner.get("tone", "info") not in TONES:
        raise SettingsError("Ungültige Banner-Art.")
    if banner.get("enabled") and not text:
        raise SettingsError("Bitte gib einen Bannertext ein oder schalte den Banner aus.")
    if raw.get("tableTheme", "light") not in TABLE_THEMES:
        raise SettingsError("Ungültiges Tischdesign.")
    return normalize(raw)


class MemorySettings:
    def __init__(self, initial: object = None) -> None:
        self._data = normalize(initial)
        self._lock = threading.Lock()

    def get(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data)

    def put(self, data: dict) -> dict:
        with self._lock:
            self._data = normalize(data)
            return copy.deepcopy(self._data)

    def reset(self) -> dict:
        return self.put({})


def dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def loads(text: str | None) -> dict:
    try:
        return normalize(json.loads(text)) if text else normalize({})
    except ValueError:
        return normalize({})
