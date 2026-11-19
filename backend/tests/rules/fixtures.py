"""Gemeinsame Hilfen: feste Kartenverteilungen, Spielskripte, Zufallsspiel."""
from __future__ import annotations

import random

from . import loader  # noqa: F401
from app.rules.cards import Card, DeckVariant, build_deck, card
from app.rules.dealing import deal
from app.rules.game import (Announce, Baptize, Declare, DeclareSchweinchen, GameState, Phase, PlayCard,
                             PovertyOffer, PovertyPass, PovertyReturn, Resolve, apply_action, legal_actions,
                             new_game)
from app.rules.profile import ddv_profile, house_no_nines_profile

WITH, WITHOUT = DeckVariant.WITH_NINES, DeckVariant.WITHOUT_NINES
DDV = ddv_profile()
HOUSE = house_no_nines_profile()

# Vier komplette 12-Karten-Haende (Geber = Sitz 3, Sitz 0 spielt auf). Hochzeiter ist Sitz 1.
WEDDING_HANDS = {
    0: "Q♠ Q♠ J♣ J♣ A♦ A♦ A♣ A♣ 10♣ 10♣ K♣ K♣",
    1: "Q♣ Q♣ 10♥ 10♥ J♦ J♦ A♠ A♠ 10♠ 10♠ K♠ K♠",
    2: "Q♥ Q♥ J♠ J♠ 10♦ 10♦ 9♣ 9♣ A♥ A♥ K♥ K♥",
    3: "Q♦ Q♦ J♥ J♥ K♦ K♦ 9♦ 9♦ 9♠ 9♠ 9♥ 9♥",
}
# Normalspiel: eine Kreuz-Dame zwischen Sitz 1 und 2 getauscht -> Re = {1, 2}, Kontra = {0, 3}
NORMAL_HANDS = dict(WEDDING_HANDS)
NORMAL_HANDS[1] = "Q♣ Q♥ 10♥ 10♥ J♦ J♦ A♠ A♠ 10♠ 10♠ K♠ K♠"
NORMAL_HANDS[2] = "Q♣ Q♥ J♠ J♠ 10♦ 10♦ 9♣ 9♣ A♥ A♥ K♥ K♥"

# Sitz 0 hat keinen Trumpf (fuer die Klaerung durch Abwurf, TSR 5.5.1 Nr. 5); Geber = Sitz 0 -> Sitz 1 spielt auf
DISCARD_HANDS = {
    0: "A♣ A♣ 10♣ 10♣ K♣ K♣ 9♣ 9♣ A♠ A♠ 10♠ 10♠",
    1: "Q♣ Q♠ Q♥ Q♦ J♣ J♠ J♥ J♦ A♦ 10♦ K♦ 9♦",
    2: "Q♣ Q♠ Q♥ Q♦ J♣ J♠ J♥ J♦ A♦ 10♦ K♦ 9♦",
    3: "10♥ 10♥ K♠ K♠ 9♠ 9♠ A♥ A♥ K♥ K♥ 9♥ 9♥",
}


def rig(hands: dict[int, str], dealer: int = 3, variant: DeckVariant = WITH) -> list[Card]:
    """Kartenreihenfolge, die ``deal`` genau in die angegebenen Haende verteilt."""
    base = build_deck(variant)
    positions = {c.id: i for i, c in enumerate(base)}
    dealt = deal(base, dealer, variant)
    order: list[Card] = [None] * len(base)  # type: ignore[list-item]
    used: dict[tuple, int] = {}
    for seat, text in hands.items():
        wanted = []
        for t in text.split():
            c = card(t)
            n = used.get(c.face, 0)
            used[c.face] = n + 1
            wanted.append(Card(c.suit, c.rank, n))
        assert len(wanted) == len(dealt[seat]), (seat, len(wanted))
        for slot, want in zip(dealt[seat], wanted):
            order[positions[slot.id]] = want
    assert len({c.id for c in order}) == len(base)
    return order


def start(hands=None, dealer=3, done=(False,) * 4, forced=None, profile=DDV):
    hands = hands or NORMAL_HANDS
    return new_game(profile, rig(hands, dealer, profile.deck_variant), dealer, done, forced)


def declare_all(state: GameState, reservations=()):
    """Alle vier antworten in Reihenfolge; ``reservations`` = Sitze mit 'Vorbehalt'."""
    for k in range(1, 5):
        seat = (state.dealer + k) % 4
        apply_action(state, Declare(seat, seat in reservations))
    return state


def play(state: GameState, *cards: tuple[int, str]):
    for seat, text in cards:
        c = card(text)
        mine = next(x for x in state.hands[seat] if x.face == c.face)
        apply_action(state, PlayCard(seat, mine.id))


def auto_play(state: GameState, rng: random.Random, announce_chance: float = 0.0):
    """Spielt zufaellig, aber nur ueber ``legal_actions``, bis das Spiel endet."""
    guard = 0
    while state.phase is not Phase.FINISHED:
        guard += 1
        assert guard < 500, "Spiel terminiert nicht"
        step_random(state, rng, announce_chance)


def step_random(state: GameState, rng: random.Random, announce_chance: float = 0.0,
                reservation_chance: float = 0.0) -> None:
    ph = state.phase
    if ph is Phase.RESERVATION_QUERY:
        apply_action(state, Declare(state.query_seat, rng.random() < reservation_chance))
    elif ph is Phase.RESERVATION_RESOLUTION:
        seat = state.resolution_queue[0]
        apply_action(state, Resolve(seat, rng.random() < 0.5))
    elif ph is Phase.BAPTISM:
        seat = state.baptism_seat
        choice = rng.choice(legal_actions(state, seat)[0]["choices"])
        apply_action(state, Baptize(seat, choice))
    elif ph is Phase.POVERTY_PASS:
        seat = state.poverty_seat
        apply_action(state, PovertyPass(seat, tuple(rng.sample(legal_actions(state, seat)[0]["cards"], 3))))
    elif ph is Phase.POVERTY_OFFER:
        apply_action(state, PovertyOffer(state.poverty_queue[0], rng.random() < 0.5))
    elif ph is Phase.POVERTY_RETURN:
        seat = state.poverty_buyer
        apply_action(state, PovertyReturn(seat, tuple(rng.sample(legal_actions(state, seat)[0]["cards"], 3))))
    elif ph is Phase.PLAYING:
        for seat in range(4):                            # Schweinchen erklaeren, sobald moeglich
            if any(a["type"] == "schweinchen" for a in legal_actions(state, seat)) and rng.random() < 0.7:
                apply_action(state, DeclareSchweinchen(seat))
                return
        if announce_chance and rng.random() < announce_chance:
            options = [(s, a) for s in range(4) for a in legal_actions(state, s) if a["type"] == "announce"]
            if options:
                seat, act = rng.choice(options)
                apply_action(state, Announce(seat, rng.choice(act["levels"])))
                return
        seat = state.turn
        acts = legal_actions(state, seat)
        play_action = next((a for a in acts if a["type"] == "play_card"), None)
        if play_action is None:                          # Pflichtansage: erst ansagen, dann spielen
            ann = next(a for a in acts if a["type"] == "announce")
            apply_action(state, Announce(seat, ann["levels"][0]))
            return
        apply_action(state, PlayCard(seat, rng.choice(play_action["cards"])))
    else:
        raise AssertionError(ph)


def with_options(deck=WITH, **options):
    from app.rules.options import RuleOptions
    from app.rules.profile import make_profile
    return make_profile(deck, RuleOptions(**options))
