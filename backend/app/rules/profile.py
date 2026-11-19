"""Regelprofil = Deck-Variante + Regeloptionen (``RuleOptions``).

``profile_id`` ist abgeleitet und nur beschreibend: ``ddv_tsr_2026`` (48 Karten, DDV-Defaults),
``house_no_nines`` (40 Karten, sonst Defaults) oder ``custom`` (alles andere). Deck-Variante und
Optionen werden vor Rundenbeginn gewaehlt und waehrend einer Runde nicht mehr geaendert.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .cards import DeckVariant, hand_size
from .errors import RuleViolation
from .options import RuleOptions, settings_from_dict
from .trump import TrumpConfig


class RuleProfileId(str, Enum):
    DDV_TSR_2026 = "ddv_tsr_2026"          # offizielle Turnierregeln: 48 Karten, DDV-Defaults
    HOUSE_NO_NINES = "house_no_nines"      # Scharfer Doppelkopf, sonst Defaults
    CUSTOM = "custom"                      # beliebige Optionskombination


@dataclass(frozen=True)
class RuleProfile:
    deck_variant: DeckVariant
    options: RuleOptions = field(default_factory=RuleOptions)
    normal_games_per_round: int = 24       # TSR 8.5.1
    bock_length: int = 4                   # "naechsten 4 Spiele"

    @property
    def id(self) -> RuleProfileId:
        if not self.options.is_ddv_default:
            return RuleProfileId.CUSTOM
        return (RuleProfileId.DDV_TSR_2026 if self.deck_variant is DeckVariant.WITH_NINES
                else RuleProfileId.HOUSE_NO_NINES)

    @property
    def is_official_ddv(self) -> bool:
        return self.id is RuleProfileId.DDV_TSR_2026

    @property
    def hand_size(self) -> int:
        return hand_size(self.deck_variant)

    @property
    def trick_count(self) -> int:
        return self.hand_size

    @property
    def first_announcement_min_cards(self) -> int:
        """TSR 6.2.2: 11 von 12 Karten. ANNAHME ohne Neunen: 9 von 10 (Fristen um 2 verschoben)."""
        return self.hand_size - 1

    @property
    def trump_config(self) -> TrumpConfig:
        return TrumpConfig(self.deck_variant, self.options.dulle)

    def min_cards_for_level(self, level: int, wedding_shift: int = 0) -> int:
        """Mindestkartenzahl fuer Stufe 0=Re/Kontra, 1=keine 90, 2=keine 60, 3=keine 30, 4=schwarz.

        TSR 6.2.2 / 6.3.4 (11,10,9,8,7) und 6.4.2 (Hochzeitsverschiebung um 0/1/2).
        """
        return self.first_announcement_min_cards - level - wedding_shift

    def to_dict(self) -> dict:
        return {"deckVariant": self.deck_variant.value, "options": self.options.to_dict()}

    @staticmethod
    def from_dict(data: dict) -> "RuleProfile":
        return make_profile(DeckVariant(data["deckVariant"]), RuleOptions.from_dict(data.get("options")))


def make_profile(deck_variant: DeckVariant = DeckVariant.WITH_NINES,
                 options: RuleOptions | None = None) -> RuleProfile:
    return RuleProfile(DeckVariant(deck_variant), options or RuleOptions())


def ddv_profile() -> RuleProfile:
    """Offizielles DDV-Profil (TSR Stand 21.02.2026): 48 Karten, 12 Stiche, DDV-Optionen."""
    return make_profile(DeckVariant.WITH_NINES)


def house_no_nines_profile() -> RuleProfile:
    """Scharfer Doppelkopf (40 Karten, 10 Stiche). Fristen-Annahme A1 siehe Regelmatrix."""
    return make_profile(DeckVariant.WITHOUT_NINES)


def validate_combination(profile_id: RuleProfileId | str, deck_variant: DeckVariant | str) -> None:
    """Prueft eine *behauptete* Kennung gegen die Deck-Variante (z. B. aus gespeicherten Daten)."""
    pid, deck = RuleProfileId(profile_id), DeckVariant(deck_variant)
    if pid is RuleProfileId.DDV_TSR_2026 and deck is not DeckVariant.WITH_NINES:
        raise RuleViolation("invalid_profile_combination",
                            "Das DDV-Turnierprofil verlangt 48 Karten mit Neunen (TSR 2.2.1).")
    if pid is RuleProfileId.HOUSE_NO_NINES and deck is not DeckVariant.WITHOUT_NINES:
        raise RuleViolation("invalid_profile_combination", "Das Profil ohne Neunen verlangt 40 Karten.")


def profile_from_settings(data: dict | None) -> RuleProfile:
    """Einstellungsobjekt der Oberflaeche (``sharp_doppelkopf`` + Optionen) -> Regelprofil."""
    return make_profile(*settings_from_dict(data))
