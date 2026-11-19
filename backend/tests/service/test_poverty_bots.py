"""Bots und die Hausregel "Armut": anmelden, abgeben, uebernehmen, zurueckgeben - und das Spiel danach zu Ende spielen."""
import random
import unittest

from ..rules import loader  # noqa: F401
from app.rules import Phase, bot_view, new_game, new_round, start_next_game
from app.rules.cards import Card, card
from app.rules.dealing import shuffled_deck
from app.rules.game import GameKind, apply_action, legal_actions
from app.rules.options import RuleOptions
from app.rules.profile import make_profile
from app.table import next_bot_action
from app.table.bots import _accepts_poverty, choose_action, known_parties

from ..rules.fixtures import WITH, rig, with_options
from ..rules.test_poverty import BUYER, POOR, POVERTY_HANDS, ids

ALL_BOTS = [True] * 4


def run_bots_until(state, stop):
    for _ in range(600):
        if stop(state):
            return
        pending = next_bot_action(state, ALL_BOTS)
        assert pending is not None, f"Bot blockiert in Phase {state.phase}"
        apply_action(state, pending[1])
    raise AssertionError("Bot-Schleife terminiert nicht")


class BotPovertyTests(unittest.TestCase):
    def start(self, **options):
        return new_game(with_options(poverty=True, **options), rig(POVERTY_HANDS, 3, WITH), 3)

    def test_bots_play_a_whole_poverty_game(self):
        s = self.start()
        run_bots_until(s, lambda g: g.phase is Phase.FINISHED)
        self.assertEqual(s.kind, GameKind.POVERTY)
        self.assertEqual((s.poverty_seat, s.poverty_buyer), (POOR, BUYER))
        self.assertEqual(sum(t.points for t in s.tricks), 240)
        self.assertEqual(sum(s.score.seat_deltas), 0)

    def test_bots_ignore_poverty_when_the_rule_is_off(self):
        s = new_game(make_profile(WITH), rig(POVERTY_HANDS, 3, WITH), 3)
        run_bots_until(s, lambda g: g.phase is Phase.PLAYING)
        self.assertEqual(s.kind, GameKind.NORMAL)
        self.assertIsNone(s.poverty_seat)

    def test_poor_bot_passes_all_trumps_and_fills_with_worthless_cards(self):
        s = self.start()
        run_bots_until(s, lambda g: g.phase is Phase.POVERTY_PASS)
        action = choose_action(bot_view(s, POOR))
        passed = {Card.from_id(i).face for i in action.card_ids}
        self.assertEqual(len(action.card_ids), 3)
        self.assertEqual(passed, {Card.from_id(i).face for i in ids(s, POOR, "Q♣", "J♦", "9♦")})
        # nur zwei Truempfe: Rest wird mit der billigsten Fehlkarte aufgefuellt (hier die Karo-Neun zaehlt als Trumpf)
        hands = dict(POVERTY_HANDS)
        hands[2] = "Q♣ J♦ 9♣ A♣ A♣ 10♣ K♣ A♠ 10♠ K♠ A♥ K♥"
        hands[3] = POVERTY_HANDS[3].replace("9♣ 9♣ 9♠", "9♦ 9♣ 9♠")
        t = new_game(with_options(poverty=True), rig(hands, 3, WITH), 3)
        run_bots_until(t, lambda g: g.phase is Phase.POVERTY_PASS)
        faces = {Card.from_id(i).face for i in choose_action(bot_view(t, POOR)).card_ids}
        self.assertEqual(faces, {Card.from_id(i).face for i in ids(t, POOR, "Q♣", "J♦", "9♣")})

    def test_bot_accepts_only_with_a_strong_hand(self):
        s = self.start()
        run_bots_until(s, lambda g: g.phase is Phase.POVERTY_OFFER)
        self.assertTrue(choose_action(bot_view(s, BUYER)).accept)            # 9 Truempfe
        # Grenzen direkt pruefen: 6 Truempfe reichen, 5 nur mit Kreuz-Dame, 4 nie
        def view(text):
            return {"hand": [card(t).to_dict() for t in text.split()], "deckVariant": "with_nines", "ruleOptions": {}}
        self.assertTrue(_accepts_poverty(view("Q♠ Q♥ J♣ J♠ A♦ 10♦ A♣ A♣ 10♣ K♣ A♠ 10♠")))      # 6
        self.assertFalse(_accepts_poverty(view("Q♠ Q♥ J♣ J♠ A♦ 9♣ A♣ A♣ 10♣ K♣ A♠ 10♠")))     # 5 ohne Kreuz-Dame
        self.assertTrue(_accepts_poverty(view("Q♣ Q♥ J♣ J♠ A♦ 9♣ A♣ A♣ 10♣ K♣ A♠ 10♠")))      # 5 mit Kreuz-Dame
        self.assertFalse(_accepts_poverty(view("Q♣ Q♥ J♣ J♠ 9♠ 9♣ A♣ A♣ 10♣ K♣ A♠ 10♠")))    # 4

    def test_buyer_bot_returns_the_weakest_side_cards(self):
        s = self.start()
        run_bots_until(s, lambda g: g.phase is Phase.POVERTY_RETURN)
        action = choose_action(bot_view(s, BUYER))
        self.assertEqual(len(set(action.card_ids)), 3)
        returned = [Card.from_id(i) for i in action.card_ids]
        self.assertTrue(all(c.value == 0 for c in returned), returned)       # die drei Neunen

    def test_bots_know_that_poor_and_buyer_are_re(self):
        s = self.start()
        run_bots_until(s, lambda g: g.phase is Phase.PLAYING)
        self.assertEqual(s.kind, GameKind.POVERTY)
        for seat in range(4):
            known = known_parties(bot_view(s, seat), [])
            self.assertEqual(known, {0: "kontra", 1: "kontra", POOR: "re", BUYER: "re"}, seat)

    def test_bot_keeps_the_wedding_when_it_also_qualifies_for_poverty(self):
        hands = dict(POVERTY_HANDS)
        hands[2] = "Q♣ Q♣ 9♦ A♣ A♣ 10♣ K♣ A♠ 10♠ K♠ A♥ K♥"                  # beide Kreuz-Damen, 3 Truempfe
        hands[3] = "10♥ 10♥ Q♠ Q♠ Q♥ J♣ J♣ A♦ J♦ 9♣ 9♣ 9♠"
        s = new_game(with_options(poverty=True), rig(hands, 3, WITH), 3)
        run_bots_until(s, lambda g: g.phase in (Phase.PLAYING, Phase.POVERTY_PASS))
        self.assertEqual((s.phase, s.kind), (Phase.PLAYING, GameKind.WEDDING))

    def test_poverty_occurs_in_random_deals_and_always_ends_with_full_hands(self):
        rng = random.Random(5)
        profile = with_options(poverty=True)
        seen = 0
        for _ in range(400):
            rnd = new_round(profile)
            g = start_next_game(rnd, profile, shuffled_deck(WITH, rng))
            run_bots_until(g, lambda x: x.phase in (Phase.PLAYING, Phase.FINISHED))
            self.assertEqual([len(h) for h in g.hands], [12] * 4)
            seen += g.kind is GameKind.POVERTY
        self.assertGreater(seen, 3)


if __name__ == "__main__":
    unittest.main()
