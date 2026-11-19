"""Hausregel "Armut": Anmeldung als Vorbehalt, Karten abgeben, Kaeufer fragen, Rueckgabe, Wertung, Datenschutz."""
import json
import random
import unittest

from . import loader  # noqa: F401
from app.rules.cards import card
from app.rules.errors import RuleViolation
from app.rules.game import (Baptize, GameKind, GameState, Phase, PlayCard, PovertyOffer, PovertyPass, PovertyReturn,
                             Resolve, apply_action, can_declare_poverty, legal_actions, player_view, public_events,
                             spectator_view)
from app.rules.options import RuleOptions
from app.rules.profile import make_profile
from app.rules.round_rules import new_round, record_game
from app.rules.trump import GameType

from .fixtures import WITH, auto_play, declare_all, play, rig, with_options
from app.rules.game import new_game

# Geber = Sitz 3. Sitz 2 ist arm (Q♣, J♦, 9♦ = 3 Truempfe), Sitz 3 hat 9 Truempfe, Sitz 0 acht, Sitz 1 sechs.
POVERTY_HANDS = {
    0: "Q♥ Q♦ J♠ J♥ A♦ 10♦ K♦ 9♦ 10♣ A♠ A♥ 9♥",
    1: "Q♦ J♠ J♥ J♦ 10♦ K♦ K♣ 10♠ K♠ 9♠ K♥ 9♥",
    2: "Q♣ J♦ 9♦ A♣ A♣ 10♣ K♣ A♠ 10♠ K♠ A♥ K♥",
    3: "10♥ 10♥ Q♣ Q♠ Q♠ Q♥ J♣ J♣ A♦ 9♣ 9♣ 9♠",
}
POOR, BUYER = 2, 3


def poverty_game(**options):
    """Spiel mit eingeschalteter Armut, Sitz 2 hat Vorbehalt angemeldet und die Armut getauft."""
    profile = with_options(poverty=True, **options)
    s = new_game(profile, rig(POVERTY_HANDS, 3, WITH), 3)
    declare_all(s, reservations={POOR})
    return s


def ids(state, seat, *texts):
    """Karten-IDs der Hand von ``seat`` zu Kurzschreibweisen wie ``Q♣`` (je Text eine Karte)."""
    hand, taken, out = list(state.hands[seat]), set(), []
    for t in texts:
        c = next(x for x in hand if x.face == card(t).face and x.id not in taken)
        taken.add(c.id)
        out.append(c.id)
    return tuple(out)


def to_pass_phase(**options):
    s = poverty_game(**options)
    apply_action(s, Baptize(POOR, "poverty"))
    return s


def to_offer_phase():
    s = to_pass_phase()
    apply_action(s, PovertyPass(POOR, ids(s, POOR, "Q♣", "J♦", "9♦")))
    return s


class PovertyAnnouncementTests(unittest.TestCase):
    def test_option_is_off_by_default(self):
        self.assertFalse(RuleOptions().poverty)
        self.assertTrue(RuleOptions().is_ddv_default)
        s = new_game(make_profile(WITH), rig(POVERTY_HANDS, 3, WITH), 3)
        declare_all(s, reservations={POOR})
        self.assertNotIn("poverty", legal_actions(s, POOR)[0]["choices"])
        with self.assertRaises(RuleViolation) as cm:
            apply_action(s, Baptize(POOR, "poverty"))
        self.assertEqual(cm.exception.code, "poverty_not_allowed")

    def test_offered_only_with_at_most_three_trumps(self):
        s = poverty_game()
        self.assertIn("poverty", legal_actions(s, POOR)[0]["choices"])
        self.assertTrue(can_declare_poverty(s, POOR))
        self.assertFalse(can_declare_poverty(s, BUYER))          # 9 Truempfe
        s2 = new_game(with_options(poverty=True), rig(POVERTY_HANDS, 3, WITH), 3)
        declare_all(s2, reservations={BUYER})
        self.assertNotIn("poverty", legal_actions(s2, BUYER)[0]["choices"])
        with self.assertRaises(RuleViolation):
            apply_action(s2, Baptize(BUYER, "poverty"))

    def test_four_trumps_is_too_many(self):
        hands = dict(POVERTY_HANDS)
        hands[2] = "Q♣ J♦ 9♦ J♣ A♣ 10♣ K♣ A♠ 10♠ K♠ A♥ K♥"       # J♣ statt A♣: 4 Truempfe
        hands[3] = POVERTY_HANDS[3].replace("J♣ J♣", "J♣ A♣")
        s = new_game(with_options(poverty=True), rig(hands, 3, WITH), 3)
        declare_all(s, reservations={POOR})
        self.assertFalse(can_declare_poverty(s, POOR))
        self.assertNotIn("poverty", legal_actions(s, POOR)[0]["choices"])

    def test_dulle_option_changes_the_trump_count(self):
        hands = dict(POVERTY_HANDS)
        hands[2] = "Q♣ 10♥ 9♦ J♦ A♣ A♣ K♣ A♠ 10♠ K♠ A♥ K♥"        # mit Dulle 4 Truempfe, ohne Dulle 3
        hands[3] = "10♥ Q♣ Q♠ Q♠ Q♥ J♣ J♣ A♦ 10♣ 9♣ 9♣ 9♠"
        s = new_game(with_options(poverty=True), rig(hands, 3, WITH), 3)
        self.assertFalse(can_declare_poverty(s, POOR))
        s = new_game(with_options(poverty=True, dulle=False), rig(hands, 3, WITH, ), 3)
        self.assertTrue(can_declare_poverty(s, POOR))

    def test_poverty_is_announced_publicly(self):
        s = to_pass_phase()
        self.assertEqual(s.phase, Phase.POVERTY_PASS)
        self.assertEqual(s.poverty_seat, POOR)
        types = [e["type"] for e in public_events(s)]
        self.assertIn("poverty", types)
        self.assertEqual(spectator_view(s)["poverty"], {"seat": POOR, "buyer": None, "offerSeat": None})

    def test_poverty_is_not_possible_as_pflichtsolo_baptism(self):
        profile = with_options(poverty=True)
        s = new_game(profile, rig(POVERTY_HANDS, 3, WITH), 3, forced_solo_seat=POOR)
        self.assertNotIn("poverty", legal_actions(s, POOR)[0]["choices"])


class PovertyFlowTests(unittest.TestCase):
    def test_pass_requires_exactly_three_own_cards(self):
        s = to_pass_phase()
        self.assertEqual(legal_actions(s, POOR)[0]["type"], "poverty_pass")
        self.assertEqual(legal_actions(s, POOR)[0]["count"], 3)
        before = json.dumps(s.to_dict(), sort_keys=True)
        mine = ids(s, POOR, "Q♣", "J♦", "9♦", "A♣")
        for bad in (mine[:2], mine, (mine[0], mine[0], mine[1]), ("A-♣-0", "9-♣-0", "9-♣-1")):
            with self.assertRaises(RuleViolation, msg=str(bad)):
                apply_action(s, PovertyPass(POOR, bad))
        with self.assertRaises(RuleViolation) as cm:                 # nicht der Arme
            apply_action(s, PovertyPass(0, ids(s, 0, "Q♥", "Q♦", "J♠")))
        self.assertEqual(cm.exception.code, "not_your_turn")
        self.assertEqual(json.dumps(s.to_dict(), sort_keys=True), before)

    def test_pass_moves_cards_out_of_the_hand_and_asks_clockwise(self):
        s = to_offer_phase()
        self.assertEqual(s.phase, Phase.POVERTY_OFFER)
        self.assertEqual(len(s.hands[POOR]), 9)
        self.assertEqual(len(s.poverty_cards), 3)
        self.assertEqual(s.poverty_queue, [3, 0, 1])                  # Uhrzeigersinn ab links vom Armen
        self.assertEqual(legal_actions(s, 3)[0]["type"], "poverty_offer")
        self.assertEqual(legal_actions(s, 0), [])
        with self.assertRaises(RuleViolation):
            apply_action(s, PovertyOffer(0, True))                    # noch nicht dran

    def test_even_with_only_non_trumps_three_cards_are_passed(self):
        s = to_pass_phase()
        apply_action(s, PovertyPass(POOR, ids(s, POOR, "A♣", "A♣", "10♣")))
        self.assertEqual(sorted(c.face for c in s.poverty_cards), sorted(card(t).face for t in ("A♣", "A♣", "10♣")))

    def test_decline_passes_the_question_on(self):
        s = to_offer_phase()
        apply_action(s, PovertyOffer(3, False))
        self.assertEqual(s.poverty_queue, [0, 1])
        self.assertEqual(spectator_view(s)["poverty"]["offerSeat"], 0)
        apply_action(s, PovertyOffer(0, False))
        self.assertEqual(s.phase, Phase.POVERTY_OFFER)

    def test_buyer_gets_the_cards_and_returns_three(self):
        s = to_offer_phase()
        apply_action(s, PovertyOffer(3, True))
        self.assertEqual((s.phase, s.poverty_buyer, len(s.hands[BUYER])), (Phase.POVERTY_RETURN, BUYER, 15))
        act = legal_actions(s, BUYER)[0]
        self.assertEqual((act["type"], act["count"], len(act["cards"])), ("poverty_return", 3, 15))
        self.assertEqual(len(act["received"]), 3)
        self.assertTrue(set(act["received"]) <= set(act["cards"]))
        before = json.dumps(s.to_dict(), sort_keys=True)
        for bad in (ids(s, BUYER, "9♣", "9♣"), ids(s, BUYER, "9♣", "9♣", "9♠", "J♣")):
            with self.assertRaises(RuleViolation):
                apply_action(s, PovertyReturn(BUYER, bad))
        with self.assertRaises(RuleViolation):
            apply_action(s, PovertyReturn(POOR, ids(s, POOR, "A♣", "A♣", "10♣")))
        self.assertEqual(json.dumps(s.to_dict(), sort_keys=True), before)

    def test_return_ends_the_exchange_and_starts_the_game(self):
        s = to_offer_phase()
        apply_action(s, PovertyOffer(3, True))
        apply_action(s, PovertyReturn(BUYER, ids(s, BUYER, "Q♣", "9♣", "9♣")))    # Q♣ geht zum Armen zurueck
        self.assertEqual(s.phase, Phase.PLAYING)
        self.assertEqual(s.kind, GameKind.POVERTY)
        self.assertEqual(s.game_type, GameType.NORMAL)
        self.assertEqual([len(h) for h in s.hands], [12, 12, 12, 12])
        self.assertEqual(s.turn, 0)                                    # links vom Geber
        self.assertEqual(sum(c.face == card("Q♣").face for c in s.hands[POOR]), 1)
        self.assertEqual((s.poverty_cards, s.poverty_queue, s.poverty_received), ([], [], []))
        self.assertEqual((s.poverty_seat, s.poverty_buyer), (POOR, BUYER))
        self.assertIn("poverty_taken", [e["type"] for e in public_events(s)])

    def test_poor_and_buyer_are_re_against_the_other_two(self):
        # unabhaengig davon, wer nach dem Tausch die Kreuz-Damen haelt
        for give_back, queens_at in ((("Q♣", "9♣", "9♣"), "beide Partner"), (("9♣", "9♣", "9♠"), "Kaeufer allein")):
            with self.subTest(queens=queens_at):
                s = to_offer_phase()
                apply_action(s, PovertyOffer(3, True))
                apply_action(s, PovertyReturn(BUYER, ids(s, BUYER, *give_back)))
                self.assertEqual(s.re_seats, [POOR, BUYER])
                self.assertEqual(s.kind, GameKind.POVERTY)             # nie "Stille Hochzeit", nie Solo
                self.assertEqual(s.clarified, ["kontra", "kontra", "re", "re"])
                self.assertEqual((s.party_of(POOR).value, s.party_of(BUYER).value), ("re", "re"))
                self.assertEqual((s.party_of(0).value, s.party_of(1).value), ("kontra", "kontra"))
                self.assertEqual(player_view(s, POOR)["myParty"], "re")
                self.assertEqual(player_view(s, 1)["myParty"], "kontra")

    def test_a_kreuz_dame_of_a_kontra_player_does_not_make_him_re(self):
        hands = dict(POVERTY_HANDS)
        hands[0] = POVERTY_HANDS[0].replace("Q♥", "Q♣", 1)             # Q♣ jetzt bei Sitz 0 (Kontra)
        hands[3] = POVERTY_HANDS[3].replace("Q♣", "Q♥", 1)
        s = new_game(with_options(poverty=True), rig(hands, 3, WITH), 3)
        declare_all(s, reservations={POOR})
        apply_action(s, Baptize(POOR, "poverty"))
        apply_action(s, PovertyPass(POOR, ids(s, POOR, "J♦", "9♦", "A♣")))   # Q♣ behaelt der Arme
        apply_action(s, PovertyOffer(3, True))
        apply_action(s, PovertyReturn(BUYER, ids(s, BUYER, "9♣", "9♣", "9♠")))
        self.assertEqual(s.re_seats, [POOR, BUYER])
        play(s, (0, "Q♣"))
        self.assertEqual(s.clarified[0], "kontra")
        self.assertEqual(s.party_of(0).value, "kontra")

    def test_nobody_buys_the_poverty_the_hand_is_packed_for_a_redeal(self):
        s = to_pass_phase()
        original = sorted(c.id for c in s.hands[POOR])
        apply_action(s, PovertyPass(POOR, ids(s, POOR, "Q♣", "J♦", "9♦")))
        for seat in (3, 0):
            apply_action(s, PovertyOffer(seat, False))
            self.assertEqual(s.phase, Phase.POVERTY_OFFER)
        apply_action(s, PovertyOffer(1, False))
        self.assertEqual((s.phase, s.redeal_seat, s.turn), (Phase.REDEAL, POOR, None))
        self.assertEqual(sorted(c.id for c in s.hands[POOR]), original)     # nichts geht verloren
        self.assertEqual(s.poverty_cards, [])
        self.assertEqual([legal_actions(s, seat) for seat in range(4)], [[], [], [], []])
        self.assertIn("poverty_void", [e["type"] for e in public_events(s)])
        with self.assertRaises(RuleViolation):                          # in dieser Phase geht nichts mehr
            apply_action(s, PlayCard(0, s.hands[0][0].id))

    def test_wrong_phase_actions_are_rejected(self):
        s = to_pass_phase()
        for action in (PovertyOffer(3, True), PovertyReturn(POOR, ids(s, POOR, "A♣", "A♣", "10♣")),
                       PlayCard(0, s.hands[0][0].id)):
            with self.assertRaises(RuleViolation) as cm:
                apply_action(s, action)
            self.assertIn(cm.exception.code, {"wrong_phase", "not_your_turn"})


class PovertyReservationOrderTests(unittest.TestCase):
    def test_several_reservations_poverty_comes_after_the_solos(self):
        s = new_game(with_options(poverty=True), rig(POVERTY_HANDS, 3, WITH), 3)
        declare_all(s, reservations={1, POOR})
        self.assertEqual((s.resolution_stage, s.resolution_queue), ("pflichtsolo", [1, 2]))
        apply_action(s, Resolve(1, False))
        apply_action(s, Resolve(2, False))
        # kein Lustsolo-Kandidat (niemand hat sein Pflichtsolo gespielt) -> Armut-Stufe, nur Seat 2 kommt in Frage
        self.assertEqual((s.phase, s.resolution_stage, s.resolution_queue), (Phase.RESERVATION_RESOLUTION, "poverty", [2]))
        self.assertEqual(legal_actions(s, 2)[0]["stage"], "poverty")
        apply_action(s, Resolve(2, True))
        self.assertEqual((s.phase, s.poverty_seat), (Phase.POVERTY_PASS, POOR))

    def test_a_solo_beats_the_poverty(self):
        s = new_game(with_options(poverty=True), rig(POVERTY_HANDS, 3, WITH), 3)
        declare_all(s, reservations={1, POOR})
        apply_action(s, Resolve(1, True))                              # Pflichtsolo vor Armut
        self.assertEqual((s.phase, s.baptism_seat), (Phase.BAPTISM, 1))
        self.assertNotIn("poverty", legal_actions(s, 1)[0]["choices"])

    def test_declined_poverty_stage_falls_back_to_a_normal_game(self):
        s = new_game(with_options(poverty=True), rig(POVERTY_HANDS, 3, WITH), 3)
        declare_all(s, reservations={1, POOR})
        for seat in (1, 2):
            apply_action(s, Resolve(seat, False))
        apply_action(s, Resolve(2, False))
        self.assertEqual((s.phase, s.kind), (Phase.PLAYING, GameKind.NORMAL))   # wer nicht anmeldet, spielt normal

    def test_without_the_option_several_reservations_end_as_before(self):
        s = new_game(make_profile(WITH), rig(POVERTY_HANDS, 3, WITH), 3)
        declare_all(s, reservations={1, POOR})
        apply_action(s, Resolve(1, False))
        apply_action(s, Resolve(2, False))
        self.assertEqual((s.phase, s.kind), (Phase.PLAYING, GameKind.NORMAL))

    def test_nobody_eligible_means_no_poverty_stage(self):
        s = new_game(with_options(poverty=True), rig(POVERTY_HANDS, 3, WITH), 3)
        declare_all(s, reservations={0, 1})                            # 8 und 6 Truempfe
        apply_action(s, Resolve(0, False))
        apply_action(s, Resolve(1, False))
        self.assertEqual((s.phase, s.kind), (Phase.PLAYING, GameKind.NORMAL))


class PovertyPrivacyTests(unittest.TestCase):
    def test_passed_cards_are_visible_only_to_the_poor_player(self):
        s = to_offer_phase()
        passed = [c.id for c in s.poverty_cards]
        mine = player_view(s, POOR)
        self.assertEqual(sorted(f"{c['rank']}-{c['suit']}-{c['copy']}" for c in mine["povertyPassed"]), sorted(passed))
        for seat in (0, 1, 3):
            text = json.dumps(player_view(s, seat), ensure_ascii=False)
            self.assertNotIn("povertyPassed", text)
            for card_id in passed:
                rank, suit, copy = card_id.split("-")
                self.assertNotIn(json.dumps({"rank": rank, "suit": suit, "copy": int(copy)}, ensure_ascii=False)[1:-1], text)
        spectator = json.dumps(spectator_view(s), ensure_ascii=False)
        self.assertNotIn("povertyPassed", spectator)
        self.assertNotIn("poverty_cards", spectator)

    def test_returned_cards_are_shown_only_to_the_poor_player(self):
        s = to_offer_phase()
        apply_action(s, PovertyOffer(3, True))
        given = ids(s, BUYER, "9♣", "9♣", "9♠")
        self.assertNotIn("povertyGot", player_view(s, POOR))            # noch nicht zurueckgegeben
        apply_action(s, PovertyReturn(BUYER, given))
        got = player_view(s, POOR)["povertyGot"]
        self.assertEqual(sorted(f"{c['rank']}-{c['suit']}-{c['copy']}" for c in got), sorted(given))
        for seat in (0, 1, BUYER):
            self.assertNotIn("povertyGot", player_view(s, seat))
        self.assertNotIn("povertyGot", spectator_view(s))
        restored = GameState.from_dict(json.loads(json.dumps(s.to_dict())))
        self.assertEqual(restored.poverty_got, list(given))

    def test_log_and_events_name_no_cards(self):
        s = to_offer_phase()
        apply_action(s, PovertyOffer(3, True))
        apply_action(s, PovertyReturn(BUYER, ids(s, BUYER, "9♣", "9♣", "9♠")))
        entries = [e for e in s.log if e["type"].startswith("poverty")]
        self.assertTrue(entries)
        for e in entries:
            self.assertFalse({"card", "cards", "cardIds"} & set(e), e)
        for e in public_events(s):
            self.assertFalse({"card", "cards", "cardIds"} & set(e), e)

    def test_only_the_buyer_sees_which_cards_he_received(self):
        s = to_offer_phase()
        apply_action(s, PovertyOffer(3, True))
        self.assertEqual(len(legal_actions(s, BUYER)[0]["received"]), 3)
        for seat in (0, 1, POOR):
            self.assertEqual(legal_actions(s, seat), [])
        self.assertNotIn("received", json.dumps(spectator_view(s)))


class PovertyPersistenceAndScoringTests(unittest.TestCase):
    def test_serialization_roundtrip_in_every_phase(self):
        s = poverty_game()
        snapshots = [s]
        apply_action(s, Baptize(POOR, "poverty"))
        snapshots.append(s)
        apply_action(s, PovertyPass(POOR, ids(s, POOR, "Q♣", "J♦", "9♦")))
        snapshots.append(s)
        apply_action(s, PovertyOffer(3, True))
        for _ in snapshots + [s]:
            d = json.loads(json.dumps(s.to_dict()))
            self.assertEqual(GameState.from_dict(d).to_dict(), s.to_dict())
        apply_action(s, PovertyReturn(BUYER, ids(s, BUYER, "9♣", "9♣", "9♠")))
        d = json.loads(json.dumps(s.to_dict()))
        self.assertEqual(GameState.from_dict(d).to_dict(), s.to_dict())

    def test_redeal_state_survives_serialization(self):
        s = to_offer_phase()
        for seat in (3, 0, 1):
            apply_action(s, PovertyOffer(seat, False))
        d = json.loads(json.dumps(s.to_dict()))
        r = GameState.from_dict(d)
        self.assertEqual((r.phase, r.redeal_seat), (Phase.REDEAL, POOR))
        self.assertEqual(r.to_dict(), s.to_dict())

    def test_failed_action_rolls_back_the_exchange(self):
        s = to_offer_phase()
        apply_action(s, PovertyOffer(3, True))
        before = json.dumps(s.to_dict(), sort_keys=True)
        with self.assertRaises(RuleViolation):
            apply_action(s, PovertyReturn(BUYER, ("x-♣-0", "9-♣-0", "9-♣-1")))
        self.assertEqual(json.dumps(s.to_dict(), sort_keys=True), before)

    def test_old_saved_games_without_poverty_fields_still_load(self):
        s = new_game(make_profile(WITH), rig(POVERTY_HANDS, 3, WITH), 3)
        d = s.to_dict()
        for key in ("povertySeat", "povertyCards", "povertyQueue", "povertyBuyer", "povertyReceived"):
            d.pop(key)
        restored = GameState.from_dict(json.loads(json.dumps(d)))
        self.assertEqual((restored.poverty_seat, restored.poverty_cards, restored.poverty_queue), (None, [], []))

    def test_a_full_poverty_game_is_scored_and_booked_as_a_normal_game(self):
        for kept in ("partner", "alone"):
            with self.subTest(queens=kept):
                s = to_offer_phase()
                apply_action(s, PovertyOffer(3, True))
                give_back = ("Q♣", "9♣", "9♣") if kept == "partner" else ("9♣", "9♣", "9♠")
                apply_action(s, PovertyReturn(BUYER, ids(s, BUYER, *give_back)))
                auto_play(s, random.Random(4))
                self.assertEqual(s.phase, Phase.FINISHED)
                self.assertEqual(sum(t.points for t in s.tricks), 240)
                self.assertEqual(sum(s.score.seat_deltas), 0)
                self.assertFalse(s.score.solo_scoring)                  # immer zwei gegen zwei
                self.assertEqual(s.re_seats, [POOR, BUYER])
                rnd = new_round(s.profile)
                dealer = rnd.dealer
                record_game(rnd, s)
                self.assertEqual(rnd.normal_games_played, 1)
                self.assertEqual(rnd.dealer, (dealer + 1) % 4)
                self.assertEqual(rnd.results[-1]["kind"], "poverty")
                self.assertEqual(rnd.pflichtsolo_done, [False] * 4)

    def test_bock_multiplier_applies_to_a_poverty_game(self):
        profile = with_options(poverty=True)
        s = new_game(profile, rig(POVERTY_HANDS, 3, WITH), 3, multiplier=2)
        declare_all(s, reservations={POOR})
        apply_action(s, Baptize(POOR, "poverty"))
        apply_action(s, PovertyPass(POOR, ids(s, POOR, "Q♣", "J♦", "9♦")))
        apply_action(s, PovertyOffer(3, True))
        apply_action(s, PovertyReturn(BUYER, ids(s, BUYER, "Q♣", "9♣", "9♣")))
        auto_play(s, random.Random(2))
        self.assertEqual(s.score.multiplier, 2)


if __name__ == "__main__":
    unittest.main()
