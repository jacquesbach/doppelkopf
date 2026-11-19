"""Fehlerklassen des Regelkerns.

Jede Regelverletzung traegt einen stabilen ``code`` (fuer Frontend/Tests) und eine
lesbare ``message``. Der Regelkern kennt weder HTTP noch Socket.IO.
"""
from __future__ import annotations


class RuleViolation(Exception):
    """Eine angeforderte Aktion ist nach den Regeln nicht erlaubt."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class VersionConflict(RuleViolation):
    """Die Aktion bezieht sich auf eine veraltete Zustandsversion."""

    def __init__(self, expected: int, actual: int) -> None:
        super().__init__("version_conflict", f"expected version {expected}, state is at {actual}")
        self.expected = expected
        self.actual = actual


class DuplicateAction(RuleViolation):
    """Dieselbe Aktionskennung wurde bereits verarbeitet."""

    def __init__(self, action_id: str) -> None:
        super().__init__("duplicate_action", f"action {action_id} was already applied")
        self.action_id = action_id
