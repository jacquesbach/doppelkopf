"""Optional zuschaltbare Regeln (Hausregeln) - alle einzeln an- und abschaltbar.

Defaults entsprechen den DDV-Turnierspielregeln: nur *Spiel mit Dullen*, *Karlchen* und
*Fuchsjagd* sind an. Das Deck (mit/ohne Neunen) ist keine Option in
``RuleOptions``, sondern die separate ``DeckVariant``; ``rule_schema()`` fuehrt es der
Oberflaeche zuliebe trotzdem mit auf.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from .cards import DeckVariant
from .errors import RuleViolation


@dataclass(frozen=True)
class RuleOptions:
    # --- Gängige Varianten ---
    dulle: bool = True                          # Herz-10 ist hoechster Trumpf; aus: normale Herz-Karte
    karlchen: bool = True                       # Sonderpunkt: letzten Stich mit Kreuz-Bube gewinnen
    fuchsjagd: bool = True                      # Sonderpunkt: gegnerischen Fuchs (Karo-Ass) gefangen
    mandatory_announcements: bool = False       # Gewinner des 1. Stichs muss Re/Kontra ansagen (nur Normalspiel)
    solo_leads: bool = False                    # Solo-Spieler spielt immer aus (auch im Lustsolo)
    # --- Hausregeln ---
    karlchen_caught: bool = False               # Sonderpunkt: gegnerischen Kreuz-Buben im letzten Stich fangen
    schweinchen: bool = False                   # 2x Karo-Ass auf der Hand: zu hoechsten Truempfen erklaerbar
    bock_heart_trick: bool = False              # Bockrunde nach Stich aus 4 Herz-Fehlkarten
    bock_zero_game: bool = False                # Bockrunde nach Spiel mit 0 Punkten
    bock_120: bool = False                      # Bockrunde bei 120:120 Augen
    second_dulle_wins: bool = False             # zweite Dulle sticht die erste
    second_dulle_wins_except_last: bool = False  # ausser im letzten Stich

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
    OptionSpec("dulle", "dulle", "popular", True, "Dulle als Höchsttrumpf",
               "Die Herz-Zehn („Dulle“) steht über allen anderen Trümpfen. Ausgeschaltet ist sie eine gewöhnliche Herz-Karte."),
    OptionSpec("sharp_doppelkopf", None, "popular", False, "Ohne Neunen (40 Karten)",
               "Die Neunen werden aussortiert. Jede Person bekommt 10 Karten, das Spiel dauert 10 Stiche."),
    OptionSpec("karlchen", "karlchen", "popular", True, "Karlchen-Punkt",
               "Wer den letzten Stich mit dem Kreuz-Buben („Karlchen“) gewinnt, holt für seine Partei einen Extrapunkt."),
    OptionSpec("fuchsjagd", "fuchsjagd", "popular", True, "Füchse jagen",
               "Extrapunkt für die Partei, die in einem Stich ein Karo-Ass („Fuchs“) der Gegenpartei einsammelt."),
    OptionSpec("mandatory_announcements", "mandatory_announcements", "popular", False, "Ansagepflicht nach dem ersten Stich",
               "Wer den ersten Stich holt, muss danach „Re“ oder „Kontra“ ansagen, bevor es weitergeht. Gilt nur im Normalspiel."),
    OptionSpec("solo_leads", "solo_leads", "popular", False, "Solist kommt raus",
               "Wer ein Solo spielt, legt auch dann die erste Karte aus, wenn er nicht links vom Geber sitzt."),
    OptionSpec("karlchen_caught", "karlchen_caught", "pub", False, "Gegnerisches Karlchen abfangen",
               "Extrapunkt, wenn im letzten Stich der Kreuz-Bube der Gegenpartei in den Stich deiner Partei fällt."),
    OptionSpec("schweinchen", "schweinchen", "pub", False, "Schweinchen",
               "Wer beide Karo-Asse auf der Hand hält, darf sie vor der ersten Karte zu den höchsten Trümpfen erklären."),
    OptionSpec("bock_heart_trick", "bock_heart_trick", "pub", False, "Bock nach Herz-Stich",
               "Besteht ein Stich ausschließlich aus Herz-Fehlkarten, zählen die nächsten vier Spiele doppelt (Bockrunde)."),
    OptionSpec("bock_zero_game", "bock_zero_game", "pub", False, "Bock nach Nullspiel",
               "Endet ein Spiel ohne jede Punktänderung (0 Punkte), zählen die nächsten vier Spiele doppelt (Bockrunde)."),
    OptionSpec("bock_120", "bock_120", "pub", False, "Bock bei 120 zu 120",
               "Erreichen beide Parteien genau 120 Augen, zählen die nächsten vier Spiele doppelt (Bockrunde)."),
    OptionSpec("second_dulle_wins", "second_dulle_wins", "pub", False, "Zweite Dulle schlägt die erste",
               "Fallen beide Dullen in denselben Stich, gewinnt ihn die später gespielte.", requires="dulle"),
    OptionSpec("second_dulle_wins_except_last", "second_dulle_wins_except_last", "pub", False, "Ausnahme im letzten Stich",
               "Im allerletzten Stich gilt die Ausnahme: Dort gewinnt die zuerst gespielte Dulle.", requires="second_dulle_wins"),
)


def rule_schema() -> list[dict]:
    """Beschreibung aller Optionen fuer die Einstellungsseite (Reihenfolge wie in der Tabelle oben)."""
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
