"""Armut ohne Kaeufer: Der Tisch gibt mit demselben Geber neu; das abgebrochene Spiel zaehlt nicht."""
import json
import random
import unittest

from ..rules import loader  # noqa: F401
from app.rules import Phase, apply_action, new_game
from app.rules.game import GameKind
from app.table import MemoryStore, TableService, TableState, new_table, next_bot_action, redeal_if_needed, start_next

from ..rules.fixtures import WITH, rig, with_options
from ..rules.test_poverty import POOR, POVERTY_HANDS, ids

HUMANS = [{"memberId": 10 + i, "name": f"P{i}", "isBot": False} for i in range(4)]


def rigged_table(profile=None, seats=HUMANS):
    """Tisch, dessen erstes Spiel die feste Armut-Verteilung hat (Geber = Sitz 3, Sitz 2 ist arm)."""
    profile = profile or with_options(poverty=True)
    table = new_table(seats, profile, random.Random(1))
    table.round.dealer = 3
    table.game = new_game(profile, rig(POVERTY_HANDS, 3, WITH), 3)
    return table


class RedealServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.svc = TableService(self.store, random.Random(7))
        self.table = rigged_table()
        self.store.create("R1", self.table)

    def act(self, seat, **payload):
        return self.svc.act("R1", 10 + seat, payload)

    def poor_goes_unanswered(self):
        for seat in (0, 1, 2, 3):
            self.act(seat, type="declare", reservation=seat == POOR)
        self.act(POOR, type="baptize", choice="poverty")
        game = self.svc.load("R1").table.game
        self.act(POOR, type="poverty_pass", cardIds=list(ids(game, POOR, "Q♣", "J♦", "9♦")))
        for seat in (3, 0, 1):
            self.act(seat, type="poverty_offer", accept=False)

    def test_table_redeals_with_the_same_dealer_and_does_not_count_the_game(self):
        old_cards = sorted(c.id for c in self.table.game.hands[POOR])
        self.poor_goes_unanswered()
        table = self.svc.load("R1").table
        self.assertEqual(table.redeals, 1)
        self.assertEqual(table.redeal_seat, POOR)
        self.assertEqual(table.game.phase, Phase.RESERVATION_QUERY)        # neue Karten, Vorbehaltsabfrage von vorn
        self.assertEqual(table.game.dealer, 3)
        self.assertEqual(table.game_number, 1)                              # keine neue Spielnummer
        self.assertEqual((table.round.normal_games_played, table.round.results, table.round.totals),
                         (0, [], [0, 0, 0, 0]))
        self.assertFalse(table.recorded)
        self.assertNotEqual(sorted(c.id for c in table.game.hands[POOR]), old_cards)
        self.assertEqual(table.game.poverty_seat, None)
        self.assertEqual([len(h) for h in table.game.hands], [12] * 4)
        view = self.svc.view("R1", 10 + POOR)
        self.assertEqual((view["table"]["redeals"], view["table"]["redealSeat"]), (1, POOR))

    def test_redeal_keeps_a_running_bock_round_and_the_forced_solo(self):
        table = self.table
        table.round.bock_remaining = 2
        self.store.save("R1", table, 1, [])
        self.poor_goes_unanswered()
        new = self.svc.load("R1").table
        self.assertEqual(new.game.score_multiplier, 2)                      # Bockspiel wurde nicht verbraucht
        self.assertEqual(new.round.bock_remaining, 2)

    def test_redeal_state_is_persisted(self):
        self.poor_goes_unanswered()
        table = self.svc.load("R1").table
        d = json.loads(json.dumps(table.to_dict()))
        self.assertEqual(TableState.from_dict(d).to_dict(), d)
        d.pop("redeals"), d.pop("redealSeat")                               # alte gespeicherte Tische
        old = TableState.from_dict(d)
        self.assertEqual((old.redeals, old.redeal_seat), (0, None))

    def test_redeal_only_in_the_redeal_phase_and_next_game_resets_the_counter(self):
        table = rigged_table()
        self.assertFalse(redeal_if_needed(table))                           # nur in der Phase REDEAL
        table.redeals, table.redeal_seat = 2, POOR
        table.game.phase, table.recorded = Phase.FINISHED, True
        start_next(table, random.Random(1))
        self.assertEqual((table.redeals, table.redeal_seat, table.game_number), (0, None, 2))

    def test_a_declining_bot_triggers_the_redeal_too(self):
        """Der letzte, der ablehnt, ist ein Bot (er uebernimmt erst ab 6 Truempfen): Auch dann wird neu gegeben."""
        for paced in (False, True):
            with self.subTest(paced=paced):
                store = MemoryStore()
                svc = TableService(store, random.Random(5), paced=paced)
                seats = [{"memberId": 40 + i, "name": f"P{i}", "isBot": i == 1} for i in range(4)]    # Sitz 1 = Bot
                table = rigged_table(seats=seats)
                table.game = new_game(table.profile, rig(hands_with_weak_bot(), 3, WITH), 3)
                store.create("R2", table)

                def act(seat, **payload):
                    svc.act("R2", 40 + seat, payload)
                    if paced:                                    # getaktet: Bots ziehen einzeln
                        while svc.pending_delay("R2") is not None:
                            svc.bot_step("R2")

                act(0, type="declare", reservation=False)
                act(2, type="declare", reservation=True)
                act(3, type="declare", reservation=False)
                act(POOR, type="baptize", choice="poverty")
                game = svc.load("R2").table.game
                act(POOR, type="poverty_pass", cardIds=list(ids(game, POOR, "Q♣", "J♦", "9♦")))
                act(3, type="poverty_offer", accept=False)
                act(0, type="poverty_offer", accept=False)            # danach lehnt der Bot (Sitz 1) ab
                after = svc.load("R2").table
                self.assertEqual((after.redeals, after.redeal_seat, after.game_number), (1, POOR, 1))
                self.assertIn(after.game.phase, (Phase.RESERVATION_QUERY, Phase.PLAYING))
                self.assertEqual(after.game.dealer, 3)
                self.assertEqual(after.round.normal_games_played, 0)


def hands_with_weak_bot():
    """Sitz 2 arm; Sitz 3 hat 8, Sitz 0 hat 10, der Bot auf Sitz 1 nur 5 Truempfe ohne Kreuz-Dame."""
    from app.rules.cards import build_deck
    from app.rules.trump import GameType, TrumpConfig, is_trump, strength
    from app.rules.cards import card
    left = build_deck(WITH)
    for t in POVERTY_HANDS[POOR].split():
        left.remove(next(c for c in left if c.face == card(t).face))
    cfg = TrumpConfig(WITH)
    trumps = sorted((c for c in left if is_trump(c, GameType.NORMAL, cfg)), key=lambda c: strength(c, GameType.NORMAL, cfg))
    side = [c for c in left if not is_trump(c, GameType.NORMAL, cfg)]
    assert len(trumps) == 23 and len(side) == 13
    text = lambda cards: " ".join(f"{c.rank.value}{c.suit.value}" for c in cards)
    weak_bot = trumps[-5:]                                          # die fuenf schwaechsten Truempfe (Karo)
    rest = trumps[:-5]
    return {0: text(rest[:10] + side[:2]), 1: text(weak_bot + side[2:9]), 2: POVERTY_HANDS[POOR],
            3: text(rest[10:] + side[9:])}


class RedealRandomDealsTests(unittest.TestCase):
    def test_poverty_deals_with_bots_never_block(self):
        rng = random.Random(11)
        profile = with_options(poverty=True)
        poverties = 0
        for _ in range(500):
            table = new_table([{"memberId": 30 + i, "name": f"B{i}", "isBot": True} for i in range(4)], profile, rng)
            for _step in range(300):
                g = table.game
                if g.phase in (Phase.PLAYING, Phase.FINISHED):
                    break
                seat, action = next_bot_action(g, [True] * 4) or (None, None)
                self.assertIsNotNone(action, f"Bots blockieren in Phase {g.phase}")
                apply_action(g, action)
                redeal_if_needed(table, rng)
            self.assertIn(table.game.phase, (Phase.PLAYING, Phase.FINISHED))
            self.assertEqual([len(h) for h in table.game.hands], [12] * 4)
            poverties += table.game.kind is GameKind.POVERTY
        # Mit hoechstens 3 Truempfen beim Armen haben die anderen zusammen mindestens 23: ein Bot uebernimmt also immer.
        self.assertGreater(poverties, 3)
        self.assertEqual(table.redeals, 0)


if __name__ == "__main__":
    unittest.main()
