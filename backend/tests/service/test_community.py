"""Vorschlaege, Daumen, Captcha, Sprueche, Betreiber-Backend, Statistik, Tischuebersicht (ohne Datenbank)."""
import random
import unittest

from flask import Flask

from app.community import captcha as cap
from app.community.admin_auth import AdminAuth, TooManyAttempts
from app.community.api import CommunityDeps, create_community_blueprint
from app.community.phrases import DEFAULT_PHRASES, MemoryPhrases, PhraseService
from app.community.ratelimit import RateLimiter
from app.community.stats import MemoryStats, summarize
from app.community.suggestions import MemorySuggestions, SuggestionService, ranked
from app.community.tables import MemoryTables, overview
from app.community.text import ValidationError, clean

SECRET = "test-secret"


class Clock:
    def __init__(self, now=1_800_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


class RateLimiterTests(unittest.TestCase):
    def test_window_slides(self):
        t = [0.0]
        rl = RateLimiter(clock=lambda: t[0])
        self.assertTrue(all(rl.allow("k", 3, 10) for _ in range(3)))
        self.assertFalse(rl.allow("k", 3, 10))
        self.assertTrue(rl.allow("other", 3, 10))
        t[0] = 10.0
        self.assertTrue(rl.allow("k", 3, 10))


class TextTests(unittest.TestCase):
    def test_clean_normalizes_and_limits(self):
        self.assertEqual(clean("  Hallo \n  Welt\x00 ", "Titel", 1, 20), "Hallo Welt")
        self.assertEqual(clean("a\r\n\r\n\r\n\r\nb", "T", 1, 20, multiline=True), "a\n\nb")
        with self.assertRaises(ValidationError):
            clean("ab", "Titel", 4, 10)
        with self.assertRaises(ValidationError):
            clean("x" * 11, "Titel", 1, 10)
        with self.assertRaises(ValidationError):
            clean(5, "Titel", 1, 10)

    def test_links_rejected_unless_allowed(self):
        for bad in ("siehe https://x.example", "www.spam.de", "kauf auf pillen.com"):
            with self.assertRaises(ValidationError) as ctx:
                clean(bad, "Text", 1, 100)
            self.assertEqual(ctx.exception.code, "links_not_allowed")
        self.assertEqual(clean("www.spam.de", "Text", 1, 100, allow_links=True), "www.spam.de")


class CaptchaTests(unittest.TestCase):
    def make(self, seed=1):
        clock = Clock()
        guard = cap.CaptchaGuard(SECRET, clock=clock, rng=random.Random(seed))
        return guard, clock

    @staticmethod
    def answer_of(guard, seed):
        """Gleicher Zufallsstrom -> gleiche Antwort (die ersten fuenf Ziehungen aus dem ALPHABET)."""
        rng = random.Random(seed)
        return "".join(rng.choice(cap.ALPHABET) for _ in range(cap.LENGTH))

    def test_correct_answer_passes_once_and_is_case_insensitive(self):
        guard, _ = self.make(3)
        ch = guard.challenge()
        ans = self.answer_of(guard, 3)
        self.assertIn("<svg", ch["svg"])
        self.assertEqual(guard.verify(ch["token"], ans.lower() + " "), "ok")
        self.assertEqual(guard.verify(ch["token"], ans), "used")          # Token ist verbraucht

    def test_wrong_answer_consumes_token(self):
        guard, _ = self.make(4)
        ch = guard.challenge()
        ans = self.answer_of(guard, 4)
        self.assertEqual(guard.verify(ch["token"], "AAAAA" if ans != "AAAAA" else "BBBBB"), "wrong")
        self.assertEqual(guard.verify(ch["token"], ans), "used")

    def test_expiry_and_tampering(self):
        guard, clock = self.make(5)
        ch = guard.challenge()
        ans = self.answer_of(guard, 5)
        clock.now += cap.TTL + 1
        self.assertEqual(guard.verify(ch["token"], ans), "expired")
        fresh = guard.challenge()
        parts = fresh["token"].split(".")
        parts[2] = "0" * 20
        self.assertEqual(guard.verify(".".join(parts), "X"), "malformed")      # Signatur passt nicht mehr
        self.assertEqual(guard.verify("kaputt", "X"), "malformed")
        self.assertEqual(guard.verify(None, None), "malformed")

    def test_token_from_other_secret_is_rejected(self):
        other = cap.CaptchaGuard("anderes-secret", clock=Clock(), rng=random.Random(6))
        ch = other.challenge()
        guard, _ = self.make(6)
        self.assertEqual(guard.verify(ch["token"], "ABCDE"), "malformed")

    def test_token_does_not_reveal_the_answer(self):
        guard, _ = self.make(7)
        ch = guard.challenge()
        self.assertNotIn(self.answer_of(guard, 7), ch["token"])


class SuggestionTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.svc = SuggestionService(MemorySuggestions(), clock=self.clock)

    def test_submit_validates_and_rejects_duplicates(self):
        item = self.svc.submit("  Neue   Statistik ", "Zeige mir meine Siege pro Woche an.")
        self.assertEqual(item["title"], "Neue Statistik")
        with self.assertRaises(ValidationError) as ctx:
            self.svc.submit("neue statistik", "Etwas ganz anderes aber gleicher Titel.")
        self.assertEqual(ctx.exception.code, "duplicate")
        with self.assertRaises(ValidationError):
            self.svc.submit("Ok", "zu kurz")
        with self.assertRaises(ValidationError):
            self.svc.submit("Guter Titel", "x" * 501)

    def test_one_vote_per_voter_toggles_and_ranking(self):
        a = self.svc.submit("Vorschlag A", "Beschreibung zu A, lang genug.")
        self.clock.now += 10
        b = self.svc.submit("Vorschlag B", "Beschreibung zu B, lang genug.")
        self.assertEqual(self.svc.vote(a["id"], "u1"), {"votes": 1, "voted": True})
        self.assertEqual(self.svc.vote(a["id"], "u1"), {"votes": 0, "voted": False})     # zweiter Klick = zurueck
        self.svc.vote(b["id"], "u1")
        self.svc.vote(b["id"], "u2")
        self.svc.vote(a["id"], "u1")
        order = [s["title"] for s in self.svc.public_list("u1")]
        self.assertEqual(order, ["Vorschlag B", "Vorschlag A"])                        # beliebteste zuerst
        mine = {s["title"]: s["voted"] for s in self.svc.public_list("u1")}
        self.assertEqual(mine, {"Vorschlag B": True, "Vorschlag A": True})
        self.assertFalse(any(s["voted"] for s in self.svc.public_list(None)))
        self.assertIsNone(self.svc.vote(999, "u1"))

    def test_ties_prefer_older(self):
        items = [{"id": 2, "votes": 1, "createdAt": 5}, {"id": 1, "votes": 1, "createdAt": 9}, {"id": 3, "votes": 2, "createdAt": 99}]
        self.assertEqual([i["id"] for i in ranked(items)], [3, 2, 1])

    def test_moderation_hides_from_public_and_blocks_votes(self):
        a = self.svc.submit("Vorschlag A", "Beschreibung zu A, lang genug.")
        self.assertTrue(self.svc.moderate(a["id"], "hidden"))
        self.assertEqual(self.svc.public_list(None), [])
        self.assertEqual(len(self.svc.admin_list()), 1)
        self.assertIsNone(self.svc.vote(a["id"], "u1"))
        self.assertTrue(self.svc.moderate(a["id"], "visible"))
        with self.assertRaises(ValidationError):
            self.svc.moderate(a["id"], "geloescht")
        self.assertTrue(self.svc.edit(a["id"], "Neuer Titel", "Neue Beschreibung, lang genug."))
        self.assertTrue(self.svc.delete(a["id"]))
        self.assertFalse(self.svc.delete(a["id"]))


class PhraseTests(unittest.TestCase):
    def setUp(self):
        self.svc = PhraseService(MemoryPhrases(DEFAULT_PHRASES))

    def test_defaults_match_the_supplied_list(self):
        self.assertEqual(len(DEFAULT_PHRASES), 8)
        self.assertEqual([p["text"] for p in self.svc.list()][:2], ["Den mach ich fett.", "... und den hab ich auch noch!"])

    def test_add_edit_delete_validate(self):
        p = self.svc.add("  Gut gespielt!  ")
        self.assertEqual(p["text"], "Gut gespielt!")
        with self.assertRaises(ValidationError):
            self.svc.add("gut GESPIELT!")
        with self.assertRaises(ValidationError):
            self.svc.add("x" * 201)
        with self.assertRaises(ValidationError):
            self.svc.add("   ")
        self.assertTrue(self.svc.update(p["id"], "Sehr gut gespielt!"))
        self.assertTrue(self.svc.update(p["id"], "Sehr gut gespielt!"))        # unveraendert speichern ist erlaubt
        self.assertFalse(self.svc.update(999, "x"))
        self.assertTrue(self.svc.delete(p["id"]))
        self.assertFalse(self.svc.delete(p["id"]))

    def test_move(self):
        ids = [p["id"] for p in self.svc.list()]
        self.svc.move(ids[1], "up")
        self.assertEqual([p["id"] for p in self.svc.list()][:2], [ids[1], ids[0]])
        self.svc.move(ids[1], "up")                                             # schon oben: nichts passiert
        self.assertEqual(self.svc.list()[0]["id"], ids[1])
        self.svc.move(ids[-1], "down")
        self.assertEqual(self.svc.list()[-1]["id"], ids[-1])
        with self.assertRaises(ValidationError):
            self.svc.move(ids[0], "seitwaerts")
        self.assertFalse(self.svc.move(12345, "up"))


class AdminAuthTests(unittest.TestCase):
    def test_login_and_token(self):
        clock = Clock()
        auth = AdminAuth("geheim-geheim", SECRET, ttl=60, clock=clock)
        self.assertTrue(auth.enabled)
        self.assertIsNone(auth.login("falsch", "1.1.1.1"))
        token = auth.login("geheim-geheim", "1.1.1.1")
        self.assertTrue(auth.verify(token))
        self.assertFalse(auth.verify(token + "x"))
        self.assertFalse(auth.verify("123.abc"))
        self.assertFalse(auth.verify(None))
        clock.now += 61
        self.assertFalse(auth.verify(token))                                    # abgelaufen
        self.assertFalse(AdminAuth("geheim-geheim", "anderes", clock=Clock()).verify(token))

    def test_disabled_without_password(self):
        auth = AdminAuth("", SECRET)
        self.assertFalse(auth.enabled)
        self.assertIsNone(auth.login("", "ip"))
        self.assertFalse(auth.verify("1.2"))

    def test_brute_force_is_limited(self):
        auth = AdminAuth("geheim-geheim", SECRET, clock=Clock(), limiter=RateLimiter(clock=lambda: 0.0))
        for _ in range(5):
            self.assertIsNone(auth.login("nein", "9.9.9.9"))
        with self.assertRaises(TooManyAttempts):
            auth.login("geheim-geheim", "9.9.9.9")                              # auch das richtige Passwort wird jetzt gebremst
        self.assertIsNotNone(auth.login("geheim-geheim", "8.8.8.8"))            # andere Adresse unberuehrt


def log(code, created, started, last, humans, bots, games, rounds=1):
    return {"code": code, "createdAt": created, "startedAt": started, "lastActivityAt": last,
            "humans": humans, "bots": bots, "games": games, "rounds": rounds}


class StatsTests(unittest.TestCase):
    NOW = 1_800_000_000.0

    def test_recorder_tracks_lifecycle(self):
        st = MemoryStats(clock=lambda: 0.0)
        st.table_created("AAA111", now=100)
        st.activity("AAA111", now=150)                      # vor dem Start: ignoriert
        st.round_started("AAA111", 1, 3, now=200)
        st.game_finished("AAA111", now=500)
        st.game_finished("AAA111", now=900)
        st.round_started("AAA111", 1, 3, now=1000)          # zweite Runde: Startzeit bleibt
        st.activity("AAA111", now=1200)
        (entry,) = st.logs()
        self.assertEqual((entry["createdAt"], entry["startedAt"], entry["lastActivityAt"]), (100, 200, 1200))
        self.assertEqual((entry["games"], entry["rounds"], entry["humans"], entry["bots"]), (2, 2, 1, 3))
        st.round_started("UNBEKANNT", 2, 2, now=5)           # kein Log -> kein Fehler

    def test_summary_numbers(self):
        n = self.NOW
        logs = [
            log("A", n - 3600, n - 3500, n - 500, 1, 3, 10),         # allein gegen Bots, 50 min, 10 Spiele
            log("B", n - 7200, n - 7100, n - 4700, 1, 3, 30),        # 40 min, 30 Spiele
            log("C", n - 86400 * 3, n - 86400 * 3 + 60, n - 86400 * 3 + 6060, 4, 0, 5),   # vier Menschen, 100 min
            log("D", n - 100, None, n - 100, 0, 0, 0, 0),            # nie gestartet
        ]
        s = summarize(logs, n)
        self.assertEqual((s["tablesTotal"], s["tablesStarted"], s["tablesNeverStarted"]), (4, 3, 1))
        self.assertEqual(s["againstBotsOnly"]["tables"], 2)
        self.assertEqual(s["withHumans"]["tables"], 1)
        self.assertEqual(s["byHumans"], {"1": 2, "2": 0, "3": 0, "4": 1})
        self.assertEqual(s["againstBotsOnly"]["minutes"]["avg"], 45.0)
        self.assertEqual(s["withHumans"]["minutes"]["avg"], 100.0)
        self.assertEqual(s["minutes"]["median"], 50.0)
        self.assertEqual(s["games"]["max"], 30.0)
        self.assertEqual({b["label"]: b["tables"] for b in s["gamesBuckets"]}, {"keins": 0, "1–3": 0, "4–11": 2, "12–27": 0, "28+": 1})
        self.assertEqual((s["last24h"], s["last7d"], s["last30d"]), (3, 4, 4))
        self.assertEqual(s["gamesTotal"], 45)
        self.assertEqual(len(s["perDay"]), 14)
        self.assertEqual(sum(d["tables"] for d in s["perDay"]), 4)

    def test_empty_summary_is_safe(self):
        s = summarize([], self.NOW)
        self.assertEqual((s["tablesTotal"], s["minutes"]["avg"], s["games"]["median"]), (0, 0.0, 0.0))


class TablesTests(unittest.TestCase):
    def test_overview_sorts_active_first_and_describes_idle(self):
        n = 1_800_000_000.0
        base = {"status": "playing", "isPublic": False, "hasPassword": False, "spectators": 0, "game": None}
        rows = [
            {**base, "code": "IDLE01", "createdAt": n - 9000, "startedAt": n - 8000, "lastActivityAt": n - 4000, "humans": 2, "bots": 2, "connectedHumans": 0},
            {**base, "code": "LIVE01", "createdAt": n - 900, "startedAt": n - 800, "lastActivityAt": n - 10, "humans": 1, "bots": 3, "connectedHumans": 1},
            {**base, "code": "WAIT01", "status": "waiting", "createdAt": n - 50, "startedAt": None, "lastActivityAt": n - 50, "humans": 1, "bots": 0, "connectedHumans": 1},
        ]
        out = overview(rows, n)
        self.assertEqual([r["code"] for r in out["tables"]], ["LIVE01", "WAIT01", "IDLE01"])
        live, wait, idle = out["tables"]
        self.assertEqual((live["state"], idle["state"]), ("active", "idle"))
        self.assertEqual(idle["idleSeconds"], 4000)
        self.assertEqual(live["activeSince"], n - 800)
        self.assertEqual(wait["activeSince"], n - 50)                   # noch nicht gestartet: seit Anlegen
        self.assertTrue(live["againstBotsOnly"])
        self.assertFalse(wait["againstBotsOnly"])                       # Lobby zaehlt noch nicht
        self.assertEqual((out["count"], out["activeCount"], out["humansTotal"], out["connectedTotal"]), (3, 2, 4, 2))


class CommunityHttp(unittest.TestCase):
    PASSWORD = "betreiber-passwort"

    def setUp(self):
        self.clock = Clock()
        self.stats = MemoryStats(clock=self.clock)
        self.tables = MemoryTables()
        self.guard = cap.CaptchaGuard(SECRET, clock=self.clock, rng=random.Random(11))
        self.rng_answers = random.Random(11)             # gleicher Strom wie der Captcha-Erzeuger
        self.deps = CommunityDeps(
            suggestions=SuggestionService(MemorySuggestions(), clock=self.clock),
            phrases=PhraseService(MemoryPhrases(DEFAULT_PHRASES)),
            stats=self.stats, tables=self.tables,
            admin=AdminAuth(self.PASSWORD, SECRET, clock=self.clock),
            captcha=self.guard, secret=SECRET, clock=self.clock)
        app = Flask(__name__)
        app.register_blueprint(create_community_blueprint(self.deps), url_prefix="/api")
        self.client = app.test_client()
        self.cid = "browser-kennung-0001"

    # Captcha: erzeugt ueber den echten Endpunkt; die Antwort rekonstruieren wir aus dem Zufallsstrom
    def challenge(self):
        res = self.client.get("/api/captcha")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        answer = "".join(self.rng_answers.choice(cap.ALPHABET) for _ in range(cap.LENGTH))
        # den Rest des Zufallsstroms (Grafik) verbrauchen, damit der naechste Aufruf synchron bleibt
        cap._svg(answer, self.rng_answers)
        return data["token"], answer

    def submit(self, title="Neue Idee", desc="Das waere eine tolle Verbesserung.", **extra):
        token, answer = self.challenge()
        body = {"title": title, "description": desc, "captchaToken": token, "captchaAnswer": answer, **extra}
        return self.client.post("/api/suggestions", json=body, headers={"X-Client-Id": self.cid})

    def login(self):
        res = self.client.post("/api/admin/login", json={"password": self.PASSWORD})
        self.assertEqual(res.status_code, 200)
        return {"Authorization": "Bearer " + res.get_json()["token"]}

    # --- oeffentlich ---
    def test_submit_requires_correct_captcha(self):
        token, answer = self.challenge()
        bad = self.client.post("/api/suggestions", json={"title": "Neue Idee", "description": "Das waere eine tolle Verbesserung.",
                                                          "captchaToken": token, "captchaAnswer": "XXXXX"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.get_json()["code"], "captcha_wrong")
        again = self.client.post("/api/suggestions", json={"title": "Neue Idee", "description": "Das waere eine tolle Verbesserung.",
                                                            "captchaToken": token, "captchaAnswer": answer})
        self.assertEqual(again.get_json()["code"], "captcha_used")             # Token verbraucht
        self.assertEqual(self.client.get("/api/suggestions").get_json()["suggestions"], [])
        self.assertEqual(self.client.post("/api/suggestions", json={"title": "Neue Idee", "description": "Das waere eine tolle Verbesserung."}).status_code, 400)

    def test_valid_submission_is_listed_for_everyone(self):
        res = self.submit()
        self.assertEqual(res.status_code, 201, res.get_json())
        listed = self.client.get("/api/suggestions").get_json()["suggestions"]
        self.assertEqual([s["title"] for s in listed], ["Neue Idee"])
        self.assertEqual(listed[0]["votes"], 0)

    def test_text_is_validated_before_captcha_is_used(self):
        token, answer = self.challenge()
        bad = self.client.post("/api/suggestions", json={"title": "x", "description": "zu kurz", "captchaToken": token, "captchaAnswer": answer})
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post("/api/suggestions", json={"title": "Gute Idee", "description": "Lang genug fuer die Pruefung.",
                                                         "captchaToken": token, "captchaAnswer": answer})
        self.assertEqual(ok.status_code, 201)                                       # dasselbe Captcha war noch frei

    def test_honeypot_links_and_duplicates_are_rejected(self):
        self.assertEqual(self.submit(website="http://spam").status_code, 400)
        res = self.submit(desc="Besuche www.billig-kaufen.de jetzt")
        self.assertEqual(res.get_json()["code"], "links_not_allowed")
        self.assertEqual(self.submit(title="Doppelt").status_code, 201)
        self.clock.now += 1
        self.assertEqual(self.submit(title="doppelt").status_code, 409)

    def test_submission_rate_limit_per_browser(self):
        for i in range(3):
            self.assertEqual(self.submit(title=f"Idee Nummer {i}").status_code, 201)
        res = self.submit(title="Idee Nummer 99")
        self.assertEqual(res.status_code, 429)

    def test_vote_needs_client_id_and_is_one_per_user(self):
        self.submit()
        sid = self.client.get("/api/suggestions").get_json()["suggestions"][0]["id"]
        self.assertEqual(self.client.post(f"/api/suggestions/{sid}/vote").status_code, 400)
        self.assertEqual(self.client.post(f"/api/suggestions/{sid}/vote", headers={"X-Client-Id": "kurz"}).status_code, 400)
        h1, h2 = {"X-Client-Id": "nutzer-eins-0001"}, {"X-Client-Id": "nutzer-zwei-0002"}
        self.assertEqual(self.client.post(f"/api/suggestions/{sid}/vote", headers=h1).get_json(), {"votes": 1, "voted": True})
        self.assertEqual(self.client.post(f"/api/suggestions/{sid}/vote", headers=h2).get_json(), {"votes": 2, "voted": True})
        self.assertEqual(self.client.post(f"/api/suggestions/{sid}/vote", headers=h1).get_json(), {"votes": 1, "voted": False})
        mine = self.client.get("/api/suggestions", headers=h2).get_json()["suggestions"][0]
        self.assertEqual((mine["votes"], mine["voted"]), (1, True))
        self.assertEqual(self.client.post("/api/suggestions/999/vote", headers=h1).status_code, 404)

    def test_public_phrases(self):
        phrases = self.client.get("/api/phrases").get_json()["phrases"]
        self.assertEqual([p["text"] for p in phrases], list(DEFAULT_PHRASES))

    # --- Betreiber ---
    def test_admin_requires_login_and_reports_status(self):
        self.assertTrue(self.client.get("/api/admin/status").get_json()["enabled"])
        for path in ("/tables", "/stats", "/phrases", "/suggestions"):
            self.assertEqual(self.client.get("/api/admin" + path).status_code, 401, path)
        self.assertEqual(self.client.get("/api/admin/tables", headers={"Authorization": "Bearer falsch"}).status_code, 401)
        self.assertEqual(self.client.post("/api/admin/login", json={"password": "nein"}).status_code, 401)
        headers = self.login()
        self.assertEqual(self.client.get("/api/admin/tables", headers=headers).status_code, 200)

    def test_admin_login_is_rate_limited(self):
        for _ in range(5):
            self.client.post("/api/admin/login", json={"password": "nein"})
        self.assertEqual(self.client.post("/api/admin/login", json={"password": self.PASSWORD}).status_code, 429)

    def test_admin_disabled_without_password(self):
        self.deps.admin = AdminAuth("", SECRET)
        self.assertFalse(self.client.get("/api/admin/status").get_json()["enabled"])
        self.assertEqual(self.client.post("/api/admin/login", json={"password": ""}).status_code, 503)
        self.assertEqual(self.client.get("/api/admin/stats").status_code, 503)

    def test_admin_phrases_crud_changes_public_list(self):
        h = self.login()
        added = self.client.post("/api/admin/phrases", json={"text": "Ihr Lieben!"}, headers=h)
        self.assertEqual(added.status_code, 201)
        pid = added.get_json()["phrase"]["id"]
        self.assertEqual(self.client.post("/api/admin/phrases", json={"text": "ihr lieben!"}, headers=h).status_code, 409)
        self.assertEqual(self.client.post("/api/admin/phrases", json={"text": ""}, headers=h).status_code, 400)
        self.assertEqual(self.client.put(f"/api/admin/phrases/{pid}", json={"text": "Ihr Süßen!"}, headers=h).status_code, 200)
        self.assertEqual(self.client.put("/api/admin/phrases/999", json={"text": "x"}, headers=h).status_code, 404)
        moved = self.client.post(f"/api/admin/phrases/{pid}/move", json={"direction": "up"}, headers=h).get_json()["phrases"]
        self.assertEqual(moved[-2]["id"], pid)
        public = [p["text"] for p in self.client.get("/api/phrases").get_json()["phrases"]]
        self.assertIn("Ihr Süßen!", public)
        self.assertEqual(self.client.delete(f"/api/admin/phrases/{pid}", headers=h).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/admin/phrases/{pid}", headers=h).status_code, 404)
        self.assertNotIn("Ihr Süßen!", [p["text"] for p in self.client.get("/api/phrases").get_json()["phrases"]])

    def test_admin_moderates_suggestions(self):
        self.submit()
        h = self.login()
        item = self.client.get("/api/admin/suggestions", headers=h).get_json()["suggestions"][0]
        self.assertEqual(item["status"], "visible")
        self.assertEqual(self.client.post(f"/api/admin/suggestions/{item['id']}/status", json={"status": "hidden"}, headers=h).status_code, 200)
        self.assertEqual(self.client.get("/api/suggestions").get_json()["suggestions"], [])        # fuer alle unsichtbar
        self.assertEqual(self.client.get("/api/admin/suggestions", headers=h).get_json()["suggestions"][0]["status"], "hidden")
        self.assertEqual(self.client.post(f"/api/admin/suggestions/{item['id']}/status", json={"status": "bla"}, headers=h).status_code, 400)
        self.assertEqual(self.client.put(f"/api/admin/suggestions/{item['id']}", json={"title": "Bereinigter Titel", "description": "Bereinigte Beschreibung, lang genug."}, headers=h).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/admin/suggestions/{item['id']}", headers=h).status_code, 200)
        self.assertEqual(self.client.delete(f"/api/admin/suggestions/{item['id']}", headers=h).status_code, 404)

    def test_admin_stats_and_tables(self):
        self.stats.table_created("AAA111", now=self.clock.now - 3000)
        self.stats.round_started("AAA111", 2, 2, now=self.clock.now - 2900)
        self.stats.game_finished("AAA111", now=self.clock.now - 100)
        self.tables.rows.append({"code": "AAA111", "status": "playing", "isPublic": False, "hasPassword": False, "spectators": 0, "game": None,
                                 "createdAt": self.clock.now - 3000, "startedAt": self.clock.now - 2900, "lastActivityAt": self.clock.now - 100,
                                 "humans": 2, "bots": 2, "connectedHumans": 2})
        h = self.login()
        stats = self.client.get("/api/admin/stats", headers=h).get_json()
        self.assertEqual((stats["tablesTotal"], stats["withHumans"]["tables"], stats["gamesTotal"]), (1, 1, 1))
        tables = self.client.get("/api/admin/tables", headers=h).get_json()
        self.assertEqual((tables["count"], tables["tables"][0]["state"], tables["tables"][0]["humans"]), (1, "active", 2))

    def test_proxy_address_only_trusted_when_configured(self):
        self.deps.trust_proxy = False
        for i in range(5):
            self.client.post("/api/admin/login", json={"password": "nein"}, headers={"X-Forwarded-For": f"10.0.0.{i}"})
        self.assertEqual(self.client.post("/api/admin/login", json={"password": "x"}, headers={"X-Forwarded-For": "10.9.9.9"}).status_code, 429)


if __name__ == "__main__":
    unittest.main()
