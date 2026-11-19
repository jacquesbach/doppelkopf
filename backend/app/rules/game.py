"""Einzelspiel als Zustandsmaschine (TSR 3-7).

Phasen: Geben -> Vorbehalte abfragen -> Vorbehalte aufloesen -> (Taufe) -> Karten spielen
-> Auswerten. Die Hochzeitsklaerung laeuft *innerhalb* der Kartenspielphase.

Der Regelkern kennt weder Flask noch Datenbank noch Zeit. Zufall steckt nur in der
vorab gemischten Kartenreihenfolge, die ``new_game`` bekommt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from typing import Sequence

from .announcements import AnnouncementBook, allowed_levels, apply_announcement, level_code
from .cards import Card, DeckVariant, Rank, Suit
from .dealing import deal
from .errors import DuplicateAction, RuleViolation, VersionConflict
from .parties import Party
from .options import RuleOptions
from .profile import RuleProfile, make_profile
from .scoring import _CHARLIE, GameScore, score_game
from .tricks import CompletedTrick, Play, playable_cards, trick_points, trick_winner_index
from .trump import SOLO_TYPES, GameType, TrumpConfig, is_trump, lead_kind, trump_rank_map

_QUEEN_CLUBS = (Rank.QUEEN, Suit.CLUBS)
_FOX = (Rank.ACE, Suit.DIAMONDS)


class Phase(str, Enum):
    RESERVATION_QUERY = "reservation_query"            # TSR 4.1.2: gesund / Vorbehalt
    RESERVATION_RESOLUTION = "reservation_resolution"  # TSR 4.1.5-4.1.7: Pflichtsolo? Lustsolo?
    BAPTISM = "baptism"                                # Taufe bzw. Bekanntgabe des Solos
    PLAYING = "playing"
    FINISHED = "finished"


class GameKind(str, Enum):
    """Buchungsart des Spiels fuer Spielliste und Geberfortschreibung (TSR 4.2.4, 4.3.2, 4.4)."""
    NORMAL = "normal"
    PFLICHTSOLO = "pflichtsolo"
    PFLICHTSOLO_FORCED = "pflichtsolo_forced"   # vorgefuehrt (TSR 4.2.3)
    LUSTSOLO = "lustsolo"
    WEDDING = "wedding"                          # angemeldete Hochzeit (kann zum Karo-Solo werden)
    SILENT_WEDDING = "silent_wedding"            # Stille Hochzeit (TSR 4.4.5)


# --- Aktionen -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Declare:
    """Antwort in der Vorbehaltsabfrage: ``reservation=False`` bedeutet 'gesund'."""
    seat: int
    reservation: bool


@dataclass(frozen=True)
class Resolve:
    """Antwort auf 'Pflichtsolo?' bzw. 'Lustsolo?' bei mehreren Vorbehalten."""
    seat: int
    accept: bool


@dataclass(frozen=True)
class Baptize:
    """``choice`` ist ``'wedding'`` oder der Wert eines ``GameType`` (Solo)."""
    seat: int
    choice: str


@dataclass(frozen=True)
class PlayCard:
    seat: int
    card_id: str


@dataclass(frozen=True)
class Announce:
    """``level``: 0 = Re/Kontra, 1 = keine 90, 2 = keine 60, 3 = keine 30, 4 = schwarz."""
    seat: int
    level: int


@dataclass(frozen=True)
class DeclareSchweinchen:
    """Kneipenregel: Karo-Asse (beide auf der Hand) zu hoechsten Truempfen erklaeren."""
    seat: int


Action = Declare | Resolve | Baptize | PlayCard | Announce | DeclareSchweinchen


# --- Zustand ------------------------------------------------------------------------------

@dataclass
class GameState:
    profile_id: str
    deck_variant: str
    dealer: int
    hands: list[list[Card]]
    pflichtsolo_done: list[bool]
    version: int = 1
    phase: Phase = Phase.RESERVATION_QUERY
    # Vorbehaltsabfrage
    declarations: list[str | None] = field(default_factory=lambda: [None] * 4)
    query_seat: int | None = None
    resolution_stage: str | None = None          # 'pflichtsolo' | 'lustsolo'
    resolution_queue: list[int] = field(default_factory=list)
    baptism_seat: int | None = None
    baptism_kind: GameKind | None = None         # None = einziger Vorbehalt, frei waehlbar
    # Spielart
    game_type: GameType = GameType.NORMAL
    kind: GameKind = GameKind.NORMAL
    solo_seat: int | None = None
    wedding_seat: int | None = None
    wedding_partner: int | None = None
    wedding_clarifying_trick: int | None = None  # 1..3, sobald die Hochzeit geklaert ist
    re_seats: list[int] = field(default_factory=list)
    # Kartenspiel
    turn: int | None = None
    current_trick: list[Play] = field(default_factory=list)
    tricks: list[CompletedTrick] = field(default_factory=list)
    announcements: AnnouncementBook = field(default_factory=AnnouncementBook)
    announcement_log: list[dict] = field(default_factory=list)
    clarified: list[str | None] = field(default_factory=lambda: [None] * 4)  # TSR 5.5.1
    score: GameScore | None = None
    log: list[dict] = field(default_factory=list)
    action_ids: list[str] = field(default_factory=list)
    # Regeloptionen (Hausregeln)
    rule_options: dict = field(default_factory=dict)
    schweinchen_seat: int | None = None
    mandatory_pending: int | None = None         # Pflichtansage ausstehend (Sitz)
    score_multiplier: int = 1                    # 2 in einer Bockrunde
    bock_triggers: list[str] = field(default_factory=list)

    # -- Ableitungen --
    @cached_property
    def options(self) -> RuleOptions:
        return RuleOptions.from_dict(self.rule_options)

    @cached_property
    def profile(self) -> RuleProfile:
        return make_profile(DeckVariant(self.deck_variant), self.options)

    @property
    def variant(self) -> DeckVariant:
        return DeckVariant(self.deck_variant)

    @property
    def trump_cfg(self) -> TrumpConfig:
        """Kartenrang des laufenden Spiels (Dulle-Regel, erklaertes Schweinchen)."""
        return TrumpConfig(self.variant, self.options.dulle, self.schweinchen_seat is not None)

    @property
    def wedding_shift(self) -> int:
        """Verschiebung der An-/Absagefristen bei angemeldeter Hochzeit (TSR 6.4.2)."""
        if self.kind is GameKind.WEDDING and self.wedding_clarifying_trick:
            return self.wedding_clarifying_trick - 1
        return 0

    @property
    def is_solo_scored(self) -> bool:
        return self.phase in (Phase.PLAYING, Phase.FINISHED) and len(self.re_seats) == 1 \
            and not self._wedding_unclarified

    @property
    def _wedding_unclarified(self) -> bool:
        return self.kind is GameKind.WEDDING and self.wedding_clarifying_trick is None

    def party_of(self, seat: int) -> Party | None:
        """Wahre Partei (nur dem Server bekannt). ``None``: bei ungeklaerter Hochzeit unbestimmt."""
        if seat in self.re_seats:
            return Party.RE
        return None if self._wedding_unclarified else Party.KONTRA

    # -- Serialisierung --
    def to_dict(self) -> dict:
        return {
            "profileId": self.profile_id, "deckVariant": self.deck_variant, "dealer": self.dealer,
            "hands": [[c.to_dict() for c in h] for h in self.hands],
            "pflichtsoloDone": list(self.pflichtsolo_done), "version": self.version,
            "phase": self.phase.value, "declarations": list(self.declarations),
            "querySeat": self.query_seat, "resolutionStage": self.resolution_stage,
            "resolutionQueue": list(self.resolution_queue), "baptismSeat": self.baptism_seat,
            "baptismKind": self.baptism_kind.value if self.baptism_kind else None,
            "gameType": self.game_type.value, "kind": self.kind.value, "soloSeat": self.solo_seat,
            "weddingSeat": self.wedding_seat, "weddingPartner": self.wedding_partner,
            "weddingClarifyingTrick": self.wedding_clarifying_trick, "reSeats": list(self.re_seats),
            "turn": self.turn,
            "currentTrick": [{"seat": p.seat, "card": p.card.to_dict()} for p in self.current_trick],
            "tricks": [t.to_dict() for t in self.tricks],
            "announcements": self.announcements.to_dict(), "announcementLog": list(self.announcement_log),
            "clarified": list(self.clarified), "score": self.score.to_dict() if self.score else None,
            "log": list(self.log), "actionIds": list(self.action_ids),
            "ruleOptions": dict(self.rule_options), "schweinchenSeat": self.schweinchen_seat,
            "mandatoryPending": self.mandatory_pending, "scoreMultiplier": self.score_multiplier,
            "bockTriggers": list(self.bock_triggers),
        }

    @staticmethod
    def from_dict(d: dict) -> "GameState":
        state = GameState(
            d["profileId"], d["deckVariant"], d["dealer"],
            [[Card.from_dict(c) for c in h] for h in d["hands"]], list(d["pflichtsoloDone"]),
        )
        state.version = d["version"]
        state.phase = Phase(d["phase"])
        state.declarations = list(d["declarations"])
        state.query_seat = d["querySeat"]
        state.resolution_stage = d["resolutionStage"]
        state.resolution_queue = list(d["resolutionQueue"])
        state.baptism_seat = d["baptismSeat"]
        state.baptism_kind = GameKind(d["baptismKind"]) if d["baptismKind"] else None
        state.game_type = GameType(d["gameType"])
        state.kind = GameKind(d["kind"])
        state.solo_seat, state.wedding_seat = d["soloSeat"], d["weddingSeat"]
        state.wedding_partner = d["weddingPartner"]
        state.wedding_clarifying_trick = d["weddingClarifyingTrick"]
        state.re_seats = list(d["reSeats"])
        state.turn = d["turn"]
        state.current_trick = [Play(p["seat"], Card.from_dict(p["card"])) for p in d["currentTrick"]]
        state.tricks = [CompletedTrick.from_dict(t) for t in d["tricks"]]
        state.announcements = AnnouncementBook.from_dict(d["announcements"])
        state.announcement_log = list(d["announcementLog"])
        state.clarified = list(d["clarified"])
        state.log = list(d["log"])
        state.action_ids = list(d["actionIds"])
        state.rule_options = dict(d.get("ruleOptions", {}))
        state.schweinchen_seat = d.get("schweinchenSeat")
        state.mandatory_pending = d.get("mandatoryPending")
        state.score_multiplier = d.get("scoreMultiplier", 1)
        state.bock_triggers = list(d.get("bockTriggers", []))
        # Das Ergebnis wird aus den Stichen neu berechnet (Wahrheit = Stiche + Ansagen).
        if state.phase is Phase.FINISHED:
            state.score = _score(state)
        return state


# --- Spielstart ---------------------------------------------------------------------------

def new_game(profile: RuleProfile, order: Sequence[Card], dealer: int,
             pflichtsolo_done: Sequence[bool] = (False, False, False, False),
             forced_solo_seat: int | None = None, multiplier: int = 1) -> GameState:
    """Gibt die Karten und startet die Vorbehaltsabfrage (bzw. die Vorfuehrung).

    ``multiplier`` = 2 in einer Bockrunde (Hausregel), sonst 1.
    """
    hands = deal(order, dealer, profile.deck_variant)
    state = GameState(profile.id.value, profile.deck_variant.value, dealer, hands, list(pflichtsolo_done))
    state.rule_options = profile.options.to_dict()
    state.score_multiplier = multiplier
    if forced_solo_seat is not None:
        if pflichtsolo_done[forced_solo_seat]:
            raise RuleViolation("bad_forced_solo", "Der Spieler hat sein Pflichtsolo schon gespielt.")
        # TSR 4.1.9: keine Vorbehaltsabfrage, der Solist gibt nur das Solo bekannt.
        state.phase = Phase.BAPTISM
        state.baptism_seat = forced_solo_seat
        state.baptism_kind = GameKind.PFLICHTSOLO_FORCED
    else:
        state.query_seat = (dealer + 1) % 4
    _log(state, "dealt", dealer=dealer, forced=forced_solo_seat)
    return state


def _log(state: GameState, type_: str, **data) -> None:
    state.log.append({"seq": len(state.log) + 1, "type": type_, **data})


# --- Anwendung von Aktionen ---------------------------------------------------------------

def apply_action(state: GameState, action: Action, *, expected_version: int | None = None,
                 action_id: str | None = None) -> None:
    """Fuehrt eine Aktion transaktional aus: bei Fehler bleibt ``state`` unveraendert."""
    if expected_version is not None and expected_version != state.version:
        raise VersionConflict(expected_version, state.version)
    if action_id is not None and action_id in state.action_ids:
        raise DuplicateAction(action_id)
    backup = state.to_dict()
    try:
        _dispatch(state, action)
    except Exception:
        restored = GameState.from_dict(backup)
        state.__dict__.update(restored.__dict__)
        raise
    state.version += 1
    if action_id is not None:
        state.action_ids = (state.action_ids + [action_id])[-200:]


def _dispatch(state: GameState, action: Action) -> None:
    if not 0 <= action.seat <= 3:
        raise RuleViolation("bad_seat", "Unbekannter Sitz.")
    handlers = {Declare: _declare, Resolve: _resolve, Baptize: _baptize,
                PlayCard: _play_card, Announce: _announce, DeclareSchweinchen: _schweinchen}
    handlers[type(action)](state, action)


def _require_phase(state: GameState, *phases: Phase) -> None:
    if state.phase not in phases:
        raise RuleViolation("wrong_phase", f"Aktion in Phase {state.phase.value} nicht moeglich.")


def _seats_in_order(state: GameState) -> list[int]:
    return [(state.dealer + k) % 4 for k in range(1, 5)]


def _declare(state: GameState, a: Declare) -> None:
    _require_phase(state, Phase.RESERVATION_QUERY)
    if a.seat != state.query_seat:
        raise RuleViolation("not_your_turn", "Du bist in der Vorbehaltsabfrage nicht an der Reihe.")
    state.declarations[a.seat] = "reservation" if a.reservation else "healthy"
    _log(state, "declared", seat=a.seat, answer=state.declarations[a.seat])
    order = _seats_in_order(state)
    nxt = order.index(a.seat) + 1
    if nxt < 4:
        state.query_seat = order[nxt]
        return
    state.query_seat = None
    holders = [s for s in order if state.declarations[s] == "reservation"]
    if not holders:                                   # TSR 4.1.3
        _begin_play(state, GameType.NORMAL, GameKind.NORMAL)
    elif len(holders) == 1:                           # TSR 4.1.4
        state.phase, state.baptism_seat, state.baptism_kind = Phase.BAPTISM, holders[0], None
    else:                                             # TSR 4.1.5/4.1.6
        state.phase = Phase.RESERVATION_RESOLUTION
        state.resolution_stage = "pflichtsolo"
        state.resolution_queue = [s for s in holders if not state.pflichtsolo_done[s]]
        _advance_resolution(state, holders)


def _advance_resolution(state: GameState, holders: list[int] | None = None) -> None:
    """Springt zur naechsten Stufe, wenn die Warteschlange leer ist; sonst Rueckfall auf Normalspiel."""
    holders = holders or [s for s in _seats_in_order(state) if state.declarations[s] == "reservation"]
    while not state.resolution_queue:
        if state.resolution_stage == "pflichtsolo":
            state.resolution_stage = "lustsolo"
            state.resolution_queue = [s for s in holders if state.pflichtsolo_done[s]]
        else:
            # Niemand will ein Solo: kein Vorbehalt kommt zum Zuge (Hochzeit kann bei mehreren
            # Vorbehalten nie zum Zuge kommen, TSR 4.1.6) -> Normalspiel. ANNAHME, siehe Regelmatrix.
            state.resolution_stage = None
            _log(state, "reservations_void")
            _begin_play(state, GameType.NORMAL, GameKind.NORMAL)
            return


def _resolve(state: GameState, a: Resolve) -> None:
    _require_phase(state, Phase.RESERVATION_RESOLUTION)
    if not state.resolution_queue or a.seat != state.resolution_queue[0]:
        raise RuleViolation("not_your_turn", "Du wirst gerade nicht gefragt.")
    _log(state, "resolved", seat=a.seat, stage=state.resolution_stage, accept=a.accept)
    if a.accept:                                       # TSR 4.1.7: Abfrage endet beim ersten 'ja'
        state.baptism_seat = a.seat
        state.baptism_kind = (GameKind.PFLICHTSOLO if state.resolution_stage == "pflichtsolo"
                              else GameKind.LUSTSOLO)
        state.phase, state.resolution_stage, state.resolution_queue = Phase.BAPTISM, None, []
        return
    state.resolution_queue.pop(0)
    _advance_resolution(state)


def _baptize(state: GameState, a: Baptize) -> None:
    _require_phase(state, Phase.BAPTISM)
    if a.seat != state.baptism_seat:
        raise RuleViolation("not_your_turn", "Nur der Spieler mit dem Vorbehalt darf taufen.")
    if a.choice == "wedding":
        both = sum(c.face == _QUEEN_CLUBS for c in state.hands[a.seat]) == 2
        if state.baptism_kind is not None or not both:
            raise RuleViolation("wedding_not_allowed",
                                "Hochzeit nur mit beiden Kreuz-Damen und als einziger Vorbehalt (TSR 4.4).")
        state.wedding_seat = a.seat
        _begin_play(state, GameType.NORMAL, GameKind.WEDDING)
        return
    try:
        game_type = GameType(a.choice)
    except ValueError:
        raise RuleViolation("unknown_game_type", "Unbekannte Spielart.") from None
    if game_type not in SOLO_TYPES:
        raise RuleViolation("unknown_game_type", "Das ist kein Solo.")
    kind = state.baptism_kind
    if kind is None:  # TSR 4.3.1: Solo ist Pflichtsolo, bis das eigene Pflichtsolo gespielt wurde
        kind = GameKind.LUSTSOLO if state.pflichtsolo_done[a.seat] else GameKind.PFLICHTSOLO
    state.solo_seat = a.seat
    _begin_play(state, game_type, kind)


def _begin_play(state: GameState, game_type: GameType, kind: GameKind) -> None:
    state.game_type, state.kind = game_type, kind
    if game_type.is_solo:
        state.re_seats = [state.solo_seat]
    elif kind is GameKind.WEDDING:
        state.re_seats = [state.wedding_seat]
    else:
        state.re_seats = [s for s in range(4)
                          if any(c.face == _QUEEN_CLUBS for c in state.hands[s])]
        if len(state.re_seats) == 1:                   # beide Kreuz-Damen, aber 'gesund' (TSR 4.4.5)
            state.kind = GameKind.SILENT_WEDDING
    # Aufspielpflicht: Pflichtsolist (TSR 4.2.2); sonst linker Nachbar des Gebers (4.3.1, 5.1.1)
    solo_leads = state.kind in (GameKind.PFLICHTSOLO, GameKind.PFLICHTSOLO_FORCED) or (
        state.kind is GameKind.LUSTSOLO and state.options.solo_leads)   # Hausregel "Solo spielt aus"
    state.turn = state.solo_seat if solo_leads else (state.dealer + 1) % 4
    state.phase, state.baptism_seat, state.baptism_kind = Phase.PLAYING, None, None
    if game_type.is_solo:   # Solo ist mit der Taufe fuer alle geklaert (TSR 5.5.1 Nr. 1)
        for s in range(4):
            state.clarified[s] = (Party.RE if s == state.solo_seat else Party.KONTRA).value
    elif state.kind is GameKind.WEDDING:
        state.clarified[state.wedding_seat] = Party.RE.value
    _log(state, "play_started", gameType=state.game_type.value, kind=state.kind.value,
         soloSeat=state.solo_seat, weddingSeat=state.wedding_seat, leader=state.turn)


def _play_card(state: GameState, a: PlayCard) -> None:
    _require_phase(state, Phase.PLAYING)
    if a.seat != state.turn:
        raise RuleViolation("not_your_turn", "Du bist nicht am Zug.")
    if state.mandatory_pending == a.seat:
        raise RuleViolation("mandatory_announcement", "Pflichtansage: Sage zuerst Re bzw. Kontra an.")
    hand = state.hands[a.seat]
    chosen = next((c for c in hand if c.id == a.card_id), None)
    if chosen is None:
        raise RuleViolation("card_not_in_hand", "Diese Karte hast du nicht auf der Hand.")
    lead = state.current_trick[0].card if state.current_trick else None
    if chosen not in playable_cards(hand, lead, state.game_type, state.trump_cfg):
        raise RuleViolation("must_follow", "Bedienpflicht: Du musst Farbe bzw. Trumpf bedienen (TSR 5.2.2).")
    hand.remove(chosen)
    state.current_trick.append(Play(a.seat, chosen))
    _note_clarification_by_card(state, a.seat, chosen, lead)
    _log(state, "card_played", seat=a.seat, card=chosen.id)
    if len(state.current_trick) < 4:
        state.turn = (a.seat + 1) % 4
        return
    _complete_trick(state)


def _queens_of_clubs_played_by(state: GameState, seat: int) -> int:
    plays = [p for t in state.tricks for p in t.plays] + state.current_trick
    return sum(p.seat == seat and p.card.face == _QUEEN_CLUBS for p in plays)


def _note_clarification_by_card(state: GameState, seat: int, card: Card, lead: Card | None) -> None:
    """Oeffentliche Parteiklaerung nach TSR 5.5.1 Nr. 3 und 5 (Normalspiel, Stille Hochzeit)."""
    if state.game_type.is_solo or state.kind is GameKind.WEDDING:
        return
    if card.face == _QUEEN_CLUBS:
        state.clarified[seat] = Party.RE.value
        if _queens_of_clubs_played_by(state, seat) == 2:  # beide Damen vom selben Spieler: Solo steht fest
            for s in range(4):
                state.clarified[s] = (Party.RE if s == seat else Party.KONTRA).value
    elif lead is not None and lead_kind(lead, state.game_type, state.trump_cfg) == "trump" \
            and not is_trump(card, state.game_type, state.trump_cfg) and state.clarified[seat] is None:
        state.clarified[seat] = Party.KONTRA.value     # Fehlkarte auf Trumpf: kein Trumpf, keine Dame


def _complete_trick(state: GameState) -> None:
    plays = tuple(state.current_trick)
    is_last = len(state.tricks) + 1 == state.profile.trick_count
    second_dulle = state.options.second_dulle_wins and not (state.options.second_dulle_wins_except_last and is_last)
    idx = trick_winner_index(plays, state.game_type, state.trump_cfg, second_dulle_wins=second_dulle)
    trick = CompletedTrick(len(state.tricks) + 1, plays, plays[idx].seat, trick_points(plays))
    state.tricks.append(trick)
    state.current_trick = []
    _log(state, "trick_completed", number=trick.number, winner=trick.winner_seat, points=trick.points)
    _maybe_clarify_wedding(state, trick)
    _log_trick_events(state, trick, is_last)
    if trick.number == 1 and state.options.mandatory_announcements and state.kind is GameKind.NORMAL \
            and not state.game_type.is_solo:        # Pflichtansage nur im Normalspiel (Hausregel)
        winner_party = state.party_of(trick.winner_seat)
        if state.announcements.of(winner_party).level < 0:
            state.mandatory_pending = trick.winner_seat
            _log(state, "mandatory_announcement", seat=trick.winner_seat)
    if is_last:
        state.score = _score(state)
        state.bock_triggers = _bock_triggers(state)
        state.phase, state.turn = Phase.FINISHED, None
        _log(state, "game_finished", winner=state.score.winner.value if state.score.winner else None,
             seatDeltas=state.score.seat_deltas)
    else:
        state.turn = trick.winner_seat


def _parties_public(state: GameState) -> bool:
    """Steht fuer alle am Tisch sichtbar fest, wer Re und wer Kontra ist?"""
    queens = sum(p.card.face == _QUEEN_CLUBS for t in state.tricks for p in t.plays)
    return queens == 2 or all(c is not None for c in state.clarified)


def _log_trick_events(state: GameState, trick: CompletedTrick, is_last: bool) -> None:
    """Oeffentliche Sonderereignisse eines Stichs (nur Normalspiel mit zwei Re-Spielern, wie die Sonderpunkte).

    Fuchs gefangen wird nur gemeldet, wenn die Parteien aller vier Spieler oeffentlich feststehen (beide Kreuz-Damen
    gespielt oder Hochzeit geklaert) - sonst wuerde die Meldung verdeckte Parteien verraten, und nicht jeder Spieler
    hat bei einer einzelnen Dame mitgedacht. Die Wertung am Spielende nennt den Fuchs in jedem Fall.
    """
    if state.game_type.is_solo or len(state.re_seats) != 2:
        return
    if trick.points >= 40:
        _log(state, "doppelkopf", seat=trick.winner_seat, points=trick.points)
    if state.options.fuchsjagd and _parties_public(state):
        taker_is_re = trick.winner_seat in state.re_seats
        for p in trick.plays:
            if p.card.face == _FOX and (p.seat in state.re_seats) != taker_is_re:
                _log(state, "fox_caught", seat=trick.winner_seat, victim=p.seat, trick=trick.number)
    if is_last and state.options.karlchen and trick.winning_card.face == _CHARLIE:
        _log(state, "charlie_last_trick", seat=trick.winner_seat)


def _maybe_clarify_wedding(state: GameState, trick: CompletedTrick) -> None:
    """TSR 4.4.3: erster Stich eines Nicht-Hochzeiters klaert (spaetestens der dritte Stich)."""
    if not state._wedding_unclarified:
        return
    if trick.winner_seat != state.wedding_seat:
        state.wedding_partner = trick.winner_seat
        state.re_seats = [state.wedding_seat, trick.winner_seat]
    elif trick.number == 3:                            # Hochzeiter macht die ersten drei Stiche
        state.re_seats = [state.wedding_seat]          # -> Farbsolo in Karo (Kartenrang = Normalspiel)
    else:
        return
    state.wedding_clarifying_trick = trick.number
    for s in range(4):
        state.clarified[s] = (Party.RE if s in state.re_seats else Party.KONTRA).value
    _log(state, "wedding_clarified", trick=trick.number, partner=state.wedding_partner,
         solo=state.wedding_partner is None)


def _announce(state: GameState, a: Announce) -> None:
    _require_phase(state, Phase.PLAYING)
    if state._wedding_unclarified:
        raise RuleViolation("wedding_unclarified",
                            "Bei angemeldeter Hochzeit sind Ansagen erst nach dem Klaerungsstich erlaubt (TSR 6.4.2).")
    party = state.party_of(a.seat)
    apply_announcement(state.profile, state.announcements, party, a.level,
                       len(state.hands[a.seat]), state.wedding_shift)
    state.clarified[a.seat] = party.value             # TSR 5.5.1 Nr. 4
    if state.mandatory_pending is not None:          # Pflichtansage erfuellt (auch durch den Partner)
        if state.announcements.of(state.party_of(state.mandatory_pending)).level >= 0:
            state.mandatory_pending = None
    state.announcement_log.append({"seat": a.seat, "party": party.value, "level": a.level,
                                   "code": level_code(a.level), "cardsInHand": len(state.hands[a.seat])})
    _log(state, "announced", seat=a.seat, party=party.value, level=a.level)


def _score(state: GameState) -> GameScore:
    return score_game(state.tricks, state.re_seats, state.announcements.levels(), state.profile.trick_count,
                      state.options, state.score_multiplier)


def _bock_triggers(state: GameState) -> list[str]:
    """Ausloeser fuer eine Bockrunde nach diesem Spiel (je Regel hoechstens einmal)."""
    o, found = state.options, []
    if o.bock_heart_trick and any(
            all(p.card.suit is Suit.HEARTS and not is_trump(p.card, state.game_type, state.trump_cfg)
                for p in t.plays) for t in state.tricks):
        found.append("heart_trick")
    if o.bock_zero_game and state.score.net == 0:
        found.append("zero_game")
    if o.bock_120 and state.score.points[Party.RE] == 120 and state.score.points[Party.KONTRA] == 120:
        found.append("points_120")
    return found


def can_declare_schweinchen(state: GameState, seat: int) -> bool:
    """Kneipenregel Schweinchen: beide Karo-Asse auf der Hand, noch keine Karte gespielt, Karo-Ass ist Trumpf."""
    return (state.options.schweinchen and state.phase is Phase.PLAYING and state.schweinchen_seat is None
            and len(state.hands[seat]) == state.profile.hand_size
            and sum(c.face == _FOX for c in state.hands[seat]) == 2
            and _FOX in trump_rank_map(state.game_type, state.trump_cfg))


def _schweinchen(state: GameState, a: DeclareSchweinchen) -> None:
    _require_phase(state, Phase.PLAYING)
    if not state.options.schweinchen:
        raise RuleViolation("option_disabled", "Die Regel 'Schweinchen' ist nicht aktiv.")
    if not can_declare_schweinchen(state, a.seat):
        raise RuleViolation("schweinchen_not_allowed",
                            "Schweinchen nur mit beiden Karo-Assen, vor der ersten eigenen Karte und wenn Karo-Ass Trumpf ist.")
    state.schweinchen_seat = a.seat
    _log(state, "schweinchen", seat=a.seat)


# --- Erlaubte Aktionen und Sichten --------------------------------------------------------

def legal_actions(state: GameState, seat: int) -> list[dict]:
    """Was darf ``seat`` jetzt tun? Der Server liefert das auch an die Oberflaeche."""
    actions: list[dict] = []
    if state.phase is Phase.RESERVATION_QUERY and seat == state.query_seat:
        actions.append({"type": "declare", "options": ["healthy", "reservation"]})
    elif state.phase is Phase.RESERVATION_RESOLUTION and state.resolution_queue \
            and seat == state.resolution_queue[0]:
        actions.append({"type": "resolve", "stage": state.resolution_stage, "options": [True, False]})
    elif state.phase is Phase.BAPTISM and seat == state.baptism_seat:
        choices = [t.value for t in SOLO_TYPES]
        if state.baptism_kind is None and sum(c.face == _QUEEN_CLUBS for c in state.hands[seat]) == 2:
            choices.append("wedding")
        actions.append({"type": "baptize", "choices": choices})
    elif state.phase is Phase.PLAYING:
        if seat == state.turn and state.mandatory_pending != seat:
            lead = state.current_trick[0].card if state.current_trick else None
            cards = playable_cards(state.hands[seat], lead, state.game_type, state.trump_cfg)
            actions.append({"type": "play_card", "cards": [c.id for c in cards]})
        if can_declare_schweinchen(state, seat):
            actions.append({"type": "schweinchen"})
        party = state.party_of(seat)
        if party is not None and not state._wedding_unclarified:
            levels = allowed_levels(state.profile, state.announcements, party,
                                    len(state.hands[seat]), state.wedding_shift)
            if levels:
                actions.append({"type": "announce", "levels": levels})
    return actions


def public_events(state: GameState) -> list[dict]:
    """Aus dem Spielprotokoll die Ereignisse, die alle Spieler sehen duerfen (fuer kurze Hinweise in der Oberflaeche)."""
    out = []
    for e in state.log:
        kind = e["type"]
        if kind == "declared" and e["answer"] == "reservation":
            out.append({"id": e["seq"], "type": "reservation", "seat": e["seat"]})
        elif kind == "play_started":
            if state.game_type.is_solo and e.get("soloSeat") is not None:
                out.append({"id": e["seq"], "type": "solo", "seat": e["soloSeat"], "gameType": e["gameType"]})
            elif e.get("kind") == GameKind.WEDDING.value:
                out.append({"id": e["seq"], "type": "wedding", "seat": e["weddingSeat"]})
        elif kind == "announced":
            out.append({"id": e["seq"], "type": "announce", "seat": e["seat"], "party": e["party"],
                        "level": e["level"], "code": level_code(e["level"])})
        elif kind == "wedding_clarified":
            out.append({"id": e["seq"], "type": "wedding_clarified", "partner": e.get("partner"),
                        "solo": bool(e.get("solo"))})
        elif kind in ("schweinchen", "doppelkopf", "fox_caught", "charlie_last_trick"):
            out.append({"id": e["seq"], **{k: v for k, v in e.items() if k != "seq"}})
    return out


def _public(state: GameState) -> dict:
    finished = state.phase is Phase.FINISHED
    last = state.tricks[-1] if state.tricks else None
    # Eine Stille Hochzeit bleibt bis Spielende verdeckt (sie sieht wie ein Normalspiel aus).
    kind_public = GameKind.NORMAL if state.kind is GameKind.SILENT_WEDDING and not finished else state.kind
    kind_public = kind_public.value
    view = {
        "phase": state.phase.value, "version": state.version, "dealer": state.dealer,
        "profileId": state.profile_id, "deckVariant": state.deck_variant,
        "declarations": list(state.declarations), "querySeat": state.query_seat,
        "resolution": {"stage": state.resolution_stage, "seat": state.resolution_queue[0]
                       if state.resolution_queue else None},
        "baptismSeat": state.baptism_seat, "turn": state.turn,
        "baptismKind": state.baptism_kind.value if state.baptism_kind else None,   # None = frei (einziger Vorbehalt)
        "gameType": state.game_type.value if state.phase in (Phase.PLAYING, Phase.FINISHED) else None,
        "kind": kind_public,
        "soloSeat": state.solo_seat, "weddingSeat": state.wedding_seat,
        "weddingPartner": state.wedding_partner, "weddingClarifyingTrick": state.wedding_clarifying_trick,
        "handCounts": [len(h) for h in state.hands],
        "currentTrick": [{"seat": p.seat, "card": p.card.to_dict()} for p in state.current_trick],
        "lastTrick": last.to_dict() if last else None,       # TSR 5.3.5: letzter Stich einsehbar
        "tricksWon": [sum(t.winner_seat == s for t in state.tricks) for s in range(4)],
        "announcements": state.announcement_log,
        "clarified": list(state.clarified),
        "ruleOptions": dict(state.rule_options), "schweinchenSeat": state.schweinchen_seat,
        "mandatoryAnnouncementSeat": state.mandatory_pending, "scoreMultiplier": state.score_multiplier,
        "bockTriggers": list(state.bock_triggers) if finished else [],
        "events": public_events(state),
    }
    if finished:   # Nach dem Spiel liegen alle Karten offen: Stiche zum Nachsehen und die Re-Partei (inkl. Stiller Hochzeit)
        view["tricks"] = [t.to_dict() for t in state.tricks]
        view["reSeats"] = list(state.re_seats)
    return view


def spectator_view(state: GameState) -> dict:
    """Zuschauer: nur oeffentliche Information, keine Haende, keine verdeckten Parteien."""
    view = _public(state)
    view["role"] = "spectator"
    if state.phase is Phase.FINISHED:
        view["score"] = state.score.to_dict()
    return view


_SUIT_ORDER = (Suit.CLUBS, Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS)


def sorted_hand(state: GameState, seat: int) -> list[Card]:
    """Hand fuer die Anzeige: Truempfe nach Staerke, danach Fehlfarben (Kreuz, Pik, Herz, Karo) nach Rang.

    Vor der Spielwahl gilt die Normalspiel-Ordnung. Der Spielzustand selbst wird nicht veraendert.
    """
    from .trump import strength
    game_type = state.game_type if state.phase in (Phase.PLAYING, Phase.FINISHED) else GameType.NORMAL
    cfg = state.trump_cfg

    def key(c: Card):
        if is_trump(c, game_type, cfg):
            return (0, strength(c, game_type, cfg), 0)
        return (1, _SUIT_ORDER.index(c.suit), strength(c, game_type, cfg))
    return sorted(state.hands[seat], key=key)


def player_view(state: GameState, seat: int) -> dict:
    """Sicht eines Spielers (auch fuer Bots: gleicher, fairer Informationsrahmen)."""
    view = _public(state)
    party = state.party_of(seat) if state.phase in (Phase.PLAYING, Phase.FINISHED) else None
    view.update({
        "role": "player", "seat": seat, "hand": [c.to_dict() for c in sorted_hand(state, seat)],
        "myParty": party.value if party else None,
        "legalActions": legal_actions(state, seat),
    })
    if state.phase is Phase.FINISHED:  # nach Spielende ist alles aufgedeckt
        view["score"] = state.score.to_dict()
        view["tricks"] = [t.to_dict() for t in state.tricks]
        view["parties"] = [state.party_of(s).value for s in range(4)]
    return view


def bot_view(state: GameState, seat: int) -> dict:
    """Sicht eines Bots: wie ``player_view`` plus die bereits gespielten Stiche.

    Alle Stiche waren fuer jeden am Tisch sichtbar; ein Mensch merkt sie sich, der Bot bekommt sie hier mitgeliefert
    (Kartenzaehlen). Handkarten oder Parteien anderer Spieler stecken darin nicht.
    """
    view = player_view(state, seat)
    view["playedTricks"] = [t.to_dict() for t in state.tricks]
    return view
