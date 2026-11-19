"""Optionale Regeln (Beliebte Regeln + Kneipenregeln): Defaults, Schema, Wirkung jeder einzelnen Option."""
import json
import random
import unittest

from . import loader  # noqa: F401
from app.rules.cards import Card, DeckVariant, Rank, Suit, card
from app.rules.dealing import shuffled_deck
from app.rules.errors import RuleViolation
from app.rules.game import (Announce, Baptize, Declare, DeclareSchweinchen, GameKind, GameState, Phase,
                             PlayCard, apply_action, legal_actions, player_view)
from app.rules.options import OPTION_SPECS, RuleOptions, rule_schema, settings_from_dict
from app.rules.parties import Party
from app.rules.profile import RuleProfile, RuleProfileId, ddv_profile, make_profile
from app.rules.round_rules import is_round_finished, new_round, next_setup, record_game, start_next_game
from app.rules.scoring import score_game
from app.rules.tricks import CompletedTrick, Play, playable_cards, trick_winner_index
from app.rules.trump import GameType, TrumpConfig, is_trump, suit_order, trump_count, trump_order

from .fixtures import (DDV, NORMAL_HANDS, WEDDING_HANDS, WITH, WITHOUT, auto_play, declare_all, play, rig,
                       start, step_random, with_options)
from .test_scoring import codes, lv, trick, tricks

RE, KON = Party.RE, Party.KONTRA


class OptionModelTests(unittest.TestCase):
    def test_defaults_are_exactly_the_checked_boxes(self):  # Screenshots: Dullen, Karlchen, Fuchsjagd
        on = {s.id for s in OPTION_SPECS if s.default}
        self.assertEqual(on, {"dulle", "karlchen", "fuchsjagd"})
        self.assertEqual(len(OPTION_SPECS), 13)
        defaults = RuleOptions().to_dict()
        self.assertEqual({k for k, v in defaults.items() if v}, {"dulle", "karlchen", "fuchsjagd"})

    def test_schema_matches_model_and_screenshots(self):
        schema = rule_schema()
        self.assertEqual([s["id"] for s in schema], [
            "dulle", "sharp_doppelkopf", "karlchen", "fuchsjagd", "mandatory_announcements", "solo_leads",
            "karlchen_caught", "schweinchen", "bock_heart_trick", "bock_zero_game", "bock_120",
            "second_dulle_wins", "second_dulle_wins_except_last"])
        self.assertEqual({s["group"] for s in schema[:6]}, {"popular"})
        self.assertEqual({s["group"] for s in schema[6:]}, {"pub"})
        fields = set(RuleOptions().to_dict())
        self.assertEqual({s["id"] for s in schema} - {"sharp_doppelkopf"}, fields)

    def test_every_option_can_be_toggled_individually(self):
        for spec in OPTION_SPECS:
            if spec.key is None:
                continue
            for value in (True, False):
                data = {spec.key: value}
                if spec.requires and value:
                    data[spec.requires] = True
                    if spec.requires == "second_dulle_wins":
                        data["second_dulle_wins"] = True
                opts = RuleOptions(**{**RuleOptions().to_dict(), **data})
                self.assertEqual(getattr(opts, spec.key), value)

    def test_validation(self):
        with self.assertRaises(RuleViolation) as cm:
            RuleOptions.from_dict({"nope": True})
        self.assertEqual(cm.exception.code, "unknown_option")
        with self.assertRaises(RuleViolation):
            RuleOptions.from_dict({"dulle": "ja"})
        with self.assertRaises(RuleViolation) as cm:
            RuleOptions(second_dulle_wins_except_last=True)
        self.assertEqual(cm.exception.code, "invalid_option_combination")
        with self.assertRaises(RuleViolation):
            RuleOptions(second_dulle_wins=True, dulle=False)
        RuleOptions(second_dulle_wins=True, second_dulle_wins_except_last=True)  # ok

    def test_settings_mapping_and_profile_ids(self):
        self.assertEqual(settings_from_dict({})[0], WITH)
        deck, opts = settings_from_dict({"sharp_doppelkopf": True, "schweinchen": True})
        self.assertEqual((deck, opts.schweinchen), (WITHOUT, True))
        self.assertEqual(make_profile(WITH).id, RuleProfileId.DDV_TSR_2026)
        self.assertEqual(make_profile(WITHOUT).id, RuleProfileId.HOUSE_NO_NINES)
        self.assertEqual(with_options(dulle=False).id, RuleProfileId.CUSTOM)
        self.assertFalse(with_options(karlchen=False).is_official_ddv)
        profile = with_options(WITHOUT, bock_120=True)
        self.assertEqual(RuleProfile.from_dict(json.loads(json.dumps(profile.to_dict()))), profile)
        self.assertEqual(profile.first_announcement_min_cards, 9)

    def test_game_and_round_keep_options(self):
        p = with_options(schweinchen=True, bock_120=True)
        rnd = new_round(p)
        g = start_next_game(rnd, p, shuffled_deck(WITH, random.Random(1)))
        self.assertTrue(g.options.schweinchen and g.options.bock_120 and g.options.dulle)
        self.assertEqual(GameState.from_dict(json.loads(json.dumps(g.to_dict()))).options, g.options)
        self.assertEqual(g.profile_id, "custom")


class DulleTests(unittest.TestCase):
    cfg = TrumpConfig(WITH, dulle=False)

    def test_without_dulle_heart_ten_is_plain_heart(self):
        self.assertFalse(is_trump(card("10♥"), GameType.NORMAL, self.cfg))
        self.assertEqual(trump_order(GameType.NORMAL, self.cfg)[0], (Rank.QUEEN, Suit.CLUBS))
        self.assertEqual([r.value for r in suit_order(GameType.NORMAL, self.cfg, Suit.HEARTS)], ["A", "10", "K", "9"])
        self.assertEqual(trump_count(GameType.NORMAL, self.cfg), 24)
        self.assertEqual(trump_count(GameType.SOLO_HEARTS, self.cfg), 24)   # alle Herz-Karten + Damen/Buben (kein Dulle-Platz)

    def test_without_dulle_follow_and_win(self):
        hand = [card("10♥"), card("A♥"), card("Q♣")]
        self.assertEqual({c.id for c in playable_cards(hand, card("K♥"), GameType.NORMAL, self.cfg)},
                         {"10-♥-0", "A-♥-0"})                      # Herz-Fehlfarbe bedienen
        plays = [Play(0, card("10♥")), Play(1, card("A♥")), Play(2, card("K♥")), Play(3, card("9♥"))]
        self.assertEqual(trick_winner_index(plays, GameType.NORMAL, self.cfg), 1)   # Ass > 10
        plays[2] = Play(2, card("J♦"))                                               # jeder Trumpf sticht
        self.assertEqual(trick_winner_index(plays, GameType.NORMAL, self.cfg), 2)

    def test_full_games_without_dulle(self):
        p = with_options(dulle=False)
        for seed in range(8):
            rnd = new_round(p)
            g = start_next_game(rnd, p, shuffled_deck(WITH, random.Random(seed)))
            while g.phase is not Phase.FINISHED:
                step_random(g, random.Random(seed + len(g.log)), 0.05, 0.1)
            self.assertEqual((sum(t.points for t in g.tricks), sum(g.score.seat_deltas)), (240, 0))


class SecondDulleTests(unittest.TestCase):
    plays = [Play(0, card("K♠")), Play(1, card("10♥")), Play(2, card("10♥#1")), Play(3, card("A♠"))]

    def test_trick_level(self):
        self.assertEqual(trick_winner_index(self.plays, GameType.NORMAL, WITH), 1)
        self.assertEqual(trick_winner_index(self.plays, GameType.NORMAL, WITH, second_dulle_wins=True), 2)

    def test_not_applicable_without_dulle_or_in_queen_solo(self):
        p = [Play(0, card("10♥")), Play(1, card("10♥#1")), Play(2, card("9♠")), Play(3, card("9♣"))]
        self.assertEqual(trick_winner_index(p, GameType.SOLO_QUEENS, WITH, second_dulle_wins=True), 0)
        self.assertEqual(trick_winner_index(p, GameType.NORMAL, TrumpConfig(WITH, dulle=False), second_dulle_wins=True), 0)

    def last_trick(self, **opts):
        """Letzter Stich mit beiden Dullen (Sitz 1 zuerst, Sitz 2 danach); Rueckgabe: Stichgewinner."""
        g = declare_all(start(NORMAL_HANDS, profile=with_options(**opts)))
        g.hands = [[card("A♠")], [card("10♥")], [Card(Suit.HEARTS, Rank.TEN, 1)], [card("K♠")]]
        g.tricks = [CompletedTrick(i + 1, tuple(Play(s, card("9♣")) for s in range(4)), i % 4, 0) for i in range(11)]
        g.turn = 0
        play(g, (0, "A♠"), (1, "10♥"), (2, "10♥#1"), (3, "K♠"))
        return g.tricks[-1].winner_seat

    def test_in_game_and_except_last(self):
        self.assertEqual(self.last_trick(), 1)
        self.assertEqual(self.last_trick(second_dulle_wins=True), 2)
        self.assertEqual(self.last_trick(second_dulle_wins=True, second_dulle_wins_except_last=True), 1)


class SpecialPointOptionTests(unittest.TestCase):
    def test_karlchen_and_fuchsjagd_can_be_disabled(self):
        ts = tricks(125, 115)
        ts[0] = CompletedTrick(1, trick(1, 0, 11, ["A♦", "9♠", "A♦#1", "9♥"]).plays, 0, 11)
        ts[-1] = CompletedTrick(12, trick(12, 2, 0, ["J♣", "9♠", "J♣#1", "9♥"]).plays, 2, 0)
        on = score_game(ts, (0, 1), lv(), 12)
        self.assertIn("fox_caught", codes(on, RE))
        self.assertIn("charlie_last_trick", codes(on, KON))
        off = score_game(ts, (0, 1), lv(), 12, RuleOptions(karlchen=False, fuchsjagd=False))
        self.assertFalse([i for p in (RE, KON) for i in off.items[p] if i.code in ("fox_caught", "charlie_last_trick")])
        no_karlchen = score_game(ts, (0, 1), lv(), 12, RuleOptions(karlchen=False))
        no_fox = score_game(ts, (0, 1), lv(), 12, RuleOptions(fuchsjagd=False))
        self.assertEqual(no_karlchen.net, on.net + 1)       # Kontra verliert den Karlchen-Punkt
        self.assertEqual(no_fox.net, on.net - 1)            # Re verliert den Fuchs-Punkt
        self.assertIn("fox_caught", codes(no_karlchen, RE))
        self.assertIn("charlie_last_trick", codes(no_fox, KON))

    def test_karlchen_caught_is_pub_rule(self):
        ts = tricks(125, 115)
        ts[-1] = CompletedTrick(12, trick(12, 0, 0, ["Q♣", "9♠", "J♣", "9♥"]).plays, 0, 0)  # Kontra-Karlchen (Sitz 2) gefangen
        self.assertNotIn("charlie_caught", codes(score_game(ts, (0, 1), lv(), 12), RE))
        self.assertEqual(codes(score_game(ts, (0, 1), lv(), 12, RuleOptions(karlchen_caught=True)), RE)["charlie_caught"], 1)
        own = tricks(125, 115)
        own[-1] = CompletedTrick(12, trick(12, 0, 0, ["9♣", "J♣", "9♠", "9♥"]).plays, 0, 0)  # eigenes Karlchen (Sitz 1) verliert nicht
        self.assertNotIn("charlie_caught", codes(score_game(own, (0, 1), lv(), 12, RuleOptions(karlchen_caught=True)), RE))
        winning = tricks(125, 115)
        winning[-1] = CompletedTrick(12, trick(12, 2, 0, ["9♣", "9♠", "J♣", "9♥"]).plays, 2, 0)  # Karlchen gewinnt: kein "gefangen"
        self.assertFalse([i for p in (RE, KON) for i in score_game(winning, (0, 1), lv(), 12, RuleOptions(karlchen_caught=True)).items[p]
                          if i.code == "charlie_caught"])


class MandatoryAnnouncementTests(unittest.TestCase):
    def game(self, hands=NORMAL_HANDS, **kw):
        g = declare_all(start(hands, profile=with_options(mandatory_announcements=True)), **kw)
        return g

    def test_winner_of_first_trick_must_announce(self):
        g = self.game()
        play(g, (0, "Q♠"), (1, "Q♣"), (2, "Q♥"), (3, "9♦"))           # Sitz 1 (Re) gewinnt
        self.assertEqual(g.mandatory_pending, 1)
        acts = {a["type"] for a in legal_actions(g, 1)}
        self.assertEqual(acts, {"announce"})
        with self.assertRaises(RuleViolation) as cm:
            apply_action(g, PlayCard(1, g.hands[1][0].id))
        self.assertEqual(cm.exception.code, "mandatory_announcement")
        apply_action(g, Announce(1, 0))
        self.assertIsNone(g.mandatory_pending)
        self.assertIn("play_card", {a["type"] for a in legal_actions(g, 1)})
        self.assertEqual(player_view(g, 3)["mandatoryAnnouncementSeat"], None)

    def test_partner_announcing_first_satisfies_it(self):
        g = self.game()
        play(g, (0, "Q♠"), (1, "Q♣"), (2, "Q♥"), (3, "9♦"))
        apply_action(g, Announce(2, 0))                                # Partner sagt Re an
        self.assertIsNone(g.mandatory_pending)

    def test_not_in_solo_wedding_or_silent_wedding(self):
        solo = declare_all(start(NORMAL_HANDS, profile=with_options(mandatory_announcements=True)), reservations={2})
        apply_action(solo, Baptize(2, "solo_queens"))
        play(solo, (2, "Q♣"), (3, "Q♦"), (0, "Q♠"), (1, "Q♥"))
        self.assertIsNone(solo.mandatory_pending)
        silent = declare_all(start(WEDDING_HANDS, profile=with_options(mandatory_announcements=True)))
        play(silent, (0, "Q♠"), (1, "Q♣"), (2, "Q♥"), (3, "9♦"))
        self.assertIsNone(silent.mandatory_pending)

    def test_off_by_default(self):
        g = declare_all(start(NORMAL_HANDS))
        play(g, (0, "Q♠"), (1, "Q♣"), (2, "Q♥"), (3, "9♦"))
        self.assertIsNone(g.mandatory_pending)

    def test_random_games_terminate(self):
        p = with_options(mandatory_announcements=True)
        for seed in range(15):
            g = start_next_game(new_round(p), p, shuffled_deck(WITH, random.Random(seed)))
            auto_play_with_reservations(g, random.Random(seed))
            self.assertEqual(len(g.tricks), 12)


def auto_play_with_reservations(g, rng, chance=0.1):
    while g.phase is not Phase.FINISHED:
        step_random(g, rng, 0.05, chance)


class SoloLeadsTests(unittest.TestCase):
    def lustsolo(self, **opts):
        g = declare_all(start(NORMAL_HANDS, done=(True,) * 4, profile=with_options(**opts)), reservations={2})
        apply_action(g, Baptize(2, "solo_queens"))
        return g

    def test_lustsolo_leader(self):
        g = self.lustsolo()
        self.assertEqual((g.kind, g.turn), (GameKind.LUSTSOLO, 0))        # TSR: linker Nachbar des Gebers
        g = self.lustsolo(solo_leads=True)
        self.assertEqual((g.kind, g.turn), (GameKind.LUSTSOLO, 2))        # Hausregel: Solist spielt aus

    def test_pflichtsolo_already_leads(self):
        g = declare_all(start(NORMAL_HANDS, profile=with_options(solo_leads=True)), reservations={1})
        apply_action(g, Baptize(1, "solo_jacks"))
        self.assertEqual(g.turn, 1)


class SchweinchenTests(unittest.TestCase):
    def game(self, hands=WEDDING_HANDS, **opts):
        return declare_all(start(hands, profile=with_options(schweinchen=True, **opts)))

    def test_declaration_makes_foxes_highest_trumps(self):
        g = self.game(NORMAL_HANDS | {0: WEDDING_HANDS[0]})
        self.assertIn("schweinchen", {a["type"] for a in legal_actions(g, 0)})
        self.assertNotIn("schweinchen", {a["type"] for a in legal_actions(g, 1)})
        apply_action(g, DeclareSchweinchen(0))
        self.assertEqual(g.schweinchen_seat, 0)
        self.assertEqual(trump_order(GameType.NORMAL, g.trump_cfg)[:2], ((Rank.ACE, Suit.DIAMONDS), (Rank.TEN, Suit.HEARTS)))
        play(g, (0, "A♦"), (1, "10♥"), (2, "Q♥"), (3, "Q♦"))
        self.assertEqual(g.tricks[-1].winner_seat, 0)                      # Karo-Ass sticht sogar die Dulle
        self.assertEqual(player_view(g, 2)["schweinchenSeat"], 0)

    def test_without_declaration_dulle_wins(self):
        g = self.game()
        play(g, (0, "A♦"), (1, "10♥"), (2, "Q♥"), (3, "Q♦"))
        self.assertEqual(g.tricks[-1].winner_seat, 1)

    def test_rejections(self):
        g = self.game()
        with self.assertRaises(RuleViolation) as cm:
            apply_action(g, DeclareSchweinchen(1))                          # nur ein Fuchs... gar keinen
        self.assertEqual(cm.exception.code, "schweinchen_not_allowed")
        play(g, (0, "A♦"))                                                  # erste Karte gespielt
        self.assertFalse(any(a["type"] == "schweinchen" for a in legal_actions(g, 0)))
        off = declare_all(start(WEDDING_HANDS))
        with self.assertRaises(RuleViolation) as cm:
            apply_action(off, DeclareSchweinchen(0))
        self.assertEqual(cm.exception.code, "option_disabled")

    def test_not_in_solo_without_fox_trump(self):
        g = declare_all(start(WEDDING_HANDS, profile=with_options(schweinchen=True)), reservations={0})
        apply_action(g, Baptize(0, "solo_queens"))                          # Karo-Ass ist dort keine Trumpfkarte
        self.assertFalse(any(a["type"] == "schweinchen" for a in legal_actions(g, 0)))
        g2 = declare_all(start(WEDDING_HANDS, profile=with_options(schweinchen=True)), reservations={0})
        apply_action(g2, Baptize(0, "solo_diamonds"))                       # im Karo-Solo schon
        self.assertTrue(any(a["type"] == "schweinchen" for a in legal_actions(g2, 0)))

    def test_survives_serialization(self):
        g = self.game()
        apply_action(g, DeclareSchweinchen(0))
        g2 = GameState.from_dict(json.loads(json.dumps(g.to_dict())))
        self.assertEqual(g2.trump_cfg, g.trump_cfg)
        self.assertEqual(g2.to_dict(), g.to_dict())


class BockTests(unittest.TestCase):
    def finish(self, hands=NORMAL_HANDS, announce=(), dummies=None, solo=None, **opts):
        """Fuehrt ein Spiel mit 11 vorgegebenen Stichen und einem Null-Augen-Schlussstich zu Ende."""
        rnd = new_round(with_options(**opts))
        g = start_next_game(rnd, with_options(**opts), rig(hands, rnd.dealer, WITH))
        declare_all(g, reservations={solo[0]} if solo else ())
        if solo:
            apply_action(g, Baptize(solo[0], solo[1]))
        for seat, level in announce:
            apply_action(g, Announce(seat, level))
        g.hands = [[card("9♠")], [Card(Suit.SPADES, Rank.NINE, 1)], [card("9♥")], [card("9♣")]]
        g.tricks = dummies
        for seat in [(g.turn + k) % 4 for k in range(4)]:     # Aufspielender laut Engine; jeder hat nur 1 Karte
            apply_action(g, PlayCard(seat, g.hands[seat][0].id))
        return rnd, g

    @staticmethod
    def dummy_tricks(re_pts, kon_pts, n_re, extra=None):
        """11 Stiche: Re (Sitze 1,2) ``n_re`` mal mit zusammen ``re_pts``, Kontra (0,3) sonst."""
        n_kon = 11 - n_re
        result = [(1 + i % 2, re_pts // n_re + (re_pts % n_re if i == 0 else 0)) for i in range(n_re)]
        result += [(0 if i % 2 == 0 else 3, kon_pts // n_kon + (kon_pts % n_kon if i == 0 else 0)) for i in range(n_kon)]
        ts = [CompletedTrick(i + 1, tuple(Play(s, card("9♣")) for s in range(4)), w, p) for i, (w, p) in enumerate(result)]
        for index, plays in (extra or {}).items():
            ts[index] = CompletedTrick(index + 1, tuple(Play(s, card(c)) for s, c in enumerate(plays)), ts[index].winner_seat, ts[index].points)
        return ts

    def test_heart_trick_trigger(self):
        hearts = ["A♥", "K♥", "9♥", "A♥#1"]
        _, g = self.finish(dummies=self.dummy_tricks(120, 120, 6, {0: hearts}), bock_heart_trick=True)
        self.assertEqual(g.bock_triggers, ["heart_trick"])
        _, g = self.finish(dummies=self.dummy_tricks(120, 120, 6, {0: ["A♥", "K♥", "9♥", "Q♣"]}), bock_heart_trick=True)
        self.assertEqual(g.bock_triggers, [])                                # Trumpf dabei -> kein Herzstich
        _, g = self.finish(dummies=self.dummy_tricks(120, 120, 6, {0: hearts}))
        self.assertEqual(g.bock_triggers, [])                                # Option aus

    def test_heart_trick_in_hearts_solo_never_triggers(self):
        hearts = ["A♥", "K♥", "9♥", "A♥#1"]
        _, g = self.finish(dummies=self.dummy_tricks(120, 120, 6, {0: hearts}), solo=(2, "solo_hearts"), bock_heart_trick=True)
        self.assertEqual(g.bock_triggers, [])

    def test_zero_game_and_120_triggers(self):
        both_no90 = ((1, 1), (0, 1))                                          # Re und Kontra sagen je 'keine 90' an
        ts = lambda: self.dummy_tricks(120, 120, 6)
        _, g = self.finish(announce=both_no90, dummies=ts(), bock_zero_game=True, bock_120=True)
        self.assertEqual((g.score.winner, g.score.net, g.bock_triggers), (None, 0, ["zero_game", "points_120"]))
        _, g = self.finish(announce=both_no90, dummies=ts(), bock_120=True)
        self.assertEqual(g.bock_triggers, ["points_120"])
        _, g = self.finish(announce=both_no90, dummies=ts(), bock_zero_game=True)
        self.assertEqual(g.bock_triggers, ["zero_game"])
        _, g = self.finish(dummies=self.dummy_tricks(121, 119, 6), bock_zero_game=True, bock_120=True)
        self.assertEqual(g.bock_triggers, [])

    def test_round_doubles_next_four_games(self):
        both_no90 = ((1, 1), (0, 1))
        opts = dict(bock_zero_game=True, bock_120=True)                       # zwei Ausloeser -> 8 Bockspiele
        rnd, g = self.finish(announce=both_no90, dummies=self.dummy_tricks(120, 120, 6), **opts)
        p = with_options(**opts)
        record_game(rnd, g)
        self.assertEqual(rnd.bock_remaining, 8)
        for i in range(8):
            g = start_next_game(rnd, p, shuffled_deck(WITH, random.Random(i)))
            self.assertEqual(g.score_multiplier, 2)
            auto_play_with_reservations(g, random.Random(i), 0.0)
            raw = score_game(g.tricks, g.re_seats, g.announcements.levels(), 12, g.options, 1)
            self.assertEqual(g.score.seat_deltas, [2 * d for d in raw.seat_deltas])
            self.assertEqual(g.score.multiplier, 2)
            before = rnd.bock_remaining
            record_game(rnd, g)
            self.assertEqual(rnd.bock_remaining, before - 1 + 4 * len(g.bock_triggers))
            rnd.bock_remaining = before - 1                                   # Folgeausloeser dieser Testspiele ignorieren
        self.assertEqual(rnd.bock_remaining, 0)
        g = start_next_game(rnd, p, shuffled_deck(WITH, random.Random(99)))
        self.assertEqual(g.score_multiplier, 1)

    def test_no_bock_without_options(self):
        rnd = new_round(DDV)
        g = start_next_game(rnd, DDV, shuffled_deck(WITH, random.Random(1)))
        self.assertEqual(g.score_multiplier, 1)
        auto_play_with_reservations(g, random.Random(1), 0.0)
        record_game(rnd, g)
        self.assertEqual(rnd.bock_remaining, 0)


class OptionSimulation(unittest.TestCase):
    def test_random_option_combinations(self):
        names = [k for k in RuleOptions().to_dict()]
        for seed in range(60):
            rng = random.Random(seed)
            chosen = {k: rng.random() < 0.5 for k in names}
            if not chosen["dulle"]:
                chosen["second_dulle_wins"] = False
            if not chosen["second_dulle_wins"]:
                chosen["second_dulle_wins_except_last"] = False
            deck = rng.choice([WITH, WITHOUT])
            p = make_profile(deck, RuleOptions(**chosen))
            rnd = new_round(p)
            rnd.bock_remaining = rng.choice([0, 0, 3])
            g = start_next_game(rnd, p, shuffled_deck(deck, rng))
            while g.phase is not Phase.FINISHED:
                step_random(g, rng, 0.08, 0.2)
                if seed < 8:
                    d = json.loads(json.dumps(g.to_dict()))
                    self.assertEqual(GameState.from_dict(d).to_dict(), g.to_dict())
            self.assertEqual(sum(t.points for t in g.tricks), 240)
            self.assertEqual(sum(g.score.seat_deltas), 0)
            self.assertEqual(g.score.multiplier, 2 if rnd.bock_remaining else 1)

    def test_full_round_with_all_options_on(self):
        opts = {k: True for k in RuleOptions().to_dict()}
        p = make_profile(WITH, RuleOptions(**opts))
        rng = random.Random(11)
        rnd = new_round(p)
        while not is_round_finished(rnd, p):
            g = start_next_game(rnd, p, shuffled_deck(WITH, rng))
            while g.phase is not Phase.FINISHED:
                step_random(g, rng, 0.05, 0.1)
            record_game(rnd, g)
        self.assertEqual((rnd.normal_games_played, sum(rnd.totals), len(rnd.results) >= 28), (24, 0, True))
        self.assertGreaterEqual(rnd.bock_remaining, 0)


if __name__ == "__main__":
    unittest.main()
