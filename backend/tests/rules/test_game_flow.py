"""TSR 4: Vorbehalte, Solo, Vorfuehrung, Hochzeit; Zustandsmaschine (Version, Transaktion, Sichten)."""
import json
import random
import unittest

from . import loader  # noqa: F401
from app.rules.errors import DuplicateAction, RuleViolation, VersionConflict
from app.rules.cards import Card
from app.rules.game import (Announce, Baptize, Declare, GameKind, GameState, Phase, PlayCard, Resolve,
                             apply_action, legal_actions, player_view, spectator_view)
from app.rules.parties import Party
from app.rules.trump import GameType

from .fixtures import DDV, DISCARD_HANDS, NORMAL_HANDS, WEDDING_HANDS, auto_play, declare_all, play, start


class ReservationTests(unittest.TestCase):
    def test_all_healthy_is_normal_game(self):  # 4.1.3
        s = declare_all(start())
        self.assertEqual((s.phase, s.kind, s.turn), (Phase.PLAYING, GameKind.NORMAL, 0))
        self.assertEqual(s.re_seats, [1, 2])

    def test_declaration_out_of_turn_rejected_and_state_unchanged(self):
        s = start()
        before = json.dumps(s.to_dict(), sort_keys=True)
        with self.assertRaises(RuleViolation) as cm:
            apply_action(s, Declare(2, False))
        self.assertEqual(cm.exception.code, "not_your_turn")
        self.assertEqual(json.dumps(s.to_dict(), sort_keys=True), before)

    def test_single_reservation_names_pflichtsolo(self):  # 4.1.4, 4.2.2
        s = declare_all(start(), reservations={2})
        self.assertEqual((s.phase, s.baptism_seat), (Phase.BAPTISM, 2))
        apply_action(s, Baptize(2, "solo_queens"))
        self.assertEqual((s.kind, s.game_type, s.turn, s.re_seats), (GameKind.PFLICHTSOLO, GameType.SOLO_QUEENS, 2, [2]))
        self.assertEqual(s.clarified, ["kontra", "kontra", "re", "kontra"])

    def test_solo_after_pflichtsolo_is_lustsolo_led_by_left_of_dealer(self):  # 4.3.1
        s = declare_all(start(done=(False, False, True, False)), reservations={2})
        apply_action(s, Baptize(2, "solo_hearts"))
        self.assertEqual((s.kind, s.turn), (GameKind.LUSTSOLO, 0))

    def test_multiple_reservations_pflichtsolo_beats_lustsolo(self):  # 4.1.5-4.1.7
        s = declare_all(start(done=(False, True, False, False)), reservations={1, 3})
        self.assertEqual((s.phase, s.resolution_stage, s.resolution_queue), (Phase.RESERVATION_RESOLUTION, "pflichtsolo", [3]))
        apply_action(s, Resolve(3, True))
        self.assertEqual((s.baptism_seat, s.baptism_kind), (3, GameKind.PFLICHTSOLO))

    def test_first_yes_in_seat_order_wins(self):
        s = declare_all(start(), reservations={1, 3})
        self.assertEqual(s.resolution_queue, [1, 3])
        apply_action(s, Resolve(1, False))
        apply_action(s, Resolve(3, True))
        self.assertEqual(s.baptism_seat, 3)

    def test_lustsolo_stage_when_nobody_owes_pflichtsolo(self):
        s = declare_all(start(done=(True, True, True, True)), reservations={0, 2})
        self.assertEqual((s.resolution_stage, s.resolution_queue), ("lustsolo", [0, 2]))
        apply_action(s, Resolve(0, False))
        apply_action(s, Resolve(2, True))
        self.assertEqual(s.baptism_kind, GameKind.LUSTSOLO)

    def test_everyone_declines_falls_back_to_normal_game(self):  # Annahme (Matrix A3)
        s = declare_all(start(), reservations={0, 3})
        apply_action(s, Resolve(0, False))
        apply_action(s, Resolve(3, False))
        self.assertEqual((s.phase, s.kind), (Phase.PLAYING, GameKind.NORMAL))
        self.assertTrue(any(e["type"] == "reservations_void" for e in s.log))

    def test_wedding_never_chosen_with_several_reservations(self):  # 4.1.6
        s = declare_all(start(WEDDING_HANDS), reservations={1, 3})
        apply_action(s, Resolve(1, True))
        self.assertNotIn("wedding", legal_actions(s, 1)[0]["choices"])
        with self.assertRaises(RuleViolation) as cm:
            apply_action(s, Baptize(1, "wedding"))
        self.assertEqual(cm.exception.code, "wedding_not_allowed")

    def test_wedding_needs_both_queens_of_clubs(self):
        s = declare_all(start(NORMAL_HANDS), reservations={1})
        with self.assertRaises(RuleViolation):
            apply_action(s, Baptize(1, "wedding"))
        s2 = declare_all(start(WEDDING_HANDS), reservations={1})
        self.assertIn("wedding", legal_actions(s2, 1)[0]["choices"])

    def test_unknown_or_non_solo_choice_rejected(self):
        s = declare_all(start(), reservations={2})
        for bad in ("normal", "foo"):
            with self.assertRaises(RuleViolation):
                apply_action(s, Baptize(2, bad))

    def test_forced_pflichtsolo_skips_reservation_round(self):  # 4.1.9, 4.2.3
        s = start(forced=2, done=(True, True, False, True))
        self.assertEqual((s.phase, s.baptism_seat, s.baptism_kind), (Phase.BAPTISM, 2, GameKind.PFLICHTSOLO_FORCED))
        self.assertNotIn("wedding", legal_actions(s, 2)[0]["choices"])
        apply_action(s, Baptize(2, "solo_aces"))
        self.assertEqual((s.kind, s.turn), (GameKind.PFLICHTSOLO_FORCED, 2))
        with self.assertRaises(RuleViolation):
            start(forced=2, done=(False, False, True, False))

    def test_silent_wedding_detected_and_hidden(self):  # 4.4.5
        s = declare_all(start(WEDDING_HANDS))
        self.assertEqual((s.kind, s.re_seats), (GameKind.SILENT_WEDDING, [1]))
        self.assertEqual(spectator_view(s)["kind"], "normal")
        self.assertEqual(spectator_view(s)["clarified"], [None] * 4)


class WeddingTests(unittest.TestCase):
    def wedding(self):
        s = declare_all(start(WEDDING_HANDS), reservations={1})
        apply_action(s, Baptize(1, "wedding"))
        return s

    def test_hochzeit_blocks_announcements_until_clarified(self):  # 6.4.2
        s = self.wedding()
        self.assertEqual((s.kind, s.re_seats, s.turn), (GameKind.WEDDING, [1], 0))
        with self.assertRaises(RuleViolation) as cm:
            apply_action(s, Announce(1, 0))
        self.assertEqual(cm.exception.code, "wedding_unclarified")
        self.assertFalse([a for a in legal_actions(s, 1) if a["type"] == "announce"])

    def test_clarified_in_first_trick(self):  # 4.4.3
        s = self.wedding()
        play(s, (0, "Q♠"), (1, "J♦"), (2, "J♠"), (3, "9♦"))
        self.assertEqual((s.wedding_clarifying_trick, s.wedding_partner, s.re_seats, s.wedding_shift), (1, 0, [1, 0], 0))
        apply_action(s, Announce(0, 0))                 # 11 Karten: Re noch erlaubt
        self.assertEqual(s.announcements.re.level, 0)

    def test_clarified_in_second_trick_shifts_deadlines_by_one(self):  # 6.4.2
        s = self.wedding()
        play(s, (0, "A♣"), (1, "10♥"), (2, "9♣"), (3, "9♠"))           # Hochzeiter gewinnt
        self.assertIsNone(s.wedding_clarifying_trick)
        play(s, (1, "A♠"), (2, "Q♥"), (3, "9♠"), (0, "Q♠"))            # Sitz 0 sticht: Partner
        self.assertEqual((s.wedding_clarifying_trick, s.wedding_partner, s.wedding_shift), (2, 0, 1))
        # Alle halten jetzt 10 Karten: Re (11-1=10) erlaubt, 'keine 90' ueberspringend (9) ebenfalls
        self.assertEqual([a["levels"] for a in legal_actions(s, 3) if a["type"] == "announce"], [[0, 1, 2, 3, 4]])
        play(s, (0, "A♦"))                                              # Sitz 0 hat nur noch 9 Karten
        self.assertFalse([a for a in legal_actions(s, 0) if a["type"] == "announce"])

    def test_hochzeiter_wins_three_tricks_becomes_diamond_solo(self):  # 4.4.3 letzter Satz
        s = self.wedding()
        play(s, (0, "A♣"), (1, "10♥"), (2, "9♣"), (3, "9♠"))
        play(s, (1, "A♠"), (2, "K♥"), (3, "9♠"), (0, "K♣"))
        play(s, (1, "A♠#1"), (2, "K♥#1"), (3, "9♥"), (0, "K♣#1"))
        self.assertEqual((s.wedding_clarifying_trick, s.wedding_partner, s.re_seats, s.wedding_shift), (3, None, [1], 2))
        self.assertTrue(s.is_solo_scored)
        self.assertEqual(s.clarified, ["kontra", "re", "kontra", "kontra"])
        auto_play(s, random.Random(1))
        self.assertTrue(s.score.solo_scoring)
        self.assertEqual(sorted(s.score.seat_deltas), sorted([3 * s.score.net, -s.score.net, -s.score.net, -s.score.net]))
        self.assertFalse([i for i in s.score.items[Party.RE] + s.score.items[Party.KONTRA]
                          if i.code in ("beat_re", "doppelkopf", "fox_caught", "charlie_last_trick")])

    def test_resolved_wedding_keeps_special_points(self):
        s = self.wedding()
        play(s, (0, "Q♠"), (1, "J♦"), (2, "J♠"), (3, "9♦"))
        auto_play(s, random.Random(2))
        self.assertFalse(s.score.solo_scoring)
        self.assertEqual(sorted(s.score.seat_deltas), sorted([s.score.net] * 2 + [-s.score.net] * 2))


class StateMachineTests(unittest.TestCase):
    def test_version_and_idempotency(self):
        s = start()
        apply_action(s, Declare(0, False), expected_version=1, action_id="a1")
        self.assertEqual(s.version, 2)
        with self.assertRaises(VersionConflict):
            apply_action(s, Declare(1, False), expected_version=1)
        with self.assertRaises(DuplicateAction):
            apply_action(s, Declare(1, False), action_id="a1")
        self.assertEqual(s.version, 2)

    def test_illegal_card_is_atomic(self):
        s = declare_all(start())
        before = json.dumps(s.to_dict(), sort_keys=True)
        for action, code in ((PlayCard(1, "A-♠-0"), "not_your_turn"), (PlayCard(0, "9-♦-0"), "card_not_in_hand")):
            with self.assertRaises(RuleViolation) as cm:
                apply_action(s, action)
            self.assertEqual(cm.exception.code, code)
        play(s, (0, "A♣"), (1, "A♠"))
        with self.assertRaises(RuleViolation) as cm:   # Sitz 2 hat 9♣ und muss Kreuz bedienen
            apply_action(s, PlayCard(2, "Q-♣-1"))
        self.assertEqual(cm.exception.code, "must_follow")
        self.assertEqual(s.version, 7)                  # 1 + 4 Antworten + 2 Karten; Fehler zaehlt nicht

    def test_serialization_roundtrip_mid_game(self):
        s = declare_all(start())
        play(s, (0, "A♣"), (1, "A♠"), (2, "9♣"), (3, "9♠"))
        d = json.loads(json.dumps(s.to_dict()))
        self.assertEqual(GameState.from_dict(d).to_dict(), s.to_dict())

    def test_views_hide_other_hands_and_hidden_parties(self):
        s = declare_all(start())
        view = player_view(s, 0)
        self.assertEqual(len(view["hand"]), 12)
        self.assertEqual(view["myParty"], "kontra")
        self.assertEqual(view["clarified"], [None] * 4)
        self.assertNotIn("hand", spectator_view(s))
        self.assertNotIn("myParty", spectator_view(s))
        self.assertEqual([a["type"] for a in view["legalActions"]], ["play_card", "announce"])
        self.assertEqual([a["type"] for a in player_view(s, 3)["legalActions"]], ["announce"])

    def test_clarification_by_queen_and_by_discard(self):  # 5.5.1 Nr. 3 und 5
        s = declare_all(start(DISCARD_HANDS, dealer=0))
        self.assertEqual((s.turn, s.re_seats), (1, [1, 2]))
        play(s, (1, "Q♣"), (2, "Q♠"), (3, "10♥"), (0, "9♣"))   # Sitz 0 wirft Fehlkarte auf Trumpf
        self.assertEqual(s.clarified, ["kontra", "re", None, None])

    def test_hand_in_view_is_sorted_trumps_first(self):
        from app.rules.trump import is_trump, strength
        s = declare_all(start(NORMAL_HANDS))
        play(s, (0, "Q♠"), (1, "Q♣"), (2, "Q♥"), (3, "9♦"))
        for seat in range(4):
            hand = [Card.from_dict(c) for c in player_view(s, seat)["hand"]]
            flags = [is_trump(c, s.game_type, s.trump_cfg) for c in hand]
            self.assertEqual(flags, sorted(flags, reverse=True))
            trumps = [strength(c, s.game_type, s.trump_cfg) for c, t in zip(hand, flags) if t]
            self.assertEqual(trumps, sorted(trumps))
            self.assertEqual({c.id for c in hand}, {c.id for c in s.hands[seat]})

    def test_baptism_kind_is_public_for_forced_solo(self):
        s = start(forced=2, done=(True, True, False, True))
        self.assertEqual(player_view(s, 2)["baptismKind"], "pflichtsolo_forced")

    def test_full_game_result_exposed_after_finish(self):
        s = declare_all(start())
        auto_play(s, random.Random(3), announce_chance=0.1)
        view = player_view(s, 0)
        self.assertEqual(len(view["tricks"]), 12)
        self.assertEqual(sorted(view["parties"]), ["kontra", "kontra", "re", "re"])
        self.assertEqual(sum(t["points"] for t in view["tricks"]), 240)


if __name__ == "__main__":
    unittest.main()
