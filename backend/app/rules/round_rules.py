"""Spielrunde: 24 Normalspiele, Pflichtsolo, Vorfuehrung, Geberfortschreibung (TSR 3.3.1, 4.2, 4.3, 8.5-8.6).

Tisch, Spielrunde und Einzelspiel sind getrennte Modelle (Briefing M0): ``RoundState`` kennt
nur Zaehler und Summen; die Karten leben im ``GameState`` des Einzelspiels.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .cards import Card
from .errors import RuleViolation
from .game import GameKind, GameState, Phase, new_game
from .profile import RuleProfile

# Buchung in der Rubrik "Normalspiele" (zaehlt auf die 24 Spiele, Geber wechselt) - TSR 4.3.2, 4.4.3, 4.4.5
_NORMAL_RUBRIC = (GameKind.NORMAL, GameKind.LUSTSOLO, GameKind.WEDDING, GameKind.SILENT_WEDDING,
                  GameKind.POVERTY)


@dataclass
class GameSetup:
    dealer: int
    forced_solo_seat: int | None


@dataclass
class RoundState:
    profile_id: str
    deck_variant: str
    rule_options: dict = field(default_factory=dict)
    bock_remaining: int = 0                            # noch offene Bockspiele (Hausregel, Punkte x2)
    dealer: int = 0                                    # Position 1 gibt zuerst (TSR 3.3.1)
    normal_games_played: int = 0
    pflichtsolo_done: list[bool] = field(default_factory=lambda: [False] * 4)
    totals: list[int] = field(default_factory=lambda: [0] * 4)
    results: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"profileId": self.profile_id, "deckVariant": self.deck_variant,
                "ruleOptions": dict(self.rule_options), "bockRemaining": self.bock_remaining, "dealer": self.dealer,
                "normalGamesPlayed": self.normal_games_played,
                "pflichtsoloDone": list(self.pflichtsolo_done), "totals": list(self.totals),
                "results": list(self.results)}

    @staticmethod
    def from_dict(d: dict) -> "RoundState":
        return RoundState(d["profileId"], d["deckVariant"], dict(d.get("ruleOptions", {})),
                          d.get("bockRemaining", 0), d["dealer"], d["normalGamesPlayed"],
                          list(d["pflichtsoloDone"]), list(d["totals"]), list(d["results"]))


def new_round(profile: RuleProfile) -> RoundState:
    return RoundState(profile.id.value, profile.deck_variant.value, profile.options.to_dict())


def is_round_finished(rnd: RoundState, profile: RuleProfile) -> bool:
    return rnd.normal_games_played >= profile.normal_games_per_round and all(rnd.pflichtsolo_done)


def next_setup(rnd: RoundState, profile: RuleProfile) -> GameSetup:
    """Wer gibt, und wird jemand zum Pflichtsolo vorgefuehrt (TSR 4.2.3)?

    Vorfuehrung, wenn die Zahl der fehlenden Pflichtsoli gleich der Zahl der noch zu
    spielenden Normalspiele ist: es trifft den ersten Spieler links vom Geber, dem eines fehlt.
    """
    if is_round_finished(rnd, profile):
        raise RuleViolation("round_finished", "Die Spielrunde ist beendet.")
    missing = rnd.pflichtsolo_done.count(False)
    remaining = profile.normal_games_per_round - rnd.normal_games_played
    forced = None
    if missing and missing >= remaining:
        forced = next(s for s in ((rnd.dealer + k) % 4 for k in range(1, 5)) if not rnd.pflichtsolo_done[s])
    return GameSetup(rnd.dealer, forced)


def start_next_game(rnd: RoundState, profile: RuleProfile, order: Sequence[Card]) -> GameState:
    setup = next_setup(rnd, profile)
    multiplier = 2 if rnd.bock_remaining > 0 else 1    # Bockrunde: Punkte verdoppelt
    return new_game(profile, order, setup.dealer, rnd.pflichtsolo_done, setup.forced_solo_seat, multiplier)


def record_game(rnd: RoundState, game: GameState) -> None:
    """Bucht ein beendetes Einzelspiel: Summen, Pflichtsolo-Status, Geberfortschreibung."""
    if game.phase is not Phase.FINISHED or game.score is None:
        raise RuleViolation("game_not_finished", "Nur beendete Spiele koennen gebucht werden.")
    kind = game.kind
    if kind is GameKind.PFLICHTSOLO:
        rnd.pflichtsolo_done[game.solo_seat] = True    # selber Geber gibt noch einmal (TSR 4.2.5)
    elif kind is GameKind.PFLICHTSOLO_FORCED:
        rnd.pflichtsolo_done[game.solo_seat] = True
        rnd.dealer = (rnd.dealer + 1) % 4              # nach Vorfuehrung gibt der naechste Spieler
    elif kind in _NORMAL_RUBRIC:
        rnd.normal_games_played += 1
        rnd.dealer = (rnd.dealer + 1) % 4              # Lustsolo/Hochzeit: anderer Geber (TSR 4.3.2)
    else:  # pragma: no cover - alle Arten sind oben abgedeckt
        raise AssertionError(kind)
    if game.score_multiplier > 1 and rnd.bock_remaining > 0:   # dieses Bockspiel ist verbraucht
        rnd.bock_remaining -= 1
    rnd.bock_remaining += game.profile.bock_length * len(game.bock_triggers)   # neue Bockrunden danach
    for seat, delta in enumerate(game.score.seat_deltas):
        rnd.totals[seat] += delta
    rnd.results.append({"kind": kind.value, "gameType": game.game_type.value,
                        "soloSeat": game.solo_seat, "deltas": list(game.score.seat_deltas),
                        "winner": game.score.winner.value if game.score.winner else None,
                        "multiplier": game.score_multiplier, "bockTriggers": list(game.bock_triggers)})
