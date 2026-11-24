"""Kartenwahl durch Stichproben ("Perfect Information Monte Carlo"), flask-frei.

Der Bot kennt die Haende der Mitspieler nicht, aber er weiss, welche Karten noch im Spiel sind (Gedaechtnis) und wer
welche Farbe nachweislich nicht mehr hat. Er verteilt die ungesehenen Karten zufaellig, aber regelkonform auf die
Mitspieler ("Stichprobe"), spielt jede erlaubte Karte in jeder Stichprobe mit einer einfachen Grundstrategie zu Ende
und waehlt die Karte mit den meisten erwarteten Augen fuer die eigene Partei. Kein Mogeln: die Stichproben benutzen nur
Information, die auch ein Mensch am Tisch hat.
"""
from __future__ import annotations

import random
import zlib

from ..rules.cards import Card, Rank, Suit
from ..rules.tricks import Play, playable_cards, trick_winner_index
from ..rules.trump import GameType, TrumpConfig, is_trump, lead_kind, strength

_QUEEN_CLUBS = (Rank.QUEEN, Suit.CLUBS)
_DULLE = (Rank.TEN, Suit.HEARTS)


def sample_hands(unseen: list[Card], sizes: dict[int, int], forbidden: dict[int, set], kind_of, must_have_queen: set,
                 no_queen: set, rng: random.Random, attempts: int = 80,
                 forced: dict[int, list[Card]] | None = None) -> dict[int, list[Card]] | None:
    """Verteilt ``unseen`` zufaellig auf die Sitze in ``sizes`` (Handgroesse je Sitz).

    ``forbidden[seat]``: Kartenarten (Farbe/'trump'), die der Sitz nicht haben darf. ``must_have_queen``: Sitze, die
    sicher eine Kreuz-Dame halten, ``no_queen``: Sitze, die sicher keine haben. ``forced[seat]``: Karten aus ``unseen``, die
    sicher bei diesem Sitz liegen (z. B. die Karo-Asse des Schweinchen-Spielers, die Kreuz-Damen des Hochzeiters).
    ``None`` = keine gueltige Verteilung gefunden.
    """
    for _ in range(attempts):
        cards = list(unseen)
        rng.shuffle(cards)
        hands = {s: [] for s in sizes}
        room = dict(sizes)
        ok = True
        for seat, fixed in (forced or {}).items():                    # sichere Karten zuerst festlegen
            for c in fixed:
                if c not in cards or room.get(seat, 0) == 0 or kind_of(c.face) in forbidden[seat]:
                    ok = False
                    break
                cards.remove(c); hands[seat].append(c); room[seat] -= 1
            if not ok:
                break
        if not ok:
            continue
        queens = [c for c in cards if c.face == _QUEEN_CLUBS]
        for seat in must_have_queen:                                   # je eine Dame fuer sichere Re-Spieler
            pick = next((q for q in queens if kind_of(q.face) not in forbidden[seat]), None)
            if pick is None or room[seat] == 0:
                ok = False
                break
            queens.remove(pick); cards.remove(pick); hands[seat].append(pick); room[seat] -= 1
        if not ok:
            continue
        # engste Karten zuerst (wenige erlaubte Sitze), sonst scheitert die Verteilung haeufiger
        def allowed(c: Card) -> list[int]:
            return [s for s in sizes if room[s] > 0 and kind_of(c.face) not in forbidden[s]
                    and not (c.face == _QUEEN_CLUBS and s in no_queen)]
        for c in sorted(cards, key=lambda c: len(allowed(c))):
            seats = allowed(c)
            if not seats:
                ok = False
                break
            weights = [room[s] for s in seats]
            seat = rng.choices(seats, weights)[0]
            hands[seat].append(c)
            room[seat] -= 1
        if ok:
            return hands
    return None


# --- Grundstrategie fuer die Zuege in den Stichproben (alle Parteien bekannt, nur Kartenbilder) ----------------

def _policy(hand: list[Card], plays: list[Play], seat: int, party: dict[int, bool], gt: GameType, cfg: TrumpConfig,
            second: bool) -> Card:
    st = lambda c: strength(c, gt, cfg)
    cheap = lambda c: (is_trump(c, gt, cfg), c.value, -st(c))
    if not plays:
        aces = [c for c in hand if c.rank is Rank.ACE and not is_trump(c, gt, cfg)]
        if aces:
            return max(aces, key=lambda c: (sum(h.suit == c.suit for h in hand), c.id))
        return min(hand, key=cheap)
    cands = playable_cards(hand, plays[0].card, gt, cfg)
    if len(cands) == 1:
        return cands[0]
    win_idx = trick_winner_index(plays, gt, cfg, second)
    winner = plays[win_idx]
    last = len(plays) == 3
    if party[winner.seat] == party[seat]:
        if last or (is_trump(winner.card, gt, cfg) and st(winner.card) <= 4):
            return max(cands, key=lambda c: (c.value, st(c)))
        return min(cands, key=cheap)
    points = sum(p.card.value for p in plays)
    wins = [c for c in cands if plays_win(plays, seat, c, gt, cfg, second)]
    if wins:
        best = max(wins, key=st)
        if last or not (is_trump(best, gt, cfg) and st(best) <= 3) or points + best.value >= 10:
            return best
    return min(cands, key=cheap)


def plays_win(plays: list[Play], seat: int, card: Card, gt: GameType, cfg: TrumpConfig, second: bool) -> bool:
    tmp = plays + [Play(seat, card)]
    return tmp[trick_winner_index(tmp, gt, cfg, second)].seat == seat


def history_weight(history: list[list[Play]], dealt: dict[int, list[Card]], party: dict[int, bool], me: int,
                   gt: GameType, cfg: TrumpConfig, second: bool, mismatch: float) -> float:
    """Wie gut passt eine Stichprobe zu dem, was die Mitspieler bisher gespielt haben?

    Fuer jede bisherige Karte eines Mitspielers wird nachgespielt, was die Grundstrategie mit der damaligen Hand (heutige
    Stichprobenhand + spaeter gespielte Karten) und den Stichproben-Parteien getan haette. Stimmt es, zaehlt die Stichprobe
    voll, sonst nur mit dem Faktor ``mismatch`` (< 1): Spieler, die Partner "schmieren" oder Gegner stechen, verraten so
    ihre wahrscheinliche Partei. Weich statt hart, weil echte Spieler nicht genau die Grundstrategie spielen.
    """
    later: dict[int, list[Card]] = {s: [] for s in dealt}
    weight = 1.0
    for t in range(len(history) - 1, -1, -1):                      # rueckwaerts: Hand "damals" waechst
        trick = history[t]
        for p in trick:
            if p.seat in later:
                later[p.seat].append(p.card)
        for i, p in enumerate(trick):
            if p.seat == me or p.seat not in dealt:
                continue
            hand = dealt[p.seat] + [c for c in later[p.seat]]
            chosen = _policy(hand, trick[:i], p.seat, party, gt, cfg, second)
            if chosen.face != p.card.face:
                weight *= mismatch
        # Karten dieses Stichs gehoeren fuer fruehere Stiche weiterhin zur Hand: nichts entfernen
    return weight


def rollout(hands: dict[int, list[Card]], plays: list[Play], party: dict[int, bool], me_party: bool, gt: GameType,
            cfg: TrumpConfig, second: bool, start: int = 0) -> int:
    """Spielt den Rest des Spiels; Rueckgabe: Augen, die die eigene Partei in den Reststichen noch holt."""
    plays = list(plays)
    mine = 0
    seat = (plays[-1].seat + 1) % 4 if plays else start
    while True:
        while len(plays) < 4:
            if not hands[seat]:
                return mine
            card = _policy(hands[seat], plays, seat, party, gt, cfg, second)
            hands[seat].remove(card)
            plays.append(Play(seat, card))
            seat = (seat + 1) % 4
        idx = trick_winner_index(plays, gt, cfg, second)
        winner = plays[idx].seat
        pts = sum(p.card.value for p in plays)
        if party[winner] == me_party:
            mine += pts
        plays, seat = [], winner
        if not any(hands.values()):
            return mine


def rollout_wedding(hands: dict[int, list[Card]], plays: list[Play], wedding: int, tricks_done: int, gt: GameType,
                    cfg: TrumpConfig, second: bool, start: int = 0) -> tuple[dict[int, int], dict[int, bool]]:
    """Spielt den Rest einer noch ungeklaerten Hochzeit zu Ende (TSR 4.4.3).

    Der Hochzeiter (``wedding``) ist Re. Wer als Erster einen Stich gewinnt, der nicht der Hochzeiter ist, wird sein Partner;
    gewinnt der Hochzeiter die ersten drei Stiche, spielt er allein (Solo). Bis dahin gelten die uebrigen drei als Kontra.
    ``tricks_done``: schon abgeschlossene Stiche. Rueckgabe: (Augen je Sitz in den Reststichen, endgueltige Parteien).
    """
    party = {s: s == wedding for s in range(4)}
    clarified = False
    plays = list(plays)
    points = {s: 0 for s in range(4)}
    trick_no = tricks_done + 1
    seat = (plays[-1].seat + 1) % 4 if plays else start
    while True:
        while len(plays) < 4:
            if not hands[seat]:
                return points, party
            card = _policy(hands[seat], plays, seat, party, gt, cfg, second)
            hands[seat].remove(card)
            plays.append(Play(seat, card))
            seat = (seat + 1) % 4
        winner = plays[trick_winner_index(plays, gt, cfg, second)].seat
        points[winner] += sum(p.card.value for p in plays)
        if not clarified:
            if winner != wedding:
                party[winner] = True
                clarified = True
            elif trick_no >= 3:
                clarified = True
        plays, seat = [], winner
        trick_no += 1
        if not any(hands.values()):
            return points, party


def _value(future: int, collected: dict[int, int] | None, party: dict[int, bool], me: int) -> float:
    """Bewertung eines ausgespielten Spiels: Sieg zaehlt am meisten, danach die Augen (mehr Augen = mehr Zusatzpunkte)."""
    if collected is None:
        return float(future)
    total = future + sum(p for s, p in collected.items() if party[s] == party[me])
    need = 121 if party[me] else 120            # Re gewinnt mit 121, Kontra mit 120 (TSR 7.1)
    return (100.0 if total >= need else 0.0) + 0.5 * (total - 120)


def choose(me: int, my_hand: list[Card], cands: list[Card], plays: list[Play], unseen: list[Card],
           sizes: dict[int, int], forbidden: dict[int, set], kind_of, re_known: set, kontra_known: set,
           re_played: set, my_party_re: bool, gt: GameType, cfg: TrumpConfig, second: bool, samples: int,
           key: str, collected: dict[int, int] | None = None, history: list[list[Play]] | None = None,
           mismatch: float = 1.0, *, fixed_party: dict[int, bool] | None = None,
           wedding: tuple[int, int] | None = None, forced: dict[int, list[Card]] | None = None) -> Card | None:
    """Beste Karte aus ``cands`` oder ``None``, wenn keine Stichprobe gelang.

    Parteien der Stichproben:
    * Normalspiel (Standard): Re ist, wer eine Kreuz-Dame haelt (``re_known``/``kontra_known``/``re_played`` schraenken die Verteilung ein).
    * ``fixed_party`` (Solo, Armut, geklaerte Hochzeit): die Parteien stehen oeffentlich fest (Sitz -> ist Re); keine Dame-Annahmen.
    * ``wedding = (Hochzeiter, abgeschlossene Stiche)``: ungeklaerte Hochzeit; der Partner ergibt sich im Durchlauf (``rollout_wedding``).
    ``forced``: Karten, die sicher bei einem Sitz liegen (siehe ``sample_hands``).
    """
    rng = random.Random(zlib.crc32(key.encode()))
    others = {s: n for s, n in sizes.items() if s != me}
    scores = {c.id: 0.0 for c in cands}
    used = 0
    for _ in range(samples):
        dealt = sample_hands(unseen, others, forbidden, kind_of, re_known - re_played, kontra_known, rng, forced=forced)
        if dealt is None:
            continue
        used += 1
        if fixed_party is not None:
            party = dict(fixed_party)
        elif wedding is None:
            re_seats = set(re_played) | {s for s, h in dealt.items() if any(c.face == _QUEEN_CLUBS for c in h)}
            if any(c.face == _QUEEN_CLUBS for c in my_hand):
                re_seats.add(me)
            party = {s: (s in re_seats) for s in range(4)}
        weight = 1.0
        if history is not None and mismatch < 1.0 and wedding is None:
            weight = history_weight(history, dealt, party, me, gt, cfg, second, mismatch)
        for c in cands:
            hands = {s: list(h) for s, h in dealt.items()}
            hands[me] = [h for h in my_hand if h != c]
            if wedding is not None:
                points, final = rollout_wedding(hands, plays + [Play(me, c)], wedding[0], wedding[1], gt, cfg, second)
                future = sum(p for s, p in points.items() if final[s] == final[me])
                scores[c.id] += weight * _value(future, collected, final, me)
            else:
                future = rollout(hands, plays + [Play(me, c)], party, party[me], gt, cfg, second)
                scores[c.id] += weight * _value(future, collected, party, me)
    if not used:
        return None
    return max(cands, key=lambda c: (scores[c.id], -strength(c, gt, cfg), c.id))


def estimate(me: int, my_hand: list[Card], plays: list[Play], unseen: list[Card], sizes: dict[int, int],
             forbidden: dict[int, set], kind_of, re_known: set, kontra_known: set, re_played: set, gt: GameType,
             cfg: TrumpConfig, second: bool, samples: int, key: str, collected: dict[int, int], start: int,
             targets: dict[int, int], history: list[list[Play]] | None = None,
             mismatch: float = 1.0) -> dict[int, float] | None:
    """Wie wahrscheinlich erreicht die eigene Partei bestimmte Augenzahlen?  ``targets``: Stufe -> noetige Augen.

    Der Bot spielt dazu seine Hand mit der Grundstrategie zu Ende (Stichproben der fremden Haende wie in ``choose``).
    ``None`` = keine gueltige Stichprobe.
    """
    rng = random.Random(zlib.crc32(key.encode()))
    others = {s: n for s, n in sizes.items() if s != me}
    hits = {lvl: 0.0 for lvl in targets}
    used = 0.0
    for _ in range(samples):
        dealt = sample_hands(unseen, others, forbidden, kind_of, re_known - re_played, kontra_known, rng)
        if dealt is None:
            continue
        re_seats = set(re_played) | {s for s, h in dealt.items() if any(c.face == _QUEEN_CLUBS for c in h)}
        if any(c.face == _QUEEN_CLUBS for c in my_hand):
            re_seats.add(me)
        party = {s: (s in re_seats) for s in range(4)}
        weight = 1.0
        if history is not None and mismatch < 1.0:
            weight = history_weight(history, dealt, party, me, gt, cfg, second, mismatch)
        used += weight
        hands = {s: list(h) for s, h in dealt.items()}
        hands[me] = list(my_hand)
        total = rollout(hands, plays, party, party[me], gt, cfg, second, start) + \
            sum(p for s, p in collected.items() if party[s] == party[me])
        for lvl, need in targets.items():
            hits[lvl] += weight * (total >= (need + 1 if (lvl == 0 and party[me]) else need))
    if not used:
        return None
    return {lvl: n / used for lvl, n in hits.items()}
