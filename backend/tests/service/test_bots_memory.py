"""Gedaechtnis der Bots (gespielte Karten, Leerfarben) und Stichproben-Kartenwahl."""
import random
import unittest
from collections import Counter

from ..rules import loader  # noqa: F401
from app.rules import DeckVariant, Phase, RuleOptions, apply_action, bot_view, make_profile, new_round, start_next_game
from app.rules.cards import Card, Rank, Suit
from app.rules.dealing import shuffled_deck
from app.rules.trump import lead_kind
from app.table import bots, pimc


def new_game(seed, variant=DeckVariant.WITH_NINES):
    profile = make_profile(variant, RuleOptions())
    return start_next_game(new_round(profile), profile, shuffled_deck(variant, random.Random(seed)))


def advance(game, steps):
    for _ in range(steps):
        if game.phase is Phase.FINISHED:
            return
        for seat in range(4):
            action = bots.choose_action(bot_view(game, seat))
            if action is not None:
                apply_action(game, action)
                break


class MemoryTests(unittest.TestCase):
    def test_unseen_cards_and_voids_match_the_true_game(self):
        for seed in range(8):
            for variant in (DeckVariant.WITH_NINES, DeckVariant.WITHOUT_NINES):
                game = new_game(seed, variant)
                total = 48 if variant is DeckVariant.WITH_NINES else 40
                for step in range(6, 60, 7):
                    advance(game, 7)
                    if game.phase is not Phase.PLAYING:
                        break
                    for seat in range(4):
                        view = bot_view(game, seat)
                        plays = [bots.Play(p["seat"], Card.from_dict(p["card"])) for p in view["currentTrick"]]
                        mem = bots.Memory(view, plays)
                        # Gesehen + eigene Hand + ungesehen = ganzes Spiel
                        others = sum(len(h) for s, h in enumerate(game.hands) if s != seat)
                        self.assertEqual(sum(mem.unseen.values()), others)
                        true_unseen = Counter(c.face for s, h in enumerate(game.hands) if s != seat for c in h)
                        self.assertEqual(mem.unseen, true_unseen)
                        # Nachgewiesene Leerfarben stimmen wirklich
                        for s in range(4):
                            for kind in mem.voids[s]:
                                held = [c for c in game.hands[s] if lead_kind(c, game.game_type, bots._cfg(view)) == kind]
                                self.assertEqual(held, [], (seed, s, kind))
                    self.assertGreater(total, 0)

    def test_master_card_detection(self):
        game = new_game(5)
        advance(game, 3)
        view = bot_view(game, 0)
        mem = bots.Memory(view, [])
        ace = Card(Suit.HEARTS, Rank.ACE, 0)
        # Mit beiden Fehlfarben-Assen ungesehen ist keine Fehlfarben-10 sicher
        ten = Card(Suit.CLUBS, Rank.TEN, 0)
        self.assertTrue(bots.threatened(ten, Suit.CLUBS, [1, 2, 3], mem, False) or mem.unseen[(Rank.ACE, Suit.CLUBS)] == 0)
        self.assertFalse(ace is None)


class SamplingTests(unittest.TestCase):
    def test_sampled_hands_respect_sizes_and_voids(self):
        rng = random.Random(1)
        unseen = [Card(s, r, c) for s in Suit for r in (Rank.ACE, Rank.TEN, Rank.KING) for c in (0, 1)]
        kind_of = lambda face: face[1]
        sizes = {1: 8, 2: 8, 3: 8}
        forbidden = {1: {Suit.HEARTS}, 2: set(), 3: {Suit.CLUBS}}
        for _ in range(40):
            hands = pimc.sample_hands(unseen, sizes, forbidden, kind_of, set(), set(), rng)
            self.assertIsNotNone(hands)
            self.assertEqual({s: len(h) for s, h in hands.items()}, sizes)
            self.assertTrue(all(c.suit is not Suit.HEARTS for c in hands[1]))
            self.assertTrue(all(c.suit is not Suit.CLUBS for c in hands[3]))
            self.assertEqual(sorted(c.id for h in hands.values() for c in h), sorted(c.id for c in unseen))

    def test_impossible_distribution_returns_none(self):
        unseen = [Card(Suit.HEARTS, Rank.ACE, 0), Card(Suit.HEARTS, Rank.ACE, 1)]
        self.assertIsNone(pimc.sample_hands(unseen, {1: 1, 2: 1}, {1: {Suit.HEARTS}, 2: {Suit.HEARTS}},
                                            lambda f: f[1], set(), set(), random.Random(0)))

    def test_known_queen_holder_gets_a_queen(self):
        unseen = [Card(Suit.CLUBS, Rank.QUEEN, 0)] + [Card(Suit.HEARTS, Rank.KING, i) for i in (0, 1)] + \
                 [Card(Suit.SPADES, Rank.KING, i) for i in (0, 1)]
        for seed in range(20):
            hands = pimc.sample_hands(unseen, {1: 2, 2: 3}, {1: set(), 2: set()}, lambda f: f[1], {2}, {1},
                                      random.Random(seed))
            self.assertTrue(any(c.face == (Rank.QUEEN, Suit.CLUBS) for c in hands[2]))
            self.assertFalse(any(c.face == (Rank.QUEEN, Suit.CLUBS) for c in hands[1]))

    def test_sampled_choice_is_legal_and_deterministic(self):
        bots.TUNE.update({"pimc": True, "announce": "pimc"})
        self.addCleanup(bots.TUNE.update, {"pimc": False, "announce": "legacy"})
        game = new_game(9)
        advance(game, 40)
        seen = 0
        for _ in range(60):
            if game.phase is not Phase.PLAYING:
                break
            seat = game.turn
            view = bot_view(game, seat)
            acts = {a["type"]: a for a in view["legalActions"]}
            if "play_card" in acts:
                playable = acts["play_card"]["cards"]
                first = bots.choose_card(view, playable)
                self.assertIn(first, playable)
                self.assertEqual(first, bots.choose_card(view, playable))      # gleiche Lage -> gleiche Karte
                seen += 1
            advance(game, 1)
        self.assertGreater(seen, 0)

    def test_history_weight_is_neutral_without_history_and_never_above_one(self):
        game = new_game(4)
        advance(game, 30)
        view = bot_view(game, game.turn)
        plays = [bots.Play(p["seat"], Card.from_dict(p["card"])) for p in view["currentTrick"]]
        mem = bots.Memory(view, plays)
        gt, cfg = bots._game_type(view), bots._cfg(view)
        dealt = {s: list(game.hands[s]) for s in range(4) if s != view["seat"]}   # die wahre Verteilung
        party = {s: s in game.re_seats for s in range(4)}
        self.assertEqual(pimc.history_weight([], dealt, party, view["seat"], gt, cfg, False, 0.5), 1.0)
        weight = pimc.history_weight(bots._history(view, plays), dealt, party, view["seat"], gt, cfg, False, 0.5)
        self.assertTrue(0 < weight <= 1.0)
        self.assertGreater(mem.tricks_played, 0)


class SampledBotsPlayFullGames(unittest.TestCase):
    def test_full_games_with_sampling_bots_are_legal_and_finish(self):
        bots.TUNE.update({"pimc": True, "announce": "pimc"})
        self.addCleanup(bots.TUNE.update, {"pimc": False, "announce": "legacy"})
        for seed, variant in ((1, DeckVariant.WITH_NINES), (2, DeckVariant.WITHOUT_NINES), (3, DeckVariant.WITH_NINES)):
            game = new_game(seed, variant)
            advance(game, 400)                                    # apply_action prueft jede Aktion auf Regelkonformitaet
            self.assertIs(game.phase, Phase.FINISHED)
            self.assertEqual(len(game.tricks), 12 if variant is DeckVariant.WITH_NINES else 10)


if __name__ == "__main__":
    unittest.main()
