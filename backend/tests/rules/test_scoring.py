"""TSR 7.1-7.2: Gewinnermittlung, Spielwerte, Sonderpunkte, Solo, Gerade-Ungerade-Regel."""
import itertools
import unittest

from . import loader  # noqa: F401
from app.rules.cards import card
from app.rules.parties import Party
from app.rules.scoring import score_game
from app.rules.tricks import CompletedTrick, Play

RE, KON = Party.RE, Party.KONTRA
NINES = ["9♣", "9♠", "9♥", "9♦"]


def trick(number, winner, points, cards=None):
    cards = cards or NINES
    return CompletedTrick(number, tuple(Play(s, card(c)) for s, c in enumerate(cards)), winner, points)


def tricks(re_pts, kon_pts, n_re=6, n_kon=6, re_seats=(0, 1)):
    """12 Stiche; Re/Kontra-Stiche mit den gewuenschten Augensummen (Punkte stecken im Stich)."""
    kon_seats = [s for s in range(4) if s not in re_seats]
    assert n_re + n_kon == 12 and (n_re or not re_pts) and (n_kon or not kon_pts)
    result = []
    for party_pts, n, seats in ((re_pts, n_re, list(re_seats)), (kon_pts, n_kon, kon_seats)):
        for i in range(n):
            share = party_pts // n + (party_pts % n if i == 0 else 0)
            result.append((seats[i % len(seats)], share))
    return [trick(i + 1, w, p) for i, (w, p) in enumerate(result)]


def lv(re=-1, kon=-1):
    return {RE: re, KON: kon}


def score(re_pts, kon_pts, re=-1, kon=-1, **kw):
    return score_game(tricks(re_pts, kon_pts, **kw), kw.get("re_seats", (0, 1)), lv(re, kon), 12)


def codes(s, party):
    return {i.code: i.points for i in s.items[party]}


class WinnerTests(unittest.TestCase):
    def test_no_announcement_thresholds(self):  # 7.1.1 Nr.1 / 7.1.2 Nr.1
        self.assertIs(score(121, 119).winner, RE)
        self.assertIs(score(120, 120).winner, KON)

    def test_only_re_announced(self):
        self.assertIs(score(120, 120, re=0).winner, KON)
        self.assertIs(score(121, 119, re=0).winner, RE)

    def test_only_kontra_announced(self):  # 7.1.1 Nr.4 / 7.1.2 Nr.4
        self.assertIs(score(120, 120, kon=0).winner, RE)
        self.assertIs(score(119, 121, kon=0).winner, KON)

    def test_both_announced(self):
        self.assertIs(score(121, 119, re=0, kon=0).winner, RE)
        self.assertIs(score(120, 120, re=0, kon=0).winner, KON)

    def test_own_absage_raises_target(self):  # 7.1.1 Nr.5
        for level, need in ((1, 151), (2, 181), (3, 211)):
            self.assertIs(score(need, 240 - need, re=level).winner, RE)
            lost = score(need - 1, 241 - need, re=level)
            self.assertIs(lost.winner, KON)      # Kontra gewinnt mit dem 90./60./30. Auge (Nr.7)

    def test_absage_against_opponent_lowers_target(self):  # 7.1.1 Nr.7
        for level, need in ((1, 90), (2, 60), (3, 30)):
            self.assertIs(score(need, 240 - need, kon=level).winner, RE)
            self.assertIsNot(score(need - 1, 241 - need, kon=level).winner, RE)

    def test_schwarz_by_tricks_not_points(self):  # 7.1.1 Nr.6, 6.3.1
        s = score_game(tricks(240, 0, n_re=12, n_kon=0), (0, 1), lv(re=4), 12)
        self.assertIs(s.winner, RE)
        # Re macht 11 von 12 Stichen: nicht schwarz, obwohl Kontra nur 0 Augen hat (Neunen!)
        almost = score_game(tricks(240, 0, n_re=11, n_kon=1), (0, 1), lv(re=4), 12)
        self.assertIs(almost.winner, KON)

    def test_kontra_schwarz_absage_won_with_first_trick(self):  # 7.1.1 Nr.8
        s = score_game(tricks(228, 12, n_re=11, n_kon=1), (0, 1), lv(kon=4), 12)
        self.assertIs(s.winner, RE)  # Re hat mindestens einen Stich
        s0 = score_game(tricks(0, 240, n_re=0, n_kon=12), (0, 1), lv(kon=4), 12)
        self.assertIs(s0.winner, KON)

    def test_both_miss_targets_no_winner(self):  # 7.1.3
        s = score(130, 110, re=1, kon=1)
        self.assertIsNone(s.winner)


class ValueTests(unittest.TestCase):
    def test_base_and_stages(self):  # 7.2.2 (a)
        for re_pts, expected in ((121, 1), (150, 1), (151, 2), (181, 3), (211, 4)):
            s = score(re_pts, 240 - re_pts)
            self.assertEqual((s.winner, s.net), (RE, expected), re_pts)

    def test_schwarz_played(self):
        s = score_game(tricks(240, 0, n_re=12, n_kon=0), (0, 1), lv(), 12)
        self.assertEqual(s.net, 5)           # gewonnen + unter 90 + 60 + 30 + schwarz
        self.assertEqual(s.seat_deltas, [5, 5, -5, -5])

    def test_zero_points_but_one_trick_is_not_black(self):
        s = score_game(tricks(240, 0, n_re=11, n_kon=1), (0, 1), lv(), 12)
        self.assertEqual(s.net, 4)           # unter 30 gespielt, aber nicht schwarz

    def test_kontra_wins_against_queens_of_clubs(self):  # 7.2.3
        s = score(120, 120)
        self.assertEqual((s.winner, s.net, codes(s, KON)), (KON, -2, {"win": 1, "beat_re": 1}))
        self.assertEqual(s.seat_deltas, [-2, -2, 2, 2])

    def test_announcements_worth_two(self):  # 7.2.2 (b)
        self.assertEqual(score(125, 115, re=0).net, 3)
        self.assertEqual(score(120, 120, kon=0).net, 3)
        self.assertEqual(score(125, 115, re=0, kon=0).net, 5)

    def test_absagen_count_all_stages(self):  # 6.4.3, 7.2.2 (c)
        s = score(155, 85, re=1)
        self.assertEqual((s.winner, s.net), (RE, 1 + 1 + 2 + 1))   # Sieg, unter 90, Re, keine 90
        s2 = score(185, 55, re=2)
        self.assertEqual(s2.net, 1 + 2 + 2 + 2)                    # Sieg+2 Stufen, Re, 2 Absagen
        s4 = score_game(tricks(240, 0, n_re=12, n_kon=0), (0, 1), lv(re=4), 12)
        self.assertEqual(s4.net, 5 + 2 + 4)

    def test_failed_absage_gives_opponent_the_game(self):
        s = score(150, 90, re=1)
        self.assertEqual(s.winner, KON)
        self.assertEqual(codes(s, KON), {"win": 1, "announced_re": 2, "called_re_no_90": 1, "beat_re": 1})
        self.assertEqual(s.net, -5)

    def test_beating_absage_bonus(self):  # 7.2.2 (e)/(f)
        self.assertEqual(score(125, 115, kon=1).net, 1 + 2 + 1 + 1)    # +120 gegen keine 90
        self.assertEqual(score(100, 140, kon=1).net, 1 + 2 + 1)        # nur 100: kein Bonus
        s = score_game(tricks(35, 205, n_re=1, n_kon=11), (0, 1), lv(kon=4), 12)
        self.assertIs(s.winner, RE)
        self.assertIn("beat_black", codes(s, RE))                      # 30 Augen gegen schwarz
        self.assertNotIn("beat_black", codes(score_game(tricks(25, 215, n_re=1, n_kon=11), (0, 1), lv(kon=4), 12), RE))

    def test_no_winner_scoring(self):  # 7.1.3: nur "gespielt"-Posten, (e)/(f), Sonderpunkte
        s = score(130, 110, re=1, kon=1)
        self.assertEqual((s.net, codes(s, RE), codes(s, KON)), (1, {"beat_no_90": 1}, {}))
        self.assertEqual(s.seat_deltas, [1, 1, -1, -1])

    def test_zero_sum_and_parity_in_exhaustive_grid(self):
        for lre, lkon in itertools.product(range(-1, 5), repeat=2):
            for n_re, re_pts in itertools.product((0, 1, 6, 11, 12), (0, 15, 29, 30, 59, 60, 89, 90, 119,
                                                                       120, 150, 151, 180, 181, 210, 211, 240)):
                n_kon = 12 - n_re
                kon_pts = 240 - re_pts
                if (n_re == 0 and re_pts) or (n_kon == 0 and kon_pts):
                    continue
                for seats in ((0, 1), (2,)):
                    s = score_game(tricks(re_pts, kon_pts, n_re, n_kon, re_seats=seats), seats, lv(lre, lkon), 12)
                    self.assertEqual(sum(s.seat_deltas), 0)
                    self.assertEqual(len({d % 2 for d in s.seat_deltas}), 1)
                    if s.winner is not None:   # der Verlierer erhaelt keine "Absage geschlagen"-Posten
                        loser = s.winner.opponent
                        self.assertFalse([i for i in s.items[loser] if i.code.startswith("beat_") and i.code != "beat_re"],
                                         (lre, lkon, n_re, re_pts))


class SpecialPointsTests(unittest.TestCase):
    def base(self, last_cards=None, mid=None, winner_last=0):
        ts = tricks(125, 115)
        if mid:
            ts[mid[0]] = mid[1]
        if last_cards:
            ts[-1] = trick(12, winner_last, ts[-1].points, last_cards)
        return ts

    def test_doppelkopf(self):
        ts = tricks(125, 115)
        ts[0] = trick(1, 0, 44, ["A♠", "A♠", "10♠", "10♠"])   # 11+11+10+10 = 42 -> Re (Sitz 0)
        ts[0] = CompletedTrick(1, ts[0].plays, 0, 42)
        s = score_game(ts, (0, 1), lv(), 12)
        self.assertEqual(codes(s, RE).get("doppelkopf"), 1)

    def test_fox_caught_only_from_opponent(self):
        ts = tricks(125, 115)
        ts[0] = trick(1, 0, 11, ["A♦", "9♠", "A♦#1", "9♥"])    # Sitz 2 (Kontra) verliert Fuchs an Re; Sitz 0 eigener
        s = score_game(ts, (0, 1), lv(), 12)
        self.assertEqual(codes(s, RE).get("fox_caught"), 1)    # nur der gegnerische Fuchs
        self.assertNotIn("fox_caught", codes(s, KON))

    def test_charlie_last_trick_only_when_winning(self):
        ts = tricks(125, 115)
        ts[-1] = trick(12, 2, 0, ["J♣", "9♠", "J♣#1", "9♥"])
        ts[-1] = CompletedTrick(12, ts[-1].plays, 2, 0)        # Sitz 2 (Kontra): Karlchen gewinnt letzten Stich
        s = score_game(ts, (0, 1), lv(), 12)
        self.assertEqual(codes(s, KON).get("charlie_last_trick"), 1)
        ts[-1] = CompletedTrick(12, trick(12, 0, 0, ["Q♣", "9♠", "J♣", "9♥"]).plays, 0, 0)  # Karlchen verliert
        s2 = score_game(ts, (0, 1), lv(), 12)
        self.assertNotIn("charlie_last_trick", codes(s2, KON))
        self.assertFalse([i for i in s2.items[RE] + s2.items[KON] if "charlie" in i.code])  # kein 'Karlchen gefangen'

    def test_special_points_net_against_game_points(self):  # 7.2.3 "zuerst miteinander verrechnet"
        ts = tricks(120, 120)
        ts[0] = CompletedTrick(1, trick(1, 0, 22, ["A♦", "9♠", "A♦#1", "9♥"]).plays, 0, 22)
        ts[1] = CompletedTrick(2, trick(2, 1, 22, ["A♦", "9♠", "A♦#1", "9♥"]).plays, 1, 22)
        ts[2] = CompletedTrick(3, trick(3, 0, 0, ["9♣", "9♠", "9♥", "9♦"]).plays, 0, 0)
        # Kontra: Sieg (1) + gegen Kreuz-Damen (1); Re: zwei gefangene Fuechse (2) -> netto 0
        s = score_game(ts, (0, 1), lv(), 12)
        self.assertEqual((s.winner, s.party_total(KON), s.party_total(RE), s.net), (KON, 2, 2, 0))

    def test_no_special_points_in_solo(self):  # 7.2.4
        ts = tricks(125, 115, re_seats=(0,))
        ts[0] = CompletedTrick(1, trick(1, 0, 44, ["A♦", "A♠", "10♠", "10♠"]).plays, 0, 44)
        s = score_game(ts, (0,), lv(), 12)
        self.assertEqual(s.net, 1)
        self.assertFalse([i for i in s.items[RE] if i.code in ("doppelkopf", "fox_caught", "beat_re")])


class SoloTests(unittest.TestCase):
    def test_solo_tripled_for_soloist(self):  # 7.2.4
        s = score_game(tricks(121, 119, 6, 6, re_seats=(1,)), (1,), lv(), 12)
        self.assertEqual(s.seat_deltas, [-1, 3, -1, -1])
        lost = score_game(tricks(100, 140, 6, 6, re_seats=(2,)), (2,), lv(), 12)
        self.assertEqual(lost.seat_deltas, [1, 1, -3, 1])


if __name__ == "__main__":
    unittest.main()
