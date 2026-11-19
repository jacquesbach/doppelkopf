"""Bedienpflicht (TSR 5.2) und Stichgewinner (TSR 5.3.3)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .cards import Card, DeckVariant
from .cards import Rank, Suit
from .trump import GameType, Variant, as_config, is_trump, lead_kind, strength, trump_rank_map


def playable_cards(hand: Sequence[Card], lead: Card | None, game_type: GameType,
                   variant: Variant) -> list[Card]:
    """Karten, die gespielt werden duerfen.

    Bedienpflicht: aufgespielte Fehlfarbe bzw. Trumpf muss bedient werden, wenn moeglich
    (TSR 5.2.2). Wer nicht bedienen kann, darf jede Karte legen (5.2.3).
    """
    if lead is None:
        return list(hand)
    kind = lead_kind(lead, game_type, variant)
    if kind == "trump":
        matching = [c for c in hand if is_trump(c, game_type, variant)]
    else:
        matching = [c for c in hand if c.suit == kind and not is_trump(c, game_type, variant)]
    return matching or list(hand)


@dataclass(frozen=True)
class Play:
    seat: int
    card: Card


_DULLE = (Rank.TEN, Suit.HEARTS)


def trick_winner_index(plays: Sequence[Play], game_type: GameType, variant: Variant,
                       second_dulle_wins: bool = False) -> int:
    """Index (in ``plays``) der stichgewinnenden Karte.

    Gleiche Karten: die zuerst gelegte ist hoeher - auch die Herz-10 (TSR 5.3.3).
    Das ergibt sich daraus, dass nur eine *streng* staerkere Karte die fuehrende ersetzt.
    Hausregel ``second_dulle_wins``: die zweite Dulle sticht die erste (nur wo die Herz-10
    tatsaechlich Dulle ist, d. h. mit Dulle-Regel und als Trumpf).
    """
    cfg = as_config(variant)
    dulle_active = second_dulle_wins and cfg.dulle and _DULLE in trump_rank_map(game_type, cfg)
    lead = plays[0].card
    kind = lead_kind(lead, game_type, variant)
    best = 0
    for i in range(1, len(plays)):
        challenger, incumbent = plays[i].card, plays[best].card
        ch_trump = is_trump(challenger, game_type, variant)
        in_trump = is_trump(incumbent, game_type, variant)
        if ch_trump and not in_trump:
            best = i
        elif ch_trump and in_trump:
            if strength(challenger, game_type, variant) < strength(incumbent, game_type, variant):
                best = i
            elif dulle_active and challenger.face == _DULLE and incumbent.face == _DULLE:
                best = i
        elif not ch_trump and not in_trump:
            # Nur Karten der aufgespielten Fehlfarbe koennen gewinnen.
            if (kind != "trump" and challenger.suit == kind and incumbent.suit == kind
                    and strength(challenger, game_type, variant) < strength(incumbent, game_type, variant)):
                best = i
    return best


def trick_points(plays: Sequence[Play]) -> int:
    return sum(p.card.value for p in plays)


@dataclass(frozen=True)
class CompletedTrick:
    """Ein vollendeter Stich (1-basierter ``number``)."""
    number: int
    plays: tuple[Play, ...]
    winner_seat: int
    points: int

    @property
    def winning_card(self) -> Card:
        return next(p.card for p in self.plays if p.seat == self.winner_seat)

    def to_dict(self) -> dict:
        return {
            "number": self.number, "winnerSeat": self.winner_seat, "points": self.points,
            "plays": [{"seat": p.seat, "card": p.card.to_dict()} for p in self.plays],
        }

    @staticmethod
    def from_dict(data: dict) -> "CompletedTrick":
        return CompletedTrick(
            data["number"],
            tuple(Play(p["seat"], Card.from_dict(p["card"])) for p in data["plays"]),
            data["winnerSeat"], data["points"],
        )
