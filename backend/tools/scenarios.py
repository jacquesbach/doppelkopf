"""Kartenverteilungen fuer gezielte Bot-Messungen je Spielart (nur Werkzeug fuer ``bot_tournament``, nicht im Betrieb).

``make_game(rng, kind, variant, options)`` mischt ein Spiel und rueckt die Haende zurecht (nur Tausch zwischen zwei Haenden), damit die
gewuenschte Spielart entsteht: ``solo`` (zufaelliges der sieben Soli, meist mit passendem Blatt), ``wedding`` (ein Sitz mit beiden Kreuz-Damen),
``poverty`` (ein Sitz mit hoechstens 3 Truempfen, ein Kaeufer mit mindestens 6; Regel ``poverty`` muss an sein), ``schweinchen`` (ein Sitz mit beiden
Karo-Assen; Regel ``schweinchen`` an) und ``normal``. Alle Vorbehalts-Entscheidungen treffen danach die Bots wie im Betrieb.
"""
from __future__ import annotations

import random

from tests.rules import loader  # noqa: F401  (``app.rules`` ohne Flask)
from app.rules import Baptize, DeckVariant, RuleOptions, apply_action, make_profile
from app.rules.cards import Card, Rank, Suit
from app.rules.dealing import shuffled_deck
from app.rules.game import GameState, new_game
from app.rules.trump import SOLO_TYPES, GameType, TrumpConfig, is_trump

KINDS = ("normal", "solo", "wedding", "poverty", "schweinchen")
_QC = (Rank.QUEEN, Suit.CLUBS)
_FOX = (Rank.ACE, Suit.DIAMONDS)


def _swap(state: GameState, a: int, ca: Card, b: int, cb: Card) -> None:
    state.hands[a].remove(ca)
    state.hands[b].remove(cb)
    state.hands[a].append(cb)
    state.hands[b].append(ca)


def _give_faces(state: GameState, rng: random.Random, seat: int, face: tuple, count: int) -> None:
    """``seat`` soll ``count`` Karten dieses Kartenbildes halten."""
    while sum(c.face == face for c in state.hands[seat]) < count:
        src = next(((s, c) for s in range(4) if s != seat for c in state.hands[s] if c.face == face), None)
        if src is None:
            return
        keep = [c for c in state.hands[seat] if c.face != face]
        _swap(state, seat, rng.choice(keep), src[0], src[1])


def _trumps(state: GameState, seat: int, cfg: TrumpConfig, gt: GameType = GameType.NORMAL) -> list[Card]:
    return [c for c in state.hands[seat] if is_trump(c, gt, cfg)]


def _strengthen(state: GameState, rng: random.Random, seat: int, cfg: TrumpConfig, gt: GameType, want: int,
                avoid: frozenset = frozenset()) -> None:
    """Der Sitz bekommt (soweit moeglich) mindestens ``want`` Truempfe der Spielart ``gt``."""
    for _ in range(12):
        if len(_trumps(state, seat, cfg, gt)) >= want:
            return
        others = [(s, c) for s in range(4) if s != seat and s not in avoid for c in _trumps(state, s, cfg, gt)]
        weak = [c for c in state.hands[seat] if not is_trump(c, gt, cfg)]
        if not others or not weak:
            return
        s, c = rng.choice(others)
        _swap(state, seat, rng.choice(weak), s, c)


def _weaken(state: GameState, rng: random.Random, seat: int, cfg: TrumpConfig, at_most: int) -> None:
    for _ in range(12):
        mine = _trumps(state, seat, cfg)
        if len(mine) <= at_most:
            return
        others = [(s, c) for s in range(4) if s != seat for c in state.hands[s] if not is_trump(c, GameType.NORMAL, cfg)]
        s, c = rng.choice(others)
        _swap(state, seat, rng.choice(mine), s, c)


def make_game(rng: random.Random, kind: str, variant: DeckVariant, options: RuleOptions) -> GameState:
    """Neues Spiel der gewuenschten Art; bei ``solo`` beginnt es schon im Kartenspiel, sonst bei der Vorbehaltsabfrage."""
    if kind not in KINDS:
        raise ValueError(f"unbekannte Spielart {kind!r}; erlaubt: {', '.join(KINDS)}")
    profile = make_profile(variant, options)
    cfg = TrumpConfig(variant, options.dulle)
    dealer = rng.randrange(4)
    order = shuffled_deck(variant, rng)
    seat = rng.randrange(4)
    done = [rng.random() < 0.5 for _ in range(4)]
    if kind == "solo":
        done[seat] = False
        state = new_game(profile, order, dealer, tuple(done), forced_solo_seat=seat)
        solo = rng.choice(SOLO_TYPES)
        if rng.random() < 0.7:                                    # Solisten haben meist ein passendes Blatt
            if solo is GameType.SOLO_ACES:
                for suit in (Suit.CLUBS, Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS):
                    _give_faces(state, rng, seat, (Rank.ACE, suit), 1)
            else:
                _strengthen(state, rng, seat, cfg, solo, 6 if solo in (GameType.SOLO_QUEENS, GameType.SOLO_JACKS) else 7)
        apply_action(state, Baptize(seat, solo.value))
        return state
    state = new_game(profile, order, dealer, tuple(done))
    if kind == "wedding":
        _give_faces(state, rng, seat, _QC, 2)
    elif kind == "schweinchen":
        _give_faces(state, rng, seat, _FOX, 2)
    elif kind == "poverty":
        _weaken(state, rng, seat, cfg, 3)
        if sum(c.face == _QC for c in state.hands[seat]) == 2:    # sonst waere es eine Hochzeit
            other = next(s for s in range(4) if s != seat)
            _swap(state, seat, next(c for c in state.hands[seat] if c.face == _QC), other,
                  next(c for c in state.hands[other] if not is_trump(c, GameType.NORMAL, cfg)))
        _strengthen(state, rng, (seat + rng.choice((1, 2, 3))) % 4, cfg, GameType.NORMAL, 6, avoid=frozenset({seat}))
    return state
