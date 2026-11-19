"""Bot-KI: regelkonform und mit solider Grundtaktik (kein Zufall, keine versteckte Information).

Bots sehen nur ihre ``bot_view`` (gleicher Informationsrahmen wie Spieler) und laufen serverseitig: sie
authentifizieren sich nie ueber HTTP. Welche Karten erlaubt sind, kommt aus ``legalActions`` - die KI waehlt nur
unter erlaubten Zuegen.

Taktik (Normalspiel, Solo, Hochzeit):
* **Vorbehalt:** nur mit beiden Kreuz-Damen (Hochzeit). Pflicht-/Lustsolo wird nie freiwillig gespielt.
* **Ausspielen:** Fehlfarben-Ass, sonst eine "leere" Fehlkarte, sonst der schwaechste Trumpf.
* **Bedienen:** liegt der Stich bei einem sicheren Partner, wird geschmiert (Augen draufgeben, beim letzten
  Spieler am meisten); sonst mit der *schwaechsten* gewinnenden Karte stechen; kann man nicht stechen, wird die
  augenaermste Karte abgeworfen. Hohe Trumpfe (Dulle, Kreuz-Dame) werden nicht fuer wenige Augen verbraucht.
* **Partner erkennen:** aus eigener Partei, Solo/Hochzeit, Ansagen (``clarified``) und gespielten Kreuz-Damen im
  laufenden Stich; sind alle Gegner bekannt, sind die uebrigen Partner (und umgekehrt).
* **Ansagen:** Re/Kontra nur mit starkem Blatt (Trumpfzahl, Dullen, Damen).
"""
from __future__ import annotations

from app.rules import (Announce, Baptize, Declare, DeclareSchweinchen, DeckVariant, GameState, Phase, PlayCard,
                     Resolve, bot_view)
from app.rules.cards import Card, Rank, Suit
from app.rules.game import Action
from app.rules.tricks import Play, trick_winner_index
from app.rules.trump import GameType, TrumpConfig, is_trump, strength, trump_order

_QUEEN_CLUBS = (Rank.QUEEN, Suit.CLUBS)
_DULLE = (Rank.TEN, Suit.HEARTS)


# --- Hilfen -------------------------------------------------------------------------------------

def _cfg(view: dict) -> TrumpConfig:
    return TrumpConfig(DeckVariant(view["deckVariant"]), view["ruleOptions"].get("dulle", True),
                       view.get("schweinchenSeat") is not None)


def _game_type(view: dict) -> GameType:
    return GameType(view["gameType"]) if view.get("gameType") else GameType.NORMAL


def _hand(view: dict) -> list[Card]:
    return [Card.from_dict(c) for c in view["hand"]]


def _solo_choice(view: dict, choices: list[str]) -> str:
    """Solo mit den meisten Trumpfkarten auf der Hand (Hochzeit wird hier nie gewaehlt)."""
    cfg = TrumpConfig(DeckVariant(view["deckVariant"]), view["ruleOptions"].get("dulle", True))
    hand = _hand(view)

    def trumps_in(choice: str) -> int:
        order = set(trump_order(GameType(choice), cfg))
        return sum(c.face in order for c in hand)

    solos = [c for c in choices if c != "wedding"]
    return max(solos, key=lambda c: (trumps_in(c), -solos.index(c)))


def hand_strength(view: dict) -> int:
    """Grobe Trumpfstaerke: Trumpfzahl + Zuschlaege fuer Dullen und Damen."""
    cfg, gt = _cfg(view), _game_type(view)
    score = 0
    for c in _hand(view):
        if is_trump(c, gt, cfg):
            score += 1
            if c.face == _DULLE and cfg.dulle:
                score += 2
            elif c.face == _QUEEN_CLUBS:
                score += 2
            elif c.rank is Rank.QUEEN:
                score += 1
    return score


def _announce_threshold(view: dict) -> int:
    return 17 if len(view["hand"]) >= 11 or DeckVariant(view["deckVariant"]) is DeckVariant.WITH_NINES else 14


def _wants_announce(view: dict) -> bool:
    full = 12 if DeckVariant(view["deckVariant"]) is DeckVariant.WITH_NINES else 10
    if len(view["hand"]) < full - 1:           # nur frueh ansagen
        return False
    return hand_strength(view) >= _announce_threshold(view)


# --- Parteikenntnis -----------------------------------------------------------------------------

def known_parties(view: dict, plays: list[Play]) -> dict[int, str | None]:
    """Partei je Sitz, soweit *dieser* Bot sie wissen kann (sonst ``None``)."""
    me, mine = view["seat"], view["myParty"]
    solo = view.get("gameType") not in (None, "normal")
    known: dict[int, str | None] = {s: None for s in range(4)}
    known[me] = mine
    if solo and view.get("soloSeat") is not None:
        for s in range(4):
            known[s] = "re" if s == view["soloSeat"] else "kontra"
        return known
    if view.get("weddingSeat") is not None:
        known[view["weddingSeat"]] = "re"
    if view.get("weddingPartner") is not None:
        known[view["weddingPartner"]] = "re"
    for s, party in enumerate(view.get("clarified", [None] * 4)):
        if party:
            known[s] = party
    for p in plays:                              # Kreuz-Dame im Stich verraet "Re"
        if p.card.face == _QUEEN_CLUBS:
            known[p.seat] = "re"
    sizes = {"re": 1 if solo else 2, "kontra": 3 if solo else 2}
    for party in ("re", "kontra"):               # Rest durch Abzaehlen
        unknown = [s for s in range(4) if known[s] is None]
        have = sum(v == party for v in known.values())
        other = "kontra" if party == "re" else "re"
        if unknown and have == sizes[party]:
            for s in unknown:
                known[s] = other
    return known


# --- Kartenwahl ---------------------------------------------------------------------------------

def _winner_seat(plays: list[Play], gt: GameType, cfg: TrumpConfig, second: bool) -> int:
    return plays[trick_winner_index(plays, gt, cfg, second)].seat


def choose_card(view: dict, playable_ids: list[str]) -> str:
    seat, gt, cfg = view["seat"], _game_type(view), _cfg(view)
    second = bool(view["ruleOptions"].get("second_dulle_wins"))
    cands = [Card.from_id(i) for i in playable_ids]
    plays = [Play(p["seat"], Card.from_dict(p["card"])) for p in view["currentTrick"]]
    st = lambda c: strength(c, gt, cfg)                                  # kleiner = staerker
    weakest_cheapest = lambda c: (is_trump(c, gt, cfg), c.value, -st(c))  # abwerfen: Fehlfarbe, wenig Augen, schwach

    if not plays:                                                        # Ausspielen
        aces = [c for c in cands if c.rank is Rank.ACE and not is_trump(c, gt, cfg)]
        if aces:
            return min(aces, key=lambda c: (-sum(h.suit == c.suit for h in cands), c.id)).id
        return min(cands, key=weakest_cheapest).id

    known = known_parties(view, plays)
    mine = view["myParty"]
    last = len(plays) == 3
    winner_seat = _winner_seat(plays, gt, cfg, second)
    winner_card = next(p.card for p in plays if p.seat == winner_seat)
    points = sum(p.card.value for p in plays)
    ally_wins = known[winner_seat] is not None and known[winner_seat] == mine

    if ally_wins:
        # Sicherer Partner liegt vorn: schmieren (beim letzten Spieler gefahrlos, sonst nur wenn der Stich hoch liegt)
        if last or (is_trump(winner_card, gt, cfg) and st(winner_card) <= 4):
            return max(cands, key=lambda c: (c.value, st(c))).id
        return min(cands, key=weakest_cheapest).id

    winners = [c for c in cands if _winner_seat(plays + [Play(seat, c)], gt, cfg, second) == seat]
    if winners:
        best = max(winners, key=st)                                      # schwaechste gewinnende Karte
        spendy = is_trump(best, gt, cfg) and st(best) <= 3               # Dulle / hohe Damen
        if last or not spendy or points + best.value >= 10:
            return best.id
    return min(cands, key=weakest_cheapest).id


# --- Aktionswahl --------------------------------------------------------------------------------

def choose_action(view: dict) -> Action | None:
    seat = view["seat"]
    acts = {a["type"]: a for a in view["legalActions"]}
    if "declare" in acts:                       # Vorbehalt nur fuer die Hochzeit (beide Kreuz-Damen)
        queens = sum(c.face == _QUEEN_CLUBS for c in _hand(view))
        return Declare(seat, queens == 2)
    if "resolve" in acts:
        return Resolve(seat, False)
    if "baptize" in acts:
        choices = acts["baptize"]["choices"]
        if "wedding" in choices:
            return Baptize(seat, "wedding")
        return Baptize(seat, _solo_choice(view, choices))
    if "announce" in acts and view["mandatoryAnnouncementSeat"] != seat:
        levels = acts["announce"]["levels"]
        if 0 in levels and _wants_announce(view):
            return Announce(seat, 0)
    if view["turn"] == seat:
        if "schweinchen" in acts:
            return DeclareSchweinchen(seat)
        if view["mandatoryAnnouncementSeat"] == seat and "announce" in acts:
            return Announce(seat, acts["announce"]["levels"][0])
        if "play_card" in acts:
            return PlayCard(seat, choose_card(view, acts["play_card"]["cards"]))
    return None


def next_bot_action(game: GameState, is_bot: list[bool]) -> tuple[int, Action] | None:
    """Erste Bot-Aktion, die jetzt faellig ist (Reihenfolge der Sitze), sonst ``None``."""
    if game.phase is Phase.FINISHED:
        return None
    for seat in range(4):
        if is_bot[seat]:
            action = choose_action(bot_view(game, seat))
            if action is not None:
                return seat, action
    return None
