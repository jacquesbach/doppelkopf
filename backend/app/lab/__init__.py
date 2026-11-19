"""Test-Tisch (Szenario-Labor fuer den Betreiber): echter Tisch mit festgelegten Karten.

Der Kern (``scenario``, ``presets``) ist flask-frei; die HTTP-Schicht steht in ``api.py``.
"""
from .presets import PRESETS, preset_list
from .scenario import Scenario, build_lab_table, parse_scenario, rigged_order

__all__ = ["PRESETS", "preset_list", "Scenario", "build_lab_table", "parse_scenario", "rigged_order"]
