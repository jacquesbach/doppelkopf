"""Optional zuschaltbare Regeln (Hausregeln/Kneipenregeln) - alle einzeln an- und abschaltbar.

Defaults entsprechen den DDV-Turnierspielregeln: nur *Spiel mit Dullen*, *Karlchen* und
*Fuchsjagd* sind an. Das Deck (mit/ohne Neunen = "Scharfer Doppelkopf") ist keine Option in
``RuleOptions``, sondern die separate ``DeckVariant``; ``rule_schema()`` fuehrt es der
Oberflaeche zuliebe trotzdem mit auf.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from .cards import DeckVariant
from .errors import RuleViolation


@dataclass(frozen=True)
class RuleOptions:
    # --- Beliebte Regeln ---
    dulle: bool = True                          # Herz-10 ist hoechster Trumpf; aus: normale Herz-Karte
    karlchen: bool = True                       # Sonderpunkt: letzten Stich mit Kreuz-Bube gewinnen
    fuchsjagd: bool = True                      # Sonderpunkt: gegnerischen Fuchs (Karo-Ass) gefangen
    mandatory_announcements: bool = False       # Gewinner des 1. Stichs muss Re/Kontra ansagen (nur Normalspiel)
    solo_leads: bool = False                    # Solo-Spieler spielt immer aus (auch im Lustsolo)
    # --- Kneipenregeln ---
    karlchen_caught: bool = False               # Sonderpunkt: gegnerischen Kreuz-Buben im letzten Stich fangen
    schweinchen: bool = False                   # 2x Karo-Ass auf der Hand: zu hoechsten Truempfen erklaerbar
    bock_heart_trick: bool = False              # Bockrunde nach Stich aus 4 Herz-Fehlkarten
    bock_zero_game: bool = False                # Bockrunde nach Spiel mit 0 Punkten
    bock_120: bool = False                      # Bockrunde bei 120:120 Augen
    second_dulle_wins: bool = False             # zweite Dulle sticht die erste
    second_dulle_wins_except_last: bool = False  # ... ausser im letzten Stich

    def __post_init__(self) -> None:
        for spec in OPTION_SPECS:
            if spec.key and spec.requires and getattr(self, spec.key) and not getattr(self, spec.requires):
                raise RuleViolation(
                    "invalid_option_combination",
                    f"'{spec.key}' setzt '{spec.requires}' voraus.",
                )

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict | None) -> "RuleOptions":
        """Unbekannte Schluessel und Nicht-Booleans werden abgelehnt; fehlende Schluessel = Default."""
        data = data or {}
        known = {f.name for f in fields(RuleOptions)}
        unknown = set(data) - known
        if unknown:
            raise RuleViolation("unknown_option", f"Unbekannte Regeloption: {', '.join(sorted(unknown))}")
        if any(not isinstance(v, bool) for v in data.values()):
            raise RuleViolation("invalid_option_value", "Regeloptionen muessen wahr/falsch sein.")
        return RuleOptions(**data)

    @property
    def is_ddv_default(self) -> bool:
        return self == RuleOptions()


@dataclass(frozen=True)
class OptionSpec:
    id: str                      # Kennung fuer die Oberflaeche
    key: str | None              # Feld in RuleOptions (None: wirkt auf die Deck-Variante)
    group: str                   # 'popular' | 'pub'
    default: bool
    label: str
    description: str
    requires: str | None = None  # Option, die an sein muss


OPTION_SPECS: tuple[OptionSpec, ...] = (
    OptionSpec("dulle", "dulle", "popular", True, "Spiel mit Dullen",
               "Die Herz Zehn (Dulle) ist der höchste Trumpf im Spiel."),
    OptionSpec("sharp_doppelkopf", None, "popular", False, "Scharfer Doppelkopf",
               "Es gibt keine Neunen im Spiel. Jeder Spieler erhält nur 10 Karten."),
    OptionSpec("karlchen", "karlchen", "popular", True, "Karlchen",
               "Du kriegst einen Sonderpunkt, wenn du den letzten Stich mit dem Kreuz Buben (Karlchen) gewinnst."),
    OptionSpec("fuchsjagd", "fuchsjagd", "popular", True, "Fuchsjagd",
               "Du kriegst einen Sonderpunkt, wenn du ein Karo Ass (Fuchs) eines Gegners in einem Stich gewinnst."),
    OptionSpec("mandatory_announcements", "mandatory_announcements", "popular", False, "Pflichtansagen",
               "Wer den ersten Stich gewinnt, muss 'Re' oder 'Kontra' ansagen (nur im Normalspiel)."),
    OptionSpec("solo_leads", "solo_leads", "popular", False, "Solo spielt aus",
               "Ein Solo-Spieler eröffnet immer den ersten Stich."),
    OptionSpec("karlchen_caught", "karlchen_caught", "pub", False, "Karlchen fangen",
               "Du kriegst einen Sonderpunkt, wenn du den Kreuz Buben (Karlchen) eines Gegners im letzten Stich fängst."),
    OptionSpec("schweinchen", "schweinchen", "pub", False, "Schweinchen",
               "Ein Spieler mit Schweinchen (2x Karo Ass auf der Hand) kann die Karo Asse zu den höchsten Trümpfe im Spiel erklären."),
    OptionSpec("bock_heart_trick", "bock_heart_trick", "pub", False, "Bockrunde bei Herzstich",
               "Wenn ein Stich mit 4 Herz Fehlkarten läuft, werden die Punkte in den nächsten 4 Spielen verdoppelt (Bockrunde)."),
    OptionSpec("bock_zero_game", "bock_zero_game", "pub", False, "Bockrunde bei Nullspiel",
               "Wenn ein Spiel mit 0 Punkten endet, werden die Punkte in den nächsten 4 Spielen verdoppelt (Bockrunde)."),
    OptionSpec("bock_120", "bock_120", "pub", False, "Bockrunde bei 120 Punkten",
               "Wenn beide Parteien 120 Augen gewinnen, werden die Punkte in den nächsten 4 Spielen verdoppelt (Bockrunde)."),
    OptionSpec("second_dulle_wins", "second_dulle_wins", "pub", False, "Zweite Dulle sticht die erste Dulle",
               "Werden beide Dullen im selben Stich gespielt, sticht die zweite Dulle die erste.", requires="dulle"),
    OptionSpec("second_dulle_wins_except_last", "second_dulle_wins_except_last", "pub", False, "... außer im letzten Stich",
               "Wenn beide Dullen im letzten Stich gespielt werden, gewinnt die erste Dulle.", requires="second_dulle_wins"),
)


def rule_schema() -> list[dict]:
    """Beschreibung aller Optionen fuer die Einstellungsseite (Reihenfolge wie im Original)."""
    return [{"id": s.id, "group": s.group, "default": s.default, "label": s.label,
             "description": s.description, "requires": s.requires} for s in OPTION_SPECS]


def settings_from_dict(data: dict | None) -> tuple[DeckVariant, RuleOptions]:
    """Einstellungsobjekt der Oberflaeche -> (Deck-Variante, Regeloptionen).

    ``sharp_doppelkopf=True`` waehlt das 40er Blatt ohne Neunen, sonst das 48er Blatt.
    """
    data = dict(data or {})
    sharp = data.pop("sharp_doppelkopf", False)
    if not isinstance(sharp, bool):
        raise RuleViolation("invalid_option_value", "sharp_doppelkopf muss wahr/falsch sein.")
    return (DeckVariant.WITHOUT_NINES if sharp else DeckVariant.WITH_NINES), RuleOptions.from_dict(data)


def normalize_settings(data: dict | None) -> dict[str, bool]:
    """Validiert Einstellungen und liefert sie vollstaendig (``sharp_doppelkopf`` + alle Optionen)."""
    deck, options = settings_from_dict(data)
    return {"sharp_doppelkopf": deck is DeckVariant.WITHOUT_NINES, **options.to_dict()}
