"""TSR 2.2, 2.3, 5.2, 5.3.3: Karten, Trumpfreihenfolge, Bedienpflicht, Stichgewinner."""
import unittest

from . import loader  # noqa: F401
from app.rules.cards import CARD_VALUES, Card, DeckVariant, Rank, Suit, build_deck, card, hand_size
from app.rules.dealing import deal
from app.rules.errors import RuleViolation
from app.rules.tricks import Play, playable_cards, trick_points, trick_winner_index
from app.rules.trump import GameType, is_trump, suit_order, trump_count, trump_order

WITH, WITHOUT = DeckVariant.WITH_NINES, DeckVariant.WITHOUT_NINES


def faces(game_type, variant=WITH):
    return [f"{r.value}{s.value}" for r, s in trump_order(game_type, variant)]


class DeckTests(unittest.TestCase):
    def test_48_cards_240_points_with_nines(self):  # TSR 2.2.1/2.2.2
        deck = build_deck(WITH)
        self.assertEqual(len(deck), 48)
        self.assertEqual(len({c.id for c in deck}), 48)
        self.assertEqual(sum(c.value for c in deck), 240)
        self.assertEqual(hand_size(WITH), 12)

    def test_40_cards_240_points_without_nines(self):
        deck = build_deck(WITHOUT)
        self.assertEqual((len(deck), sum(c.value for c in deck), hand_size(WITHOUT)), (40, 240, 10))

    def test_card_values(self):
        self.assertEqual([CARD_VALUES[r] for r in Rank], [11, 10, 4, 3, 2, 0])

    def test_id_roundtrip(self):
        c = Card(Suit.HEARTS, Rank.TEN, 1)
        self.assertEqual(c.id, "10-♥-1")
        self.assertEqual(Card.from_id(c.id), c)
        self.assertEqual(Card.from_dict(c.to_dict()), c)

    def test_deal_three_by_three_starting_left_of_dealer(self):  # TSR 3.3.7
        deck = build_deck(WITH)
        hands = deal(deck, dealer=2, variant=WITH)
        self.assertEqual([len(h) for h in hands], [12] * 4)
        self.assertEqual(hands[3][:3], deck[0:3])    # linker Nachbar von Sitz 2 bekommt zuerst
        self.assertEqual(hands[0][:3], deck[3:6])
        self.assertEqual(hands[3][3:6], deck[12:15])  # zweites Dreierpaket
        with self.assertRaises(RuleViolation):
            deal(deck[:-1], 0, WITH)


class TrumpOrderTests(unittest.TestCase):
    def test_normal_order_exact(self):  # TSR 2.3.4
        self.assertEqual(faces(GameType.NORMAL),
                         ["10♥", "Q♣", "Q♠", "Q♥", "Q♦", "J♣", "J♠", "J♥", "J♦", "A♦", "10♦", "K♦", "9♦"])

    def test_normal_without_nines(self):
        self.assertEqual(faces(GameType.NORMAL, WITHOUT)[-3:], ["A♦", "10♦", "K♦"])

    def test_color_solo_replaces_diamonds(self):  # TSR 2.3.5
        self.assertEqual(faces(GameType.SOLO_CLUBS)[9:], ["A♣", "10♣", "K♣", "9♣"])
        self.assertEqual(faces(GameType.SOLO_SPADES)[9:], ["A♠", "10♠", "K♠", "9♠"])

    def test_hearts_solo_keeps_heart_ten_on_top(self):
        order = faces(GameType.SOLO_HEARTS)
        self.assertEqual(order[0], "10♥")
        self.assertEqual(order[9:], ["A♥", "K♥", "9♥"])
        self.assertEqual(order.count("10♥"), 1)

    def test_queen_and_jack_solo(self):  # TSR 2.3.6
        self.assertEqual(faces(GameType.SOLO_QUEENS), ["Q♣", "Q♠", "Q♥", "Q♦"])
        self.assertEqual(faces(GameType.SOLO_JACKS), ["J♣", "J♠", "J♥", "J♦"])

    def test_aces_solo_has_no_trump(self):  # TSR 2.3.7
        self.assertEqual(trump_order(GameType.SOLO_ACES, WITH), ())

    def test_trump_counts_with_nines(self):  # TSR 2.3.4-2.3.7: 26/22, 24/24, 8/40, 0/48
        expected = {GameType.NORMAL: 26, GameType.SOLO_CLUBS: 26, GameType.SOLO_SPADES: 26,
                    GameType.SOLO_DIAMONDS: 26, GameType.SOLO_HEARTS: 24, GameType.SOLO_QUEENS: 8,
                    GameType.SOLO_JACKS: 8, GameType.SOLO_ACES: 0}
        for game_type, count in expected.items():
            deck = build_deck(WITH)
            self.assertEqual(trump_count(game_type, WITH), count, game_type)
            self.assertEqual(sum(is_trump(c, game_type, WITH) for c in deck), count, game_type)

    def test_trump_counts_without_nines(self):
        self.assertEqual(trump_count(GameType.NORMAL, WITHOUT), 24)
        self.assertEqual(trump_count(GameType.SOLO_HEARTS, WITHOUT), 22)

    def test_off_suit_order(self):
        o = lambda gt, s: [r.value for r in suit_order(gt, WITH, s)]
        self.assertEqual(o(GameType.NORMAL, Suit.CLUBS), ["A", "10", "K", "9"])
        self.assertEqual(o(GameType.NORMAL, Suit.SPADES), ["A", "10", "K", "9"])
        self.assertEqual(o(GameType.NORMAL, Suit.HEARTS), ["A", "K", "9"])   # Herz-10 ist Trumpf
        self.assertEqual(o(GameType.SOLO_QUEENS, Suit.HEARTS), ["A", "10", "K", "J", "9"])
        self.assertEqual(o(GameType.SOLO_JACKS, Suit.CLUBS), ["A", "10", "K", "Q", "9"])
        self.assertEqual(o(GameType.SOLO_ACES, Suit.DIAMONDS), ["A", "10", "K", "Q", "J", "9"])
        self.assertEqual(o(GameType.SOLO_CLUBS, Suit.DIAMONDS), ["A", "10", "K", "9"])  # Karo ist Fehlfarbe
        self.assertEqual(o(GameType.SOLO_HEARTS, Suit.HEARTS), [])                      # alles Trumpf

    def test_heart_ten_is_plain_card_in_queen_solo(self):
        self.assertFalse(is_trump(card("10♥"), GameType.SOLO_QUEENS, WITH))
        self.assertTrue(is_trump(card("10♥"), GameType.NORMAL, WITH))


class FollowTests(unittest.TestCase):
    def play(self, hand, lead, gt=GameType.NORMAL):
        return {c.id for c in playable_cards([card(x) for x in hand], card(lead) if lead else None, gt, WITH)}

    def test_free_lead(self):
        self.assertEqual(len(self.play(["A♣", "Q♣"], None)), 2)

    def test_must_follow_off_suit_not_trump(self):  # TSR 5.2.2
        self.assertEqual(self.play(["A♣", "K♣", "Q♣", "10♥"], "10♣"), {"A-♣-0", "K-♣-0"})

    def test_queen_of_clubs_is_trump_not_clubs(self):
        self.assertEqual(self.play(["Q♣", "A♠"], "A♣"), {"Q-♣-0", "A-♠-0"})  # keine Kreuz-Fehlkarte -> frei

    def test_trump_lead_requires_trump(self):
        self.assertEqual(self.play(["A♣", "10♥", "9♦"], "J♦"), {"10-♥-0", "9-♦-0"})

    def test_no_trump_free_choice(self):  # TSR 5.2.3
        self.assertEqual(len(self.play(["A♣", "A♠"], "Q♣")), 2)

    def test_heart_ten_lead_depends_on_game_type(self):
        self.assertEqual(self.play(["A♥", "Q♣"], "10♥"), {"Q-♣-0"})                      # Normal: Trumpf gefordert
        self.assertEqual(self.play(["A♥", "Q♣"], "10♥", GameType.SOLO_QUEENS), {"A-♥-0"})  # Damensolo: Herz gefordert

    def test_aces_solo_follow_suit_only(self):
        self.assertEqual(self.play(["Q♥", "K♥", "A♣"], "A♥", GameType.SOLO_ACES), {"Q-♥-0", "K-♥-0"})


class TrickWinnerTests(unittest.TestCase):
    def winner(self, cards, gt=GameType.NORMAL):
        plays = [Play(i, card(c)) for i, c in enumerate(cards)]
        return trick_winner_index(plays, gt, WITH)

    def test_highest_of_led_off_suit(self):  # TSR 5.3.3 Nr. 1
        self.assertEqual(self.winner(["K♠", "A♠", "10♠", "9♠"]), 1)

    def test_discards_never_win(self):  # Nr. 2
        self.assertEqual(self.winner(["9♠", "A♣", "A♥", "K♣"]), 0)

    def test_single_trump_wins_off_suit_lead(self):  # Nr. 3
        self.assertEqual(self.winner(["A♠", "K♠", "9♦", "10♠"]), 2)

    def test_over_trump(self):  # Nr. 4
        self.assertEqual(self.winner(["A♠", "9♦", "J♣", "10♠"]), 2)

    def test_highest_trump_on_trump_lead(self):  # Nr. 5
        self.assertEqual(self.winner(["K♦", "A♦", "Q♦", "A♠"]), 2)

    def test_trump_lead_all_discard(self):  # Nr. 6
        self.assertEqual(self.winner(["9♦", "A♠", "A♣", "K♥"]), 0)

    def test_equal_cards_first_wins(self):  # TSR 5.3.3 letzter Absatz
        self.assertEqual(self.winner(["A♠", "A♠#1", "K♠", "9♠"]), 0)
        self.assertEqual(self.winner(["9♦", "K♠", "9♦#1", "A♠"]), 0)

    def test_equal_heart_ten_first_wins(self):
        self.assertEqual(self.winner(["K♠", "10♥", "10♥#1", "A♠"]), 1)
        self.assertEqual(self.winner(["10♥#1", "A♠", "K♠", "10♥"]), 0)

    def test_heart_ten_beats_queen_of_clubs(self):
        self.assertEqual(self.winner(["Q♣", "10♥", "A♠", "K♠"]), 1)

    def test_heart_ten_is_plain_in_queen_solo(self):
        self.assertEqual(self.winner(["10♥", "A♥", "K♠", "9♠"], GameType.SOLO_QUEENS), 1)  # Herz-Ass schlaegt Herz-10

    def test_jack_solo_order(self):
        self.assertEqual(self.winner(["J♦", "J♥", "Q♣", "A♠"], GameType.SOLO_JACKS), 1)

    def test_aces_solo_no_trumps(self):
        self.assertEqual(self.winner(["K♠", "9♠", "A♣", "A♠"], GameType.SOLO_ACES), 3)

    def test_points(self):
        plays = [Play(i, card(c)) for i, c in enumerate(["A♠", "10♠", "K♠", "9♠"])]
        self.assertEqual(trick_points(plays), 25)


if __name__ == "__main__":
    unittest.main()
