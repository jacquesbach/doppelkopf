"""TSR 6.2-6.4: Ansage- und Absagezeitpunkte, Ueberspringen, Erwiderung."""
import unittest

from . import loader  # noqa: F401
from app.rules.announcements import AnnouncementBook, allowed_levels, apply_announcement, check_announcement
from app.rules.errors import RuleViolation
from app.rules.parties import Party

from .fixtures import DDV, HOUSE

RE, KON = Party.RE, Party.KONTRA


def ok(book, party, level, cards, shift=0, profile=DDV):
    check_announcement(profile, book, party, level, cards, shift)


def bad(test, book, party, level, cards, shift=0, profile=DDV, code=None):
    with test.assertRaises(RuleViolation) as cm:
        check_announcement(profile, book, party, level, cards, shift)
    if code:
        test.assertEqual(cm.exception.code, code)


class TimingTests(unittest.TestCase):
    def test_first_announcement_needs_11_cards(self):  # TSR 6.2.2
        b = AnnouncementBook()
        ok(b, RE, 0, 12)
        ok(b, RE, 0, 11)
        bad(self, b, RE, 0, 10, code="announcement_too_late")

    def test_absage_deadlines_10_9_8_7(self):  # TSR 6.3.4
        for level, cards in ((1, 10), (2, 9), (3, 8), (4, 7)):
            b = AnnouncementBook()
            b.re.level = level - 1                      # Vorstufe schon angesagt
            ok(b, RE, level, cards)
            bad(self, b, RE, level, cards - 1, code="announcement_too_late")

    def test_jump_requires_all_skipped_levels_timely(self):  # TSR 6.4.3
        b = AnnouncementBook()
        ok(b, RE, 1, 11)       # 'keine 90' direkt: Re (11) und keine 90 (10) noch zulaessig
        ok(b, RE, 4, 11)       # sogar direkt schwarz
        bad(self, b, RE, 1, 10, code="announcement_too_late")  # Re waere schon zu spaet
        b.re.level = 0
        ok(b, RE, 2, 10)
        bad(self, b, RE, 3, 9)  # keine 60 (9) ok, aber keine 90 (10) uebersprungen und zu spaet

    def test_no_repetition(self):  # TSR 6.4.7
        b = AnnouncementBook()
        apply_announcement(DDV, b, RE, 1, 11)
        for level in (0, 1):
            bad(self, b, RE, level, 11, code="announcement_repeated")
        ok(b, RE, 2, 11)

    def test_parties_have_separate_ladders(self):
        b = AnnouncementBook()
        apply_announcement(DDV, b, RE, 2, 11)
        ok(b, KON, 0, 11)

    def test_unknown_level(self):
        bad(self, AnnouncementBook(), RE, 5, 12, code="unknown_announcement")


class ReplyTests(unittest.TestCase):
    def test_reply_one_card_later_than_opponent_needed(self):  # TSR 6.4.4
        b = AnnouncementBook()
        apply_announcement(DDV, b, RE, 0, 12)
        ok(b, KON, 0, 10)                                       # 11 - 1
        bad(self, b, KON, 0, 9)

    def test_reply_to_absage_is_later_still(self):
        b = AnnouncementBook()
        apply_announcement(DDV, b, RE, 1, 11)                  # keine 90 braucht 10 -> Erwiderung mit 9
        ok(b, KON, 0, 9)
        bad(self, b, KON, 0, 8)
        b2 = AnnouncementBook()
        apply_announcement(DDV, b2, RE, 4, 11)                 # schwarz braucht 7 -> Erwiderung mit 6
        ok(b2, KON, 0, 6)

    def test_no_reply_without_opposing_announcement(self):
        bad(self, AnnouncementBook(), KON, 0, 10)

    def test_reply_is_only_for_re_or_kontra_not_absage(self):
        b = AnnouncementBook()
        apply_announcement(DDV, b, RE, 0, 12)
        bad(self, b, KON, 1, 10)

    def test_late_reply_blocks_own_absagen(self):  # TSR 6.4.4 zweiter Satz
        b = AnnouncementBook()
        apply_announcement(DDV, b, RE, 0, 12)
        apply_announcement(DDV, b, KON, 0, 10)                 # verspaetete Erwiderung
        self.assertTrue(b.kontra.late_reply)
        bad(self, b, KON, 1, 10, code="absage_after_late_reply")

    def test_timely_reply_keeps_absagen(self):
        b = AnnouncementBook()
        apply_announcement(DDV, b, RE, 0, 12)
        apply_announcement(DDV, b, KON, 0, 11)
        self.assertFalse(b.kontra.late_reply)
        ok(b, KON, 1, 10)


class WeddingShiftTests(unittest.TestCase):
    def test_shift_by_clarifying_trick(self):  # TSR 6.4.2
        b = AnnouncementBook()
        ok(b, RE, 0, 10, shift=1)
        bad(self, b, RE, 0, 9, shift=1)
        ok(b, RE, 0, 9, shift=2)
        bad(self, b, RE, 0, 8, shift=2)
        b.re.level = 3
        ok(b, RE, 4, 5, shift=2)                                # schwarz: 7 - 2
        bad(self, b, RE, 4, 4, shift=2)


class ProfileTests(unittest.TestCase):
    def test_no_nines_profile_scales_deadlines(self):
        b = AnnouncementBook()
        ok(b, RE, 0, 9, profile=HOUSE)
        bad(self, b, RE, 0, 8, profile=HOUSE)
        b.re.level = 3
        ok(b, RE, 4, 5, profile=HOUSE)

    def test_allowed_levels(self):
        b = AnnouncementBook()
        self.assertEqual(allowed_levels(DDV, b, RE, 12), [0, 1, 2, 3, 4])
        self.assertEqual(allowed_levels(DDV, b, RE, 10), [])
        apply_announcement(DDV, b, RE, 0, 11)
        self.assertEqual(allowed_levels(DDV, b, RE, 10), [1, 2, 3, 4])
        # Eine uebersprungene Absage laesst sich nicht nachholen (TSR 6.4.3 letzter Satz):
        self.assertEqual(allowed_levels(DDV, b, RE, 9), [])
        self.assertEqual(allowed_levels(DDV, b, KON, 10), [0])       # nur Erwiderung


if __name__ == "__main__":
    unittest.main()
