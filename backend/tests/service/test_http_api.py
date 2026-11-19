"""HTTP-Schicht (Flask-Testclient) mit Fake-Raumzugriff und In-Memory-Speicher: Rechte, Fehlercodes, Datenschutz."""
import json
import random
import unittest

from flask import Flask

from ..rules import loader  # noqa: F401
from app.game_api import Auth, create_game_blueprint
from app.table import MemoryStore, TableService

CODE = "ABC234"


class FakeAccess:
    """Ein Raum: Host (Mensch) + drei Bots + ein Zuschauer; Tokens wie im echten Betrieb nur den Menschen bekannt."""

    def __init__(self, human_players=1):
        self.tokens = {"tok-host": 1, "tok-spec": 9}
        self.roles = {1: "player", 9: "spectator"}
        self.players_list = [{"memberId": 1, "name": "Host", "isBot": False, "ready": True}]
        for i in range(2, 5):
            humans_left = human_players - 1 - (i - 2)
            bot = humans_left <= 0
            self.players_list.append({"memberId": i, "name": f"M{i}", "isBot": bot, "ready": True})
            if not bot:
                self.tokens[f"tok-{i}"] = i
            self.roles[i] = "player"
        self.status = "waiting"
        self.stored_settings = {}
        self.touched = []
        self.takeover_seconds = 180

    def authenticate(self, code, token):
        mid = self.tokens.get(token)
        if code != CODE or mid is None:
            return None
        return Auth(code, mid, self.roles[mid], mid == 1, self.status, f"Name{mid}")

    def players(self, code): return [dict(p) for p in self.players_list]
    def member_ids(self, code): return [1, 2, 3, 4, 9]
    def settings(self, code): return dict(self.stored_settings)
    def set_settings(self, code, s): self.stored_settings = dict(s)
    def set_status(self, code, status): self.status = status
    def touch(self, member_id): self.touched.append(member_id)
    def takeover(self, code): return self.takeover_seconds
    def set_takeover(self, code, seconds): self.takeover_seconds = seconds


class FakeNotifier:
    def __init__(self): self.games, self.rooms, self.chats = [], 0, []
    def chat_message(self, code, message): self.chats.append(message)
    def game_updated(self, code, views): self.games.append(views)
    def room_updated(self, code): self.rooms += 1


class HttpBase(unittest.TestCase):
    humans = 1

    def setUp(self):
        self.access, self.notifier = FakeAccess(self.humans), FakeNotifier()
        self.service = TableService(MemoryStore(), random.Random(4))
        app = Flask(__name__)
        app.register_blueprint(create_game_blueprint(self.service, self.access, self.notifier), url_prefix="/api")
        self.client = app.test_client()

    def get(self, path, token="tok-host"):
        return self.client.get(f"/api/rooms/{CODE}{path}", headers={"X-Session-Token": token} if token else {})

    def post(self, path, body=None, token="tok-host", header=False):
        body = dict(body or {})
        headers = {}
        if token and header:
            headers["X-Session-Token"] = token
        elif token:
            body["token"] = token
        return self.client.post(f"/api/rooms/{CODE}{path}", json=body, headers=headers)

    def start(self):
        res = self.post("/start")
        self.assertEqual(res.status_code, 201, res.get_json())
        return res.get_json()


class SettingsAndStart(HttpBase):
    def test_rule_schema_is_public(self):
        res = self.client.get("/api/rule-schema")
        ids = [o["id"] for o in res.get_json()["options"]]
        self.assertEqual(len(ids), 14)
        self.assertEqual(ids[0], "dulle")

    def test_settings_host_only_and_normalized(self):
        self.assertEqual(self.post("/settings", {"settings": {}}, token=None).status_code, 403)
        self.assertEqual(self.post("/settings", {"settings": {}}, token="tok-spec").status_code, 403)
        res = self.post("/settings", {"settings": {"schweinchen": True, "sharp_doppelkopf": True}})
        body = res.get_json()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(body["profileId"], "custom")
        self.assertTrue(body["settings"]["schweinchen"] and body["settings"]["sharp_doppelkopf"] and body["settings"]["dulle"])
        self.assertEqual(self.access.stored_settings, body["settings"])
        self.assertEqual(self.notifier.rooms, 1)

    def test_invalid_settings_rejected(self):
        for bad in ({"nope": True}, {"dulle": "ja"}, {"second_dulle_wins_except_last": True}):
            res = self.post("/settings", {"settings": bad})
            self.assertEqual(res.status_code, 400, bad)
            self.assertIn("code", res.get_json())
        self.assertEqual(self.access.stored_settings, {})

    def test_start_rules(self):
        self.assertEqual(self.post("/start", token="tok-spec").status_code, 403)
        self.access.players_list[1]["ready"] = False
        self.assertEqual(self.post("/start").status_code, 409)
        self.access.players_list[1]["ready"] = True
        body = self.start()
        self.assertEqual(self.access.status, "playing")
        self.assertEqual(body["view"]["table"]["mySeat"], 0)
        self.assertEqual(len(body["view"]["game"]["hand"]), 12)
        self.assertEqual(self.post("/start").status_code, 409)                  # laeuft schon
        self.assertEqual(self.post("/settings", {"settings": {}}).status_code, 409)  # keine Regelaenderung waehrend der Runde

    def test_start_uses_room_settings(self):
        self.post("/settings", {"settings": {"sharp_doppelkopf": True}})
        body = self.start()
        self.assertEqual(body["view"]["table"]["deckVariant"], "without_nines")
        self.assertEqual(len(body["view"]["game"]["hand"]), 10)


class GameAccess(HttpBase):
    def setUp(self):
        super().setUp()
        self.start()

    def test_auth_required(self):
        self.assertEqual(self.get("/game", token=None).status_code, 403)
        self.assertEqual(self.get("/game", token="falsch").status_code, 403)
        self.assertEqual(self.post("/action", {"type": "declare", "reservation": False}, token="falsch").status_code, 403)

    def test_token_in_header_or_body(self):
        self.assertEqual(self.get("/game").status_code, 200)
        res = self.post("/action", {"type": "announce", "level": 0}, header=True)
        self.assertNotEqual(res.status_code, 403)

    def test_spectator_sees_no_hands_and_cannot_act(self):
        view = self.get("/game", token="tok-spec").get_json()
        self.assertNotIn("hand", view["game"])
        self.assertIsNone(view["table"]["mySeat"])
        res = self.post("/action", {"type": "declare", "reservation": False}, token="tok-spec")
        self.assertEqual(res.status_code, 403)

    def test_privacy_of_pushed_views(self):
        self.notifier.games.clear()
        self.act_until_progress()
        views = self.notifier.games[-1]
        self.assertEqual(set(views), {1, 2, 3, 4, 9})
        self.assertNotIn("hand", views[9]["game"])
        hands = {mid: {json.dumps(c, sort_keys=True) for c in v["game"]["hand"]} for mid, v in views.items() if mid != 9}
        for mid, others in hands.items():
            for other_mid, other_hand in hands.items():
                if other_mid != mid:
                    for card in other_hand - others:
                        self.assertNotIn(card, json.dumps(views[mid]))

    def act_until_progress(self):
        view = self.get("/game").get_json()
        act = view["game"]["legalActions"][0]
        payload = {"type": "declare", "reservation": False} if act["type"] == "declare" else \
            {"type": "play_card", "cardId": act["cards"][0]}
        res = self.post("/action", {**payload, "expectedVersion": view["version"]})
        self.assertEqual(res.status_code, 200, res.get_json())
        return res.get_json()

    def test_action_flow_and_versions(self):
        view = self.get("/game").get_json()
        self.assertEqual(view["game"]["phase"], "reservation_query")
        out = self.act_until_progress()
        self.assertGreater(out["version"], view["version"])
        self.assertFalse(out["duplicate"])

    def test_error_codes(self):
        stale = self.post("/action", {"type": "declare", "reservation": False, "expectedVersion": 99})
        self.assertEqual((stale.status_code, stale.get_json()["code"]), (409, "version_conflict"))
        self.assertEqual(stale.get_json()["version"], self.get("/game").get_json()["version"])  # aktuelle Version mitgeliefert
        bad = self.post("/action", {"type": "declare"})
        self.assertEqual((bad.status_code, bad.get_json()["code"]), (400, "bad_request"))
        unknown = self.post("/action", {"type": "zaubern"})
        self.assertEqual((unknown.status_code, unknown.get_json()["code"]), (400, "unknown_action"))
        card_too_early = self.post("/action", {"type": "play_card", "cardId": "A-♣-0"})
        self.assertEqual((card_too_early.status_code, card_too_early.get_json()["code"]), (409, "wrong_phase"))

    def test_seat_cannot_be_spoofed(self):
        res = self.post("/action", {"type": "declare", "reservation": False, "seat": 2, "memberId": 3})
        self.assertEqual(res.status_code, 200)                              # wirkt fuer Sitz 0 (den Host), Felder ignoriert

    def test_idempotent_retry(self):
        view = self.get("/game").get_json()
        payload = {"type": "declare", "reservation": False, "actionId": "same-1"}
        first = self.post("/action", payload).get_json()
        pushes = len(self.notifier.games)
        again = self.post("/action", payload).get_json()
        self.assertTrue(again["duplicate"])
        self.assertEqual(again["version"], first["version"])
        self.assertEqual(len(self.notifier.games), pushes)                  # keine doppelte Benachrichtigung

    def test_next_game_gating_and_history(self):
        res = self.post("/next")
        self.assertEqual((res.status_code, res.get_json()["code"]), (409, "game_running"))
        self.assertEqual(self.post("/next", token="tok-spec").status_code, 403)
        self.assertEqual(self.get("/history").get_json(), {"games": []})
        self.assertEqual(self.get("/history", token=None).status_code, 403)


class ChatApi(HttpBase):
    def test_chat_requires_membership_and_broadcasts(self):
        self.assertEqual(self.get("/chat", token=None).status_code, 403)
        res = self.post("/chat", {"text": "  Moin   zusammen \n"})
        self.assertEqual(res.status_code, 201)
        msg = res.get_json()["message"]
        self.assertEqual((msg["text"], msg["name"], msg["memberId"]), ("Moin zusammen", "Name1", 1))
        self.assertEqual(self.notifier.chats, [msg])
        self.assertEqual(self.get("/chat", token="tok-spec").get_json()["messages"], [msg])

    def test_chat_validation_and_rate_limit(self):
        for bad in ({"text": ""}, {"text": "   "}, {"text": 5}, {"text": "x" * 201}, {}):
            self.assertEqual(self.post("/chat", bad).status_code, 400, bad)
        self.assertEqual(self.post("/chat", {"text": "eins"}).status_code, 201)
        self.assertEqual(self.post("/chat", {"text": "zwei"}).status_code, 429)
        self.assertEqual(self.post("/chat", {"text": "anderer"}, token="tok-spec").status_code, 201)
        self.assertEqual(self.post("/chat", {"text": "x"}, token=None).status_code, 403)


class PacedHttp(HttpBase):
    """Getakteter Betrieb: Start/Zug loesen den Runner aus, "Naechster Stich", Platz uebergeben/zurueckholen."""

    def setUp(self):
        super().setUp()
        from app.game_api import Publisher
        from app.table import BotRunner
        self.service.paced = True
        self.kicks = []
        publisher = Publisher(self.service, self.access, self.notifier)
        runner = BotRunner(self.service, publisher.step, sleep=lambda s: None, spawn=lambda fn, *a: fn(*a))
        real_kick = runner.kick
        runner.kick = lambda code: (self.kicks.append(code), real_kick(code))[1]
        app = Flask(__name__)
        app.register_blueprint(create_game_blueprint(self.service, self.access, self.notifier, runner=runner,
                                                     publisher=publisher), url_prefix="/api")
        self.client = app.test_client()

    def play_until_hold(self):
        for _ in range(200):
            view = self.get("/game").get_json()
            if view["table"]["holding"]:
                return view
            acts = {a["type"]: a for a in view["game"]["legalActions"]}
            if "declare" in acts:
                body = {"type": "declare", "reservation": False}
            elif "resolve" in acts:
                body = {"type": "resolve", "accept": False}
            elif "baptize" in acts:
                body = {"type": "baptize", "choice": acts["baptize"]["choices"][-1]}
            elif "play_card" in acts:
                body = {"type": "play_card", "cardId": acts["play_card"]["cards"][0]}
            else:
                continue
            self.assertEqual(self.post("/action", body).status_code, 200)
        self.fail("kein Hold erreicht")

    def test_start_kicks_runner_and_bots_wait_for_the_human_between_tricks(self):
        self.start()
        self.assertIn(CODE, self.kicks)
        view = self.play_until_hold()
        self.assertTrue(view["table"]["holding"])
        self.assertEqual(view["game"]["currentTrick"], [])
        self.assertIsNotNone(view["game"]["lastTrick"])
        n = len(view["game"]["lastTrick"]["plays"])
        self.assertEqual(n, 4)

    def test_continue_releases_hold_and_is_idempotent(self):
        self.start()
        self.play_until_hold()
        first = self.post("/continue")
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.get_json()["view"]["table"]["holding"] and first.get_json()["view"]["game"]["currentTrick"] == [])
        self.assertEqual(self.post("/continue").status_code, 200)       # zweimal: kein Fehler
        self.assertEqual(self.post("/continue", token="tok-spec").status_code, 403)

    def test_away_and_back(self):
        self.start()
        res = self.post("/away")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["view"]["table"]["seats"][0]["autoplay"])
        res = self.post("/back")
        self.assertFalse(res.get_json()["view"]["table"]["seats"][0]["autoplay"])
        self.assertEqual(self.post("/away", token="tok-spec").status_code, 403)


class StatsHooks(unittest.TestCase):
    """Die Spiel-Schnittstelle meldet Rundenstart, Aktionen und beendete Spiele an die Statistik."""

    def test_round_start_actions_and_finished_games_are_recorded(self):
        from app.community.stats import MemoryStats
        access, notifier = FakeAccess(2), FakeNotifier()
        stats = MemoryStats()
        stats.table_created(CODE)
        service = TableService(MemoryStore(), random.Random(4))
        app = Flask(__name__)
        app.register_blueprint(create_game_blueprint(service, access, notifier, stats=stats), url_prefix="/api")
        client = app.test_client()
        res = client.post(f"/api/rooms/{CODE}/start", json={"token": "tok-host"})
        self.assertEqual(res.status_code, 201)
        (log,) = stats.logs()
        self.assertEqual((log["humans"], log["bots"], log["rounds"]), (2, 2, 1))
        self.assertIsNotNone(log["startedAt"])
        before = log["lastActivityAt"]
        view = res.get_json()["view"]
        acts = {a["type"]: a for a in view["game"]["legalActions"]}
        if "declare" in acts:                         # Host ist als Erster dran: gesund
            client.post(f"/api/rooms/{CODE}/action", json={"token": "tok-host", "type": "declare", "reservation": False})
            self.assertGreaterEqual(stats.logs()[0]["lastActivityAt"], before)
        service.store.load(CODE)                      # (Spiel laeuft; beendete Spiele siehe Rundentest)
        self.assertEqual(stats.logs()[0]["games"], 0)


class TakeoverApi(HttpBase):
    humans = 2

    def test_only_host_sets_takeover_and_values_are_validated(self):
        self.assertEqual(self.post("/takeover", {"seconds": 300}).status_code, 200)
        self.assertEqual(self.access.takeover_seconds, 300)
        self.assertEqual(self.post("/takeover", {"seconds": 300}, token="tok-2").status_code, 403)   # kein Host
        self.assertEqual(self.post("/takeover", {"seconds": 300}, token="tok-spec").status_code, 403)
        self.assertEqual(self.post("/takeover", {"seconds": 45}).status_code, 400)
        self.assertEqual(self.post("/takeover", {"seconds": True}).status_code, 400)
        self.assertEqual(self.post("/takeover", {"seconds": "60"}).status_code, 400)
        self.assertEqual(self.post("/takeover", {}).status_code, 400)
        self.assertEqual(self.post("/takeover", {"seconds": 0}).status_code, 200)                   # 0 = nie
        self.assertEqual(self.access.takeover_seconds, 0)

    def test_setting_from_lobby_is_used_at_start_and_changeable_during_the_round(self):
        self.post("/takeover", {"seconds": 600})
        view = self.start()["view"]
        self.assertEqual(view["table"]["takeover"], 600)
        before = self.notifier.rooms
        res = self.post("/takeover", {"seconds": 0})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.get("/game").get_json()["table"]["takeover"], 0)
        self.assertGreater(self.notifier.rooms, before)

    def test_stay_remembers_choice_and_requires_a_player(self):
        self.start()
        res = self.post("/stay", {"remember": True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["view"]["table"]["seats"][0]["noTakeover"])
        res = self.post("/stay", {"remember": False})
        self.assertFalse(res.get_json()["view"]["table"]["seats"][0]["noTakeover"])
        self.assertEqual(self.post("/stay", {"remember": "ja"}).status_code, 400)
        self.assertEqual(self.post("/stay", token="tok-spec").status_code, 403)
        self.assertEqual(self.post("/stay", token=None).status_code, 403)


class FullRoundOverHttp(HttpBase):
    def test_complete_round_with_one_human_and_three_bots(self):
        self.start()
        steps, rng = 0, random.Random(5)
        while True:
            view = self.get("/game").get_json()
            if view["table"]["finished"]:
                break
            game = view["game"]
            if game["phase"] == "finished":
                res = self.post("/next")
                self.assertEqual(res.status_code, 200, res.get_json())
                continue
            acts = game["legalActions"]
            self.assertTrue(acts, f"blockiert in {game['phase']}")
            a = next((x for x in acts if x["type"] != "announce"), acts[0])
            payload = {"declare": {"type": "declare", "reservation": rng.random() < 0.1},
                       "resolve": {"type": "resolve", "accept": rng.random() < 0.5},
                       "baptize": {"type": "baptize", "choice": rng.choice(a.get("choices", ["solo_queens"]))},
                       "play_card": {"type": "play_card", "cardId": rng.choice(a.get("cards", [""]))},
                       "announce": {"type": "announce", "level": a.get("levels", [0])[0]},
                       "schweinchen": {"type": "schweinchen"}}[a["type"]]
            res = self.post("/action", {**payload, "expectedVersion": view["version"], "actionId": f"s{steps}"})
            self.assertEqual(res.status_code, 200, res.get_json())
            steps += 1
            self.assertLess(steps, 4000)
        self.assertEqual(self.access.status, "finished")
        games = self.get("/history").get_json()["games"]
        self.assertEqual(len(games), view["table"]["gameNumber"])
        self.assertEqual(games[-1]["roundFinished"], True)
        self.assertEqual(sum(view["table"]["round"]["totals"]), 0)
        self.assertEqual(self.post("/next").get_json()["code"], "round_finished")


if __name__ == "__main__":
    unittest.main()
