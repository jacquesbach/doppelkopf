"""Spielstaerke der Bots messen: neue Bots (Sitze 0/2) gegen die alte Version (Sitze 1/3), dieselben Kartenverteilungen
in beiden Sitzzuordnungen. Aufruf (im Ordner ``backend``):

    python3 -m tools.bot_tournament [Verteilungen] [Seed] [ddv|alle|ohne9] [einstellung=wert ...]

Einstellungen gelten fuer beide Seiten; mit Praefix nur fuer eine (a.infer=1 b.infer=0: zwei Varianten der neuen Bots
gegeneinander, sonst spielt b die alte Version).

Gibt die Punktesumme beider Seiten aus (Nullsumme) und die Zahl der gewonnenen Spiele. Die alte Version liegt als
``tests/service/legacy_bots.py`` (Grundstrategie ohne Gedaechtnis).
"""
import random
import sys
import time

from tests.rules import loader  # noqa: F401  (``app.rules`` ohne Flask)
from app.rules import DeckVariant, Phase, RuleOptions, apply_action, bot_view, make_profile, new_round, start_next_game
from app.rules.dealing import shuffled_deck
from app.table import bots as new
import tests.service.legacy_bots as old

ALL = RuleOptions(mandatory_announcements=True, solo_leads=True, karlchen_caught=True, schweinchen=True,
                  bock_heart_trick=True, bock_zero_game=True, bock_120=True, second_dulle_wins=True)


def play(game, strat):
    for _ in range(600):
        if game.phase is Phase.FINISHED:
            return
        for seat in range(4):
            action = strat[seat](bot_view(game, seat))
            if action is not None:
                apply_action(game, action)
                break
        else:
            raise AssertionError(game.phase)


def run(n, seed, options, variant, strat_a=new.choose_action, strat_b=old.choose_action):
    profile = make_profile(variant, options)
    rng = random.Random(seed)
    total, wins, games = {"a": 0, "b": 0}, {"a": 0, "b": 0}, 0
    for _ in range(n):
        deck = shuffled_deck(variant, rng)
        for assign in (("a", "b", "a", "b"), ("b", "a", "b", "a")):
            game = start_next_game(new_round(profile), profile, list(deck))
            play(game, [strat_a if x == "a" else strat_b for x in assign])
            games += 1
            for seat, x in enumerate(assign):
                total[x] += game.score.seat_deltas[seat]
            winner = game.score.winner
            if winner:
                for seat, x in enumerate(assign):
                    wins[x] += (seat in game.re_seats) == (winner.value == "re")
    return total, wins, games


def parse(value, current):
    if value in ("0", "1") and isinstance(current, bool):
        return value == "1"
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def with_tune(overrides):
    """Bot mit abweichenden Einstellungen (Vergleich zweier Varianten der neuen Bots)."""
    def choose(view):
        saved = {k: new.TUNE[k] for k in overrides}
        new.TUNE.update(overrides)
        try:
            return new.choose_action(view)
        finally:
            new.TUNE.update(saved)
    return choose


if __name__ == "__main__":
    args = sys.argv[1:]
    n = int(args[0]) if args else 100
    seed = int(args[1]) if len(args) > 1 else 1
    which = args[2] if len(args) > 2 else "ddv"
    side = {"a": {}, "b": {}}
    for flag in args[3:]:
        key, _, value = flag.partition("=")
        target, _, name = key.rpartition(".")
        parsed = parse(value, new.TUNE.get(name))
        if target in ("a", "b"):
            side[target][name] = parsed
        else:
            new.TUNE[name] = parsed
    strat_a = with_tune(side["a"]) if side["a"] else new.choose_action
    strat_b = with_tune(side["b"]) if side["b"] else old.choose_action   # b.xyz=... -> b ist eine Variante der neuen Bots
    start = time.time()
    total, wins, games = run(n, seed, ALL if which == "alle" else RuleOptions(),
                             DeckVariant.WITHOUT_NINES if which == "ohne9" else DeckVariant.WITH_NINES, strat_a, strat_b)
    print(f"{which}: Punkte a {total['a']:+d} / b {total['b']:+d}, Siege {wins['a']}:{wins['b']} "
          f"({games} Spiele, {time.time() - start:.0f}s)")
