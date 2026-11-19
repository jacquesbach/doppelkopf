"""Mischen und Geben (TSR 3.3). Zufall ist bewusst vom Regelkern getrennt.

Der Regelkern bekommt eine *fertige Kartenreihenfolge*; ``shuffled_deck`` ist nur eine
Hilfsfunktion fuer die Service-Schicht. Es wird fair (ohne Verteilungsfilter) gemischt:
die Zusatzbedingungen des Originals (``Hand.isPlayable``) sind kein DDV-Bestandteil.
"""
from __future__ import annotations

import random
import secrets
from typing import Sequence

from .cards import Card, DeckVariant, build_deck, hand_size
from .errors import RuleViolation


def shuffled_deck(variant: DeckVariant, rng: random.Random | None = None) -> list[Card]:
    deck = build_deck(variant)
    (rng or secrets.SystemRandom()).shuffle(deck)
    return deck


def _packets(variant: DeckVariant) -> tuple[int, ...]:
    # TSR 3.3.7: viermal drei Karten (48er Blatt). Beim 40er Blatt 3-3-4 (Packetgroesse ohne Regelwirkung).
    return (3, 3, 3, 3) if variant is DeckVariant.WITH_NINES else (3, 3, 4)


def deal(order: Sequence[Card], dealer: int, variant: DeckVariant) -> list[list[Card]]:
    """Verteilt eine fertige Kartenreihenfolge; Rueckgabe indiziert nach Sitz 0..3.

    Es wird beim linken Nachbarn des Gebers begonnen (TSR 3.3.7), also bei Sitz ``dealer + 1``.
    """
    expected = 4 * hand_size(variant)
    if len(order) != expected:
        raise RuleViolation("bad_deck", f"{expected} Karten erwartet, {len(order)} erhalten")
    if len({c.id for c in order}) != expected:
        raise RuleViolation("bad_deck", "Karten muessen eindeutig sein")
    hands: list[list[Card]] = [[] for _ in range(4)]
    pos = 0
    for size in _packets(variant):
        for k in range(4):
            seat = (dealer + 1 + k) % 4
            hands[seat].extend(order[pos:pos + size])
            pos += size
    return hands
