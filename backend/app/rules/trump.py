"""Spieltypen, Trumpfreihenfolge und Fehlfarbenreihenfolge (TSR 2.3).

Kein Zufall, kein Zustand: reine Funktionen ueber (Spieltyp, Deck-Variante).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache

from .cards import BASE_SUIT_ORDER, Card, DeckVariant, Rank, Suit, ranks_for


class GameType(str, Enum):
    NORMAL = "normal"                # Normalspiel (inkl. angemeldeter Hochzeit, solange nicht Solo)
    SOLO_CLUBS = "solo_clubs"        # Farbsolo Kreuz
    SOLO_SPADES = "solo_spades"      # Farbsolo Pik
    SOLO_HEARTS = "solo_hearts"      # Farbsolo Herz
    SOLO_DIAMONDS = "solo_diamonds"  # Farbsolo Karo (Kartenrang = Normalspiel)
    SOLO_QUEENS = "solo_queens"      # Damensolo
    SOLO_JACKS = "solo_jacks"        # Bubensolo
    SOLO_ACES = "solo_aces"          # Fleischloser / Asse-Solo

    @property
    def is_solo(self) -> bool:
        return self is not GameType.NORMAL


# Alle waehlbaren Soli (TSR 2.3.3: Farbsolo x4, Damensolo, Bubensolo, Fleischloser)
SOLO_TYPES: tuple[GameType, ...] = tuple(t for t in GameType if t.is_solo)

_COLOR_SOLO_SUIT = {
    GameType.SOLO_CLUBS: Suit.CLUBS, GameType.SOLO_SPADES: Suit.SPADES,
    GameType.SOLO_HEARTS: Suit.HEARTS, GameType.SOLO_DIAMONDS: Suit.DIAMONDS,
}

_QUEENS = [(Rank.QUEEN, s) for s in (Suit.CLUBS, Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS)]
_JACKS = [(Rank.JACK, s) for s in (Suit.CLUBS, Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS)]
_HEART_TEN = (Rank.TEN, Suit.HEARTS)
_FOX = (Rank.ACE, Suit.DIAMONDS)


@dataclass(frozen=True)
class TrumpConfig:
    """Alles, was die Kartenrangfolge beeinflusst: Deck, Dulle-Regel, erklaertes Schweinchen."""
    variant: DeckVariant = DeckVariant.WITH_NINES
    dulle: bool = True            # aus: Herz-10 ist normale Herz-Karte
    schweinchen: bool = False     # beide Karo-Asse sind hoechste Truempfe (nur wo Karo-Ass Trumpf ist)


Variant = DeckVariant | TrumpConfig


def as_config(variant: Variant) -> TrumpConfig:
    return variant if isinstance(variant, TrumpConfig) else TrumpConfig(variant)


def trump_order(game_type: GameType, variant: Variant) -> tuple[tuple[Rank, Suit], ...]:
    """Absteigende Rangfolge der Trumpfkartenbilder (TSR 2.3.4 - 2.3.7)."""
    return _trump_order(game_type, as_config(variant))


@lru_cache(maxsize=None)
def _trump_order(game_type: GameType, cfg: TrumpConfig) -> tuple[tuple[Rank, Suit], ...]:
    with_nines = cfg.variant is DeckVariant.WITH_NINES
    if game_type is GameType.SOLO_QUEENS:
        return tuple(_QUEENS)
    if game_type is GameType.SOLO_JACKS:
        return tuple(_JACKS)
    if game_type is GameType.SOLO_ACES:
        return ()
    # Normalspiel und Farbsolo: Herz-10, Damen, Buben, dann Trumpffarbe (Normal = Karo).
    trump_suit = _COLOR_SOLO_SUIT.get(game_type, Suit.DIAMONDS)
    order: list[tuple[Rank, Suit]] = [_HEART_TEN, *_QUEENS, *_JACKS] if cfg.dulle else [*_QUEENS, *_JACKS]
    for rank in (Rank.ACE, Rank.TEN, Rank.KING, Rank.NINE):
        if rank is Rank.NINE and not with_nines:
            continue
        face = (rank, trump_suit)
        if face not in order:  # mit Dulle steht Herz-10 schon ganz oben (TSR 2.3.5: "ausser Herz-10")
            order.append(face)
    if cfg.schweinchen and _FOX in order:   # erklaertes Schweinchen: Karo-Asse vor allem anderen
        order.remove(_FOX)
        order.insert(0, _FOX)
    return tuple(order)


def trump_rank_map(game_type: GameType, variant: Variant) -> dict[tuple[Rank, Suit], int]:
    return _rank_map(game_type, as_config(variant))


@lru_cache(maxsize=None)
def _rank_map(game_type: GameType, cfg: TrumpConfig) -> dict[tuple[Rank, Suit], int]:
    return {face: i for i, face in enumerate(_trump_order(game_type, cfg))}


def suit_order(game_type: GameType, variant: Variant, suit: Suit) -> tuple[Rank, ...]:
    """Absteigende Rangfolge der Fehlkarten einer Farbe (ohne Trumpfkarten)."""
    return _suit_order(game_type, as_config(variant), suit)


@lru_cache(maxsize=None)
def _suit_order(game_type: GameType, cfg: TrumpConfig, suit: Suit) -> tuple[Rank, ...]:
    trumps = _rank_map(game_type, cfg)
    return tuple(r for r in BASE_SUIT_ORDER if r in ranks_for(cfg.variant) and (r, suit) not in trumps)


def is_trump(card: Card, game_type: GameType, variant: Variant) -> bool:
    return card.face in trump_rank_map(game_type, variant)


def lead_kind(card: Card, game_type: GameType, variant: Variant) -> Suit | str:
    """``'trump'`` oder die Fehlfarbe, die eine aufgespielte Karte fordert."""
    return "trump" if is_trump(card, game_type, variant) else card.suit


def strength(card: Card, game_type: GameType, variant: Variant) -> int:
    """Kleinerer Wert = staerker. Trumpf stets staerker als jede Fehlkarte (TSR 2.3.2).

    Innerhalb der Fehlfarben ist der Wert nur zwischen Karten *derselben* Farbe vergleichbar.
    """
    ranks = trump_rank_map(game_type, variant)
    if card.face in ranks:
        return ranks[card.face]
    return 1000 + suit_order(game_type, variant, card.suit).index(card.rank)


def trump_count(game_type: GameType, variant: Variant) -> int:
    """Anzahl Trumpfkarten im gesamten Spiel (jede Karte doppelt)."""
    return 2 * len(trump_order(game_type, variant))
