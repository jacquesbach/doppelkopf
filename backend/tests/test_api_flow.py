"""Ende-zu-Ende-Test ueber die echte App (Flask + SQLAlchemy + Raeume + Spielschicht), ohne Browser.

Benoetigt die Pakete aus requirements.txt (pytest oder unittest). Er legt einen Raum an, fuellt mit
Bots, startet eine Runde mit Hausregeln, spielt sie komplett als einziger Mensch durch und prueft
Rechte, Datenschutz und Raumstatus. Laeuft gegen eine SQLite-Datenbank im Arbeitsspeicher.
"""
import random
import unittest

from app import create_app, socketio


class ApiFlow(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True, "PACED_BOTS": False})
        self.client = self.app.test_client()

    def call(self, method, path, body=None, token=None):
        headers = {"X-Session-Token": token} if token else {}
        return getattr(self.client, method)(f"/api{path}", json=body, headers=headers) if body is not None \
            else getattr(self.client, method)(f"/api{path}", headers=headers)

    def new_room(self, settings=None):
        res = self.call("post", "/rooms", {"name": "Host", "settings": settings or {}})
        self.assertEqual(res.status_code, 201, res.get_json())
        data = res.get_json()
        return data["room"]["code"], data["token"], data

    def test_invalid_settings_are_rejected_on_create(self):
        res = self.call("post", "/rooms", {"name": "Host", "settings": {"gibt_es_nicht": True}})
        self.assertEqual(res.status_code, 400)

    def test_room_exposes_settings_and_profile(self):
        code, token, data = self.new_room({"schweinchen": True})
        self.assertTrue(data["room"]["settings"]["schweinchen"])
        self.assertEqual(data["room"]["profileId"], "custom")
        _, _, plain = self.new_room()
        self.assertEqual(plain["room"]["profileId"], "ddv_tsr_2026")

    def test_bots_cannot_be_impersonated(self):
        code, token, _ = self.new_room()
        self.assertEqual(self.call("post", f"/rooms/{code}/bots", {"token": token}).status_code, 200)
        for index in (2, 3, 4):                       # fruehere, aus dem Raumcode ableitbare Bot-Tokens
            guess = f"bot:{code}:{index}"
            self.assertEqual(self.call("get", f"/rooms/{code}/game", token=guess).status_code, 403)
            self.assertEqual(self.call("post", f"/rooms/{code}/action",
                                       {"type": "declare", "reservation": False, "token": guess}).status_code, 403)

    def test_full_round_over_http(self):
        code, token, _ = self.new_room({"schweinchen": True, "bock_120": True})
        spectator = self.call("post", f"/rooms/{code}/join", {"name": "Zuschauer", "role": "spectator"}).get_json()
        self.assertEqual(self.call("post", f"/rooms/{code}/bots", {"token": token}).status_code, 200)
        self.assertEqual(self.call("post", f"/rooms/{code}/start", {"token": spectator["token"]}).status_code, 403)
        start = self.call("post", f"/rooms/{code}/start", {"token": token})
        self.assertEqual(start.status_code, 201, start.get_json())
        self.assertEqual(self.call("post", f"/rooms/{code}/settings", {"token": token, "settings": {}}).status_code, 409)

        view = self.call("get", f"/rooms/{code}/game", token=spectator["token"]).get_json()
        self.assertNotIn("hand", view["game"])
        rng, steps = random.Random(3), 0
        while True:
            view = self.call("get", f"/rooms/{code}/game", token=token).get_json()
            if view["table"]["finished"]:
                break
            game = view["game"]
            if game["phase"] == "finished":
                self.assertEqual(self.call("post", f"/rooms/{code}/next", {}, token=token).status_code, 200)
                continue
            acts = game["legalActions"]
            self.assertTrue(acts)
            a = next((x for x in acts if x["type"] != "announce"), acts[0])
            payload = {"declare": {"type": "declare", "reservation": rng.random() < 0.1},
                       "resolve": {"type": "resolve", "accept": rng.random() < 0.5},
                       "baptize": {"type": "baptize", "choice": rng.choice(a.get("choices", ["solo_queens"]))},
                       "play_card": {"type": "play_card", "cardId": rng.choice(a.get("cards", [""]))},
                       "announce": {"type": "announce", "level": a.get("levels", [0])[0]},
                       "schweinchen": {"type": "schweinchen"}}[a["type"]]
            res = self.call("post", f"/rooms/{code}/action",
                            {**payload, "expectedVersion": view["version"], "actionId": f"s{steps}"}, token=token)
            self.assertEqual(res.status_code, 200, res.get_json())
            steps += 1
            self.assertLess(steps, 4000)

        self.assertEqual(self.call("get", f"/rooms/{code}").get_json()["room"]["status"], "finished")
        games = self.call("get", f"/rooms/{code}/history", token=token).get_json()["games"]
        self.assertEqual(len(games), view["table"]["gameNumber"])
        self.assertEqual(sum(view["table"]["round"]["totals"]), 0)
        if hasattr(socketio, "emitted"):                           # nur mit Test-Doppel von Socket.IO pruefbar
            for event, payload, target in socketio.emitted:
                if event == "game:state" and target == f"member:{spectator['memberId']}":
                    self.assertNotIn("hand", payload["game"])


if __name__ == "__main__":
    unittest.main()
