"""Szenario eines Test-Tisches: Regeln, Geber, Karten je Sitz, Besetzung, Rundenstand, Vorspielen.

Ein Szenario ist reine Daten (JSON). ``build_lab_table`` macht daraus einen gewoehnlichen ``TableState`` - mit demselben
Regelkern und derselben Tischschicht wie ein echter Tisch. Der einzige Unterschied: Die Kartenreihenfolge wird nicht
gemischt, sondern so gebaut, dass die gewuenschten Haende entstehen (nicht angegebene Karten werden zufaellig verteilt).
"""
from __future__ import annotations

import random
import time
from collections import Counter
from dataclasses import dataclass, field

from ..rules import Phase, RuleViolation, new_round, normalize_settings, profile_from_settings, start_next_game
from ..rules.cards import Card, DeckVariant, Rank, Suit, build_deck, hand_size, ranks_for
from ..rules.dealing import deal
from ..table.bots import next_bot_action
from ..table.state import TableState, redeal_if_needed, settle

MAX_ADVANCE_STEPS = 400
NAME_MAX = 32
ADVANCE_KINDS = ("none", "playing", "tricks")


def _bad(message: str) -> RuleViolation:
    return RuleViolation("bad_scenario", message)


@dataclass
class Scenario:
    settings: dict
    dealer: int = 0
    hands: dict[int, list[str]] = field(default_factory=dict)          # Sitz -> Karten ("Q♣", "10♥", ...)
    seats: list[dict] = field(default_factory=list)                    # 4 x {"name", "bot"}
    round: dict = field(default_factory=dict)                          # optionale Rundenwerte
    advance: str = "none"                                              # none | playing | tricks
    tricks: int = 0                                                    # bei advance == "tricks"
    title: str = ""

    @property
    def variant(self) -> DeckVariant:
        return DeckVariant.WITHOUT_NINES if self.settings.get("sharp_doppelkopf") else DeckVariant.WITH_NINES

    def to_dict(self) -> dict:
        return {"settings": dict(self.settings), "dealer": self.dealer,
                "hands": {str(k): list(v) for k, v in self.hands.items()},
                "seats": [dict(s) for s in self.seats], "round": dict(self.round),
                "advance": self.advance, "tricks": self.tricks, "title": self.title}


def _parse_face(text: object, variant: DeckVariant) -> tuple[Rank, Suit]:
    if not isinstance(text, str) or len(text) < 2:
        raise _bad(f"Ungültige Karte: {text!r}.")
    try:
        rank, suit = Rank(text[:-1]), Suit(text[-1])
    except ValueError:
        raise _bad(f"Unbekannte Karte: {text!r}.") from None
    if rank not in ranks_for(variant):
        raise _bad(f"Die Karte {text} gibt es in diesem Blatt nicht (Spiel ohne Neunen).")
    return rank, suit


def _int(value: object, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise _bad(f"{name} muss eine Zahl von {low} bis {high} sein.")
    return value


def parse_scenario(data: object) -> Scenario:
    """Prueft ein Szenario aus JSON und liefert die bereinigte Fassung; Fehler: ``RuleViolation('bad_scenario')``."""
    if not isinstance(data, dict):
        raise _bad("Das Szenario fehlt.")
    settings = normalize_settings(data.get("settings"))
    variant = DeckVariant.WITHOUT_NINES if settings["sharp_doppelkopf"] else DeckVariant.WITH_NINES
    size = hand_size(variant)
    dealer = _int(data.get("dealer", 0), "Geber", 0, 3)

    hands: dict[int, list[str]] = {}
    raw_hands = data.get("hands") or {}
    if not isinstance(raw_hands, dict):
        raise _bad("Die Karten müssen je Sitz angegeben werden.")
    counts: Counter = Counter()
    for key, cards in raw_hands.items():
        try:
            seat = int(key)
        except (TypeError, ValueError):
            raise _bad(f"Ungültiger Sitz: {key!r}.") from None
        if seat not in range(4):
            raise _bad(f"Ungültiger Sitz: {key!r}.")
        if not isinstance(cards, list):
            raise _bad("Die Karten eines Sitzes müssen eine Liste sein.")
        if len(cards) > size:
            raise _bad(f"Sitz {seat + 1}: höchstens {size} Karten.")
        faces = [_parse_face(c, variant) for c in cards]
        counts.update(faces)
        hands[seat] = [f"{r.value}{s.value}" for r, s in faces]
    for (rank, suit), n in counts.items():
        if n > 2:
            raise _bad(f"{rank.value}{suit.value} gibt es nur zweimal im Spiel.")

    raw_seats = data.get("seats")
    if raw_seats is None:
        raw_seats = [{"bot": False}] * 4
    if not isinstance(raw_seats, list) or len(raw_seats) != 4:
        raise _bad("Es werden genau vier Sitze gebraucht.")
    seats = []
    for i, s in enumerate(raw_seats):
        s = s if isinstance(s, dict) else {}
        bot = bool(s.get("bot"))
        default = f"Bot {i + 1}" if bot else f"Platz {i + 1}"
        name = str(s.get("name") or default).strip()[:NAME_MAX] or default
        seats.append({"name": name, "bot": bot})
    if all(s["bot"] for s in seats):
        raise _bad("Mindestens ein Sitz muss von dir gespielt werden (kein Bot).")

    advance = data.get("advance", "none") or "none"
    if advance not in ADVANCE_KINDS:
        raise _bad("Unbekannte Vorspiel-Art.")
    tricks = _int(data.get("tricks", 0) or 0, "Stiche", 0, size) if advance == "tricks" else 0

    return Scenario(settings, dealer, hands, seats, _parse_round(data.get("round")), advance, tricks,
                    str(data.get("title") or "")[:80])


def _parse_round(raw: object) -> dict:
    if raw in (None, {}):
        return {}
    if not isinstance(raw, dict):
        raise _bad("Die Rundenwerte sind ungültig.")
    out: dict = {}
    if "normalGamesPlayed" in raw:
        out["normalGamesPlayed"] = _int(raw["normalGamesPlayed"], "Gespielte Normalspiele", 0, 24)
    if "bockRemaining" in raw:
        out["bockRemaining"] = _int(raw["bockRemaining"], "Bockspiele", 0, 99)
    if "pflichtsoloDone" in raw:
        done = raw["pflichtsoloDone"]
        if not isinstance(done, list) or len(done) != 4:
            raise _bad("Pflichtsoli: vier Angaben nötig.")
        out["pflichtsoloDone"] = [bool(x) for x in done]
    if "totals" in raw:
        totals = raw["totals"]
        if not isinstance(totals, list) or len(totals) != 4:
            raise _bad("Punktestände: vier Zahlen nötig.")
        out["totals"] = [_int(t, "Punktestand", -9999, 9999) for t in totals]
    return out


def rigged_order(hands: dict[int, list[str]], dealer: int, variant: DeckVariant,
                 rng: random.Random | None = None) -> list[Card]:
    """Kartenreihenfolge, die ``deal`` so verteilt, dass jeder Sitz die angegebenen Karten bekommt.

    Karten, die nirgends vorgegeben sind, werden zufaellig auf die uebrigen Plaetze gelegt.
    """
    base = build_deck(variant)
    positions = {c.id: i for i, c in enumerate(base)}
    slots = deal(base, dealer, variant)
    order: list[Card | None] = [None] * len(base)
    used: Counter = Counter()
    for seat, faces in hands.items():
        for slot, text in zip(slots[seat], faces):
            rank, suit = Rank(text[:-1]), Suit(text[-1])
            order[positions[slot.id]] = Card(suit, rank, used[(rank, suit)])
            used[(rank, suit)] += 1
    rest = [c for c in base if c.copy >= used[c.face]]
    (rng or random.Random()).shuffle(rest)
    it = iter(rest)
    return [c if c is not None else next(it) for c in order]


def build_lab_table(scenario: Scenario, seats: list[dict], rng: random.Random | None = None,
                    now: float | None = None) -> TableState:
    """Baut den Tisch fuer ``scenario``. ``seats`` = vier Eintraege ``{"memberId", "name", "isBot"}``."""
    profile = profile_from_settings(scenario.settings)
    rnd = new_round(profile)
    rnd.dealer = scenario.dealer
    r = scenario.round
    rnd.normal_games_played = r.get("normalGamesPlayed", 0)
    rnd.bock_remaining = r.get("bockRemaining", 0)
    if "pflichtsoloDone" in r:
        rnd.pflichtsolo_done = list(r["pflichtsoloDone"])
    if "totals" in r:
        rnd.totals = list(r["totals"])
    order = rigged_order(scenario.hands, scenario.dealer, scenario.variant, rng)
    game = start_next_game(rnd, profile, order)
    table = TableState([{"memberId": s["memberId"], "name": s["name"], "isBot": bool(s["isBot"])} for s in seats],
                       profile, rnd, game, game_number=rnd.normal_games_played + 1,
                       takeover=0)                     # Test-Tisch: nie eine Bot-Uebernahme
    table.touched = time.time() if now is None else now
    _advance(table, scenario)
    return table


def _reached(table: TableState, scenario: Scenario) -> bool:
    game = table.game
    if game.phase is Phase.FINISHED:
        return True
    if scenario.advance == "playing":
        return game.phase is Phase.PLAYING
    return game.phase is Phase.PLAYING and not game.current_trick and len(game.tricks) >= scenario.tricks


def _advance(table: TableState, scenario: Scenario) -> None:
    """Spielt (mit Bot-Entscheidungen fuer alle vier Sitze) bis zum gewuenschten Punkt vor."""
    if scenario.advance == "none" or (scenario.advance == "tricks" and scenario.tricks == 0):
        return
    for _ in range(MAX_ADVANCE_STEPS):
        if _reached(table, scenario):
            break
        pending = next_bot_action(table.game, [True] * 4)
        if pending is None:
            break
        from ..rules import apply_action
        apply_action(table.game, pending[1])
        if redeal_if_needed(table):
            raise _bad("Beim Vorspielen wurde neu gegeben (Armut ohne Käufer). Wähle „Vorspielen: nein“ "
                       "oder andere Karten.")
    else:  # pragma: no cover - Schutz vor Endlosschleifen
        raise _bad("Das Vorspielen terminiert nicht.")
    settle(table)
