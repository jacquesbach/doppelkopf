"""Tischschicht: Runde mit Bots, Sichten/Datenschutz, Serialisierung, Aktionsparser."""
import json
import random
import unittest

from ..rules import loader  # noqa: F401
from app.rules import GameKind, Phase, RuleOptions, RuleViolation, ddv_profile, make_profile, DeckVariant
from app.rules.game import legal_actions
from app.table import (MemoryStore, TableService, TableState, new_table, parse_action, run_bots, settle,
                       start_next, view_for)

SEATS = [{"memberId": 10 + i, "name": f"P{i}", "isBot": i != 0} for i in range(4)]   # Sitz 0 = Mensch, 1-3 = Bots


def human_move(table, rng):
    """Zufaellige legale Aktion des Menschen auf Sitz 0 (nur wenn er etwas tun darf)."""
    acts = legal_actions(table.game, 0)
    turn_acts = [a for a in acts if a["type"] != "announce" or rng.random() < 0.05]
    if not turn_acts and table.game.turn == 0:      # z. B. Pflichtansage: einzige Aktion
        turn_acts = acts
    if not turn_acts:
        return None
    a = rng.choice(turn_acts) if table.game.turn != 0 else next((x for x in turn_acts if x["type"] != "announce"), turn_acts[0])
    t = a["type"]
    payload = {"declare": {"type": "declare", "reservation": rng.random() < 0.15},
               "resolve": {"type": "resolve", "accept": rng.random() < 0.5},
               "baptize": {"type": "baptize", "choice": rng.choice(a.get("choices", ["solo_queens"]))},
               "play_card": {"type": "play_card", "cardId": rng.choice(a.get("cards", [""]))},
               "announce": {"type": "announce", "level": rng.choice(a.get("levels", [0]))},
               "schweinchen": {"type": "schweinchen"},
               "poverty_pass": lambda: {"type": "poverty_pass", "cardIds": rng.sample(a["cards"], 3)},
               "poverty_offer": lambda: {"type": "poverty_offer", "accept": rng.random() < 0.5},
               "poverty_return": lambda: {"type": "poverty_return", "cardIds": rng.sample(a["cards"], 3)}}[t]
    return payload() if callable(payload) else payload


class RoundWithBots(unittest.TestCase):
    def play_round(self, profile, seed, check_every=7):
        rng = random.Random(seed)
        svc = TableService(MemoryStore(), rng)
        svc.start("ABC123", SEATS, profile)
        summaries, last_version, steps = [], 1, 0
        while True:
            stored = svc.load("ABC123")
            table = stored.table
            self.assertGreaterEqual(stored.version, last_version)
            last_version = stored.version
            if table.finished:
                break
            if table.game.phase is Phase.FINISHED:
                out = svc.next_game("ABC123", 10)
                summaries += out.summaries
                continue
            payload = human_move(table, rng)
            self.assertIsNotNone(payload, f"Mensch blockiert: phase={table.game.phase} turn={table.game.turn}")
            steps += 1
            self.assertLess(steps, 6000)
            out = svc.act("ABC123", 10, {**payload, "expectedVersion": stored.version, "actionId": f"a{steps}"})
            summaries += out.summaries
            if steps % check_every == 0:
                d = json.loads(json.dumps(svc.load("ABC123").table.to_dict()))
                self.assertEqual(TableState.from_dict(d).to_dict(), d)
        return svc.load("ABC123").table, summaries

    def check_round(self, table, summaries, profile):
        rnd = table.round
        self.assertTrue(table.finished)
        self.assertEqual(rnd.normal_games_played, profile.normal_games_per_round)
        self.assertTrue(all(rnd.pflichtsolo_done))
        self.assertEqual(sum(rnd.totals), 0)
        self.assertEqual(len(rnd.results), table.game_number)
        self.assertEqual(len(summaries), table.game_number)               # jedes Spiel genau einmal gebucht
        self.assertEqual(sum(1 for r in rnd.results if r["kind"].startswith("pflichtsolo")), 4)
        self.assertEqual([s["gameNumber"] for s in summaries], list(range(1, table.game_number + 1)))

    def test_full_round_ddv(self):
        for seed in (1, 2, 3):
            table, summaries = self.play_round(ddv_profile(), seed)
            self.check_round(table, summaries, ddv_profile())

    def test_full_round_without_nines_and_all_options(self):
        profile = make_profile(DeckVariant.WITHOUT_NINES, RuleOptions(**{k: True for k in RuleOptions().to_dict()}))
        table, summaries = self.play_round(profile, 7)
        self.check_round(table, summaries, profile)

    def test_full_round_with_poverty_rule(self):
        profile = make_profile(DeckVariant.WITH_NINES, RuleOptions(poverty=True))
        kinds = set()
        for seed in (4, 8):
            table, summaries = self.play_round(profile, seed)
            self.check_round(table, summaries, profile)
            kinds |= {r["kind"] for r in table.round.results}
        self.assertTrue(kinds <= {"normal", "pflichtsolo", "pflichtsolo_forced", "lustsolo", "wedding",
                                  "silent_wedding", "poverty"})

    def test_bots_deal_with_forced_solo(self):
        """Bots, die vorgefuehrt werden, taufen selbst ein Solo; passive Menschen erzwingen 4 Vorfuehrungen."""
        table, summaries = self.play_round(ddv_profile(), 5)
        self.assertGreaterEqual(sum(1 for r in table.round.results if r["kind"] == "pflichtsolo_forced"), 1)


class ViewPrivacy(unittest.TestCase):
    def setUp(self):
        self.svc = TableService(MemoryStore(), random.Random(3))
        self.svc.start("ROOM01", SEATS, ddv_profile())
        self.stored = self.svc.load("ROOM01")

    def test_player_sees_only_own_hand(self):
        view = view_for(self.stored.table, 10, self.stored.version)
        self.assertEqual(view["table"]["mySeat"], 0)
        mine = {json.dumps(c, sort_keys=True) for c in view["game"]["hand"]}
        others = {json.dumps(c.to_dict(), sort_keys=True) for s in (1, 2, 3) for c in self.stored.table.game.hands[s]}
        text = json.dumps(view)
        for c in others - mine:
            self.assertNotIn(c, text)
        self.assertEqual(len(view["game"]["hand"]), 12)

    def test_spectator_and_unknown_member_get_no_hands(self):
        for member in (None, 999):
            view = view_for(self.stored.table, member, self.stored.version)
            self.assertNotIn("hand", view["game"])
            self.assertIsNone(view["table"]["mySeat"])
            self.assertEqual(view["game"]["role"], "spectator")
            self.assertNotIn("legalActions", view["game"])

    def test_bot_member_view_equals_player_rules(self):
        view = view_for(self.stored.table, 11, self.stored.version)
        self.assertEqual(view["table"]["mySeat"], 1)
        self.assertEqual(len(view["game"]["hand"]), 12)


class ParserTests(unittest.TestCase):
    def test_valid_payloads(self):
        self.assertEqual(parse_action(2, {"type": "play_card", "cardId": "A-♣-0"}).seat, 2)
        self.assertEqual(parse_action(1, {"type": "announce", "level": 0}).level, 0)
        self.assertTrue(parse_action(0, {"type": "declare", "reservation": True}).reservation)
        self.assertEqual(parse_action(3, {"type": "schweinchen"}).seat, 3)
        self.assertEqual(parse_action(2, {"type": "poverty_pass", "cardIds": ["A-♣-0", "9-♣-1", "K-♠-0"]}).card_ids,
                         ("A-♣-0", "9-♣-1", "K-♠-0"))
        self.assertTrue(parse_action(1, {"type": "poverty_offer", "accept": True}).accept)
        self.assertEqual(parse_action(3, {"type": "poverty_return", "cardIds": ["A-♣-0"]}).seat, 3)

    def test_seat_never_taken_from_payload(self):
        self.assertEqual(parse_action(1, {"type": "play_card", "cardId": "A-♣-0", "seat": 3, "memberId": 99}).seat, 1)

    def test_rejects_bad_payloads(self):
        for bad in (None, [], {}, {"type": "nope"}, {"type": "play_card"}, {"type": "play_card", "cardId": 5},
                    {"type": "announce", "level": "0"}, {"type": "announce", "level": True},
                    {"type": "declare", "reservation": "yes"}, {"type": "resolve"},
                    {"type": "poverty_pass"}, {"type": "poverty_pass", "cardIds": "A-♣-0"},
                    {"type": "poverty_pass", "cardIds": [1, 2, 3]}, {"type": "poverty_return", "cardIds": None},
                    {"type": "poverty_offer"}, {"type": "poverty_offer", "accept": "yes"}):
            with self.assertRaises(RuleViolation, msg=str(bad)):
                parse_action(0, bad)


if __name__ == "__main__":
    unittest.main()
