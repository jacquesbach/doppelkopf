"""Oeffentliche Spielereignisse (fuer die Hinweise in der Oberflaeche) stimmen mit der Wertung ueberein."""
import random
import unittest

from ..rules import loader  # noqa: F401
from app.rules import DeckVariant, Phase, RuleOptions, apply_action, bot_view, make_profile, new_round, player_view, \
    start_next_game
from app.rules.cards import Rank, Suit
from app.rules.dealing import shuffled_deck
from app.table.bots import choose_action

QUEEN_CLUBS = (Rank.QUEEN, Suit.CLUBS)
OPTIONS = RuleOptions(mandatory_announcements=True, solo_leads=True, karlchen=True, karlchen_caught=True,
                      fuchsjagd=True, schweinchen=True, bock_heart_trick=True)


def play(profile, rng):
    rnd = new_round(profile)
    game = start_next_game(rnd, profile, shuffled_deck(profile.deck_variant, rng))
    for _ in range(500):
        if game.phase is Phase.FINISHED:
            return game
        for seat in range(4):
            action = choose_action(bot_view(game, seat))
            if action is not None:
                apply_action(game, action)
                break
    raise AssertionError("terminiert nicht")


class PublicEvents(unittest.TestCase):
    def test_events_match_scoring_and_never_leak_parties(self):
        rng = random.Random(5)
        seen = set()
        for variant in (DeckVariant.WITH_NINES, DeckVariant.WITHOUT_NINES):
            profile = make_profile(variant, OPTIONS)
            for _ in range(60):
                game = play(profile, rng)
                view = player_view(game, 0)
                events = view["events"]
                ids = [e["id"] for e in events]
                self.assertEqual(ids, sorted(set(ids)))
                self.assertEqual(len(view["tricks"]), profile.trick_count)
                self.assertEqual(view["reSeats"], game.re_seats)
                items = game.score.to_dict().get("items", {})
                codes = [i["code"] for party in items.values() for i in party]
                for e in events:
                    seen.add(e["type"])
                    if e["type"] == "fox_caught":      # nur zwischen echten Gegnern ...
                        self.assertNotEqual(e["seat"] in game.re_seats, e["victim"] in game.re_seats)
                        # ... und erst, wenn beide Kreuz-Damen gespielt sind (oder eine Hochzeit geklaert ist)
                        played = [p for t in game.tricks[:e["trick"]] for p in t.plays if p.card.face == QUEEN_CLUBS]
                        self.assertTrue(len(played) == 2 or game.kind.value == "wedding", e)
                self.assertEqual(sum(e["type"] == "doppelkopf" for e in events), codes.count("doppelkopf"))
                self.assertEqual(sum(e["type"] == "charlie_last_trick" for e in events),
                                 codes.count("charlie_last_trick"))
                self.assertLessEqual(sum(e["type"] == "fox_caught" for e in events), codes.count("fox_caught"))
        self.assertIn("doppelkopf", seen)
        self.assertIn("fox_caught", seen)

    def test_events_hidden_before_game_end_have_no_tricks(self):
        profile = make_profile(DeckVariant.WITH_NINES, OPTIONS)
        game = start_next_game(new_round(profile), profile, shuffled_deck(profile.deck_variant, random.Random(1)))
        view = player_view(game, 0)
        self.assertNotIn("tricks", view)
        self.assertNotIn("reSeats", view)


if __name__ == "__main__":
    unittest.main()
