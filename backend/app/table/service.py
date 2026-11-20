"""Tischdienst: Aktion annehmen -> pruefen -> Bots laufen lassen -> buchen -> speichern (flask-frei)."""
from __future__ import annotations

import random
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from ..rules import DuplicateAction, Phase, RuleProfile, RuleViolation, VersionConflict, apply_action
from .actions import parse_action
from .bots import next_bot_action
from .state import (DEFAULT_TAKEOVER, TAKEOVER_CHOICES, WARN_SECONDS, TableState, new_table, redeal_if_needed, settle,
                    start_next, view_for)
from .store import Stored, TableStore


class AccessDenied(Exception):
    """Mitglied ist kein Spieler dieses Tisches / nicht berechtigt."""


class NoSuchTable(LookupError):
    """Fuer den Raum laeuft kein Spiel."""


@dataclass
class Outcome:
    version: int
    duplicate: bool = False
    summaries: list[dict] = field(default_factory=list)


# Bedenkzeiten im getakteten Betrieb (Sekunden)
THINK = (1.0, 1.7)      # Botkarte
SHORT = 1.2             # Taufe, Ansage, Vorbehalts-Entscheidung (Solo/Armut)
DECLARE = 1.7           # Vorbehaltsabfrage ("gesund"/"Vorbehalt"): so lange, dass man jede Antwort mitlesen kann
REVEAL = 3.0            # nach der letzten Antwort: Ergebnis der Abfrage bleibt sichtbar, bevor die erste Karte faellt
TRICK_PAUSE = 2.4       # nach einem vollstaendigen Stich: alle sollen ihn sehen koennen


MAX_BOT_STEPS = 400  # Schutz vor Endlosschleifen; ein Spiel hat < 120 Aktionen


def _acting_seat(game) -> int | None:
    """Sitz, von dem gerade eine Handlung erwartet wird."""
    if game.phase is Phase.RESERVATION_QUERY:
        return game.query_seat
    if game.phase is Phase.RESERVATION_RESOLUTION:
        return game.resolution_queue[0] if game.resolution_queue else None
    if game.phase is Phase.BAPTISM:
        return game.baptism_seat
    if game.phase is Phase.POVERTY_PASS:
        return game.poverty_seat
    if game.phase is Phase.POVERTY_OFFER:
        return game.poverty_queue[0] if game.poverty_queue else None
    if game.phase is Phase.POVERTY_RETURN:
        return game.poverty_buyer
    if game.phase is Phase.PLAYING:
        return game.mandatory_pending if game.mandatory_pending is not None else game.turn
    return None


def _just_after_reservations(game) -> bool:
    """Spiel hat gerade begonnen, nachdem eine Vorbehaltsabfrage stattfand: noch keine Karte gespielt."""
    if game.tricks or game.current_trick or not game.log:
        return False
    return game.log[-1].get("type") == "play_started" and any(e.get("type") == "declared" for e in game.log)


def run_bots(table: TableState, rng: random.Random | None = None) -> list[dict]:
    """Laesst Bots handeln, bis ein Mensch dran ist oder das Spiel endet; bucht das Spielende.

    Wird eine Armut von niemandem uebernommen, wird neu gegeben (``rng`` mischt) und weitergespielt."""
    summaries: list[dict] = []
    for _ in range(MAX_BOT_STEPS):
        pending = next_bot_action(table.game, table.bot_seats)
        if pending is None:
            break
        seat, action = pending
        apply_action(table.game, action)
        redeal_if_needed(table, rng)
    else:  # pragma: no cover - waere ein Fehler in der Bot-Logik
        raise RuntimeError("Bot-Schleife terminiert nicht")
    summary = settle(table)
    if summary:
        summaries.append(summary)
    return summaries


def _trick_completed(table: TableState, tricks_before: int) -> bool:
    return len(table.game.tricks) > tricks_before and table.game.phase is Phase.PLAYING


def _maybe_hold(table: TableState, tricks_before: int) -> None:
    """Spiel gegen Bots: nach einem Stich wartet der Botbetrieb auf "Naechster Stich"."""
    if _trick_completed(table, tricks_before) and table.manual_continue:
        turn = table.game.turn
        if turn is not None and table.bot_seats[turn]:
            table.holding = True


class TableService:
    def __init__(self, store: TableStore, rng: random.Random | None = None, paced: bool = False,
                 clock=time.time) -> None:
        """``paced=True``: Bots spielen nicht innerhalb des Requests, sondern getaktet ueber ``BotRunner``.

        ``clock`` liefert die Unix-Zeit fuer die Inaktivitaetsuhr (in Tests ersetzbar).
        """
        self.store = store
        self.rng = rng
        self.paced = paced
        self.clock = clock
        self._locks: dict[str, threading.Lock] = defaultdict(threading.Lock)
        self._meta = threading.Lock()

    def _lock(self, code: str) -> threading.Lock:
        with self._meta:
            return self._locks[code]

    # --- Lesen ---
    def load(self, code: str) -> Stored | None:
        return self.store.load(code)

    def view(self, code: str, member_id: int | None) -> dict | None:
        stored = self.store.load(code)
        return None if stored is None else view_for(stored.table, member_id, stored.version, self.clock())

    def _save(self, code: str, table: TableState, expected: int, summaries: list[dict],
              warning: dict | None = None) -> int:
        """Speichert und stellt die Inaktivitaetsuhr: Jede Aenderung setzt sie zurueck und beendet einen Countdown."""
        table.touched = self.clock()
        table.warning = warning
        return self.store.save(code, table, expected, summaries)

    # --- Schreiben ---
    def start(self, code: str, seats: list[dict], profile: RuleProfile, takeover: int = DEFAULT_TAKEOVER) -> int:
        """Neue Runde beginnen (ersetzt einen alten Tisch dieses Raums).

        Wer in der vorigen Runde "nie durch einen Bot ersetzen" gewaehlt hat, behaelt das (gleiche ``memberId``).
        """
        if takeover not in TAKEOVER_CHOICES:
            raise RuleViolation("bad_request", "Ungueltige Zeit fuer die Bot-Uebernahme.")
        with self._lock(code):
            previous = self.store.load(code)
            kept = {s["memberId"] for s in previous.table.seats if s.get("noTakeover")} if previous else set()
            seats = [dict(s, noTakeover=True) if s["memberId"] in kept else s for s in seats]
            table = new_table(seats, profile, self.rng, takeover)
            table.touched = self.clock()
            summaries = [] if self.paced else run_bots(table, self.rng)
            version = self.store.create(code, table)
            if summaries:  # nur moeglich, wenn alle Sitze Bots sind
                version = self._save(code, table, version, summaries)
            return version

    def install(self, code: str, table: TableState) -> int:
        """Fertig gebauten Tisch (z. B. Test-Tisch mit festen Karten) einsetzen; ersetzt einen vorhandenen Tisch."""
        with self._lock(code):
            table.touched = self.clock()
            summaries = [] if self.paced else run_bots(table, self.rng)
            version = self.store.create(code, table)
            if summaries:
                version = self._save(code, table, version, summaries)
            return version

    def act(self, code: str, member_id: int, payload: dict) -> Outcome:
        expected = payload.get("expectedVersion")
        action_id = payload.get("actionId")
        if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool)):
            raise RuleViolation("bad_request", "expectedVersion muss eine Zahl sein.")
        if action_id is not None and (not isinstance(action_id, str) or not 0 < len(action_id) <= 64):
            raise RuleViolation("bad_request", "actionId muss ein String (max. 64 Zeichen) sein.")
        with self._lock(code):
            stored = self._require(code)
            table = stored.table
            seat = table.seat_of(member_id)
            if seat is None:
                raise AccessDenied("Nur Spieler dieses Tisches koennen handeln.")
            if expected is not None and expected != stored.version:
                raise VersionConflict(expected, stored.version)
            action = parse_action(seat, payload)
            tricks_before = len(table.game.tricks)
            try:
                apply_action(table.game, action, action_id=action_id)
            except DuplicateAction:                # Wiederholung desselben Requests: Erfolg ohne Wirkung
                return Outcome(stored.version, duplicate=True)
            redeal_if_needed(table, self.rng)
            table.seats[seat].pop("autoplay", None)     # wer handelt, ist wieder da
            _maybe_hold(table, tricks_before)
            summaries = [s for s in [settle(table)] if s]
            if not self.paced:
                summaries += run_bots(table, self.rng)
            version = self._save(code, table, stored.version, summaries)
            return Outcome(version, summaries=summaries)

    def next_game(self, code: str, member_id: int) -> Outcome:
        with self._lock(code):
            stored = self._require(code)
            table = stored.table
            if table.seat_of(member_id) is None:
                raise AccessDenied("Nur Spieler dieses Tisches koennen das naechste Spiel starten.")
            start_next(table, self.rng)
            table.holding = False
            summaries = [] if self.paced else run_bots(table, self.rng)
            return Outcome(self._save(code, table, stored.version, summaries), summaries=summaries)

    def _require(self, code: str) -> Stored:
        stored = self.store.load(code)
        if stored is None:
            raise NoSuchTable("Fuer diesen Raum laeuft noch kein Spiel.")
        return stored

    # --- Getakteter Botbetrieb ---
    def pending_delay(self, code: str) -> float | None:
        """Wartezeit vor dem naechsten Botzug oder ``None``, wenn kein Bot dran ist (oder der Mensch "weiter" druecken muss)."""
        stored = self.store.load(code)
        if stored is None:
            return None
        table = stored.table
        if table.holding or next_bot_action(table.game, table.bot_seats) is None:
            return None
        game = table.game
        if game.phase is Phase.PLAYING:
            if not game.current_trick and game.tricks:
                return TRICK_PAUSE
            if _just_after_reservations(game):
                return REVEAL
            return (self.rng or random).uniform(*THINK)
        if game.phase is Phase.RESERVATION_QUERY:
            return DECLARE
        return SHORT

    def bot_step(self, code: str) -> "Outcome | None":
        """Genau einen Botzug ausfuehren und speichern."""
        with self._lock(code):
            stored = self.store.load(code)
            if stored is None:
                return None
            table = stored.table
            if table.holding:
                return None
            pending = next_bot_action(table.game, table.bot_seats)
            if pending is None:
                return None
            _, action = pending
            tricks_before = len(table.game.tricks)
            apply_action(table.game, action)
            redeal_if_needed(table, self.rng)
            _maybe_hold(table, tricks_before)
            summaries = [s for s in [settle(table)] if s]
            return Outcome(self._save(code, table, stored.version, summaries), summaries=summaries)

    def release(self, code: str, member_id: int) -> Outcome:
        """"Naechster Stich": hebt das Warten des Botbetriebs auf."""
        with self._lock(code):
            stored = self._require(code)
            table = stored.table
            if table.seat_of(member_id) is None:
                raise AccessDenied("Nur Spieler dieses Tisches koennen weiterspielen.")
            if not table.holding:
                return Outcome(stored.version, duplicate=True)
            table.holding = False
            return Outcome(self._save(code, table, stored.version, []))

    def waiting_on(self, code: str) -> tuple[int, int] | None:
        """(memberId, version) des Menschen, auf den gewartet wird UND der ersetzt werden duerfte - sonst ``None``.

        ``None`` heisst fuer den Botbetrieb: nichts zu ueberwachen (kein Mensch dran, Uebernahme abgeschaltet, der
        Spieler hat sie abgelehnt oder er spielt als einziger Mensch gegen Bots). Dann laeuft keine Wartschleife.
        """
        stored = self.store.load(code)
        if stored is None:
            return None
        table = stored.table
        game = table.game
        if game.phase is Phase.FINISHED or table.holding:
            return None
        seat = _acting_seat(game)
        if seat is None or table.bot_seats[seat] or table.takeover_idle(seat) is None:
            return None
        return table.seats[seat]["memberId"], stored.version

    def watch_tick(self, code: str) -> "Outcome | None":
        """Inaktivitaetsuhr des wartenden Menschen pruefen (der Botbetrieb ruft das im Wartetakt auf).

        Nach ``takeover`` Sekunden ohne Aenderung beginnt ein Countdown (``WARN_SECONDS``, im Spielstand sichtbar);
        laeuft er ab, spielt ein Bot den Sitz. Jede Aktion/Aenderung (``_save``) setzt Uhr und Countdown zurueck.
        Gibt ``None`` zurueck, wenn nichts geschah.
        """
        with self._lock(code):
            stored = self.store.load(code)
            if stored is None:
                return None
            table = stored.table
            if table.game.phase is Phase.FINISHED or table.holding:
                return None
            seat = _acting_seat(table.game)
            if seat is None or table.bot_seats[seat]:
                return None
            idle = table.takeover_idle(seat)
            if idle is None:
                return None
            now = self.clock()
            warning = table.warning
            if warning and warning["seat"] == seat:
                if now < warning["until"]:
                    return None
                table.seats[seat]["autoplay"] = True       # Countdown abgelaufen: Bot uebernimmt
                return Outcome(self._save(code, table, stored.version, []))
            if table.touched is None or now - table.touched >= idle:
                if table.touched is None:                   # Altbestand ohne Uhr: ab jetzt zaehlen
                    return Outcome(self._save(code, table, stored.version, []))
                return Outcome(self._save(code, table, stored.version, [],
                                          warning={"seat": seat, "until": now + WARN_SECONDS}))
            return None

    def set_away(self, code: str, member_id: int, away: bool) -> "Outcome | None":
        """Platz an einen Bot uebergeben (``away=True``) bzw. zurueckholen. Die Werte bleiben dem Sitz zugeordnet."""
        with self._lock(code):
            stored = self.store.load(code)
            if stored is None:
                return None
            table = stored.table
            seat = table.seat_of(member_id)
            if seat is None:
                raise AccessDenied("Nur Spieler dieses Tisches koennen den Platz uebergeben.")
            if bool(table.seats[seat].get("autoplay")) == away:
                return Outcome(stored.version, duplicate=True)
            if away:
                table.seats[seat]["autoplay"] = True
            else:
                table.seats[seat].pop("autoplay", None)
            table.holding = False
            return Outcome(self._save(code, table, stored.version, []))

    def stay(self, code: str, member_id: int, remember: bool | None = None) -> Outcome:
        """"Weiterspielen": Countdown beenden und Inaktivitaetsuhr neu starten.

        ``remember=True`` merkt sich, dass fuer diesen Spieler nie ein Bot uebernimmt; ``False`` hebt das wieder auf;
        ``None`` laesst die Einstellung unveraendert.
        """
        if remember is not None and not isinstance(remember, bool):
            raise RuleViolation("bad_request", "remember muss true oder false sein.")
        with self._lock(code):
            stored = self._require(code)
            table = stored.table
            seat = table.seat_of(member_id)
            if seat is None:
                raise AccessDenied("Nur Spieler dieses Tisches koennen weiterspielen.")
            if remember is True:
                table.seats[seat]["noTakeover"] = True
            elif remember is False:
                table.seats[seat].pop("noTakeover", None)
            return Outcome(self._save(code, table, stored.version, []))

    def set_takeover(self, code: str, seconds: int) -> "Outcome | None":
        """Host-Einstellung bei laufendem Spiel aendern (0 = nie). ``None``, wenn noch kein Spiel laeuft."""
        if isinstance(seconds, bool) or seconds not in TAKEOVER_CHOICES:
            raise RuleViolation("bad_request", "Ungueltige Zeit fuer die Bot-Uebernahme.")
        with self._lock(code):
            stored = self.store.load(code)
            if stored is None:
                return None
            table = stored.table
            if table.takeover == seconds:
                return Outcome(stored.version, duplicate=True)
            table.takeover = seconds
            return Outcome(self._save(code, table, stored.version, []))
