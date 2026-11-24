"""Betreiber-Einstellungen der Bots: Katalog, Pruefung, Anwenden auf ``bots.TUNE``/Tempo und die HTTP-Routen."""
import copy
import unittest

from flask import Flask

from ..rules import loader  # noqa: F401
from app.community.admin_auth import AdminAuth
from app.community.stats import MemoryStats
from app.ops import bot_tuning as bt
from app.ops import errors as errlog
from app.ops import settings as site
from app.ops.api import OpsDeps, create_ops_blueprint
from app.table import bots, service


class Isolated(unittest.TestCase):
    """Stellt ``TUNE``, Tempo und die Zwischenspeicher nach jedem Test wieder her (globaler Zustand)."""

    def setUp(self):
        self._tune = copy.deepcopy(bots.TUNE)
        self._pace = dict(service.PACE)
        self.addCleanup(self._restore)

    def _restore(self):
        bots.TUNE.clear()
        bots.TUNE.update(self._tune)
        service.PACE.update(self._pace)
        bots._PIMC_CACHE.clear()
        bots._ANNOUNCE_CACHE.clear()


class CatalogTests(unittest.TestCase):
    def test_every_catalog_key_exists_in_tune_and_defaults_match(self):
        for item in bt.CATALOG:
            if item["key"] == "tempo":
                continue
            self.assertIn(item["key"], bots.TUNE_DEFAULTS, item["key"])
        d = bt.defaults()
        self.assertTrue(d["pimc_solo"] and d["pimc_poverty"] and d["pimc_wedding"] and d["pimc_public"])
        self.assertEqual((d["announce_p0"], d["announce_p1"], d["pimc_budget"], d["tempo"]), (75, 85, 160, "normal"))

    def test_every_item_has_text_group_and_valid_dependency(self):
        groups = {g["id"] for g in bt.GROUPS}
        keys = {i["key"] for i in bt.CATALOG}
        self.assertEqual(len(keys), len(bt.CATALOG))                       # keine doppelten Schluessel
        for item in bt.CATALOG:
            self.assertGreater(len(item["text"]), 30, item["key"])
            self.assertIn(item["group"], groups)
            if item["needs"]:
                self.assertIn(item["needs"]["key"], keys)
            if item["kind"] == "number":
                self.assertLessEqual(item["min"], bt.defaults()[item["key"]] if item["key"] != "tempo" else item["min"])
                self.assertGreaterEqual(item["max"], bt.defaults()[item["key"]])

    def test_every_tune_switch_in_the_code_is_either_listed_or_deliberately_internal(self):
        internal = {"pimc_tricks"}
        listed = {i["key"] for i in bt.CATALOG}
        self.assertEqual(set(bots.TUNE_DEFAULTS) - listed, internal)

    def test_normalize_is_tolerant(self):
        out = bt.normalize({"pimc_solo": "ja", "pimc_budget": 99999, "announce": "x", "announce_p0": 80, "unbekannt": 1, "tempo": "ruhig"})
        self.assertTrue(out["pimc_solo"])                                  # Unbrauchbares = Standard
        self.assertEqual((out["pimc_budget"], out["announce"], out["announce_p0"], out["tempo"]), (160, "pimc", 80, "ruhig"))
        self.assertNotIn("unbekannt", out)
        self.assertEqual(bt.normalize(None), bt.defaults())

    def test_validate_update_is_strict(self):
        cur = bt.defaults()
        bad = [{"values": {"unbekannt": 1}}, {"values": {"pimc_solo": 1}}, {"values": {"pimc_budget": 5}},
               {"values": {"pimc_budget": True}}, {"values": {"announce": "foo"}}, {"values": {"tempo": "turbo"}},
               {"values": {"announce_p0": 90, "announce_p1": 80}}, {"values": []}, [], {}]
        for raw in bad:
            with self.assertRaises(bt.BotTuningError, msg=str(raw)):
                bt.validate_update(raw, cur)
        out = bt.validate_update({"values": {"pimc_wedding": False}}, cur)    # Teilmenge: der Rest bleibt
        self.assertFalse(out["pimc_wedding"])
        self.assertTrue(out["pimc_solo"])


class ApplyTests(Isolated):
    def test_apply_sets_tune_converts_percent_and_clears_caches(self):
        bots._PIMC_CACHE["x"] = "y"
        bots._ANNOUNCE_CACHE["x"] = 1
        values = bt.defaults() | {"pimc_poverty": False, "announce_p0": 80, "announce_p1": 90, "pimc_budget": 200, "infer_w": 30,
                                  "announce": "legacy", "lead_trump": True}
        bt.apply(values)
        self.assertFalse(bots.TUNE["pimc_poverty"])
        self.assertEqual((bots.TUNE["announce_p0"], bots.TUNE["announce_p1"], bots.TUNE["infer_w"]), (0.8, 0.9, 0.3))
        self.assertEqual((bots.TUNE["pimc_budget"], bots.TUNE["announce"], bots.TUNE["lead_trump"]), (200, "legacy", True))
        self.assertEqual((bots._PIMC_CACHE, bots._ANNOUNCE_CACHE), ({}, {}))

    def test_defaults_applied_reproduce_the_code_defaults(self):
        bt.apply(bt.defaults())
        for key, value in bots.TUNE_DEFAULTS.items():
            if key != "pimc_tricks":
                self.assertEqual(bots.TUNE[key], value, key)

    def test_tempo_scales_the_pending_delay(self):
        bt.apply(bt.defaults() | {"tempo": "sehr_ruhig"})
        self.assertEqual(service.PACE["factor"], 2.0)
        bt.apply(bt.defaults() | {"tempo": "schnell"})
        self.assertEqual(service.PACE["factor"], 0.6)
        bt.apply(bt.defaults())
        self.assertEqual(service.PACE["factor"], 1.0)

    def test_tempo_changes_the_real_waiting_times(self):
        import random
        from app.rules import normalize_settings, profile_from_settings
        from app.table import MemoryStore
        svc = service.TableService(MemoryStore(), rng=random.Random(3), paced=True)
        svc.start("R1", [{"memberId": i + 1, "name": f"S{i}", "isBot": True} for i in range(4)], profile_from_settings(normalize_settings({})))
        base = svc.pending_delay("R1")                                          # Vorbehaltsabfrage: feste Zeit
        self.assertEqual(base, service.DECLARE)
        bt.apply(bt.defaults() | {"tempo": "ruhig"})
        self.assertAlmostEqual(svc.pending_delay("R1"), service.DECLARE * 1.5)
        bt.apply(bt.defaults() | {"tempo": "schnell"})
        self.assertAlmostEqual(svc.pending_delay("R1"), service.DECLARE * 0.6)

    def test_switch_changes_what_the_bot_does(self):
        """Ein im Betreiber-Backend ausgeschalteter Spielart-Schalter laesst die Kartenwahl bei der Heuristik (``None``), an rechnet er."""
        from .test_bots_pimc_kinds import first_choice, solo_game, SOLO_TYPES
        game = solo_game(SOLO_TYPES[0])
        bt.apply(bt.defaults() | {"pimc": True, "pimc_budget": 40})
        self.assertIsNotNone(first_choice(game, game.turn)[0])
        bt.apply(bt.defaults() | {"pimc": True, "pimc_solo": False})          # apply leert auch die Zwischenspeicher
        self.assertIsNone(first_choice(game, game.turn)[0])
        bt.apply(bt.defaults() | {"pimc": False})                              # Hauptschalter: ``choose_card`` ruft das Durchrechnen gar nicht erst
        self.assertFalse(bots.TUNE["pimc"])


class FakeAdminTuning:
    def __init__(self):
        self.doc = bt.normalize({})

    def get(self):
        return copy.deepcopy(self.doc)

    def put(self, data):
        self.doc = bt.normalize(data)
        return self.get()

    def reset(self):
        return self.put({})


class BotsHttpTests(Isolated):
    def setUp(self):
        super().setUp()
        self.admin = AdminAuth("geheimes-passwort", "secret")
        self.store = FakeAdminTuning()
        deps = OpsDeps(admin=self.admin, settings=site.MemorySettings(), live=None, errors=errlog.MemoryErrors(), stats=MemoryStats(),
                       system=lambda: {}, notify=lambda *a: None, bots=self.store)
        app = Flask(__name__)
        app.register_blueprint(create_ops_blueprint(deps), url_prefix="/api")
        self.client = app.test_client()
        self.h = {"Authorization": f"Bearer {self.admin.login('geheimes-passwort', 'ip')}"}

    def test_routes_need_login(self):
        for method, path in (("get", "/api/admin/bots"), ("put", "/api/admin/bots"), ("post", "/api/admin/bots/reset")):
            self.assertEqual(getattr(self.client, method)(path).status_code, 401, path)

    def test_get_returns_values_and_schema(self):
        data = self.client.get("/api/admin/bots", headers=self.h).get_json()
        self.assertEqual(data["values"], bt.defaults())
        self.assertEqual({i["key"] for i in data["items"]}, {i["key"] for i in bt.CATALOG})
        self.assertTrue(data["groups"] and data["defaults"])

    def test_not_part_of_the_public_site_settings(self):
        self.assertNotIn("pimc_solo", self.client.get("/api/site-settings").get_json())

    def test_put_saves_applies_and_reset_restores(self):
        r = self.client.put("/api/admin/bots", headers=self.h, json={"values": {"pimc_poverty": False, "announce_p0": 82}})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()["values"]["pimc_poverty"])
        self.assertFalse(bots.TUNE["pimc_poverty"])
        self.assertEqual(bots.TUNE["announce_p0"], 0.82)
        self.assertFalse(self.store.doc["pimc_poverty"])                            # gespeichert
        self.client.put("/api/admin/bots", headers=self.h, json={"values": {"pimc_solo": False}})
        self.assertFalse(self.store.doc["pimc_poverty"] or self.store.doc["pimc_solo"])  # Teilmengen ueberschreiben nicht den Rest
        r = self.client.post("/api/admin/bots/reset", headers=self.h)
        self.assertEqual(r.get_json()["values"], bt.defaults())
        self.assertTrue(bots.TUNE["pimc_poverty"] and bots.TUNE["pimc_solo"])

    def test_invalid_input_is_rejected_and_changes_nothing(self):
        before = dict(bots.TUNE)
        for payload in ({"values": {"pimc_budget": 1}}, {"values": {"x": 1}}, {"values": {"announce_p0": 95, "announce_p1": 60}}, {}):
            r = self.client.put("/api/admin/bots", headers=self.h, json=payload)
            self.assertEqual((r.status_code, r.get_json()["code"]), (400, "bad_bot_tuning"), payload)
        self.assertEqual(bots.TUNE, before)
        self.assertEqual(self.store.doc, bt.defaults())


if __name__ == "__main__":
    unittest.main()
