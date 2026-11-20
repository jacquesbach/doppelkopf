"""Betreiber-Werkzeuge: Einstellungen/Banner, Live-Uebersicht, Auswertungen, Fehler-Log, Systemstatus, Online-Status."""
import logging
import sys
import unittest
from datetime import datetime, timezone

from flask import Flask

from ..rules import loader  # noqa: F401
from app.community.admin_auth import AdminAuth
from app.community.stats import MemoryStats
from app.ops import errors as errlog
from app.ops import settings as site
from app.ops.api import OpsDeps, create_ops_blueprint
from app.ops.insights import berlin, berlin_offset_hours, summarize_insights
from app.ops.live import NoticeError, clean_notice, live_overview
from app.presence import PresenceRegistry, valid_code, valid_table
from app.table.service import REVEAL, DECLARE, TableService
from app.table import MemoryStore


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc).timestamp()


class SettingsTests(unittest.TestCase):
    def test_defaults_and_normalize(self):
        d = site.normalize(None)
        self.assertEqual(d["colors"], site.DEFAULT_COLORS)
        self.assertFalse(d["banner"]["enabled"])
        self.assertTrue(d["friendsEnabled"])
        self.assertEqual(d["tableTheme"], "light")

    def test_normalize_ignores_garbage(self):
        d = site.normalize({"colors": {"yellow": "red", "coral": "#ABCDEF", "x": "#000000"},
                            "banner": {"enabled": True, "text": "  ", "tone": "boom"}, "tableTheme": "neon"})
        self.assertEqual(d["colors"]["yellow"], site.DEFAULT_COLORS["yellow"])
        self.assertEqual(d["colors"]["coral"], "#abcdef")
        self.assertNotIn("x", d["colors"])
        self.assertFalse(d["banner"]["enabled"])           # ohne Text kein Banner
        self.assertEqual(d["banner"]["tone"], "info")
        self.assertEqual(d["tableTheme"], "light")

    def test_validate_rejects(self):
        for bad in ({"colors": {"yellow": "yellow"}}, {"colors": {"pink": "#ffffff"}}, {"colors": []},
                    {"banner": {"enabled": True, "text": ""}}, {"banner": {"text": "x" * 281}},
                    {"banner": {"tone": "loud"}}, {"tableTheme": "x"}, "text"):
            with self.assertRaises(site.SettingsError, msg=str(bad)):
                site.validate_update(bad)

    def test_validate_accepts_and_cleans_text(self):
        d = site.validate_update({"banner": {"enabled": True, "text": "Wartung\n um 22 Uhr\t<b>!</b>", "tone": "warn"},
                                  "colors": {"yellow": "#FFAA00"}})
        self.assertEqual(d["banner"]["text"], "Wartung um 22 Uhr <b>!</b>")   # Text bleibt Text (kein HTML-Umbau)
        self.assertEqual(d["colors"]["yellow"], "#ffaa00")

    def test_memory_store_roundtrip_and_reset(self):
        m = site.MemorySettings()
        m.put({"tableTheme": "dark"})
        self.assertEqual(m.get()["tableTheme"], "dark")
        self.assertEqual(m.reset()["tableTheme"], "light")

    def test_loads_tolerates_broken_json(self):
        self.assertEqual(site.loads("{kaputt"), site.normalize({}))


class ErrorLogTests(unittest.TestCase):
    def raise_it(self):
        try:
            raise ValueError("Boom 1")
        except ValueError:
            return errlog.describe(sys.exc_info(), where="/api/x", source="http")

    def test_same_error_is_counted(self):
        log = errlog.MemoryErrors(clock=lambda: 100)
        log.record(self.raise_it())
        log.record(self.raise_it())
        rows = log.list()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["count"], 2)
        self.assertIn("ValueError", rows[0]["trace"])
        self.assertNotIn("sig", rows[0])

    def test_limit_delete_clear(self):
        t = [0]
        log = errlog.MemoryErrors(clock=lambda: t.__setitem__(0, t[0] + 1) or t[0])
        for i in range(errlog.MAX_ENTRIES + 20):
            log.record({"source": "log", "where": "w", "kind": "E", "message": f"m{i}", "trace": "", "sig": f"s{i}"})
        self.assertEqual(len(log.list(1000)), errlog.MAX_ENTRIES)
        first = log.list(1)[0]["id"]
        self.assertTrue(log.delete(first))
        self.assertFalse(log.delete(first))
        self.assertGreater(log.clear(), 0)
        self.assertEqual(log.list(), [])

    def test_count_since(self):
        t = [1000]
        log = errlog.MemoryErrors(clock=lambda: t[0])
        log.record(self.raise_it())
        t[0] = 5000
        log.record(self.raise_it())
        self.assertEqual(log.count_since(4000), 2)
        self.assertEqual(log.count_since(6000), 0)

    def test_log_handler_collects_errors_with_path(self):
        log = errlog.MemoryErrors()
        handler = errlog.LogHandler(log)
        lg = logging.getLogger("doppelkopf.test_handler")
        lg.propagate = False
        lg.addHandler(handler)
        try:
            try:
                raise RuntimeError("kaputt")
            except RuntimeError:
                lg.error("Fehler", exc_info=True, extra={"path": "/api/rooms"})
            lg.warning("nur Warnung")                      # unterhalb von ERROR: nicht erfasst
            lg.error("ohne Ausnahme")
        finally:
            lg.removeHandler(handler)
        rows = log.list()
        self.assertEqual({r["where"] for r in rows}, {"/api/rooms", "doppelkopf.test_handler"})
        self.assertEqual(len(rows), 2)
        self.assertEqual(next(r for r in rows if r["where"] == "/api/rooms")["source"], "http")


class InsightsTests(unittest.TestCase):
    def test_berlin_summer_time(self):
        self.assertEqual(berlin_offset_hours(utc(2026, 1, 15, 12)), 1)
        self.assertEqual(berlin_offset_hours(utc(2026, 7, 15, 12)), 2)
        self.assertEqual(berlin_offset_hours(utc(2026, 3, 29, 0, 59)), 1)      # Umstellung: letzter Maerz-Sonntag 01:00 UTC
        self.assertEqual(berlin_offset_hours(utc(2026, 3, 29, 1, 0)), 2)
        self.assertEqual(berlin_offset_hours(utc(2026, 10, 25, 0, 59)), 2)
        self.assertEqual(berlin_offset_hours(utc(2026, 10, 25, 1, 0)), 1)
        self.assertEqual(berlin(utc(2026, 7, 1, 22, 30)).hour, 0)             # 22:30 UTC = 00:30 MESZ am Folgetag
        self.assertEqual(berlin(utc(2026, 7, 1, 22, 30)).day, 2)

    def test_summary(self):
        now = utc(2026, 11, 20, 12)
        ev = [{"at": utc(2026, 11, 20, 8, 5), "duration": 600, "humans": 1},      # 09:05 MEZ
              {"at": utc(2026, 11, 20, 8, 40), "duration": 1200, "humans": 3},
              {"at": utc(2026, 11, 19, 19, 0), "duration": 900, "humans": 2},     # 20:00 MEZ, Donnerstag
              {"at": utc(2026, 11, 19, 19, 30), "duration": 4 * 3600, "humans": 2},   # Pause: nicht in der Dauer
              {"at": utc(2026, 8, 1, 10), "duration": 600, "humans": 2}]          # ausserhalb von 30 Tagen
        logs = [{"startedAt": 1, "lastActivityAt": now - 7200, "games": 0, "rounds": 1, "roundsFinished": 0},
                {"startedAt": 1, "lastActivityAt": now - 7200, "games": 5, "rounds": 2, "roundsFinished": 1},
                {"startedAt": 1, "lastActivityAt": now - 60, "games": 0, "rounds": 1, "roundsFinished": 0},   # laeuft noch
                {"startedAt": None, "lastActivityAt": now - 9000, "games": 0, "rounds": 0, "roundsFinished": 0}]
        s = summarize_insights(ev, logs, now)
        self.assertEqual(s["gamesInPeriod"], 4)
        self.assertEqual(s["gamesTotal"], 5)
        self.assertEqual(len(s["perDay"]), 30)
        self.assertEqual(s["perDay"][-1], {"date": "2026-11-20", "games": 2})
        self.assertEqual(s["perDay"][-2]["games"], 2)
        self.assertEqual(s["byHour"][9], 2)
        self.assertEqual(s["peak"]["hour"], 9)
        self.assertEqual(sum(w["games"] for w in s["byWeekday"]), 4)
        self.assertEqual(s["duration"]["count"], 3)                  # 4-Stunden-Spiel zaehlt nicht
        self.assertEqual(s["duration"]["median"], 15.0)
        self.assertEqual(s["durationWithHumans"]["count"], 2)
        self.assertEqual(s["abort"]["tablesEnded"], 2)               # nur seit > 1 Std. ruhende, gestartete Tische
        self.assertEqual(s["abort"]["neverFinishedAGame"], 1)
        self.assertEqual(s["abort"]["neverFinishedRate"], 0.5)
        self.assertEqual(s["abort"]["rounds"], 3)
        self.assertEqual(s["abort"]["roundsAborted"], 2)

    def test_empty(self):
        s = summarize_insights([], [], utc(2026, 11, 20))
        self.assertIsNone(s["peak"]["hour"])
        self.assertIsNone(s["abort"]["neverFinishedRate"])
        self.assertEqual(s["duration"]["count"], 0)

    def test_stats_record_events_and_rounds(self):
        st = MemoryStats(clock=lambda: 10)
        st.table_created("AAA111", now=1)
        st.round_started("AAA111", 2, 2, now=2)
        st.game_finished("AAA111", now=500, duration=300)
        st.round_finished("AAA111", now=900)
        self.assertEqual(st.events(), [{"at": 500, "duration": 300, "humans": 2}])
        self.assertEqual(st.logs()[0]["roundsFinished"], 1)


def row(code, status="playing", idle=10, now=1000.0, players=None, **extra):
    players = players if players is not None else [{"name": "Anna", "isBot": False, "isHost": True, "connected": True},
                                                  {"name": "Bot 2", "isBot": True, "isHost": False, "connected": True}]
    return {"code": code, "status": status, "isPublic": False, "hasPassword": False, "isLab": False, "createdAt": now - 500,
            "startedAt": now - 400, "lastActivityAt": now - idle, "players": players, "spectators": 0,
            "game": {"number": 1, "phase": "playing", "tricks": 2, "normalGamesPlayed": 0}, **extra}


class LiveTests(unittest.TestCase):
    def test_overview(self):
        now = 1000.0
        raw = [row("RUN111", now=now), row("IDLE11", idle=900, now=now),
               row("WAIT11", status="waiting", now=now,
                   players=[{"name": "Ben", "isBot": False, "isHost": True, "connected": False}]),
               row("TEST11", isLab=True, now=now)]
        o = live_overview(raw, now)
        self.assertEqual(o["count"], 4)
        self.assertEqual((o["running"], o["waiting"], o["idle"]), (1, 1, 1))     # Test-Tische zaehlen nicht mit
        self.assertEqual(o["humansOnline"], 2)                                    # Anna (RUN) + Anna (IDLE); Ben getrennt
        self.assertEqual(o["botOnlyTables"], 1)
        self.assertEqual(o["tables"][0]["code"] in ("RUN111", "TEST11"), True)
        run = next(t for t in o["tables"] if t["code"] == "RUN111")
        self.assertEqual((run["humans"], run["bots"], run["connectedHumans"], run["state"]), (1, 1, 1, "running"))

    def test_notice_validation(self):
        self.assertEqual(clean_notice("  Wartung \n in 5 Min "), "Wartung in 5 Min")
        with self.assertRaises(NoticeError):
            clean_notice("   ")
        with self.assertRaises(NoticeError):
            clean_notice("x" * 301)
        self.assertEqual(clean_notice("", required=False), "")


class FakeLive:
    def __init__(self):
        self.rooms = {"ABC234": row("ABC234")}
        self.spectators = []

    def tables(self):
        return list(self.rooms.values())

    def close(self, code):
        return self.rooms.pop(code, None) is not None

    def add_spectator(self, code):
        if code not in self.rooms:
            return None
        self.spectators.append(code)
        return {"memberId": 9, "token": "tok"}


class OpsHttpTests(unittest.TestCase):
    def setUp(self):
        self.admin = AdminAuth("geheimes-passwort", "secret")
        self.live = FakeLive()
        self.notes = []
        self.errors = errlog.MemoryErrors(clock=lambda: utc(2026, 11, 20, 9))
        self.settings = site.MemorySettings()
        self.stats = MemoryStats(clock=lambda: utc(2026, 11, 20, 9))
        deps = OpsDeps(admin=self.admin, settings=self.settings, live=self.live, errors=self.errors, stats=self.stats,
                       system=lambda: {"db": {"kind": "sqlite", "bytes": 4096, "rows": {}}, "runtime": {"botLoops": 1}},
                       notify=lambda code, event, payload: self.notes.append((code, event, payload)),
                       clock=lambda: utc(2026, 11, 20, 12), started_at=utc(2026, 11, 20, 11),
                       environ={"APP_VERSION": "abc1234", "DEPLOYED_AT": "2026-11-20T10:00:00Z"})
        app = Flask(__name__)
        app.register_blueprint(create_ops_blueprint(deps), url_prefix="/api")
        self.client = app.test_client()
        self.h = {"Authorization": f"Bearer {self.admin.login('geheimes-passwort', 'ip')}"}

    def test_public_settings_need_no_login_admin_routes_do(self):
        self.assertEqual(self.client.get("/api/site-settings").status_code, 200)
        for method, path in (("get", "/api/admin/site-settings"), ("get", "/api/admin/live"), ("get", "/api/admin/system"),
                             ("get", "/api/admin/insights"), ("get", "/api/admin/errors"),
                             ("post", "/api/admin/live/ABC234/close"), ("post", "/api/admin/live/ABC234/spectate"),
                             ("put", "/api/admin/site-settings"), ("delete", "/api/admin/errors")):
            self.assertEqual(getattr(self.client, method)(path).status_code, 401, path)

    def test_save_settings_and_public_view(self):
        r = self.client.put("/api/admin/site-settings", headers=self.h,
                            json={"banner": {"enabled": True, "text": "Wartung", "tone": "warn"}, "colors": {"yellow": "#ff0000"}})
        self.assertEqual(r.status_code, 200)
        pub = self.client.get("/api/site-settings").get_json()
        self.assertTrue(pub["banner"]["enabled"])
        self.assertEqual(pub["colors"]["yellow"], "#ff0000")
        bad = self.client.put("/api/admin/site-settings", headers=self.h, json={"colors": {"yellow": "rot"}})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.client.get("/api/site-settings").get_json()["colors"]["yellow"], "#ff0000")   # unveraendert
        self.assertEqual(self.client.post("/api/admin/site-settings/reset", headers=self.h).get_json()["colors"]["yellow"],
                         site.DEFAULT_COLORS["yellow"])

    def test_live_and_message(self):
        data = self.client.get("/api/admin/live", headers=self.h).get_json()
        self.assertEqual(data["count"], 1)
        r = self.client.post("/api/admin/live/abc234/message", headers=self.h, json={"message": " Hallo  zusammen "})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.notes[-1], ("ABC234", "room:notice", {"message": "Hallo zusammen", "closed": False}))
        self.assertEqual(self.client.post("/api/admin/live/ABC234/message", headers=self.h, json={"message": ""}).status_code, 400)
        self.assertEqual(self.client.post("/api/admin/live/ZZZ999/message", headers=self.h, json={"message": "x"}).status_code, 404)

    def test_close_notifies_first_then_removes(self):
        r = self.client.post("/api/admin/live/ABC234/close", headers=self.h, json={"message": "Server-Neustart"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.notes[-1], ("ABC234", "room:notice", {"message": "Server-Neustart", "closed": True}))
        self.assertNotIn("ABC234", self.live.rooms)
        self.assertEqual(self.client.post("/api/admin/live/ABC234/close", headers=self.h, json={}).status_code, 404)

    def test_close_without_message_uses_default(self):
        self.client.post("/api/admin/live/ABC234/close", headers=self.h, json={})
        self.assertIn("beendet", self.notes[-1][2]["message"])

    def test_spectate_returns_session_and_refreshes_room(self):
        r = self.client.post("/api/admin/live/ABC234/spectate", headers=self.h)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json(), {"code": "ABC234", "memberId": 9, "token": "tok"})
        self.assertEqual(self.notes[-1][1], "room:refresh")
        self.assertEqual(self.client.post("/api/admin/live/NOPE22/spectate", headers=self.h).status_code, 404)

    def test_system_and_errors_and_insights(self):
        try:
            raise KeyError("x")
        except KeyError:
            self.errors.record(errlog.describe(sys.exc_info(), where="/api/y"))
        s = self.client.get("/api/admin/system", headers=self.h).get_json()
        self.assertEqual(s["version"], "abc1234")
        self.assertEqual(s["deployedAt"], "2026-11-20T10:00:00Z")
        self.assertEqual(s["uptimeSeconds"], 3600)
        self.assertEqual(s["db"]["bytes"], 4096)
        self.assertEqual(s["runtime"]["botLoops"], 1)
        self.assertEqual(s["runtime"]["errors24h"], 1)
        errs = self.client.get("/api/admin/errors", headers=self.h).get_json()["errors"]
        self.assertEqual(len(errs), 1)
        self.assertEqual(self.client.delete(f"/api/admin/errors/{errs[0]['id']}", headers=self.h).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/admin/errors/{errs[0]['id']}", headers=self.h).status_code, 404)
        self.assertEqual(self.client.delete("/api/admin/errors", headers=self.h).get_json()["deleted"], 0)
        ins = self.client.get("/api/admin/insights", headers=self.h).get_json()
        self.assertEqual(len(ins["perDay"]), 30)

    def test_version_unknown_when_not_set(self):
        from app.ops.system import build_info
        self.assertEqual(build_info({}), {"version": "unbekannt", "deployedAt": None})
        self.assertEqual(build_info({"APP_VERSION": "a\nb\x00c"})["version"], "abc")


class PresenceTests(unittest.TestCase):
    CODE_A, CODE_B = "ABCDEFGHJK", "MNPQRSTUVW"

    def test_code_validation(self):
        self.assertEqual(valid_code("abcde-fghjk"), self.CODE_A)
        self.assertEqual(valid_code(" ABCDE FGHJK "), self.CODE_A)
        for bad in ("ABCDEFGHJ", "ABCDEFGHJKL", "ABCDEFGHJ0", "ABCDEFGHJI", None, 5, "<script>"):
            self.assertIsNone(valid_code(bad))
        self.assertEqual(valid_table("abc234"), "ABC234")
        self.assertIsNone(valid_table("ABC23"))

    def test_hello_requires_code_and_name(self):
        r = PresenceRegistry()
        with self.assertRaises(ValueError):
            r.hello("s1", "kurz", "Anna")
        with self.assertRaises(ValueError):
            r.hello("s1", self.CODE_A, "   ")
        self.assertEqual(r.hello("s1", self.CODE_A, "Anna\n"), (self.CODE_A, True))
        self.assertEqual(r.name_of(self.CODE_A), "Anna")

    def test_two_tabs_one_code(self):
        r = PresenceRegistry()
        self.assertEqual(r.hello("s1", self.CODE_A, "Anna"), (self.CODE_A, True))
        self.assertEqual(r.hello("s2", self.CODE_A, "Anna"), (self.CODE_A, False))     # schon online
        self.assertEqual(r.goodbye("s1"), (self.CODE_A, False))                        # zweiter Tab haelt ihn online
        self.assertTrue(r.is_online(self.CODE_A))
        self.assertEqual(r.goodbye("s2"), (self.CODE_A, True))
        self.assertFalse(r.is_online(self.CODE_A))
        self.assertIsNone(r.name_of(self.CODE_A))                                      # nichts bleibt gespeichert

    def test_watch_shows_only_known_online_codes_and_needs_opt_in(self):
        r = PresenceRegistry()
        with self.assertRaises(ValueError):
            r.watch("anon", [self.CODE_A])                      # wer selbst nicht sichtbar ist, sieht auch nichts
        r.hello("a", self.CODE_A, "Anna")
        r.hello("b", self.CODE_B, "Ben")
        old, new = r.watch("a", [self.CODE_B, "quatsch", "ZZZZZZZZZZ"])
        self.assertEqual((old, new), (set(), {self.CODE_B, "ZZZZZZZZZZ"}))
        self.assertEqual(r.status(new), {self.CODE_B: {"online": True, "name": "Ben"}})   # Unbekannte: einfach nicht online
        self.assertEqual(r.watch("a", [])[0], {self.CODE_B, "ZZZZZZZZZZ"})

    def test_watch_limit(self):
        r = PresenceRegistry()
        r.hello("a", self.CODE_A, "Anna")
        many = [f"{chr(65 + i // 26)}{chr(65 + i % 26)}ABCDEFGH".replace("I", "J").replace("O", "P") for i in range(300)]
        _, new = r.watch("a", many)
        self.assertLessEqual(len(new), 100)

    def test_invite_rate_limit(self):
        t = [0.0]
        r = PresenceRegistry(clock=lambda: t[0])
        r.hello("a", self.CODE_A, "Anna")
        self.assertEqual([r.allow_invite("a") for _ in range(7)], [True] * 6 + [False])
        t[0] = 61
        self.assertTrue(r.allow_invite("a"))


class ReservationPacingTests(unittest.TestCase):
    def test_declare_and_reveal_delays_exist(self):
        self.assertGreaterEqual(DECLARE, 1.5)
        self.assertGreaterEqual(REVEAL, 2.5)

    def test_first_card_waits_for_reveal_after_query(self):
        from app.rules import RuleProfile
        from app.table.state import new_table
        import random
        seats = [{"memberId": i + 1, "name": f"S{i}", "isBot": True} for i in range(4)]
        profile = RuleProfile.default() if hasattr(RuleProfile, "default") else None
        if profile is None:
            from app.rules import profile_from_settings, normalize_settings
            profile = profile_from_settings(normalize_settings({}))
        store = MemoryStore()
        svc = TableService(store, rng=random.Random(3), paced=True)
        svc.start("R1", seats, profile)
        delays = []
        for _ in range(60):
            d = svc.pending_delay("R1")
            if d is None:
                break
            delays.append(d)
            svc.bot_step("R1")
            game = svc.load("R1").table.game
            if game.phase.value == "playing" and not game.tricks and not game.current_trick:
                break
        delays.append(svc.pending_delay("R1"))               # erste Botkarte nach der Abfrage
        self.assertIn(DECLARE, delays)                       # Vorbehaltsabfrage ist langsamer
        self.assertIn(REVEAL, delays)                        # und nach der letzten Antwort gibt es die Pause
        self.assertLess(delays.index(DECLARE), delays.index(REVEAL))


if __name__ == "__main__":
    unittest.main()
