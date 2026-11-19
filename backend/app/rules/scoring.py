"""Gewinnermittlung und Wertung (TSR 7.1, 7.2) - rein, ohne Zustand.

Alle Bestandteile werden als benannte Posten gefuehrt (``code``, Punkte), damit Wertung,
Historie und UI nachvollziehbar bleiben. ``schwarz`` wird ueber *Stiche* entschieden
(TSR 6.3.1), nicht ueber Augen: mit Neunen kann ein Stich 0 Augen haben.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .announcements import LEVEL_CODES
from .cards import Rank, Suit
from .options import RuleOptions
from .parties import Party
from .tricks import CompletedTrick

# TSR 7.1: eigene Ziele bei Absage / Schwellen, wenn die Gegenpartei abgesagt hat
_OWN_TARGET = {1: 151, 2: 181, 3: 211}        # nach eigener Absage: keine 90/60/30
_VS_ABSAGE_TARGET = {1: 90, 2: 60, 3: 30}     # gegen Absage der Gegenpartei
_BONUS_TARGET = {1: 120, 2: 90, 3: 60, 4: 30}  # TSR 7.2.2 (e)/(f)
_FOX = (Rank.ACE, Suit.DIAMONDS)
_CHARLIE = (Rank.JACK, Suit.CLUBS)             # Karlchen = Kreuz-Bube


@dataclass(frozen=True)
class Item:
    code: str
    points: int


@dataclass
class GameScore:
    winner: Party | None
    points: dict[Party, int]
    tricks: dict[Party, int]
    items: dict[Party, list[Item]] = field(default_factory=dict)
    net: int = 0                        # Re minus Kontra, in Spielpunkten
    solo_scoring: bool = False
    seat_deltas: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    multiplier: int = 1                 # Bockrunde: 2

    def party_total(self, party: Party) -> int:
        return sum(i.points for i in self.items[party])

    def to_dict(self) -> dict:
        return {
            "winner": self.winner.value if self.winner else None,
            "points": {p.value: v for p, v in self.points.items()},
            "tricks": {p.value: v for p, v in self.tricks.items()},
            "items": {p.value: [{"code": i.code, "points": i.points} for i in lst]
                      for p, lst in self.items.items()},
            "net": self.net, "soloScoring": self.solo_scoring, "seatDeltas": list(self.seat_deltas),
            "multiplier": self.multiplier,
        }


def target_reached(party: Party, points: dict[Party, int], tricks: dict[Party, int],
                   levels: dict[Party, int], total_tricks: int) -> bool:
    """Hat ``party`` sein Gewinnziel erreicht (TSR 7.1.1 / 7.1.2)?"""
    own_absage = levels[party] if levels[party] >= 1 else 0
    opp_absage = levels[party.opponent] if levels[party.opponent] >= 1 else 0
    if own_absage:                                   # eigene Absage -> eigenes, hoeheres Ziel
        if own_absage == 4:
            return tricks[party] == total_tricks
        return points[party] >= _OWN_TARGET[own_absage]
    if opp_absage:                                   # Gegenpartei hat abgesagt
        if opp_absage == 4:
            return tricks[party] >= 1
        return points[party] >= _VS_ABSAGE_TARGET[opp_absage]
    only_kontra = levels[Party.KONTRA] >= 0 and levels[Party.RE] < 0
    if party is Party.RE:
        return points[party] >= (120 if only_kontra else 121)
    return points[party] >= (121 if only_kontra else 120)


def _tallies(tricks: Sequence[CompletedTrick], re_seats: Sequence[int]):
    points = {Party.RE: 0, Party.KONTRA: 0}
    counts = {Party.RE: 0, Party.KONTRA: 0}
    for t in tricks:
        party = Party.RE if t.winner_seat in re_seats else Party.KONTRA
        points[party] += t.points
        counts[party] += 1
    return points, counts


def _special_items(tricks: Sequence[CompletedTrick], re_seats: Sequence[int],
                   items: dict[Party, list[Item]], winner: Party | None, options: RuleOptions) -> None:
    """Sonderpunkte (TSR 7.2.3) - nur im Normalspiel mit zwei Re-Spielern; je Regel abschaltbar."""
    def party_of(seat: int) -> Party:
        return Party.RE if seat in re_seats else Party.KONTRA

    if winner is Party.KONTRA:
        items[Party.KONTRA].append(Item("beat_re", 1))               # gegen die Kreuz-Damen gewonnen
    for t in tricks:
        taker = party_of(t.winner_seat)
        if t.points >= 40:
            items[taker].append(Item("doppelkopf", 1))
        if options.fuchsjagd:
            for p in t.plays:
                if p.card.face == _FOX and party_of(p.seat) is not taker:
                    items[taker].append(Item("fox_caught", 1))
    last = tricks[-1]
    taker = party_of(last.winner_seat)
    if options.karlchen and last.winning_card.face == _CHARLIE:
        items[taker].append(Item("charlie_last_trick", 1))
    if options.karlchen_caught:                                      # Kneipenregel (Original: charlie_caught)
        for p in last.plays:
            if p.card.face == _CHARLIE and party_of(p.seat) is not taker:
                items[taker].append(Item("charlie_caught", 1))


def score_game(tricks: Sequence[CompletedTrick], re_seats: Sequence[int],
               levels: dict[Party, int], total_tricks: int, options: RuleOptions | None = None,
               multiplier: int = 1) -> GameScore:
    """Wertet ein vollstaendig gespieltes Spiel.

    ``re_seats`` hat zwei Eintraege (Normalspiel) oder einen (Solo, Stille Hochzeit,
    Hochzeit-als-Solo); bei einem Eintrag gilt TSR 7.2.4 (keine Sonderpunkte, Solist x3).
    """
    options = options or RuleOptions()
    if len(tricks) != total_tricks:
        raise ValueError("Wertung nur fuer vollstaendige Spiele")
    solo = len(re_seats) == 1
    points, counts = _tallies(tricks, re_seats)
    reached = {p: target_reached(p, points, counts, levels, total_tricks) for p in Party}
    if reached[Party.RE] and reached[Party.KONTRA]:
        raise AssertionError("Beide Parteien koennen ihr Ziel nicht gleichzeitig erreichen")
    winner = Party.RE if reached[Party.RE] else Party.KONTRA if reached[Party.KONTRA] else None

    items: dict[Party, list[Item]] = {Party.RE: [], Party.KONTRA: []}

    def under_items(party: Party) -> None:       # TSR 7.2.2 (a), Teil "gespielt"
        lost = points[party.opponent]
        for limit, code in ((90, "under_90"), (60, "under_60"), (30, "under_30")):
            if lost < limit:
                items[party].append(Item(code, 1))
        if counts[party.opponent] == 0:
            items[party].append(Item("black", 1))

    if winner is not None:
        items[winner].append(Item("win", 1))                           # (a) Grundwert
        under_items(winner)
        for party in Party:                                            # (b) Ansagen: je 2 Punkte
            if levels[party] >= 0:
                items[winner].append(Item(f"announced_{party.value}", 2))
            for level in range(1, levels[party] + 1):                  # (c)/(d) Absagen: je 1 Punkt
                items[winner].append(Item(f"called_{party.value}_{LEVEL_CODES[level]}", 1))
    else:
        # TSR 7.1.3: kein Sieger -> nur (a) "gespielt"-Posten, (e)/(f) und Sonderpunkte;
        # kein Grundwert, keine Ansage-/Absagepunkte (vgl. 6.3.3).
        for party in Party:
            under_items(party)

    for party in Party:                                                # (e)/(f) Absage geschlagen
        for level in range(1, levels[party.opponent] + 1):
            if points[party] >= _BONUS_TARGET[level]:
                items[party].append(Item(f"beat_{LEVEL_CODES[level]}", 1))

    if not solo:
        _special_items(tricks, re_seats, items, winner, options)

    net = sum(i.points for i in items[Party.RE]) - sum(i.points for i in items[Party.KONTRA])
    deltas = [0, 0, 0, 0]
    for seat in range(4):
        if seat in re_seats:
            deltas[seat] = net * 3 if solo else net
        else:
            deltas[seat] = -net
    deltas = [d * multiplier for d in deltas]                         # Bockrunde: Punkte verdoppelt
    return GameScore(winner, points, counts, items, net, solo, deltas, multiplier)
