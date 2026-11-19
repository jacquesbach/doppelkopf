"""JSON-Aktion (HTTP/Socket) -> Regelkern-Aktion. Der Sitz kommt IMMER aus der Authentifizierung, nie aus dem Body."""
from __future__ import annotations

from ..rules import Announce, Baptize, Declare, DeclareSchweinchen, PlayCard, Resolve, RuleViolation
from ..rules.game import Action


def _need(payload: dict, key: str, types: tuple[type, ...], label: str):
    value = payload.get(key)
    if not isinstance(value, types) or (isinstance(value, bool) and bool not in types):
        raise RuleViolation("bad_request", f"Ungueltige Angabe '{label}'.")
    return value


def parse_action(seat: int, payload: dict) -> Action:
    if not isinstance(payload, dict):
        raise RuleViolation("bad_request", "Aktion muss ein Objekt sein.")
    kind = payload.get("type")
    if kind == "declare":
        return Declare(seat, _need(payload, "reservation", (bool,), "reservation"))
    if kind == "resolve":
        return Resolve(seat, _need(payload, "accept", (bool,), "accept"))
    if kind == "baptize":
        return Baptize(seat, _need(payload, "choice", (str,), "choice"))
    if kind == "play_card":
        return PlayCard(seat, _need(payload, "cardId", (str,), "cardId"))
    if kind == "announce":
        return Announce(seat, _need(payload, "level", (int,), "level"))
    if kind == "schweinchen":
        return DeclareSchweinchen(seat)
    raise RuleViolation("unknown_action", "Unbekannte Aktion.")
