"""Rate-Limiter (Aufraeumen, Obergrenze), Zugangs-Schutz und Platz-Code."""
import unittest
from datetime import datetime, timezone

from ..rules import loader  # noqa: F401
from app import seatcode
from app.community.ratelimit import MAX_KEYS, SWEEP_EVERY, RateLimiter
from app.guard import AccessGuard, FAIL_LIMIT, FAIL_WINDOW, MISS_LIMIT, client_ip


class RateLimiterCleanupTests(unittest.TestCase):
    def test_unused_keys_disappear_without_being_touched_again(self):
        t = [0.0]
        rl = RateLimiter(clock=lambda: t[0])
        for i in range(500):
            rl.allow(f"ip{i}", 5, 60)
        self.assertEqual(len(rl), 500)
        t[0] = 61 + SWEEP_EVERY
        rl.allow("neu", 5, 60)                      # ein beliebiger Zugriff genuegt: alte Schluessel sind weg
        self.assertEqual(len(rl), 1)

    def test_keys_with_longer_window_stay_until_their_window_ends(self):
        t = [0.0]
        rl = RateLimiter(clock=lambda: t[0])
        rl.allow("stunde", 1, 3600)
        rl.allow("minute", 1, 60)
        t[0] = 120
        rl.allow("x", 1, 60)
        self.assertFalse(rl.allow("stunde", 1, 3600))
        t[0] = 3600
        self.assertTrue(rl.allow("stunde", 1, 3600))

    def test_hard_cap_evicts_least_recently_used(self):
        t = [0.0]
        rl = RateLimiter(clock=lambda: t[0], max_keys=50)
        for i in range(500):
            t[0] += 0.001
            rl.allow(f"k{i}", 3, 3600)
        self.assertLessEqual(len(rl), 50)
        self.assertGreater(MAX_KEYS, 1000)
        self.assertFalse(rl.peek("k499", 1, 3600) is False)          # juengster Schluessel ist noch da

    def test_denied_attempt_does_not_count_and_limit_holds(self):
        t = [0.0]
        rl = RateLimiter(clock=lambda: t[0])
        self.assertEqual([rl.allow("k", 2, 10) for _ in range(4)], [True, True, False, False])
        t[0] = 10.0
        self.assertTrue(rl.allow("k", 2, 10))

    def test_peek_and_record(self):
        t = [0.0]
        rl = RateLimiter(clock=lambda: t[0])
        self.assertFalse(rl.peek("k", 2, 10))
        rl.record("k", 10)
        self.assertFalse(rl.peek("k", 2, 10))
        rl.record("k", 10)
        self.assertTrue(rl.peek("k", 2, 10))
        t[0] = 11
        self.assertFalse(rl.peek("k", 2, 10))
        rl.reset("k")
        self.assertEqual(len(rl), 0)


class AccessGuardTests(unittest.TestCase):
    def make(self, **kw):
        self.t = [0.0]
        return AccessGuard(RateLimiter(clock=lambda: self.t[0]), **kw)

    def test_create_limit_per_ip_and_hour(self):
        g = self.make(create_per_hour=3)
        self.assertEqual([g.allow_create("1.1.1.1") for _ in range(4)], [True, True, True, False])
        self.assertTrue(g.allow_create("2.2.2.2"))
        self.t[0] = 3600
        self.assertTrue(g.allow_create("1.1.1.1"))

    def test_failed_attempts_block_per_ip_and_table_then_recover(self):
        g = self.make()
        for _ in range(FAIL_LIMIT):
            self.assertFalse(g.blocked("1.1.1.1", "ABC234"))
            g.failed("1.1.1.1", "ABC234")
        self.assertTrue(g.blocked("1.1.1.1", "ABC234"))
        self.assertFalse(g.blocked("1.1.1.1", "XYZ234"))          # anderer Tisch
        self.assertFalse(g.blocked("9.9.9.9", "ABC234"))          # andere Adresse
        self.t[0] = FAIL_WINDOW + 1
        self.assertFalse(g.blocked("1.1.1.1", "ABC234"))

    def test_success_clears_failures(self):
        g = self.make()
        for _ in range(FAIL_LIMIT - 1):
            g.failed("ip", "ABC234")
        g.succeeded("ip", "ABC234")
        g.failed("ip", "ABC234")
        self.assertFalse(g.blocked("ip", "ABC234"))

    def test_guessing_many_codes_blocks_lookups_but_one_stale_code_does_not(self):
        g = self.make()
        for _ in range(500):                                       # offener Tab eines beendeten Tisches
            g.missed("fam", "GONE22")
        self.assertFalse(g.lookups_blocked("fam"))
        for i in range(MISS_LIMIT):
            g.missed("bot", f"AAAAA{i:01d}"[:6].ljust(6, "A") + str(i))
        self.assertTrue(g.lookups_blocked("bot"))
        self.assertFalse(g.lookups_blocked("fam"))

    def test_disabled_guard_never_blocks(self):
        g = self.make(enabled=False)
        for _ in range(100):
            g.failed("ip", "ABC234")
            g.missed("ip", "ABC234")
            self.assertTrue(g.allow_create("ip"))
        self.assertFalse(g.blocked("ip", "ABC234"))
        self.assertFalse(g.lookups_blocked("ip"))

    def test_client_ip_only_trusts_proxy_when_configured(self):
        headers = {"X-Forwarded-For": "6.6.6.6, 10.0.0.9"}
        self.assertEqual(client_ip(headers, "172.18.0.2", True), "10.0.0.9")     # letzter Eintrag: vom eigenen Proxy
        self.assertEqual(client_ip(headers, "172.18.0.2", False), "172.18.0.2")
        self.assertEqual(client_ip({}, None, False), "unknown")

    def test_ipv6_is_counted_per_64_network(self):
        a = client_ip({}, "2001:db8:1:2:aaaa:bbbb:cccc:dddd", False)
        b = client_ip({}, "2001:db8:1:2:1111:2222:3333:4444", False)
        self.assertEqual(a, b)
        self.assertEqual(a, "2001:db8:1:2::/64")
        self.assertNotEqual(a, client_ip({}, "2001:db8:1:3::1", False))
        self.assertEqual(client_ip({"X-Forwarded-For": "1.2.3.4, 2001:db8::5"}, "172.18.0.2", True), "2001:db8::/64")


class SeatCodeTests(unittest.TestCase):
    JOINED = datetime(2026, 11, 20, 9, 30, 15, 123456, tzinfo=timezone.utc)

    def test_deterministic_format_and_alphabet(self):
        a = seatcode.seat_code("geheim", "ABC234", 7, self.JOINED)
        self.assertEqual(a, seatcode.seat_code("geheim", "ABC234", 7, self.JOINED))
        self.assertEqual(len(a), 8)
        self.assertTrue(all(ch in seatcode.ALPHABET for ch in a))
        self.assertEqual(seatcode.display(a), f"{a[:4]}-{a[4:]}")

    def test_naive_and_aware_timestamps_give_the_same_code(self):
        self.assertEqual(seatcode.seat_code("s", "ABC234", 1, self.JOINED),
                         seatcode.seat_code("s", "ABC234", 1, self.JOINED.replace(tzinfo=None)))

    def test_every_input_changes_the_code(self):
        base = seatcode.seat_code("geheim", "ABC234", 7, self.JOINED)
        self.assertNotEqual(base, seatcode.seat_code("anders", "ABC234", 7, self.JOINED))
        self.assertNotEqual(base, seatcode.seat_code("geheim", "ABC235", 7, self.JOINED))
        self.assertNotEqual(base, seatcode.seat_code("geheim", "ABC234", 8, self.JOINED))
        self.assertNotEqual(base, seatcode.seat_code("geheim", "ABC234", 7, self.JOINED.replace(microsecond=1)))

    def test_codes_are_spread_over_many_values(self):
        codes = {seatcode.seat_code("geheim", "ABC234", i, self.JOINED) for i in range(2000)}
        self.assertEqual(len(codes), 2000)

    def test_parse_and_match(self):
        code = seatcode.seat_code("geheim", "ABC234", 7, self.JOINED)
        shown = seatcode.display(code)
        self.assertTrue(seatcode.matches(code, shown))
        self.assertTrue(seatcode.matches(code, shown.lower()))
        self.assertTrue(seatcode.matches(code, f" {code[:4]} {code[4:]} "))
        for bad in (None, "", 5, code[:-1], code + "A", "ABCD-EFG0", "<script>", seatcode.display("AAAAAAAA")):
            self.assertFalse(seatcode.matches(code, bad), bad)


if __name__ == "__main__":
    unittest.main()


class AdminSessionTests(unittest.TestCase):
    def make(self, **kw):
        from app.community.admin_auth import AdminAuth
        self.now = [1000.0]
        return AdminAuth("geheim-geheim", "secret", clock=lambda: self.now[0], limiter=RateLimiter(clock=lambda: 0.0), **kw)

    def test_default_lifetime_is_two_hours(self):
        from app.community.admin_auth import TOKEN_TTL
        self.assertEqual(TOKEN_TTL, 7200)

    def test_token_is_opaque_and_expires(self):
        auth = self.make(ttl=60)
        token = auth.login("geheim-geheim", "ip")
        self.assertNotIn(".", token)
        self.assertTrue(auth.verify(token))
        self.assertFalse(auth.verify(token + "x"))
        self.assertFalse(auth.verify(""))
        self.now[0] += 61
        self.assertFalse(auth.verify(token))
        self.assertEqual(auth.session_count(), 0)

    def test_logout_revokes_only_that_session(self):
        auth = self.make()
        a, b = auth.login("geheim-geheim", "ip"), auth.login("geheim-geheim", "ip")
        self.assertNotEqual(a, b)
        self.assertTrue(auth.logout(a))
        self.assertFalse(auth.verify(a))
        self.assertTrue(auth.verify(b))
        self.assertFalse(auth.logout(a))

    def test_logout_all(self):
        auth = self.make()
        tokens = [auth.login("geheim-geheim", "ip") for _ in range(3)]
        self.assertEqual(auth.logout_all(), 3)
        self.assertFalse(any(auth.verify(t) for t in tokens))

    def test_session_cap_drops_oldest(self):
        from app.community.admin_auth import MAX_SESSIONS
        auth = self.make()
        first = auth.login("geheim-geheim", "ip")
        for _ in range(MAX_SESSIONS):
            self.now[0] += 1
            last = auth.login("geheim-geheim", "ip")
        self.assertFalse(auth.verify(first))
        self.assertTrue(auth.verify(last))
        self.assertEqual(auth.session_count(), MAX_SESSIONS)

    def test_disabled_without_password(self):
        from app.community.admin_auth import AdminAuth
        auth = AdminAuth("", "secret")
        self.assertIsNone(auth.login("", "ip"))
        self.assertFalse(auth.verify("irgendwas"))
