"""Sicherheitsgrenze: Niemand sieht fremde Handkarten oder verdeckte Tauschkarten.

Ueber ganze Spiele (mit Armut, Vorbehalten, Bot-Uebernahme) wird nach JEDER Aktion fuer jedes Mitglied, einen Zuschauer und
einen Unbekannten die serialisierte Sicht (so geht sie ueber HTTP und Socket) nach Karten durchsucht, die dem Betrachter
nicht gehoeren duerfen: Karten in fremden Haenden und verdeckte Armut-Karten.
"""
import json
import random
import unittest

from ..rules import loader  # noqa: F401
from app.game_api import Auth, Publisher, create_game_blueprint  # noqa: F401
from app.rules import Phase, RuleOptions, make_profile, DeckVariant
from app.rules.game import legal_actions
from app.table import MemoryStore, TableService, view_for

from .test_bots_pacing import ALL_OPTIONS

MEMBERS = [10, 11, 12, 13]
VIEWERS = [*MEMBERS, None, 999]            # None = Zuschauer ohne Mitgliedschaft, 999 = unbekannt
HUMANS = [{"memberId": m, "name": f"P{i}", "isBot": False} for i, m in enumerate(MEMBERS)]


def profile():
    from app.rules import ddv_profile
    return ddv_profile()


def key(card_dict):
    return json.dumps(card_dict, sort_keys=True)


def hidden_from(table, seat):
    """Karten, die der Sitz `seat` (None = Zuschauer) jetzt nicht kennen darf."""
    game = table.game
    hidden = set()
    for s, hand in enumerate(game.hands):
        if s != seat:
            hidden |= {key(c.to_dict()) for c in hand}
    if game.poverty_seat is not None and seat != game.poverty_seat:
        hidden |= {key(c.to_dict()) for c in game.poverty_cards}
    return hidden


def own(table, seat):
    return set() if seat is None else {key(c.to_dict()) for c in table.game.hands[seat]}


def random_payload(table, seat, rng):
    acts = legal_actions(table.game, seat)
    if not acts:
        return None
    a = rng.choice([x for x in acts if x["type"] != "announce"] or acts)
    t = a["type"]
    return {"declare": lambda: {"type": "declare", "reservation": rng.random() < 0.3},
            "resolve": lambda: {"type": "resolve", "accept": rng.random() < 0.5},
            "baptize": lambda: {"type": "baptize", "choice": rng.choice(a.get("choices", ["solo_queens"]))},
            "play_card": lambda: {"type": "play_card", "cardId": rng.choice(a.get("cards", [""]))},
            "announce": lambda: {"type": "announce", "level": rng.choice(a.get("levels", [0]))},
            "schweinchen": lambda: {"type": "schweinchen"},
            "poverty_pass": lambda: {"type": "poverty_pass", "cardIds": rng.sample(a["cards"], 3)},
            "poverty_offer": lambda: {"type": "poverty_offer", "accept": rng.random() < 0.5},
            "poverty_return": lambda: {"type": "poverty_return", "cardIds": rng.sample(a["cards"], 3)}}[t]()


class ViewLeakTests(unittest.TestCase):
    def assert_no_leak(self, svc, code, note=""):
        stored = svc.load(code)
        table = stored.table
        if table.game.phase is Phase.FINISHED:
            return                                    # nach Spielende liegt alles offen (Stiche zum Nachsehen)
        for viewer in VIEWERS:
            seat = table.seat_of(viewer) if viewer is not None else None
            text = json.dumps(view_for(table, viewer, stored.version))           # genau das geht ueber HTTP/Socket
            forbidden = hidden_from(table, seat) - own(table, seat)
            for card in forbidden:
                self.assertNotIn(card, text, f"{note}: Betrachter {viewer} sieht eine verdeckte Karte ({table.game.phase.value})")

    def play(self, seed, steps=1500, away_after=None, opts=ALL_OPTIONS):
        rng = random.Random(seed)
        svc = TableService(MemoryStore(), rng)
        prof = make_profile(DeckVariant.WITH_NINES, opts) if hasattr(DeckVariant, "WITH_NINES") else profile()
        svc.start("LEAK01", HUMANS, prof)
        poverty_seen = set()
        for n in range(steps):
            stored = svc.load("LEAK01")
            table = stored.table
            if table.finished:
                break
            if table.game.phase is Phase.FINISHED:
                svc.next_game("LEAK01", 10)
                self.assert_no_leak(svc, "LEAK01", f"seed {seed} neues Spiel")
                continue
            if away_after is not None and n == away_after:
                svc.set_away("LEAK01", 10, True)                     # Bot uebernimmt Sitz 0
                self.assert_no_leak(svc, "LEAK01", f"seed {seed} nach Bot-Uebernahme")
                stored = svc.load("LEAK01")
                table = stored.table
            seats = [s for s in range(4) if legal_actions(table.game, s)]
            self.assertTrue(seats, f"niemand am Zug in {table.game.phase}")
            seat = rng.choice(seats)
            payload = random_payload(table, seat, rng)
            poverty_seen.add(table.game.phase.value)
            svc.act("LEAK01", MEMBERS[seat], {**payload, "expectedVersion": stored.version, "actionId": f"a{n}"})
            self.assert_no_leak(svc, "LEAK01", f"seed {seed} Schritt {n}")
        return poverty_seen

    def test_whole_games_never_leak(self):
        phases = set()
        for seed in range(3):
            phases |= self.play(seed)
        self.assertIn("playing", phases)
        self.assertIn("reservation_query", phases)

    def test_poverty_cards_stay_hidden(self):
        phases = set()
        for seed in range(60):
            phases |= self.play(seed, steps=400)
            if "poverty_offer" in phases:
                break
        self.assertIn("poverty_offer", phases, "Szenario hat keine Armut erreicht - Seeds/Optionen anpassen")

    def test_bot_takeover_does_not_leak(self):
        for seed in (1, 2, 3):
            self.play(seed, steps=300, away_after=5)

    def test_spectator_view_is_free_of_player_data(self):
        svc = TableService(MemoryStore(), random.Random(5))
        svc.start("LEAK02", HUMANS, profile())
        stored = svc.load("LEAK02")
        view = view_for(stored.table, None, stored.version)
        self.assertEqual(view["game"]["role"], "spectator")
        for forbidden in ("hand", "legalActions", "myParty", "povertyPassed", "povertyGot"):
            self.assertNotIn(forbidden, view["game"])

    def test_publisher_sends_each_member_only_their_own_hand(self):
        class Access:
            def member_ids(self, code): return [*MEMBERS, 77]            # 77 = Zuschauer

        class Notifier:
            def __init__(self): self.views = None
            def game_updated(self, code, views): self.views = views

        svc = TableService(MemoryStore(), random.Random(2))
        svc.start("LEAK03", HUMANS, profile())
        notifier = Notifier()
        Publisher(svc, Access(), notifier).game("LEAK03")
        table = svc.load("LEAK03").table
        self.assertEqual(set(notifier.views), {*MEMBERS, 77})
        for member, view in notifier.views.items():
            if member == 77:
                self.assertNotIn("hand", view["game"])
                continue
            seat = MEMBERS.index(member)
            mine = {key(c) for c in view["game"]["hand"]}
            self.assertEqual(mine, own(table, seat))
            text = json.dumps(view)
            for card in hidden_from(table, seat):
                self.assertNotIn(card, text)


if __name__ == "__main__":
    unittest.main()
