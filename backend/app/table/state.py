"""Tisch = vier Sitze + Regelprofil + Spielrunde + laufendes Einzelspiel (flask-frei, JSON-serialisierbar)."""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..rules import (GameState, Phase, RoundState, RuleProfile, RuleViolation, is_round_finished,
                     new_round, next_setup, player_view, record_game, spectator_view, start_next_game)
from ..rules.dealing import shuffled_deck


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Bot-Uebernahme bei Inaktivitaet: Auswahl des Hosts (Sekunden; 0 = nie), Standard und Vorwarnzeit (Countdown-Dialog).
TAKEOVER_CHOICES = (0, 60, 120, 180, 300, 600, 1800)
DEFAULT_TAKEOVER = 180
WARN_SECONDS = 30


@dataclass
class TableState:
    seats: list[dict]                 # Index = Sitz 0..3: {"memberId", "name", "isBot"}
    profile: RuleProfile
    round: RoundState
    game: GameState
    game_number: int = 1              # wievieltes gegebenes Spiel der Runde (inkl. Pflichtsoli)
    recorded: bool = False            # aktuelles, beendetes Spiel ist in der Runde gebucht
    finished: bool = False            # Runde komplett gespielt
    game_started_at: str = field(default_factory=_now)
    holding: bool = False             # Bots warten nach einem Stich auf "Naechster Stich" (nur Spiel gegen Bots)
    takeover: int = DEFAULT_TAKEOVER  # Sekunden Inaktivitaet bis zur Bot-Uebernahme; 0 = nie (Einstellung des Hosts)
    touched: float | None = None      # Unix-Zeit der letzten Zustandsaenderung (Inaktivitaetsuhr, ueberlebt Neustarts)
    warning: dict | None = None       # {"seat", "until"}: Countdown laeuft, danach uebernimmt ein Bot fuer den Sitz
    redeals: int = 0                  # wie oft in diesem Spiel neu gegeben wurde (Armut ohne Kaeufer); nicht gebucht
    redeal_seat: int | None = None    # wessen Armut zuletzt niemand uebernahm

    def to_dict(self) -> dict:
        return {"seats": [dict(s) for s in self.seats], "profile": self.profile.to_dict(),
                "round": self.round.to_dict(), "game": self.game.to_dict(), "gameNumber": self.game_number,
                "recorded": self.recorded, "finished": self.finished, "gameStartedAt": self.game_started_at,
                "holding": self.holding, "takeover": self.takeover, "touched": self.touched,
                "warning": dict(self.warning) if self.warning else None,
                "redeals": self.redeals, "redealSeat": self.redeal_seat}

    @staticmethod
    def from_dict(d: dict) -> "TableState":
        return TableState([dict(s) for s in d["seats"]], RuleProfile.from_dict(d["profile"]),
                          RoundState.from_dict(d["round"]), GameState.from_dict(d["game"]), d["gameNumber"],
                          d["recorded"], d["finished"], d["gameStartedAt"], d.get("holding", False),
                          d.get("takeover", DEFAULT_TAKEOVER), d.get("touched"), d.get("warning"),
                          d.get("redeals", 0), d.get("redealSeat"))

    def seat_of(self, member_id: int) -> int | None:
        return next((i for i, s in enumerate(self.seats) if s["memberId"] == member_id), None)

    @property
    def bot_seats(self) -> list[bool]:
        """Sitze, fuer die der Server spielt: Bots und Spieler, die weg sind (``autoplay``)."""
        return [bool(s["isBot"] or s.get("autoplay")) for s in self.seats]

    @property
    def humans_present(self) -> int:
        """Menschen, die selbst spielen (nicht Bot, nicht von einem Bot vertreten)."""
        return sum(not s["isBot"] and not s.get("autoplay") for s in self.seats)

    def takeover_idle(self, seat: int) -> int | None:
        """Sekunden Inaktivitaet, nach denen ein Bot fuer ``seat`` einspringt - ``None``: nie.

        Nie, wenn der Host es abgeschaltet hat, der Spieler es abgelehnt hat ("Entscheidung merken") oder wenn dieser
        eine Mensch allein gegen Bots spielt: Dann wartet niemand auf ihn und der Tisch darf einfach stehen bleiben.
        """
        if self.takeover <= 0 or self.seats[seat].get("noTakeover") or self.humans_present < 2:
            return None
        return self.takeover

    @property
    def manual_continue(self) -> bool:
        """Genau ein Mensch am Tisch: nach jedem Stich wartet das Spiel auf "Naechster Stich"."""
        return sum(not s["isBot"] for s in self.seats) == 1 and not any(s.get("autoplay") for s in self.seats)


def new_table(seats: list[dict], profile: RuleProfile, rng: random.Random | None = None,
              takeover: int = DEFAULT_TAKEOVER) -> TableState:
    if len(seats) != 4 or len({s["memberId"] for s in seats}) != 4:
        raise RuleViolation("bad_seats", "Ein Tisch braucht vier verschiedene Sitze.")
    rnd = new_round(profile)
    game = start_next_game(rnd, profile, shuffled_deck(profile.deck_variant, rng))
    table_seats = []
    for s in seats:
        entry = {"memberId": s["memberId"], "name": s["name"], "isBot": bool(s["isBot"])}
        if s.get("noTakeover"):
            entry["noTakeover"] = True
        table_seats.append(entry)
    return TableState(table_seats, profile, rnd, game, takeover=takeover)


def settle(table: TableState) -> dict | None:
    """Bucht ein beendetes Spiel genau einmal in die Runde. Gibt eine Spielzusammenfassung zurueck."""
    game = table.game
    if game.phase is not Phase.FINISHED or table.recorded:
        return None
    record_game(table.round, game)
    table.recorded = True
    table.finished = is_round_finished(table.round, table.profile)
    return {"gameNumber": table.game_number, "startedAt": table.game_started_at, "finishedAt": _now(),
            "kind": game.kind.value, "gameType": game.game_type.value, "soloSeat": game.solo_seat,
            "reSeats": list(game.re_seats),
            "winner": game.score.winner.value if game.score.winner else None,
            "seatDeltas": list(game.score.seat_deltas), "multiplier": game.score_multiplier,
            "bockTriggers": list(game.bock_triggers), "roundFinished": table.finished,
            "totals": list(table.round.totals)}


def redeal_if_needed(table: TableState, rng: random.Random | None = None) -> bool:
    """Armut ohne Kaeufer: Das Blatt wird eingepackt und mit demselben Geber neu gegeben.

    Das abgebrochene Spiel zaehlt nicht (kein Eintrag in der Runde, kein Bockspiel verbraucht, Spielnummer bleibt).
    """
    game = table.game
    if game.phase is not Phase.REDEAL:
        return False
    table.redeal_seat = game.redeal_seat
    table.redeals += 1
    table.game = start_next_game(table.round, table.profile, shuffled_deck(table.profile.deck_variant, rng))
    table.game_started_at = _now()
    return True


def start_next(table: TableState, rng: random.Random | None = None) -> None:
    """Naechstes Spiel der Runde geben (nur nach gebuchtem, beendetem Spiel)."""
    if table.finished:
        raise RuleViolation("round_finished", "Die Spielrunde ist beendet.")
    if table.game.phase is not Phase.FINISHED or not table.recorded:
        raise RuleViolation("game_running", "Das aktuelle Spiel ist noch nicht beendet.")
    table.game = start_next_game(table.round, table.profile, shuffled_deck(table.profile.deck_variant, rng))
    table.game_number += 1
    table.redeals, table.redeal_seat = 0, None
    table.recorded = False
    table.game_started_at = _now()


def _round_view(table: TableState) -> dict:
    rnd = table.round
    info = {"dealer": rnd.dealer, "normalGamesPlayed": rnd.normal_games_played,
            "normalGamesTotal": table.profile.normal_games_per_round,
            "pflichtsoloDone": list(rnd.pflichtsolo_done), "totals": list(rnd.totals),
            "bockRemaining": rnd.bock_remaining, "results": list(rnd.results)}
    if table.recorded and not table.finished:
        setup = next_setup(rnd, table.profile)
        info["next"] = {"dealer": setup.dealer, "forcedSoloSeat": setup.forced_solo_seat}
    return info


def _warning_view(table: TableState, now: float) -> dict | None:
    w = table.warning
    return None if not w else {"seat": w["seat"], "remaining": max(0, int(w["until"] - now + 0.999))}


def view_for(table: TableState, member_id: int | None, version: int, now: float | None = None) -> dict:
    """Personalisierte Sicht. Zuschauer/Unbekannte bekommen nie Haende."""
    now = time.time() if now is None else now
    seat = table.seat_of(member_id) if member_id is not None else None
    game = player_view(table.game, seat) if seat is not None else spectator_view(table.game)
    return {
        "version": version,
        "table": {"seats": [{"seat": i, "memberId": s["memberId"], "name": s["name"], "isBot": s["isBot"],
                            "autoplay": bool(s.get("autoplay")), "noTakeover": bool(s.get("noTakeover"))}
                           for i, s in enumerate(table.seats)],
                  "mySeat": seat, "gameNumber": table.game_number, "gameRecorded": table.recorded,
                  "holding": table.holding, "takeover": table.takeover,
                  "redeals": table.redeals, "redealSeat": table.redeal_seat,
                  "takeoverWarning": _warning_view(table, now),
                  "finished": table.finished, "profileId": table.profile.id.value,
                  "deckVariant": table.profile.deck_variant.value,
                  "ruleOptions": table.profile.options.to_dict(), "round": _round_view(table)},
        "game": game,
    }
