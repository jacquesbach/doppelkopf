"""Eingabepruefung fuer Freitext (Vorschlaege, Sprueche)."""
from __future__ import annotations

import re

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_LINK = re.compile(r"(https?://|www\.|\b[\w-]+\.(com|net|org|de|ru|xyz|top|info|biz|io)\b)", re.IGNORECASE)


class ValidationError(ValueError):
    """Eingabe unzulaessig; ``code`` ist maschinenlesbar, ``args[0]`` die Meldung fuer Menschen."""

    def __init__(self, message: str, code: str = "bad_request") -> None:
        super().__init__(message)
        self.code = code


def clean(value: object, label: str, minimum: int, maximum: int, multiline: bool = False, allow_links: bool = False) -> str:
    """Normalisiert Leerraum, entfernt Steuerzeichen und prueft die Laenge (gezaehlt nach der Bereinigung)."""
    if not isinstance(value, str):
        raise ValidationError(f"{label} muss Text sein.")
    text = _CONTROL.sub("", value.replace("\r\n", "\n").replace("\r", "\n"))
    if multiline:
        lines = [" ".join(line.split()) for line in text.split("\n")]
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    else:
        text = " ".join(text.split())
    if len(text) < minimum:
        raise ValidationError(f"{label}: mindestens {minimum} Zeichen." if minimum > 1 else f"{label} darf nicht leer sein.")
    if len(text) > maximum:
        raise ValidationError(f"{label}: höchstens {maximum} Zeichen.")
    if not allow_links and _LINK.search(text):
        raise ValidationError(f"{label}: bitte ohne Links oder Internetadressen.", "links_not_allowed")
    return text
