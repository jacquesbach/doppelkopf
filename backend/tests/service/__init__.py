"""Tests der Service-Schicht.

Die Bots rechnen hier standardmaessig OHNE Stichproben (schnell); die Stichproben-Bots testet ``test_bots_memory``
gezielt (mit wenigen Stichproben). Die Spielstaerke wird per Selbstspiel gemessen, nicht in den Unit-Tests.
"""
from ..rules import loader  # noqa: F401  (stellt ``app.rules`` ohne Flask bereit)
from app.table import bots as _bots

DEFAULT_TUNE = {"pimc": False, "announce": "legacy", "pimc_budget": 24, "announce_samples": 8}
_bots.TUNE.update(DEFAULT_TUNE)
