"""Parteien (TSR 2.4)."""
from __future__ import annotations

from enum import Enum


class Party(str, Enum):
    RE = "re"
    KONTRA = "kontra"

    @property
    def opponent(self) -> "Party":
        return Party.KONTRA if self is Party.RE else Party.RE
