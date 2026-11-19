"""Getakteter Botbetrieb: ein Zug nach dem anderen mit Bedenkzeit, damit Menschen mitlesen koennen (flask-frei).

``BotRunner.kick(code)`` stoesst pro Tisch hoechstens eine Schleife an. Die Schleife wartet vor jedem Botzug
(``service.pending_delay``), spielt genau einen Zug (``service.bot_step``) und meldet ihn per ``on_step``
(Sicht an alle Mitglieder pushen). Sind nur noch Menschen dran, ueberwacht sie die Inaktivitaet des Handelnden
(``service.watch_tick``): erst Countdown, dann uebernimmt ein Bot. Gilt die Uebernahme fuer den Wartenden nicht
(abgeschaltet, abgelehnt, einziger Mensch am Tisch), endet die Schleife sofort - der Tisch darf beliebig lange warten.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable


class NullRunner:
    """Fuer Tests und ungetaktete Betriebsart: tut nichts."""

    def kick(self, code: str) -> None:  # pragma: no cover - trivial
        pass


class BotRunner:
    def __init__(self, service, on_step: Callable[[str, object], None],
                 spawn: Callable[..., object] | None = None, sleep: Callable[[float], None] = time.sleep,
                 poll: float = 2.0, watch_limit: float = 3600.0,
                 refresh: Callable[[], None] | None = None) -> None:
        self.service = service
        self.on_step = on_step
        self.sleep = sleep
        self.poll = poll
        self.watch_limit = watch_limit
        # Vor jedem Lesen neue Datenbank-Sicht holen: Die Schleife lebt lange in einer eigenen DB-Sitzung und sähe sonst
        # veraltete Zustände (Aktionen des Menschen aus anderen Requests kämen nie an).
        self.refresh = refresh or (lambda: None)
        self._spawn = spawn or self._thread
        self._lock = threading.Lock()
        self._running: set[str] = set()
        self._again: set[str] = set()

    @staticmethod
    def _thread(fn, *args) -> None:
        threading.Thread(target=fn, args=args, daemon=True).start()

    def kick(self, code: str) -> None:
        with self._lock:
            if code in self._running:
                self._again.add(code)
                return
            self._running.add(code)
        self._spawn(self._loop, code)

    def _take_again(self, code: str) -> bool:
        with self._lock:
            if code in self._again:
                self._again.discard(code)
                return True
            return False

    def _loop(self, code: str) -> None:
        log = logging.getLogger(__name__)
        log.info("Bot-Schleife gestartet (%s)", code)
        try:
            while True:
                self.refresh()
                delay = self.service.pending_delay(code)
                if delay is not None:
                    self.sleep(delay)
                    step = self.service.bot_step(code)
                    if step is not None:
                        self.on_step(code, step)
                    continue
                if self._take_again(code):
                    continue
                if not self._watch(code):
                    break
        except Exception:  # pragma: no cover - ein Fehler darf den Prozess nicht beenden
            log.exception("Bot-Schleife abgebrochen (%s)", code)
        finally:
            with self._lock:
                self._running.discard(code)
                self._again.discard(code)

    def _watch(self, code: str) -> bool:
        """Wartet auf einen ersetzbaren Menschen. True = Schleife soll weiterlaufen (z. B. weil ein Bot uebernommen hat)."""
        waiting = self.service.waiting_on(code)
        if waiting is None:
            return False
        waited = 0.0
        while waited < self.watch_limit:      # danach beendet sich die Ueberwachung; die naechste Anfrage startet sie neu
            self.sleep(self.poll)
            waited += self.poll
            if self._take_again(code):
                return True
            self.refresh()
            now = self.service.waiting_on(code)
            if now is None:
                return False
            if now != waiting:
                return True
            step = self.service.watch_tick(code)      # Countdown starten bzw. Bot einsetzen (Uhr steht im Spielstand)
            if step is not None:
                self.on_step(code, step)
                return True
        return False
