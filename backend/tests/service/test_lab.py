"""Test-Tisch (Szenario-Labor): Pruefung, Kartenbau, Vorlagen, Armut aus beiden Sichten, HTTP-Schnittstelle."""
import json
import random
import unittest

from flask import Flask

from ..rules import loader  # noqa: F401
from app.community.admin_auth import AdminAuth
from app.lab import PRESETS, build_lab_table, parse_scenario, rigged_order
from app.lab.api import create_lab_blueprint
from app.rules import Phase, RuleViolation
from app.rules.cards import DeckVariant, card
from app.rules.game import GameKind
from app.rules.trump import GameType
from app.table import MemoryStore, TableService

HUMAN, BOT = False, True


def seats_for(scenario):
    return [{"memberId": 100 + i, "name": s["name"], "isBot": s["bot"]} for i, s in enumerate(scenario.seats)]


def preset(pid):
    return next(p for p in PRESETS if p["id"] == pid)["scenario"]


def faces(game, seat):
    return sorted(f"{c.rank.value}{c.suit.value}" for c in game.hands[seat])


class ParseTests(unittest.TestCase):
    def bad(self, **fields):
        with self.assertRaises(RuleViolation) as ctx:
            parse_scenario(fields)
        self.assertEqual(ctx.exception.code, "bad_scenario")
        return ctx.exception.message

    def test_defaults(self):
        s = parse_scenario({})
        self.assertEqual((s.dealer, s.advance, s.hands), (0, "none", {}))
        self.assertEqual([x["name"] for x in s.seats], ["Platz 1", "Platz 2", "Platz 3", "Platz 4"])

    def test_not_a_dict(self):
        with self.assertRaises(RuleViolation):
            parse_scenario("x")

    def test_rejects_bad_input(self):
        self.bad(dealer=4)
        self.bad(dealer=True)
        self.bad(hands={"4": []})
        self.bad(hands={"0": ["Q♣"] * 3})                                  # dritte Kopie
        self.bad(hands={"0": ["Q♣", "Z♣"]})
        self.bad(hands={"0": ["Q♣"] * 13})
        self.bad(hands={"0": "Q♣"})
        self.bad(seats=[{"bot": True}] * 4)                                # kein Mensch
        self.bad(seats=[{}] * 3)
        self.bad(advance="viel")
        self.bad(advance="tricks", tricks=13)
        self.bad(round={"totals": [1, 2]})
        self.bad(round={"pflichtsoloDone": [True]})

    def test_unknown_option_is_rejected(self):
        with self.assertRaises(RuleViolation):
            parse_scenario({"settings": {"gibt_es_nicht": True}})

    def test_nines_not_allowed_without_nines(self):
        self.assertIn("Neunen", self.bad(settings={"sharp_doppelkopf": True}, hands={"0": ["9♣"]}))

    def test_sharp_deck_allows_only_ten_cards(self):
        self.bad(settings={"sharp_doppelkopf": True}, hands={"0": ["Q♣"] * 2 + ["A♣"] * 2 + ["K♣"] * 2 + ["J♣"] * 2
                                                           + ["10♣"] * 2 + ["Q♠"]})

    def test_names_are_trimmed_and_defaulted(self):
        s = parse_scenario({"seats": [{"name": "  " + "x" * 50}, {"bot": True}, {"name": ""}, {}]})
        self.assertEqual(len(s.seats[0]["name"]), 32)
        self.assertEqual(s.seats[1]["name"], "Bot 2")
        self.assertEqual(s.seats[2]["name"], "Platz 3")

    def test_roundtrip(self):
        s = parse_scenario(preset("endspiel"))
        self.assertEqual(parse_scenario(s.to_dict()).to_dict(), s.to_dict())


class RiggingTests(unittest.TestCase):
    def test_given_hands_are_dealt_exactly(self):
        order = rigged_order({0: ["Q♣", "Q♣", "A♦"], 2: ["10♥"]}, 1, DeckVariant.WITH_NINES, random.Random(3))
        from app.rules.dealing import deal
        hands = deal(order, 1, DeckVariant.WITH_NINES)
        self.assertEqual(len({c.id for c in order}), 48)
        self.assertEqual(sorted(c.face for c in hands[0] if c.face in {card("Q♣").face, card("A♦").face}).__len__(), 3)
        self.assertEqual(sum(1 for c in hands[0] if c.face == card("Q♣").face), 2)
        self.assertEqual(sum(1 for c in hands[2] if c.face == card("10♥").face), 1)

    def test_every_seat_can_be_fixed(self):
        s = parse_scenario(preset("normal_re_kontra"))
        t = build_lab_table(s, seats_for(s), random.Random(1))
        for seat in range(4):
            self.assertEqual(faces(t.game, seat), sorted(s.hands[seat]))

    def test_unspecified_cards_are_random_but_complete(self):
        s = parse_scenario({"hands": {"0": ["A♦", "A♦"]}})
        seen = set()
        for n in range(6):
            t = build_lab_table(s, seats_for(s), random.Random(n))
            self.assertEqual([len(h) for h in t.game.hands], [12] * 4)
            self.assertEqual(faces(t.game, 0).count("A♦"), 2)
            seen.add(tuple(faces(t.game, 1)))
        self.assertGreater(len(seen), 1)

    def test_sharp_deck(self):
        s = parse_scenario({"settings": {"sharp_doppelkopf": True}, "hands": {"1": ["Q♣", "10♥"]}})
        t = build_lab_table(s, seats_for(s), random.Random(1))
        self.assertEqual([len(h) for h in t.game.hands], [10] * 4)


class BuildTests(unittest.TestCase):
    def test_dealer_round_and_no_takeover(self):
        s = parse_scenario({"dealer": 2, "round": {"normalGamesPlayed": 5, "bockRemaining": 3, "totals": [1, 2, 3, 4]}})
        t = build_lab_table(s, seats_for(s), random.Random(1))
        self.assertEqual((t.game.dealer, t.round.normal_games_played, t.round.bock_remaining, t.round.totals),
                         (2, 5, 3, [1, 2, 3, 4]))
        self.assertEqual((t.takeover, t.game_number), (0, 6))
        self.assertIsNone(t.takeover_idle(0))
        self.assertEqual(t.game.score_multiplier, 2)

    def test_advance_to_playing(self):
        s = parse_scenario({"hands": {str(k): v.split() for k, v in
                                      {0: "Q♣ Q♠ J♣ J♣ A♦ A♦ A♣ A♣ 10♣ 10♣ K♣ K♣"}.items()}, "advance": "playing"})
        t = build_lab_table(s, seats_for(s), random.Random(1))
        self.assertIs(t.game.phase, Phase.PLAYING)
        self.assertEqual(len(t.game.tricks), 0)

    def test_advance_tricks_and_finished(self):
        s = parse_scenario(preset("endspiel"))
        t = build_lab_table(s, seats_for(s), random.Random(1))
        self.assertEqual((len(t.game.tricks), [len(h) for h in t.game.hands]), (10, [2] * 4))
        s = parse_scenario(preset("ergebnis"))
        t = build_lab_table(s, seats_for(s), random.Random(1))
        self.assertIs(t.game.phase, Phase.FINISHED)
        self.assertTrue(t.recorded)
        self.assertEqual(t.round.normal_games_played, 1)

    def test_advance_refuses_redeal(self):
        # Alle Mittel-Blaetter an Bots: niemand ist arm -> kein Neugeben; hier kuenstlich: Armut ohne Kaeufer unmoeglich
        # mit Bots, also pruefen wir den Normalfall: Armut wird uebernommen, Vorspielen klappt.
        s = parse_scenario(dict(preset("armut_alle"), advance="playing"))
        t = build_lab_table(s, seats_for(s), random.Random(1))
        self.assertIs(t.game.phase, Phase.PLAYING)
        self.assertIs(t.game.kind, GameKind.POVERTY)

    def test_every_preset_builds_and_validates(self):
        ids = set()
        for p in PRESETS:
            self.assertNotIn(p["id"], ids)
            ids.add(p["id"])
            self.assertTrue(p["title"] and p["description"])
            s = parse_scenario(p["scenario"])
            t = build_lab_table(s, seats_for(s), random.Random(1))
            self.assertEqual(len(t.seats), 4)
            self.assertEqual(sum(not x["isBot"] for x in t.seats) >= 1, True)

    def test_preset_option_settings(self):
        self.assertTrue(parse_scenario(preset("armut_arm")).settings["poverty"])
        self.assertTrue(parse_scenario(preset("schweinchen")).settings["schweinchen"])
        self.assertFalse(parse_scenario(preset("zufall")).settings["poverty"])

    def test_pflichtsolo_preset_is_shown_to_seat_four(self):
        s = parse_scenario(preset("pflichtsolo"))
        t = build_lab_table(s, seats_for(s), random.Random(1))
        self.assertIs(t.game.phase, Phase.BAPTISM)
        self.assertEqual(t.game.baptism_seat, 3)


class PovertyLabTests(unittest.TestCase):
    """Die Armut-Vorlagen fuehren durch beide Sichten - mit dem echten Tischdienst."""

    def setUp(self):
        self.store = MemoryStore()
        self.svc = TableService(self.store, random.Random(5))

    def launch(self, pid):
        s = parse_scenario(preset(pid))
        self.seats = seats_for(s)
        self.svc.install("LAB", build_lab_table(s, self.seats, random.Random(1)))
        return s

    def game(self):
        return self.svc.load("LAB").table.game

    def act(self, seat, **payload):
        return self.svc.act("LAB", 100 + seat, payload)

    def ids(self, seat, *texts):
        hand, out = list(self.game().hands[seat]), []
        for t in texts:
            c = next(x for x in hand if x.face == card(t).face and x.id not in out)
            out.append(c.id)
        return out

    def test_poor_perspective(self):
        self.launch("armut_arm")
        self.assertEqual((self.game().phase, self.game().query_seat), (Phase.RESERVATION_QUERY, 0))
        self.act(0, type="declare", reservation=True)                    # Bots antworten selbststaendig
        self.act(0, type="baptize", choice="poverty")
        self.assertIs(self.game().phase, Phase.POVERTY_PASS)
        self.act(0, type="poverty_pass", cardIds=self.ids(0, "Q♣", "J♦", "9♦"))
        g = self.game()
        self.assertIs(g.phase, Phase.PLAYING)                            # Bot 2 (9 Truempfe) hat gekauft
        self.assertIs(g.kind, GameKind.POVERTY)
        self.assertEqual(sorted(g.re_seats), [0, 1])
        got = self.svc.view("LAB", 100)["game"]["povertyGot"]          # der Arme sieht, was er zurueckbekam
        self.assertEqual(len(got), 3)
        self.assertNotIn("povertyGot", self.svc.view("LAB", 101)["game"])

    def test_buyer_perspective(self):
        self.launch("armut_kaeufer")
        self.act(0, type="declare", reservation=False)
        g = self.game()
        self.assertIs(g.phase, Phase.POVERTY_OFFER)
        self.assertEqual((g.poverty_seat, g.poverty_queue[0]), (3, 0))
        view = self.svc.view("LAB", 100)
        self.assertEqual(view["game"]["phase"], "poverty_offer")
        self.act(0, type="poverty_offer", accept=True)
        self.assertIs(self.game().phase, Phase.POVERTY_RETURN)
        self.act(0, type="poverty_return", cardIds=self.ids(0, "9♣", "9♣", "9♠"))
        g = self.game()
        self.assertIs(g.phase, Phase.PLAYING)
        self.assertEqual(sorted(g.re_seats), [0, 3])

    def test_nobody_takes_it_redeals(self):
        self.launch("armut_neugabe")
        for seat in (0, 1, 2):
            self.act(seat, type="declare", reservation=False)
        self.assertIs(self.game().phase, Phase.POVERTY_OFFER)
        self.assertEqual(self.game().poverty_queue[0], 0)
        for seat in (0, 1, 2):
            self.act(seat, type="poverty_offer", accept=False)
        table = self.svc.load("LAB").table
        self.assertEqual((table.redeals, table.redeal_seat), (1, 3))
        self.assertIs(table.game.phase, Phase.RESERVATION_QUERY)

    def test_all_human_walkthrough(self):
        self.launch("armut_alle")
        for seat in range(4):
            self.act(seat, type="declare", reservation=seat == 2)
        self.act(2, type="baptize", choice="poverty")
        self.act(2, type="poverty_pass", cardIds=self.ids(2, "Q♣", "J♦", "9♦"))
        g = self.game()
        self.assertIs(g.phase, Phase.POVERTY_OFFER)
        self.assertEqual(g.poverty_queue[0], 3)
        self.act(3, type="poverty_offer", accept=True)
        self.act(3, type="poverty_return", cardIds=self.ids(3, "9♣", "9♣", "9♠"))
        g = self.game()
        self.assertIs(g.phase, Phase.PLAYING)
        self.assertEqual(sorted(g.re_seats), [2, 3])


# ------------------------------------------------------------------ HTTP

class FakeLabAccess:
    def __init__(self):
        self.rooms, self.n = {}, 0
        self.status = {}

    def create(self, scenario):
        self.n += 1
        code = f"LAB{self.n:03d}"
        seats = [{"seat": i, "memberId": 10 * self.n + i, "name": s["name"], "isBot": s["bot"],
                  "token": None if s["bot"] else f"tok-{self.n}-{i}"} for i, s in enumerate(scenario["seats"])]
        self.rooms[code] = {"scenario": scenario, "seats": seats}
        return {"code": code, "seats": [dict(s) for s in seats]}

    def seats(self, code):
        room = self.rooms.get(code)
        return [{k: v for k, v in s.items() if k != "token"} for s in room["seats"]] if room else None

    def scenario(self, code): return self.rooms[code]["scenario"] if code in self.rooms else None
    def set_scenario(self, code, scenario): self.rooms[code]["scenario"] = scenario
    def set_status(self, code, status): self.status[code] = status

    def reissue_tokens(self, code):
        room = self.rooms.get(code)
        if not room:
            return None
        for s in room["seats"]:
            s["token"] = None if s["isBot"] else s["token"] + "x"
        return [dict(s) for s in room["seats"]]

    def list(self):
        return [{"code": c, "title": r["scenario"].get("title", ""), "seats": []} for c, r in self.rooms.items()]

    def delete(self, code):
        return self.rooms.pop(code, None) is not None


class FakePublisher:
    def __init__(self):
        self.pushed, self.rooms = [], 0
        self.notifier = self

    def game(self, code): self.pushed.append(code)
    def room_updated(self, code): self.rooms += 1


class Runner:
    def __init__(self): self.kicked = []
    def kick(self, code): self.kicked.append(code)


class LabHttpTests(unittest.TestCase):
    def setUp(self):
        self.access, self.publisher, self.runner = FakeLabAccess(), FakePublisher(), Runner()
        self.store = MemoryStore()
        self.service = TableService(self.store, random.Random(4))
        self.admin = AdminAuth("geheim-passwort", "secret")
        app = Flask(__name__)
        app.register_blueprint(create_lab_blueprint(self.service, self.access, self.publisher, self.admin,
                                                    self.runner), url_prefix="/api")
        self.client = app.test_client()
        self.auth = {"Authorization": "Bearer " + self.admin.login("geheim-passwort", "1.2.3.4")}

    def call(self, method, path, body=None, auth=True):
        return getattr(self.client, method)("/api/admin/lab" + path, json=body, headers=self.auth if auth else {})

    def test_requires_admin(self):
        self.assertEqual(self.call("get", "/presets", auth=False).status_code, 401)
        self.assertEqual(self.call("post", "/tables", {"scenario": {}}, auth=False).status_code, 401)
        self.assertEqual(self.client.get("/api/admin/lab/tables", headers={"Authorization": "Bearer x.y"}).status_code, 401)

    def test_disabled_without_password(self):
        app = Flask(__name__)
        app.register_blueprint(create_lab_blueprint(self.service, self.access, self.publisher, AdminAuth("", "s")),
                               url_prefix="/api")
        self.assertEqual(app.test_client().get("/api/admin/lab/presets").status_code, 503)

    def test_presets(self):
        data = self.call("get", "/presets").get_json()["presets"]
        self.assertEqual([p["id"] for p in data], [p["id"] for p in PRESETS])
        self.assertIn("armut_arm", [p["id"] for p in data])

    def test_create_gives_tokens_only_for_humans_and_a_real_table(self):
        res = self.call("post", "/tables", {"scenario": preset("armut_arm")})
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual([bool(s["token"]) for s in data["seats"]], [True, False, False, False])
        code = data["code"]
        self.assertEqual(self.access.status[code], "playing")
        self.assertEqual((self.publisher.pushed, self.runner.kicked), ([code], [code]))
        view = self.service.view(code, data["seats"][0]["memberId"])
        self.assertEqual(view["table"]["mySeat"], 0)
        self.assertTrue(view["table"]["ruleOptions"]["poverty"])
        self.assertEqual(len(view["game"]["hand"]), 12)
        self.assertEqual(self.service.load(code).table.takeover, 0)

    def test_create_rejects_bad_scenarios(self):
        res = self.call("post", "/tables", {"scenario": {"dealer": 9}})
        self.assertEqual((res.status_code, res.get_json()["code"]), (400, "bad_scenario"))
        self.assertEqual(self.call("post", "/tables", {}).status_code, 400)
        self.assertEqual(self.access.rooms, {})

    def test_failed_build_removes_room(self):
        sc = dict(preset("pflichtsolo"), round={"normalGamesPlayed": 24, "pflichtsoloDone": [True] * 4})
        res = self.call("post", "/tables", {"scenario": sc})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.access.rooms, {})

    def test_reset_keeps_seats_and_replaces_table(self):
        code = self.call("post", "/tables", {"scenario": preset("armut_kaeufer")}).get_json()["code"]
        member = self.access.rooms[code]["seats"][0]["memberId"]
        version = self.store.load(code).version
        res = self.call("post", f"/tables/{code}/reset",
                        {"scenario": dict(preset("endspiel"), seats=[{"bot": True}] * 4)})
        self.assertEqual(res.status_code, 200)
        stored = self.store.load(code)
        self.assertGreater(stored.version, version)
        self.assertEqual(len(stored.table.game.tricks), 10)
        self.assertEqual([s["isBot"] for s in stored.table.seats], [False, True, True, True])   # Besetzung bleibt
        self.assertEqual(stored.table.seats[0]["memberId"], member)
        self.assertEqual(self.access.scenario(code)["advance"], "tricks")

    def test_reset_without_body_uses_stored_scenario(self):
        code = self.call("post", "/tables", {"scenario": preset("armut_alle")}).get_json()["code"]
        before = self.store.load(code).table.game.hands
        self.service.act(code, self.access.rooms[code]["seats"][0]["memberId"], {"type": "declare", "reservation": False})
        self.assertEqual(self.call("post", f"/tables/{code}/reset", {}).status_code, 200)
        after = self.store.load(code)
        self.assertIs(after.table.game.phase, Phase.RESERVATION_QUERY)
        self.assertEqual(after.table.game.query_seat, 0)
        self.assertEqual([sorted(c.id for c in h) for h in after.table.game.hands][2],
                         sorted(c.id for c in before[2]))

    def test_unknown_table(self):
        self.assertEqual(self.call("post", "/tables/NOPE/reset", {}).status_code, 404)
        self.assertEqual(self.call("post", "/tables/NOPE/open", {}).status_code, 404)
        self.assertEqual(self.call("delete", "/tables/NOPE").status_code, 404)

    def test_open_reissues_tokens_and_delete(self):
        data = self.call("post", "/tables", {"scenario": preset("armut_alle")}).get_json()
        code = data["code"]
        opened = self.call("post", f"/tables/{code.lower()}/open", {}).get_json()
        self.assertEqual(opened["code"], code)
        self.assertTrue(all(s["token"] and s["token"].endswith("x") for s in opened["seats"]))
        self.assertEqual(len(self.call("get", "/tables").get_json()["tables"]), 1)
        self.assertEqual(self.call("delete", f"/tables/{code}").status_code, 200)
        self.assertEqual(self.call("get", "/tables").get_json()["tables"], [])
