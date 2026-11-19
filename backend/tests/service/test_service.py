"""TableService: Berechtigung, Versionskonflikte, Idempotenz, Nebenlaeufigkeit, Spielablauf."""
import random
import threading
import unittest

from ..rules import loader  # noqa: F401
from app.rules import Phase, RuleViolation, VersionConflict, ddv_profile
from app.rules.game import legal_actions
from app.table import AccessDenied, MemoryStore, NoSuchTable, TableService

HUMANS = [{"memberId": 10 + i, "name": f"P{i}", "isBot": False} for i in range(4)]
MIXED = [{"memberId": 10, "name": "Ich", "isBot": False}] + [
    {"memberId": 11 + i, "name": f"Bot {i + 1}", "isBot": True} for i in range(3)]


def first_declare(svc, code="R1"):
    stored = svc.load(code)
    seat = stored.table.game.query_seat
    return stored, 10 + seat, {"type": "declare", "reservation": False}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.svc = TableService(self.store, random.Random(1))
        self.svc.start("R1", HUMANS, ddv_profile())

    def test_start_creates_version_one(self):
        self.assertEqual(self.svc.load("R1").version, 1)
        with self.assertRaises(NoSuchTable):
            self.svc.act("NOPE", 10, {"type": "declare", "reservation": False})

    def test_only_seated_members_may_act(self):
        _, _, payload = first_declare(self.svc)
        with self.assertRaises(AccessDenied):
            self.svc.act("R1", 99, payload)
        with self.assertRaises(AccessDenied):
            self.svc.next_game("R1", 99)

    def test_wrong_turn_and_rule_violations_do_not_change_state(self):
        stored, _, payload = first_declare(self.svc)
        wrong = 10 + (stored.table.game.query_seat + 1) % 4
        with self.assertRaises(RuleViolation) as cm:
            self.svc.act("R1", wrong, payload)
        self.assertEqual(cm.exception.code, "not_your_turn")
        self.assertEqual(self.svc.load("R1").version, 1)

    def test_version_conflict(self):
        stored, member, payload = first_declare(self.svc)
        out = self.svc.act("R1", member, {**payload, "expectedVersion": 1})
        self.assertEqual(out.version, 2)
        stored, member, payload = first_declare(self.svc)
        with self.assertRaises(VersionConflict) as cm:
            self.svc.act("R1", member, {**payload, "expectedVersion": 1})     # veraltet
        self.assertEqual((cm.exception.expected, cm.exception.actual), (1, 2))

    def test_action_id_makes_retries_idempotent(self):
        _, member, payload = first_declare(self.svc)
        first = self.svc.act("R1", member, {**payload, "actionId": "x1"})
        again = self.svc.act("R1", member, {**payload, "actionId": "x1"})
        self.assertFalse(first.duplicate)
        self.assertTrue(again.duplicate)
        self.assertEqual((again.version, self.svc.load("R1").version), (2, 2))

    def test_bad_meta_fields(self):
        _, member, payload = first_declare(self.svc)
        for extra in ({"expectedVersion": "1"}, {"expectedVersion": True}, {"actionId": ""}, {"actionId": 5},
                      {"actionId": "x" * 65}):
            with self.assertRaises(RuleViolation):
                self.svc.act("R1", member, {**payload, **extra})

    def test_next_game_only_after_finished_game(self):
        with self.assertRaises(RuleViolation) as cm:
            self.svc.next_game("R1", 10)
        self.assertEqual(cm.exception.code, "game_running")

    def test_next_game_deals_again_and_books_history(self):
        svc = TableService(MemoryStore(), random.Random(2))
        svc.start("R2", MIXED, ddv_profile())
        rng = random.Random(9)
        while svc.load("R2").table.game.phase is not Phase.FINISHED:
            table = svc.load("R2").table
            acts = [a for a in legal_actions(table.game, 0) if a["type"] in ("declare", "play_card", "baptize")]
            a = acts[0]
            payload = ({"type": "declare", "reservation": False} if a["type"] == "declare" else
                       {"type": "baptize", "choice": "solo_queens"} if a["type"] == "baptize" else
                       {"type": "play_card", "cardId": rng.choice(a["cards"])})
            svc.act("R2", 10, payload)
        stored = svc.load("R2")
        self.assertTrue(stored.table.recorded)
        self.assertEqual(len(svc.store.history("R2")), 1)
        out = svc.next_game("R2", 10)
        self.assertEqual(svc.load("R2").table.game_number, 2)
        self.assertEqual(out.version, stored.version + 1)

    def test_concurrent_acts_are_serialized(self):
        """Zwei Threads senden gleichzeitig dieselbe legale Aktion: genau eine wirkt, keine Beschaedigung."""
        _, member, payload = first_declare(self.svc)
        results, errors = [], []

        def worker():
            try:
                results.append(self.svc.act("R1", member, payload))
            except RuleViolation as exc:
                errors.append(exc.code)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(len(results), 1)
        self.assertEqual(errors, ["not_your_turn"] * 5)
        self.assertEqual(self.svc.load("R1").version, 2)

    def test_store_detects_lost_update(self):
        stored = self.svc.load("R1")
        self.store.save("R1", stored.table, 1, [])
        with self.assertRaises(VersionConflict):
            self.store.save("R1", stored.table, 1, [])


if __name__ == "__main__":
    unittest.main()
