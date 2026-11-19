"""Karten, Deck-Varianten und Augenwerte (TSR 2.2).

Kartenkennung ``rank-suit-copy`` (z. B. ``10-♥-0``) bleibt kompatibel zum bisherigen
Frontend und zur alten Python-Engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Suit(str, Enum):
    CLUBS = "♣"      # Kreuz
    SPADES = "♠"     # Pik
    HEARTS = "♥"     # Herz
    DIAMONDS = "♦"   # Karo


class Rank(str, Enum):
    ACE = "A"
    TEN = "10"
    KING = "K"
    QUEEN = "Q"      # Dame
    JACK = "J"       # Bube
    NINE = "9"


class DeckVariant(str, Enum):
    WITH_NINES = "with_nines"        # 48 Karten, 12 Handkarten (DDV, TSR 2.2.1)
    WITHOUT_NINES = "without_nines"  # 40 Karten, 10 Handkarten (eigenstaendige Variante)


# TSR 2.2.2: Zaehlwerte (Augen)
CARD_VALUES: dict[Rank, int] = {
    Rank.ACE: 11, Rank.TEN: 10, Rank.KING: 4, Rank.QUEEN: 3, Rank.JACK: 2, Rank.NINE: 0,
}
TOTAL_POINTS = 240

# Grundreihenfolge einer Fehlfarbe, absteigend (TSR 2.3.4-2.3.7); Trumpfkarten werden je Spieltyp entfernt.
BASE_SUIT_ORDER: tuple[Rank, ...] = (
    Rank.ACE, Rank.TEN, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE,
)


def ranks_for(variant: DeckVariant) -> tuple[Rank, ...]:
    if variant is DeckVariant.WITH_NINES:
        return BASE_SUIT_ORDER
    return tuple(r for r in BASE_SUIT_ORDER if r is not Rank.NINE)


def hand_size(variant: DeckVariant) -> int:
    """Handkarten pro Spieler = Anzahl Stiche."""
    return 12 if variant is DeckVariant.WITH_NINES else 10


@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: Rank
    copy: int  # 0 oder 1: jede Karte ist doppelt im Spiel

    @property
    def id(self) -> str:
        return f"{self.rank.value}-{self.suit.value}-{self.copy}"

    @property
    def value(self) -> int:
        return CARD_VALUES[self.rank]

    @property
    def face(self) -> tuple[Rank, Suit]:
        """Kartenbild ohne Kopie: zwei gleiche Karten haben dasselbe ``face``."""
        return (self.rank, self.suit)

    def to_dict(self) -> dict:
        return {"rank": self.rank.value, "suit": self.suit.value, "copy": self.copy}

    @staticmethod
    def from_dict(data: dict) -> "Card":
        return Card(Suit(data["suit"]), Rank(data["rank"]), int(data["copy"]))

    @staticmethod
    def from_id(card_id: str) -> "Card":
        rank, suit, copy_no = card_id.split("-")
        return Card(Suit(suit), Rank(rank), int(copy_no))

    def __repr__(self) -> str:  # kompakt fuer Testausgaben
        return f"{self.rank.value}{self.suit.value}#{self.copy}"


def build_deck(variant: DeckVariant) -> list[Card]:
    """Alle Karten in fester Grundreihenfolge (nicht gemischt)."""
    return [Card(suit, rank, c) for suit in Suit for rank in ranks_for(variant) for c in (0, 1)]


def card(text: str) -> Card:
    """Kurzschreibweise fuer Tests/Skripte: ``card('Q♣')`` oder ``card('10♥#1')`` (Kopie 1)."""
    face, _, copy_no = text.partition("#")
    return Card(Suit(face[-1]), Rank(face[:-1]), int(copy_no or 0))
