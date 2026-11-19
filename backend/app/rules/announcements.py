"""Ansagen und Absagen: Stufen, Zeitpunkte, Erwiderung (TSR 6).

Stufen je Partei: 0 = Re bzw. Kontra, 1 = keine 90, 2 = keine 60, 3 = keine 30, 4 = schwarz.
Stufen duerfen uebersprungen werden, wenn alle uebersprungenen Stufen zu diesem Zeitpunkt noch
zulaessig waeren; sie werden dann mitgewertet (TSR 6.4.3).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import RuleViolation
from .parties import Party
from .profile import RuleProfile

LEVEL_CODES = ("announce", "no_90", "no_60", "no_30", "black")
MAX_LEVEL = 4


def level_code(level: int) -> str:
    return LEVEL_CODES[level]


@dataclass
class PartyAnnouncements:
    """Hoechste angesagte Stufe je Partei (-1 = nichts) und Fristenstatus der Erstansage."""
    level: int = -1
    late_reply: bool = False  # Erstansage kam als verspaetete Erwiderung (TSR 6.4.4, 2. Satz)


@dataclass
class AnnouncementBook:
    re: PartyAnnouncements = field(default_factory=PartyAnnouncements)
    kontra: PartyAnnouncements = field(default_factory=PartyAnnouncements)

    def of(self, party: Party) -> PartyAnnouncements:
        return self.re if party is Party.RE else self.kontra

    def levels(self) -> dict[Party, int]:
        return {Party.RE: self.re.level, Party.KONTRA: self.kontra.level}

    def to_dict(self) -> dict:
        return {p.value: {"level": self.of(p).level, "lateReply": self.of(p).late_reply} for p in Party}

    @staticmethod
    def from_dict(data: dict) -> "AnnouncementBook":
        book = AnnouncementBook()
        for p in Party:
            book.of(p).level = data[p.value]["level"]
            book.of(p).late_reply = data[p.value]["lateReply"]
        return book


def check_announcement(profile: RuleProfile, book: AnnouncementBook, party: Party, target: int,
                       cards_in_hand: int, wedding_shift: int = 0) -> None:
    """Wirft ``RuleViolation``, wenn ``target`` jetzt nicht angesagt werden darf."""
    if not 0 <= target <= MAX_LEVEL:
        raise RuleViolation("unknown_announcement", "Unbekannte Ansage/Absage.")
    own, opp = book.of(party), book.of(party.opponent)
    if target <= own.level:
        raise RuleViolation("announcement_repeated", "Diese An-/Absage wurde bereits gemacht (TSR 6.4.7).")
    first_missing = own.level + 1
    if own.late_reply and target >= 1:
        raise RuleViolation(
            "absage_after_late_reply",
            "Nach einer verspaeteten Erwiderung sind keine Absagen mehr moeglich (TSR 6.4.4).",
        )

    def need(level: int) -> int:
        return profile.min_cards_for_level(level, wedding_shift)

    # Erwiderung (TSR 6.4.4): nur als Erstansage, mit einer Karte weniger als die Gegenpartei brauchte.
    if own.level == -1 and target == 0 and opp.level >= 0 and cards_in_hand >= need(opp.level) - 1:
        return
    for level in range(first_missing, target + 1):  # uebersprungene Stufen muessen noch zulaessig sein
        if cards_in_hand < need(level):
            raise RuleViolation(
                "announcement_too_late",
                f"Zu spaet: {level_code(level)} braucht mindestens {need(level)} Handkarten (TSR 6.2/6.3).",
            )


def apply_announcement(profile: RuleProfile, book: AnnouncementBook, party: Party, target: int,
                       cards_in_hand: int, wedding_shift: int = 0) -> None:
    """Prueft und bucht die Ansage in ``book``."""
    check_announcement(profile, book, party, target, cards_in_hand, wedding_shift)
    own = book.of(party)
    if own.level == -1 and cards_in_hand < profile.min_cards_for_level(0, wedding_shift):
        own.late_reply = True
    own.level = target


def allowed_levels(profile: RuleProfile, book: AnnouncementBook, party: Party, cards_in_hand: int,
                   wedding_shift: int = 0) -> list[int]:
    result = []
    for target in range(MAX_LEVEL + 1):
        try:
            check_announcement(profile, book, party, target, cards_in_hand, wedding_shift)
        except RuleViolation:
            continue
        result.append(target)
    return result
