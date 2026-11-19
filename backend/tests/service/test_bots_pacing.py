"""Bot-KI (Selbstspiel, Staerke, Parteikenntnis) und getakteter Botbetrieb (Pausen, Hold, Platzuebergabe)."""
import random
import unittest

from ..rules import loader  # noqa: F401
from app.rules import (Announce, Baptize, Declare, DeclareSchweinchen, DeckVariant, Phase, PlayCard, Resolve,
                       RuleOptions, apply_action, bot_view, make_profile, new_round, start_next_game)
from app.rules.cards import Card
from app.rules.dealing import shuffled_deck
from app.rules.tricks import Play
from app.table import BotRunner, MemoryStore, TableService
from app.table.bots import choose_action, hand_strength, known_parties
from app.table.service import THINK, TRICK_PAUSE

ALL_OPTIONS = RuleOptions(mandatory_announcements=True, solo_leads=True, karlchen_caught=True, schweinchen=True,
                          poverty=True, bock_heart_trick=True, bock_zero_game=True, bock_120=True, second_dulle_wins=True)


def baseline_action(view):
    """Alte Grundstrategie als Vergleich: nie Vorbehalt/Ansage, billigste erlaubte Karte."""
    acts = {a["type"]: a for a in view["legalActions"]}
    seat = view["seat"]
    if "declare" in acts:
        return Declare(seat, False)
    if "resolve" in acts:
        return Resolve(seat, False)
    if "baptize" in acts:
        return Baptize(seat, next(c for c in acts["baptize"]["choices"] if c != "wedding"))
    if view["turn"] == seat:
        if "schweinchen" in acts:
            return DeclareSchweinchen(seat)
        if view["mandatoryAnnouncementSeat"] == seat and "announce" in acts:
            return Announce(seat, acts["announce"]["levels"][0])
        if "play_card" in acts:
            return PlayCard(seat, min(acts["play_card"]["cards"], key=lambda c: (Card.from_id(c).value, c)))
    return None


def play_game(profile, rng, smart):
    rnd = new_round(profile)
    game = start_next_game(rnd, profile, shuffled_deck(profile.deck_variant, rng))
    for _ in range(400):
        if game.phase is Phase.FINISHED:
            return game
        for seat in range(4):
            action = (choose_action if seat in smart else baseline_action)(bot_view(game, seat))
            if action is not None:
                apply_action(game, action)
                break
        else:
            raise AssertionError(f"Niemand kann handeln: {game.phase}")
    raise AssertionError("Spiel terminiert nicht")


class BotPlay(unittest.TestCase):
    def test_self_play_completes_for_both_decks_with_all_options(self):
        rng = random.Random(11)
        for variant in (DeckVariant.WITH_NINES, DeckVariant.WITHOUT_NINES):
            for options in (RuleOptions(), ALL_OPTIONS):
                profile = make_profile(variant, options)
                for _ in range(40):
                    self.assertIs(play_game(profile, rng, {0, 1, 2, 3}).phase, Phase.FINISHED)

    def test_smart_bots_beat_the_old_baseline(self):
        rng = random.Random(7)
        profile = make_profile(DeckVariant.WITH_NINES)
        smart_total = 0
        for i in range(160):
            smart = {0, 2} if i % 2 == 0 else {1, 3}
            deltas = play_game(profile, rng, smart).score.seat_deltas
            smart_total += sum(deltas[s] for s in smart) - sum(deltas[s] for s in range(4) if s not in smart)
        self.assertGreater(smart_total, 100)

    def test_strong_hand_announces_weak_hand_does_not(self):
        rng = random.Random(5)
        profile = make_profile(DeckVariant.WITH_NINES)
        strong = weak = None
        for _ in range(400):
            game = start_next_game(new_round(profile), profile, shuffled_deck(profile.deck_variant, rng))
            for seat in range(4):                       # Vorbehaltsrunde: alle gesund
                if game.phase is Phase.RESERVATION_QUERY:
                    apply_action(game, Declare(game.query_seat, False))
            scores = [hand_strength(bot_view(game, s)) for s in range(4)]
            if game.phase is Phase.PLAYING and max(scores) >= 17 and strong is None:
                strong = (game, scores.index(max(scores)))
            if game.phase is Phase.PLAYING and max(scores) <= 12 and weak is None:
                weak = (game, scores.index(max(scores)))
        for (game, seat), expected in ((strong, True), (weak, False)):
            action = choose_action(bot_view(game, seat))
            self.assertEqual(isinstance(action, Announce), expected)

    def test_known_parties_infers_from_counts_and_queen_of_clubs(self):
        view = {"seat": 0, "myParty": "kontra", "gameType": "normal", "clarified": [None, "re", None, None]}
        known = known_parties(view, [Play(2, Card.from_id("Q-♣-0"))])
        self.assertEqual([known[s] for s in range(4)], ["kontra", "re", "re", "kontra"])   # Rest = Partner
        solo = {"seat": 1, "myParty": "kontra", "gameType": "solo_queens", "soloSeat": 3,
                "clarified": [None] * 4}
        self.assertEqual([known_parties(solo, [])[s] for s in range(4)], ["kontra", "kontra", "kontra", "re"])


SEATS = [{"memberId": 10 + i, "name": f"P{i}", "isBot": i != 0} for i in range(4)]


def make_service(seed=3):
    return TableService(MemoryStore(), random.Random(seed), paced=True)


def human_play(svc, code="ABC123", member=10):
    """Menschlicher Zug: erste erlaubte Karte bzw. Vorbehalt 'gesund'."""
    stored = svc.load(code)
    view = svc.view(code, member)["game"]
    acts = {a["type"]: a for a in view["legalActions"]}
    if "declare" in acts:
        payload = {"type": "declare", "reservation": False}
    elif "resolve" in acts:
        payload = {"type": "resolve", "accept": False}
    elif "baptize" in acts:
        payload = {"type": "baptize", "choice": acts["baptize"]["choices"][-1]}
    elif "play_card" in acts:
        payload = {"type": "play_card", "cardId": acts["play_card"]["cards"][0]}
    else:
        return None
    return svc.act(code, member, {**payload, "expectedVersion": stored.version})


class PacedBots(unittest.TestCase):
    def test_bots_do_not_move_inside_the_request(self):
        svc = make_service()
        svc.start("ABC123", SEATS, make_profile(DeckVariant.WITH_NINES))
        table = svc.load("ABC123").table
        self.assertEqual(len(table.game.current_trick), 0)
        self.assertIsNotNone(svc.pending_delay("ABC123") or svc.waiting_on("ABC123"))

    def test_runner_plays_one_step_at_a_time_with_pauses_and_pushes_each_step(self):
        svc = make_service()
        svc.start("ABC123", SEATS, make_profile(DeckVariant.WITH_NINES))
        sleeps, pushed = [], []
        runner = BotRunner(svc, on_step=lambda code, o: pushed.append(o.version), sleep=sleeps.append,
                           spawn=lambda fn, *a: fn(*a))
        # bis der Mensch dran ist
        runner.kick("ABC123")
        self.assertTrue(pushed)
        self.assertEqual(pushed, sorted(set(pushed)))                    # jeder Schritt = eigene Version
        self.assertTrue(all(0.5 <= s for s in sleeps))
        out = None
        for _ in range(200):                                              # Mensch spielt, Bots folgen getaktet
            table = svc.load("ABC123").table
            if table.game.phase is Phase.FINISHED:
                break
            if table.holding:                                             # Spiel gegen Bots: "Naechster Stich"
                svc.release("ABC123", 10)
            else:
                human_play(svc)
            runner.kick("ABC123")
        self.assertIn(TRICK_PAUSE, sleeps)                               # nach vollen Stichen laengere Pause
        self.assertTrue(any(THINK[0] <= s <= THINK[1] for s in sleeps))
        # der Tisch wurde Schritt fuer Schritt gespielt (viele Versionen)
        self.assertGreater(svc.load("ABC123").version, 30)

    def test_manual_continue_holds_bots_after_each_trick(self):
        svc = make_service(seed=9)
        svc.start("ABC123", SEATS, make_profile(DeckVariant.WITH_NINES))
        runner = BotRunner(svc, on_step=lambda *a: None, sleep=lambda s: None, spawn=lambda fn, *a: fn(*a))
        runner.kick("ABC123")
        held = 0
        for _ in range(300):
            table = svc.load("ABC123").table
            if table.game.phase is Phase.FINISHED:
                break
            if table.holding:
                held += 1
                self.assertIsNone(svc.pending_delay("ABC123"))           # Bots warten
                self.assertEqual(len(table.game.current_trick), 0)
                svc.release("ABC123", 10)
                runner.kick("ABC123")
                continue
            self.assertIsNotNone(human_play(svc))
            runner.kick("ABC123")
        self.assertGreater(held, 3)

    def test_no_hold_with_two_humans(self):
        seats = [{"memberId": 10 + i, "name": f"P{i}", "isBot": i > 1} for i in range(4)]
        svc = make_service()
        svc.start("ABC123", seats, make_profile(DeckVariant.WITH_NINES))
        self.assertFalse(svc.load("ABC123").table.manual_continue)

    def test_away_seat_is_played_by_bot_and_returns_on_action(self):
        seats = [{"memberId": 10 + i, "name": f"P{i}", "isBot": i > 1} for i in range(4)]   # zwei Menschen
        svc = make_service()
        svc.start("ABC123", seats, make_profile(DeckVariant.WITH_NINES))
        runner = BotRunner(svc, on_step=lambda *a: None, sleep=lambda s: None, spawn=lambda fn, *a: fn(*a))
        svc.set_away("ABC123", 11, True)
        view = svc.view("ABC123", 10)
        self.assertTrue(view["table"]["seats"][1]["autoplay"])
        # Spieler 10 spielt weiter; Sitz 1 (weg) wird von der KI bedient, es blockiert nichts
        for _ in range(400):
            if svc.load("ABC123").table.game.phase is Phase.FINISHED:
                break
            runner.kick("ABC123")
            if human_play(svc) is None and svc.load("ABC123").table.game.phase is not Phase.FINISHED:
                self.fail("Spiel haengt")
        self.assertIs(svc.load("ABC123").table.game.phase, Phase.FINISHED)
        # zurueckholen
        out = svc.set_away("ABC123", 11, False)
        self.assertFalse(svc.view("ABC123", 11)["table"]["seats"][1]["autoplay"])
        self.assertIsNotNone(out)

    def test_runner_refreshes_db_view_before_reading(self):
        """Regression: die Schleife lebt in einer langen DB-Sitzung und muss vor jedem Lesen neu laden."""
        seats = [{"memberId": 10 + i, "name": f"P{i}", "isBot": i > 1} for i in range(4)]   # zwei Menschen: Wartschleife laeuft
        svc = make_service()
        svc.start("ABC123", seats, make_profile(DeckVariant.WITH_NINES))
        calls = []
        runner = BotRunner(svc, on_step=lambda *a: None, sleep=lambda s: None, spawn=lambda fn, *a: fn(*a),
                           watch_limit=6.0, refresh=lambda: calls.append(1))
        runner.kick("ABC123")
        self.assertGreater(len(calls), 3)    # je Schleifendurchlauf und je Wartetakt


if __name__ == "__main__":
    unittest.main()
