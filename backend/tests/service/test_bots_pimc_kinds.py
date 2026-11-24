"""Durchrechnen (Stichproben-Kartenwahl) in allen Spielarten: Solo, Armut, Hochzeit, Schweinchen - nicht nur im Normalspiel."""
import random
import unittest

from ..rules import loader  # noqa: F401
from app.rules import Phase, bot_view
from app.rules.cards import Card, Rank, Suit
from app.rules.game import Baptize, DeclareSchweinchen, GameKind, apply_action
from app.rules.trump import SOLO_TYPES, GameType, TrumpConfig
from app.table import bots, pimc

from ..rules.fixtures import DDV, NORMAL_HANDS, WEDDING_HANDS, WITH, declare_all, rig, start, with_options
from ..rules.test_poverty import POVERTY_HANDS
from .test_poverty_bots import run_bots_until

ALL_BOTS = [True] * 4
CHEAP = {"pimc": True, "announce": "pimc", "pimc_budget": 24, "announce_samples": 8}   # die Testumgebung schaltet das Durchrechnen sonst aus (tests/service/__init__.py)


class TuneCase(unittest.TestCase):
    """Billiges Durchrechnen fuer die Tests; Einstellungen und Zwischenspeicher danach wie vorher."""

    def setUp(self):
        self._saved = dict(bots.TUNE)
        bots.TUNE.update(CHEAP)
        bots._PIMC_CACHE.clear()
        bots._ANNOUNCE_CACHE.clear()

    def tearDown(self):
        bots.TUNE.clear()
        bots.TUNE.update(self._saved)
        bots._PIMC_CACHE.clear()
        bots._ANNOUNCE_CACHE.clear()


def solo_game(game_type: GameType, seat: int = 0):
    s = start(NORMAL_HANDS)
    declare_all(s, reservations={seat})
    apply_action(s, Baptize(seat, game_type.value))
    return s


def wedding_game():
    s = start(WEDDING_HANDS)
    run_bots_until(s, lambda g: g.phase is Phase.PLAYING)
    return s


def poverty_game():
    from app.rules.game import new_game
    s = new_game(with_options(poverty=True), rig(POVERTY_HANDS, 3, WITH), 3)
    run_bots_until(s, lambda g: g.phase is Phase.PLAYING)
    return s


def first_choice(game, seat):
    """Entscheidung ``_sampled_choice`` des Sitzes in der laufenden Lage (``None`` = Heuristik)."""
    view = bot_view(game, seat)
    plays = [bots.Play(p["seat"], Card.from_dict(p["card"])) for p in view["currentTrick"]]
    mem = bots.Memory(view, plays)
    cands = [Card.from_id(i) for i in next(a for a in view["legalActions"] if a["type"] == "play_card")["cards"]]
    return bots._sampled_choice(view, cands, plays, mem, bots.known_parties(view, plays), False), cands


class KindDetectionTests(TuneCase):
    def test_kinds(self):
        s = start(NORMAL_HANDS)
        declare_all(s)
        self.assertEqual(bots._pimc_kind(bot_view(s, 0)), "normal")
        self.assertEqual(bots._pimc_kind(bot_view(solo_game(GameType.SOLO_JACKS), 1)), "solo")
        self.assertEqual(bots._pimc_kind(bot_view(wedding_game(), 0)), "wedding")
        g = poverty_game()
        self.assertEqual(g.kind, GameKind.POVERTY)
        self.assertEqual(bots._pimc_kind(bot_view(g, 0)), "poverty")

    def test_before_the_game_starts_there_is_no_kind_for_cards(self):
        s = start(NORMAL_HANDS)
        self.assertEqual(bots._pimc_kind(bot_view(s, 0)), "normal")      # Vorbehaltsabfrage: noch keine Karten gefragt, nur der Normalfall als Rueckfall


class EveryKindUsesSamplingTests(TuneCase):
    def check(self, game, kind_flag):
        seat = game.turn
        choice, cands = first_choice(game, seat)
        self.assertIsNotNone(choice, "Das Durchrechnen hat nicht gerechnet")
        self.assertIn(choice, [c.id for c in cands])
        bots._PIMC_CACHE.clear()
        self.assertEqual(first_choice(game, seat)[0], choice, "gleiche Lage, gleiche Wahl (deterministisch)")
        bots._PIMC_CACHE.clear()
        bots.TUNE[kind_flag] = False
        self.assertIsNone(first_choice(game, seat)[0], "Mit ausgeschaltetem Schalter entscheidet die Heuristik")

    def test_all_seven_solos(self):
        for gt in SOLO_TYPES:
            with self.subTest(gt=gt.value):
                bots.TUNE["pimc_solo"] = True
                s = solo_game(gt)
                self.assertIs(s.game_type, gt)
                self.check(s, "pimc_solo")

    def test_poverty(self):
        bots.TUNE["pimc_poverty"] = True
        self.check(poverty_game(), "pimc_poverty")

    def test_wedding_unclarified_and_clarified(self):
        bots.TUNE["pimc_wedding"] = True
        s = wedding_game()
        self.assertIsNone(s.wedding_clarifying_trick)
        self.check(s, "pimc_wedding")
        bots.TUNE["pimc_wedding"] = True
        while s.wedding_clarifying_trick is None:                       # bis zum Klaerungsstich spielen
            seat = s.turn
            apply_action(s, bots.choose_action(bot_view(s, seat)))
        if s.phase is not Phase.FINISHED:
            self.check(s, "pimc_wedding")

    def test_normal_game_with_schweinchen_still_samples(self):
        s = with_options(schweinchen=True)
        from app.rules.game import new_game
        hands = dict(NORMAL_HANDS)
        hands[0] = "A♦ A♦ Q♠ Q♠ J♣ J♣ A♣ A♣ 10♣ 10♣ K♣ K♣"
        hands[3] = "Q♦ Q♦ J♥ J♥ K♦ K♦ 9♦ 9♦ 9♠ 9♠ 9♥ 9♥"
        g = new_game(s, rig(hands, 3, WITH), 3)
        declare_all(g)
        apply_action(g, DeclareSchweinchen(0))
        self.assertEqual(g.schweinchen_seat, 0)
        g.turn = 1
        choice, cands = first_choice(g, 1)
        self.assertIsNotNone(choice)


class WholeGamesTests(TuneCase):
    def test_bots_finish_every_kind_with_valid_scores(self):
        games = [solo_game(gt) for gt in SOLO_TYPES] + [wedding_game(), poverty_game()]
        for g in games:
            run_bots_until(g, lambda x: x.phase is Phase.FINISHED)
            self.assertEqual(sum(t.points for t in g.tricks), 240)
            self.assertEqual(sum(g.score.seat_deltas), 0)

    def test_random_scenarios_do_not_crash(self):
        from ..rules.fixtures import step_random
        rng = random.Random(7)
        for seed in range(6):
            from app.rules.game import new_game
            from app.rules.dealing import shuffled_deck
            s = new_game(with_options(poverty=True, schweinchen=True), shuffled_deck(WITH, random.Random(seed)), seed % 4)
            for _ in range(40):                                          # zufaellige Vorbehalte/Taufen, danach spielen die Bots
                if s.phase is Phase.PLAYING:
                    break
                step_random(s, rng, reservation_chance=0.5)
            run_bots_until(s, lambda x: x.phase is Phase.FINISHED)
            self.assertEqual(sum(s.score.seat_deltas), 0)


class NormalGameUnchangedTests(TuneCase):
    def test_normal_decisions_do_not_depend_on_the_new_switches(self):
        """Regression: im reinen Normalspiel (ohne Schweinchen) aendert sich keine Entscheidung."""
        def play_all(flags):
            bots.TUNE.update(flags)
            bots._PIMC_CACHE.clear()
            s = start(NORMAL_HANDS)
            declare_all(s)
            log = []
            for _ in range(60):
                if s.phase is Phase.FINISHED:
                    break
                for seat in range(4):
                    a = bots.choose_action(bot_view(s, seat))
                    if a is not None:
                        log.append(repr(a))
                        apply_action(s, a)
                        break
            return log

        on = play_all({"pimc_solo": True, "pimc_poverty": True, "pimc_wedding": True, "pimc_public": True})
        off = play_all({"pimc_solo": False, "pimc_poverty": False, "pimc_wedding": False, "pimc_public": False})
        self.assertEqual(on, off)


class SamplerTests(unittest.TestCase):
    def setUp(self):
        self.unseen = [Card(s, r, i) for r in (Rank.ACE, Rank.KING, Rank.QUEEN) for s in (Suit.CLUBS, Suit.DIAMONDS) for i in (0, 1)]
        self.kind_of = lambda face: face[1]

    def test_forced_cards_land_at_the_seat(self):
        rng = random.Random(1)
        fox = [c for c in self.unseen if c.face == (Rank.ACE, Suit.DIAMONDS)]
        for _ in range(30):
            hands = pimc.sample_hands(self.unseen, {1: 4, 2: 4, 3: 4}, {1: set(), 2: set(), 3: set()}, self.kind_of, set(), set(), rng,
                                      forced={2: fox})
            self.assertIsNotNone(hands)
            self.assertTrue(all(c in hands[2] for c in fox))
            self.assertEqual(sorted(len(h) for h in hands.values()), [4, 4, 4])

    def test_impossible_forced_cards_give_no_sample(self):
        fox = [c for c in self.unseen if c.face == (Rank.ACE, Suit.DIAMONDS)]
        hands = pimc.sample_hands(self.unseen, {1: 4, 2: 4, 3: 4}, {1: set(), 2: {Suit.DIAMONDS}, 3: set()}, self.kind_of, set(), set(),
                                  random.Random(1), forced={2: fox})
        self.assertIsNone(hands)

    def test_default_sampling_is_unchanged_without_forced(self):
        a = pimc.sample_hands(self.unseen, {1: 4, 2: 4, 3: 4}, {1: set(), 2: set(), 3: set()}, self.kind_of, set(), set(), random.Random(5))
        b = pimc.sample_hands(self.unseen, {1: 4, 2: 4, 3: 4}, {1: set(), 2: set(), 3: set()}, self.kind_of, set(), set(), random.Random(5), forced=None)
        self.assertEqual(a, b)


class WeddingRolloutTests(unittest.TestCase):
    cfg = TrumpConfig()

    def test_partner_is_the_first_foreign_trick_winner(self):
        # Sitz 0 = Hochzeiter spielt Pik-Neun aus; Sitz 1 und 2 koennen weder bedienen noch stechen; Sitz 3 sticht als Letzter mit der Herz-Dame -> Partner
        h = {0: [Card(Suit.SPADES, Rank.NINE, 0), Card(Suit.SPADES, Rank.NINE, 1)],
             1: [Card(Suit.CLUBS, Rank.KING, 0), Card(Suit.CLUBS, Rank.KING, 1)],
             2: [Card(Suit.CLUBS, Rank.TEN, 0), Card(Suit.CLUBS, Rank.TEN, 1)],
             3: [Card(Suit.HEARTS, Rank.QUEEN, 0), Card(Suit.HEARTS, Rank.NINE, 0)]}
        total = sum(c.value for hand in h.values() for c in hand)
        points, party = pimc.rollout_wedding(h, [], 0, 0, GameType.NORMAL, self.cfg, False, start=0)
        self.assertEqual(sum(points.values()), total)
        self.assertEqual(party, {0: True, 1: False, 2: False, 3: True})

    def test_wedding_player_alone_after_three_tricks(self):
        # Der Hochzeiter holt die ersten drei Stiche (vier Damen, alle anderen haben nur Fehlkarten) -> Solo
        q = lambda s: Card(s, Rank.QUEEN, 0)
        h = {0: [q(Suit.CLUBS), q(Suit.SPADES), q(Suit.HEARTS), q(Suit.DIAMONDS)],
             1: [Card(Suit.CLUBS, Rank.NINE, 0), Card(Suit.CLUBS, Rank.NINE, 1), Card(Suit.SPADES, Rank.NINE, 0), Card(Suit.SPADES, Rank.NINE, 1)],
             2: [Card(Suit.CLUBS, Rank.KING, 0), Card(Suit.CLUBS, Rank.KING, 1), Card(Suit.SPADES, Rank.KING, 0), Card(Suit.SPADES, Rank.KING, 1)],
             3: [Card(Suit.CLUBS, Rank.TEN, 0), Card(Suit.CLUBS, Rank.TEN, 1), Card(Suit.SPADES, Rank.TEN, 0), Card(Suit.SPADES, Rank.TEN, 1)]}
        _points, party = pimc.rollout_wedding(h, [], 0, 0, GameType.NORMAL, self.cfg, False, start=0)
        self.assertEqual(party, {0: True, 1: False, 2: False, 3: False})

    def test_tricks_done_counts_towards_the_third_trick(self):
        # zwei Stiche sind schon gespielt, der Hochzeiter holt auch den dritten -> ab jetzt Solo
        h = {0: [Card(Suit.CLUBS, Rank.QUEEN, 0)], 1: [Card(Suit.CLUBS, Rank.NINE, 0)], 2: [Card(Suit.CLUBS, Rank.KING, 0)],
             3: [Card(Suit.CLUBS, Rank.TEN, 0)]}
        _points, party = pimc.rollout_wedding(h, [], 0, 2, GameType.NORMAL, self.cfg, False, start=0)
        self.assertEqual(party, {0: True, 1: False, 2: False, 3: False})

    def test_no_clarification_when_nothing_is_left(self):
        h = {s: [] for s in range(4)}
        points, party = pimc.rollout_wedding(h, [], 1, 5, GameType.NORMAL, self.cfg, False, start=0)
        self.assertEqual(points, {0: 0, 1: 0, 2: 0, 3: 0})
        self.assertEqual(party, {0: False, 1: True, 2: False, 3: False})


class PublicAnnouncementTests(TuneCase):
    def test_declared_schweinchen_puts_the_unseen_foxes_at_the_declarer(self):
        from app.rules.game import new_game
        hands = dict(NORMAL_HANDS)
        hands[0] = "A♦ A♦ Q♠ Q♠ J♣ J♣ A♣ A♣ 10♣ 10♣ K♣ K♣"
        hands[3] = "Q♦ Q♦ J♥ J♥ K♦ K♦ 9♦ 9♦ 9♠ 9♠ 9♥ 9♥"
        g = new_game(with_options(schweinchen=True), rig(hands, 3, WITH), 3)
        declare_all(g)
        apply_action(g, DeclareSchweinchen(0))
        for seat in (1, 2, 3):
            view = bot_view(g, seat)
            mem = bots.Memory(view, [])
            unseen = [Card(face[1], face[0], i) for face, n in mem.unseen.items() for i in range(n)]
            forced = bots._announced_cards(view, unseen)
            self.assertEqual(sorted(forced), [0])
            self.assertEqual({c.face for c in forced[0]}, {(Rank.ACE, Suit.DIAMONDS)})
            self.assertEqual(len(forced[0]), 2)
        view0 = bot_view(g, 0)                                           # der Ansager selbst: nichts zu folgern
        mem0 = bots.Memory(view0, [])
        self.assertEqual(bots._announced_cards(view0, [Card(Suit.DIAMONDS, Rank.ACE, 0)]), {})

    def test_wedding_queens_are_placed_at_the_wedding_player(self):
        g = wedding_game()
        view = bot_view(g, 0)
        mem = bots.Memory(view, [])
        unseen = [Card(face[1], face[0], i) for face, n in mem.unseen.items() for i in range(n)]
        forced = bots._announced_cards(view, unseen)
        self.assertEqual(sorted(forced), [g.wedding_seat])
        self.assertEqual(len(forced[g.wedding_seat]), 2)

    def test_switch_turns_the_deduction_off(self):
        g = wedding_game()
        bots.TUNE["pimc_public"] = False
        choice_off, _ = first_choice(g, g.turn)
        bots._PIMC_CACHE.clear()
        bots.TUNE["pimc_public"] = True
        choice_on, _ = first_choice(g, g.turn)
        self.assertIsNotNone(choice_off)
        self.assertIsNotNone(choice_on)


if __name__ == "__main__":
    unittest.main()
