"""Bot-Uebernahme bei Inaktivitaet: Host-Einstellung, Countdown, "Weiterspielen", kein Eingriff beim Spiel gegen Bots."""
import random
import unittest
from datetime import datetime, timedelta, timezone

from ..rules import loader  # noqa: F401
from app.housekeeping import is_idle, last_activity
from app.rules import DeckVariant, Phase, make_profile
from app.rules.errors import RuleViolation
from app.table import BotRunner, MemoryStore, TableService
from app.table.state import TableState, WARN_SECONDS

CODE = "TAK123"
TWO = [{"memberId": 10 + i, "name": f"P{i}", "isBot": i > 1} for i in range(4)]       # zwei Menschen (10, 11)
SOLO = [{"memberId": 10 + i, "name": f"P{i}", "isBot": i > 0} for i in range(4)]      # ein Mensch (10)
PROFILE = make_profile(DeckVariant.WITH_NINES)


class Clock:
    def __init__(self):
        self.now = 1_000_000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def make(seats, takeover=120, seed=5):
    clock = Clock()
    svc = TableService(MemoryStore(), random.Random(seed), paced=True, clock=clock)
    svc.start(CODE, seats, PROFILE, takeover)
    return svc, clock


def awaited_member(svc):
    """Mensch, der gerade dran ist (die Bots laufen im Test ueber ``play_bots``)."""
    table = svc.load(CODE).table
    from app.table.service import _acting_seat
    seat = _acting_seat(table.game)
    return seat, table.seats[seat]["memberId"]


def play_bots(svc):
    for _ in range(300):
        if svc.pending_delay(CODE) is None:
            return
        svc.bot_step(CODE)


class Takeover(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock = make(TWO)
        play_bots(self.svc)
        self.seat, self.member = awaited_member(self.svc)

    def test_nothing_happens_before_the_idle_time(self):
        self.clock.advance(119)
        self.assertIsNone(self.svc.watch_tick(CODE))
        self.assertIsNone(self.svc.load(CODE).table.warning)

    def test_countdown_starts_after_idle_time_and_is_visible_to_everyone(self):
        self.clock.advance(120)
        out = self.svc.watch_tick(CODE)
        self.assertIsNotNone(out)
        for member in (10, 11):
            warn = self.svc.view(CODE, member)["table"]["takeoverWarning"]
            self.assertEqual(warn, {"seat": self.seat, "remaining": WARN_SECONDS})
        self.clock.advance(10)
        self.assertEqual(self.svc.view(CODE, 10)["table"]["takeoverWarning"]["remaining"], WARN_SECONDS - 10)
        self.assertIsNone(self.svc.watch_tick(CODE))             # Countdown laeuft noch, nichts Neues
        self.assertFalse(self.svc.load(CODE).table.seats[self.seat].get("autoplay"))

    def test_bot_takes_over_when_countdown_expires(self):
        self.clock.advance(120)
        self.svc.watch_tick(CODE)
        self.clock.advance(WARN_SECONDS)
        out = self.svc.watch_tick(CODE)
        self.assertIsNotNone(out)
        table = self.svc.load(CODE).table
        self.assertTrue(table.seats[self.seat]["autoplay"])
        self.assertIsNone(table.warning)
        self.assertIsNone(self.svc.view(CODE, 10)["table"]["takeoverWarning"])

    def test_stay_cancels_countdown_and_restarts_the_clock(self):
        self.clock.advance(120)
        self.svc.watch_tick(CODE)
        self.svc.stay(CODE, self.member)
        self.assertIsNone(self.svc.load(CODE).table.warning)
        self.clock.advance(WARN_SECONDS + 60)                      # alte Frist waere laengst abgelaufen
        self.assertIsNone(self.svc.watch_tick(CODE))
        self.assertFalse(self.svc.load(CODE).table.seats[self.seat].get("autoplay"))
        self.clock.advance(60)                                     # 120 s seit "Weiterspielen"
        self.assertIsNotNone(self.svc.watch_tick(CODE))

    def test_playing_a_card_cancels_countdown(self):
        self.clock.advance(120)
        self.svc.watch_tick(CODE)
        view = self.svc.view(CODE, self.member)["game"]
        acts = {a["type"]: a for a in view["legalActions"]}
        payload = ({"type": "declare", "reservation": False} if "declare" in acts
                   else {"type": "play_card", "cardId": acts["play_card"]["cards"][0]} if "play_card" in acts
                   else None)
        if payload is None:
            self.skipTest("erste Handlung ist keine einfache Aktion")
        self.svc.act(CODE, self.member, payload)
        self.assertIsNone(self.svc.load(CODE).table.warning)

    def test_remember_means_never(self):
        self.svc.stay(CODE, self.member, remember=True)
        self.assertTrue(self.svc.view(CODE, self.member)["table"]["seats"][self.seat]["noTakeover"])
        self.assertIsNone(self.svc.waiting_on(CODE))
        self.clock.advance(10 * 3600)
        self.assertIsNone(self.svc.watch_tick(CODE))
        self.assertFalse(self.svc.load(CODE).table.seats[self.seat].get("autoplay"))
        self.svc.stay(CODE, self.member, remember=False)           # wieder zulassen
        self.assertIsNotNone(self.svc.waiting_on(CODE))

    def test_stay_without_remember_keeps_the_choice(self):
        self.svc.stay(CODE, self.member, remember=True)
        self.svc.stay(CODE, self.member)
        self.assertTrue(self.svc.load(CODE).table.seats[self.seat]["noTakeover"])

    def test_stay_validates_input_and_membership(self):
        with self.assertRaises(RuleViolation):
            self.svc.stay(CODE, self.member, remember="ja")
        from app.table import AccessDenied
        with self.assertRaises(AccessDenied):
            self.svc.stay(CODE, 999)

    def test_host_can_switch_it_off_and_on_during_the_game(self):
        self.svc.set_takeover(CODE, 0)
        self.assertEqual(self.svc.view(CODE, 10)["table"]["takeover"], 0)
        self.assertIsNone(self.svc.waiting_on(CODE))
        self.clock.advance(5 * 3600)
        self.assertIsNone(self.svc.watch_tick(CODE))
        self.svc.set_takeover(CODE, 60)
        self.assertIsNotNone(self.svc.waiting_on(CODE))
        self.clock.advance(60)
        self.assertIsNotNone(self.svc.watch_tick(CODE))

    def test_invalid_takeover_values_are_rejected(self):
        for bad in (7, -1, True, "120"):
            with self.assertRaises(RuleViolation):
                self.svc.set_takeover(CODE, bad)
        with self.assertRaises(RuleViolation):
            self.svc.start(CODE, TWO, PROFILE, 45)

    def test_remember_survives_a_new_round(self):
        self.svc.stay(CODE, self.member, remember=True)
        self.svc.start(CODE, TWO, PROFILE, 120)
        seat = self.svc.load(CODE).table.seat_of(self.member)
        self.assertTrue(self.svc.load(CODE).table.seats[seat]["noTakeover"])

    def test_legacy_table_without_clock_gets_one(self):
        stored = self.svc.load(CODE)
        stored.table.touched = None
        self.svc.store.save(CODE, stored.table, stored.version, [])
        self.assertIsNotNone(self.svc.watch_tick(CODE))             # Uhr gestellt
        self.assertIsNotNone(self.svc.load(CODE).table.touched)
        self.assertIsNone(self.svc.load(CODE).table.warning)

    def test_state_roundtrip_keeps_takeover_fields(self):
        self.clock.advance(120)
        self.svc.watch_tick(CODE)
        table = self.svc.load(CODE).table
        again = TableState.from_dict(table.to_dict())
        self.assertEqual((again.takeover, again.touched, again.warning), (table.takeover, table.touched, table.warning))


class NoTakeoverAgainstBots(unittest.TestCase):
    def test_single_human_is_never_replaced(self):
        svc, clock = make(SOLO)
        play_bots(svc)
        self.assertIsNone(svc.waiting_on(CODE))
        clock.advance(13 * 3600)
        self.assertIsNone(svc.watch_tick(CODE))
        self.assertFalse(svc.load(CODE).table.seats[0].get("autoplay"))

    def test_runner_ends_its_loop_immediately_for_a_single_human(self):
        svc, clock = make(SOLO)
        sleeps = []
        runner = BotRunner(svc, on_step=lambda *a: None, sleep=lambda s: (sleeps.append(s), clock.advance(s)),
                           spawn=lambda fn, *a: fn(*a))
        runner.kick(CODE)
        clock.advance(6 * 3600)
        n = len(sleeps)
        runner.kick(CODE)                                           # nichts zu ueberwachen: keine Wartetakte
        self.assertEqual(len(sleeps), n)
        self.assertFalse(svc.load(CODE).table.seats[0].get("autoplay"))

    def test_human_left_alone_by_an_away_partner_is_not_replaced_either(self):
        svc, clock = make(TWO)
        svc.set_away(CODE, 11, True)                                # der zweite Mensch ist weg -> nur einer da
        play_bots(svc)
        self.assertIsNone(svc.waiting_on(CODE))


class RunnerIntegration(unittest.TestCase):
    def test_idle_human_gets_countdown_then_a_bot(self):
        svc, clock = make(TWO, takeover=60)
        pushed = []
        runner = BotRunner(svc, on_step=lambda code, o: pushed.append(svc.view(CODE, 10)["table"]["takeoverWarning"]),
                           sleep=lambda s: clock.advance(s), spawn=lambda fn, *a: fn(*a))
        runner.kick(CODE)
        table = svc.load(CODE).table
        away = [i for i, s in enumerate(table.seats) if s.get("autoplay")]
        self.assertEqual(len(away), 1)                              # genau einer wurde ersetzt
        self.assertTrue(table.seats[away[0]]["memberId"] in (10, 11))
        self.assertTrue(any(w for w in pushed))                     # der Countdown wurde vorher veroeffentlicht
        self.assertEqual(table.humans_present, 1)


class Housekeeping(unittest.TestCase):
    NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)

    def test_idle_after_twelve_hours(self):
        old = self.NOW - timedelta(hours=12, minutes=1)
        recent = self.NOW - timedelta(hours=3)
        self.assertTrue(is_idle([old, old], self.NOW))
        self.assertFalse(is_idle([old, recent], self.NOW))
        self.assertFalse(is_idle([self.NOW - timedelta(hours=11, minutes=59)], self.NOW))

    def test_naive_sqlite_times_are_treated_as_utc_and_none_is_ignored(self):
        naive_old = (self.NOW - timedelta(hours=20)).replace(tzinfo=None)
        self.assertTrue(is_idle([naive_old, None], self.NOW))
        self.assertIsNone(last_activity([None]))
        self.assertFalse(is_idle([], self.NOW))


if __name__ == "__main__":
    unittest.main()
