"""TSR 4.2/4.3/8: Spielrunde, Vorfuehrung, Geberfolge; Zufallssimulation ganzer Spiele und Runden."""
import json
import random
import unittest
from collections import Counter

from . import loader  # noqa: F401
from app.rules.cards import build_deck
from app.rules.dealing import shuffled_deck
from app.rules.errors import RuleViolation
from app.rules.game import (Baptize, Declare, GameKind, GameState, Phase, apply_action, legal_actions,
                             player_view, spectator_view)
from app.rules.round_rules import (RoundState, is_round_finished, new_round, next_setup, record_game,
                                    start_next_game)

from .fixtures import DDV, HOUSE, WITH, WITHOUT, auto_play, step_random


def finished_game(rnd, profile, rng, solo_seat=None, solo="solo_queens"):
    """Spielt das naechste Spiel der Runde komplett: optional mit freiwilligem Solo von ``solo_seat``."""
    g = start_next_game(rnd, profile, shuffled_deck(profile.deck_variant, rng))
    while g.phase is Phase.RESERVATION_QUERY:
        apply_action(g, Declare(g.query_seat, g.query_seat == solo_seat))
    if g.phase is Phase.BAPTISM:
        apply_action(g, Baptize(g.baptism_seat, solo))
    auto_play(g, rng)
    return g


class RoundRuleTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(7)
        self.rnd = new_round(DDV)

    def test_normal_game_advances_dealer_and_counter(self):
        g = finished_game(self.rnd, DDV, self.rng)
        record_game(self.rnd, g)
        self.assertEqual((self.rnd.dealer, self.rnd.normal_games_played, self.rnd.pflichtsolo_done), (1, 1, [False] * 4))
        self.assertEqual(sum(self.rnd.totals), 0)

    def test_voluntary_pflichtsolo_same_dealer_and_not_counted(self):  # 4.2.5, 4.2.4
        g = finished_game(self.rnd, DDV, self.rng, solo_seat=2)
        self.assertEqual(g.kind, GameKind.PFLICHTSOLO)
        record_game(self.rnd, g)
        self.assertEqual((self.rnd.dealer, self.rnd.normal_games_played, self.rnd.pflichtsolo_done[2]), (0, 0, True))

    def test_lustsolo_counts_as_normal_game_and_moves_dealer(self):  # 4.3.2
        self.rnd.pflichtsolo_done[1] = True
        g = finished_game(self.rnd, DDV, self.rng, solo_seat=1)
        self.assertEqual(g.kind, GameKind.LUSTSOLO)
        record_game(self.rnd, g)
        self.assertEqual((self.rnd.dealer, self.rnd.normal_games_played), (1, 1))

    def test_forced_when_missing_equals_remaining(self):  # 4.2.3
        self.rnd.pflichtsolo_done = [True, True, False, False]
        self.rnd.normal_games_played, self.rnd.dealer = 21, 1
        self.assertIsNone(next_setup(self.rnd, DDV).forced_solo_seat)        # fehlen 2, bleiben 3
        self.rnd.normal_games_played = 22
        setup = next_setup(self.rnd, DDV)
        self.assertEqual((setup.dealer, setup.forced_solo_seat), (1, 2))     # erster links vom Geber ohne Pflichtsolo
        g = finished_game(self.rnd, DDV, self.rng)
        self.assertEqual((g.kind, g.solo_seat), (GameKind.PFLICHTSOLO_FORCED, 2))
        record_game(self.rnd, g)
        self.assertEqual((self.rnd.dealer, self.rnd.normal_games_played), (2, 22))  # naechster gibt, Zaehler gleich
        self.assertIsNone(next_setup(self.rnd, DDV).forced_solo_seat)        # fehlt 1, bleiben 2 -> noch nicht

    def test_dealer_can_be_forced_last(self):
        self.rnd.pflichtsolo_done = [False, True, True, True]
        self.rnd.normal_games_played, self.rnd.dealer = 23, 0
        self.assertEqual(next_setup(self.rnd, DDV).forced_solo_seat, 0)      # Geber selbst (4. Position)

    def test_round_end_and_no_setup_after(self):
        self.rnd.normal_games_played, self.rnd.pflichtsolo_done = 24, [True] * 4
        self.assertTrue(is_round_finished(self.rnd, DDV))
        with self.assertRaises(RuleViolation):
            next_setup(self.rnd, DDV)

    def test_serialization(self):
        g = finished_game(self.rnd, DDV, self.rng)
        record_game(self.rnd, g)
        self.assertEqual(RoundState.from_dict(json.loads(json.dumps(self.rnd.to_dict()))), self.rnd)

    def test_only_finished_games_can_be_recorded(self):
        g = start_next_game(self.rnd, DDV, shuffled_deck(WITH, self.rng))
        with self.assertRaises(RuleViolation):
            record_game(self.rnd, g)


class FullRoundSimulation(unittest.TestCase):
    def run_round(self, profile, seed, reservation_chance):
        rng = random.Random(seed)
        rnd = new_round(profile)
        kinds = Counter()
        while not is_round_finished(rnd, profile):
            setup = next_setup(rnd, profile)
            missing = rnd.pflichtsolo_done.count(False)
            remaining = profile.normal_games_per_round - rnd.normal_games_played
            self.assertEqual(setup.forced_solo_seat is not None, missing >= remaining and missing > 0)
            g = start_next_game(rnd, profile, shuffled_deck(profile.deck_variant, rng))
            while g.phase is not Phase.PLAYING:
                step_random(g, rng, reservation_chance=reservation_chance)
            auto_play(g, rng, announce_chance=0.05)
            kinds[g.kind] += 1
            record_game(rnd, g)
        return rnd, kinds

    def check_round(self, profile, rnd, kinds):
        self.assertEqual(rnd.normal_games_played, profile.normal_games_per_round)
        self.assertTrue(all(rnd.pflichtsolo_done))
        self.assertEqual(kinds[GameKind.PFLICHTSOLO] + kinds[GameKind.PFLICHTSOLO_FORCED], 4)   # genau 4 Pflichtsoli
        self.assertEqual(len(rnd.results), 24 + 4)
        self.assertEqual(sum(rnd.totals), 0)
        solo_seats = [r["soloSeat"] for r in rnd.results if r["kind"].startswith("pflichtsolo")]
        self.assertEqual(sorted(solo_seats), [0, 1, 2, 3])                                          # jeder genau eins

    def test_rounds_with_nines(self):
        for seed in range(12):
            rnd, kinds = self.run_round(DDV, seed, reservation_chance=0.12 if seed % 2 else 0.03)
            self.check_round(DDV, rnd, kinds)

    def test_rounds_without_nines(self):
        for seed in range(6):
            rnd, kinds = self.run_round(HOUSE, 100 + seed, reservation_chance=0.1)
            self.check_round(HOUSE, rnd, kinds)

    def test_forced_solos_happen_with_passive_players(self):
        rnd, kinds = self.run_round(DDV, 5, reservation_chance=0.0)
        self.assertEqual(kinds[GameKind.PFLICHTSOLO_FORCED], 4)
        self.check_round(DDV, rnd, kinds)


class GameSimulation(unittest.TestCase):
    def test_invariants_over_many_random_games(self):
        for profile in (DDV, HOUSE):
            for seed in range(40):
                rng = random.Random(seed)
                dealer = seed % 4
                rnd = new_round(profile)
                rnd.dealer = dealer
                g = start_next_game(rnd, profile, shuffled_deck(profile.deck_variant, rng))
                all_cards = {c.id for h in g.hands for c in h}
                self.assertEqual(len(all_cards), 4 * profile.hand_size)
                while g.phase is not Phase.FINISHED:
                    step_random(g, rng, announce_chance=0.08, reservation_chance=0.2)
                    if seed < 6:                                 # teurer Test nur fuer einige Seeds
                        d = json.loads(json.dumps(g.to_dict()))
                        self.assertEqual(GameState.from_dict(d).to_dict(), g.to_dict())
                    self.check_views(g)
                self.assertEqual(len(g.tricks), profile.trick_count)
                self.assertEqual(sum(t.points for t in g.tricks), 240)
                self.assertEqual(sum(g.score.seat_deltas), 0)
                self.assertEqual({p.card.id for t in g.tricks for p in t.plays}, all_cards)
                self.assertFalse([h for h in g.hands if h])

    def check_views(self, g):
        for seat in range(4):
            view = player_view(g, seat)
            text = json.dumps(view)
            self.assertEqual(len(view["hand"]), len(g.hands[seat]))
            if g.phase is not Phase.FINISHED:
                public_cards = {json.dumps(c, sort_keys=True) for c in
                                [p["card"] for p in view["currentTrick"]] + [p["card"] for p in (view["lastTrick"] or {"plays": []})["plays"]]}
                for other in range(4):
                    if other == seat:
                        continue
                    for c in g.hands[other]:
                        self.assertNotIn(json.dumps(c.to_dict(), sort_keys=True), public_cards - {json.dumps(x, sort_keys=True) for x in view["hand"]})
                self.assertNotIn("parties", view)
        spec = spectator_view(g)
        self.assertNotIn("hand", spec)
        if g.phase is not Phase.FINISHED:
            self.assertNotIn("tricks", spec)
        # Wer an der Reihe ist, hat immer eine legale Aktion
        if g.phase is Phase.PLAYING:
            self.assertTrue(any(a["type"] == "play_card" for a in legal_actions(g, g.turn)))


if __name__ == "__main__":
    unittest.main()
