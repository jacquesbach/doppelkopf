"""Bot-KI: regelkonform, mit Gedaechtnis und Durchrechnen (kein Zufall im Regelwerk, keine versteckte Information).

Bots sehen nur ihre ``bot_view`` (gleicher Informationsrahmen wie Spieler, dazu die bereits gespielten Stiche - die hat
jeder am Tisch gesehen) und laufen serverseitig: sie authentifizieren sich nie ueber HTTP. Welche Karten erlaubt sind,
kommt aus ``legalActions`` - die KI waehlt nur unter erlaubten Zuegen.

Bausteine (siehe auch ``pimc.py``):
* **Gedaechtnis** (``Memory``): ungesehene Karten, Farben/Trumpf, die ein Mitspieler nachweislich nicht mehr hat, Augen je Sitz.
  Daraus: "ist meine Karte sicher?" (``threatened``/``is_master``) fuer Ausspielen, Schmieren und Stechen.
* **Durchrechnen** (``pimc.choose``): ungesehene Karten werden regelkonform auf die Mitspieler verteilt, jede erlaubte Karte
  wird in vielen solchen Stichproben zu Ende gespielt; gewaehlt wird die Karte mit den meisten erwarteten Augen (nur
  Normalspiel; sonst gilt die Heuristik unten).
* **Ansagen** (``_sampled_announce``): Re/Kontra und Absagen, wenn die Erfolgschance in den Stichproben hoch genug ist
  (Re/Kontra ab 75 %, Absagen ab 85 %).
* **Heuristik** (Solo, Hochzeit, Rueckfall): Ausspielen sicherer Fehlfarben-Karten, sonst "leere" Karte; Partner schmieren,
  sonst mit der schwaechsten (sicheren) gewinnenden Karte stechen; sonst augenaermste Karte abwerfen. Hohe Truempfe werden
  nicht fuer wenige Augen verbraucht.
* **Partner erkennen** (``known_parties``): aus eigener Partei, Solo/Hochzeit, Ansagen (``clarified``) und gespielten
  Kreuz-Damen; sind alle Gegner bekannt, sind die uebrigen Partner (und umgekehrt).
* **Vorbehalt:** nur mit beiden Kreuz-Damen (Hochzeit) oder - bei aktiver Hausregel - mit hoechstens 3 Truempfen (Armut).
  Pflicht-/Lustsolo wird nie freiwillig gespielt.
* **Armut:** abgegeben werden alle Truempfe (aufgefuellt mit den schwaechsten Fehlkarten); uebernommen wird ab 6 Truempfen
  (ab 5 mit Kreuz-Dame); zurueckgegeben werden die schwaechsten Fehlkarten. Der Arme und der Kaeufer sind Re (``known_parties``);
  die Stichproben-KI (pimc) kennt nur Kreuz-Damen-Parteien und bleibt in einer Armut aus.

Staerke gemessen per Selbstspiel gegen die alte Grundstrategie: ``python3 -m tools.bot_tournament``.
"""
from __future__ import annotations

from collections import Counter

from . import pimc
from ..rules import (Announce, Baptize, Declare, DeclareSchweinchen, DeckVariant, GameState, Phase, PlayCard,
                     PovertyOffer, PovertyPass, PovertyReturn, Resolve, bot_view)
from ..rules.cards import Card, Rank, Suit, ranks_for
from ..rules.game import Action
from ..rules.tricks import Play, trick_winner_index
from ..rules.trump import GameType, TrumpConfig, is_trump, lead_kind, strength, trump_order, trump_rank_map

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


# --- Armut (Hausregel) --------------------------------------------------------------------------

_POVERTY_MAX = 3       # wie ``rules.game.POVERTY_MAX_TRUMPS``
_POVERTY_CARDS = 3


def _trump_count(view: dict) -> int:
    cfg = _cfg(view)
    return sum(is_trump(c, GameType.NORMAL, cfg) for c in _hand(view))


def _queens_clubs(view: dict) -> int:
    return sum(c.face == _QUEEN_CLUBS for c in _hand(view))


def _is_poverty_game(view: dict) -> bool:
    """Laufende Armut (Parteien stehen fest: Armer + Kaeufer = Re) - die Stichproben-KI kennt nur Kreuz-Damen-Parteien."""
    p = view.get("poverty") or {}
    return view.get("kind") == "poverty" and p.get("seat") is not None and p.get("buyer") is not None


def _wants_poverty(view: dict) -> bool:
    """Armut anmelden: Regel aktiv, hoechstens 3 Truempfe, und keine Hochzeit (beide Kreuz-Damen)."""
    return bool(view["ruleOptions"].get("poverty")) and _trump_count(view) <= _POVERTY_MAX and _queens_clubs(view) < 2


def _poverty_pass_ids(view: dict, ids: list[str]) -> list[str]:
    """Alle Truempfe abgeben; auffuellen mit den wertlosesten, schwaechsten Fehlkarten."""
    cfg = _cfg(view)
    cards = [Card.from_id(i) for i in ids]
    trumps = [c for c in cards if is_trump(c, GameType.NORMAL, cfg)]
    side = sorted((c for c in cards if c not in trumps),
                  key=lambda c: (c.value, -strength(c, GameType.NORMAL, cfg), c.id))
    return [c.id for c in (trumps + side)[:_POVERTY_CARDS]]


def _accepts_poverty(view: dict) -> bool:
    n = _trump_count(view)
    return n >= 6 or (n >= 5 and _queens_clubs(view) >= 1)


def _poverty_return_ids(view: dict, ids: list[str]) -> list[str]:
    """Schwaechste Fehlkarten zurueckgeben; reichen sie nicht, die schwaechsten Truempfe."""
    cfg = _cfg(view)
    cards = [Card.from_id(i) for i in ids]
    side = sorted((c for c in cards if not is_trump(c, GameType.NORMAL, cfg)),
                  key=lambda c: (c.value, -strength(c, GameType.NORMAL, cfg), c.id))
    trumps = sorted((c for c in cards if is_trump(c, GameType.NORMAL, cfg)),
                    key=lambda c: (-strength(c, GameType.NORMAL, cfg), c.id))
    return [c.id for c in (side + trumps)[:_POVERTY_CARDS]]


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
    if _is_poverty_game(view):                    # Armut: der Arme und sein Kaeufer sind Re (oeffentlich bekannt)
        re = {view["poverty"]["seat"], view["poverty"]["buyer"]}
        return {s: "re" if s in re else "kontra" for s in range(4)}
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


# Schalter fuer Auswertungen (Selbstspiel-Vergleich); Standard = alles an.
TUNE = {"lead_master": True, "lead_trump": False, "lead_risk": True, "ally_secure": True, "safe_win": True,
        "short_suit": True, "pimc": True, "pimc_tricks": 12, "pimc_budget": 160, "pimc_win": False,
        "infer": False, "infer_w": 0.5, "announce": "pimc", "announce_p0": 0.75, "announce_p1": 0.85, "announce_samples": 30}


# --- Gedaechtnis --------------------------------------------------------------------------------

class Memory:
    """Was ein aufmerksamer Spieler ueber den bisherigen Spielverlauf weiss (nur oeffentliche Information).

    * ``unseen``: Kartenbilder, die weder in der eigenen Hand noch gespielt sind (liegen bei den Mitspielern),
    * ``voids``: Farben/Trumpf, die ein Mitspieler nachweislich nicht (mehr) hat (er hat nicht bedient),
    * ``points``: Augen, die jeder Sitz bisher in Stichen gesammelt hat.
    """

    def __init__(self, view: dict, plays: list[Play]) -> None:
        gt, cfg = _game_type(view), _cfg(view)
        self.gt, self.cfg = gt, cfg
        faces = Counter()
        for suit in Suit:
            for rank in ranks_for(cfg.variant):
                faces[(rank, suit)] = 2
        for c in _hand(view):
            faces[c.face] -= 1
        self.voids: dict[int, set] = {s: set() for s in range(4)}
        self.points: dict[int, int] = {s: 0 for s in range(4)}
        self.tricks_played = 0
        seen = []
        for t in view.get("playedTricks", []):
            trick = [Play(p["seat"], Card.from_dict(p["card"])) for p in t["plays"]]
            self._note_voids(trick)
            seen += [p.card for p in trick]
            self.points[t["winnerSeat"]] += t["points"]
            self.tricks_played += 1
        self._note_voids(plays)
        seen += [p.card for p in plays]
        for c in seen:
            faces[c.face] -= 1
        self.unseen = Counter({f: n for f, n in faces.items() if n > 0})

    def _note_voids(self, plays: list[Play]) -> None:
        if not plays:
            return
        kind = lead_kind(plays[0].card, self.gt, self.cfg)
        for p in plays[1:]:
            if lead_kind(p.card, self.gt, self.cfg) != kind:
                self.voids[p.seat].add(kind)

    def kind_of(self, face: tuple[Rank, Suit]) -> object:
        return "trump" if face in trump_rank_map(self.gt, self.cfg) else face[1]

    def unseen_of_kind(self, kind: object) -> int:
        return sum(n for f, n in self.unseen.items() if self.kind_of(f) == kind)

    def possible_void(self, seat: int, kind: object) -> bool:
        return kind in self.voids[seat] or self.unseen_of_kind(kind) == 0


def _beats(u: Card, c: Card, gt: GameType, cfg: TrumpConfig, second_dulle: bool) -> bool:
    """Schlaegt Karte ``u`` die Karte ``c`` im selben Stich? (``c`` fuehrt den Stich bzw. liegt vorn)"""
    tu, tc = is_trump(u, gt, cfg), is_trump(c, gt, cfg)
    if tu != tc:
        return tu
    if tu:
        if second_dulle and u.face == _DULLE and c.face == _DULLE:
            return True
        return strength(u, gt, cfg) < strength(c, gt, cfg)
    return u.suit == c.suit and strength(u, gt, cfg) < strength(c, gt, cfg)


def threatened(card: Card, lead: object, behind: list[int], mem: Memory, second_dulle: bool) -> bool:
    """Kann ein noch nicht gespielter Gegner hinter mir ``card`` mit einer ungesehenen Karte ueberbieten?"""
    for face, n in mem.unseen.items():
        if n <= 0:
            continue
        u = Card(face[1], face[0], 0)
        if u.face == card.face and not (second_dulle and u.face == _DULLE):
            continue                                                  # gleiche zweite Karte schlaegt nicht
        if not _beats(u, card, mem.gt, mem.cfg, second_dulle):
            continue
        kind = mem.kind_of(face)
        for seat in behind:
            if kind == lead:
                if lead not in mem.voids[seat]:
                    return True
            elif mem.possible_void(seat, lead):                       # Trumpf auf Fehlfarbe: nur wer nicht bedienen kann
                if kind not in mem.voids[seat]:
                    return True
    return False


def is_master(card: Card, others: list[int], mem: Memory, second_dulle: bool) -> bool:
    """Hoechste verbleibende Karte ihrer Art: Ausspielen gewinnt den Stich mit grosser Sicherheit."""
    return not threatened(card, lead_kind(card, mem.gt, mem.cfg), others, mem, second_dulle)


# --- Kartenwahl ---------------------------------------------------------------------------------

def _winner_seat(plays: list[Play], gt: GameType, cfg: TrumpConfig, second: bool) -> int:
    return plays[trick_winner_index(plays, gt, cfg, second)].seat


_PIMC_CACHE: dict[str, str] = {}


def _history(view: dict, plays: list[Play]) -> list[list[Play]]:
    """Alle bisher gespielten Stiche (in Spielreihenfolge) samt laufendem Stich - fuer die Parteien-Schaetzung."""
    done = [[Play(q["seat"], Card.from_dict(q["card"])) for q in t["plays"]] for t in view.get("playedTricks", [])]
    return done + ([plays] if plays else [])


def _tune_key() -> str:
    return f"{TUNE['infer']}{TUNE['infer_w']}{TUNE['pimc_budget']}"


def _sampled_choice(view: dict, cands: list[Card], plays: list[Play], mem: Memory, known: dict, second: bool) -> str | None:
    """Kartenwahl per Stichproben (siehe ``pimc``); ``None`` = Heuristik soll entscheiden."""
    gt, cfg, seat = _game_type(view), _cfg(view), view["seat"]
    hand = _hand(view)
    if gt is not GameType.NORMAL or view.get("weddingSeat") is not None or len(cands) < 2 or _is_poverty_game(view):
        return None
    if len(hand) > TUNE["pimc_tricks"]:
        return None
    key = "|".join([str(seat), ",".join(sorted(c.id for c in hand)), ",".join(f"{p.seat}{p.card.id}" for p in plays),
                    str(mem.tricks_played), str(view["myParty"]), _tune_key()])
    if key in _PIMC_CACHE:
        return _PIMC_CACHE[key]
    unseen = [Card(face[1], face[0], i) for face, n in mem.unseen.items() for i in range(n)]
    sizes = dict(enumerate(view["handCounts"]))
    re_played = {p.seat for t in view.get("playedTricks", []) for p in
                 (Play(q["seat"], Card.from_dict(q["card"])) for q in t["plays"]) if p.card.face == _QUEEN_CLUBS}
    re_played |= {p.seat for p in plays if p.card.face == _QUEEN_CLUBS}
    mine = view["myParty"]
    re_known = {s for s in range(4) if s != seat and known[s] == "re"}
    kontra_known = {s for s in range(4) if s != seat and known[s] == "kontra"}
    samples = max(6, min(40, TUNE["pimc_budget"] // len(cands)))
    best = pimc.choose(seat, hand, cands, plays, unseen, sizes, mem.voids, mem.kind_of, re_known, kontra_known,
                       re_played, mine == "re", gt, cfg, second, samples, key, dict(mem.points) if TUNE["pimc_win"] else None,
                       _history(view, plays) if TUNE["infer"] else None, TUNE["infer_w"])
    if len(_PIMC_CACHE) > 512:
        _PIMC_CACHE.clear()
    if best is not None:
        _PIMC_CACHE[key] = best.id
        return best.id
    return None


# Augen, die die eigene Partei fuer Re/Kontra (Stufe 0) bzw. die Absagen (1 keine 90, 2 keine 60, 3 keine 30, 4 schwarz)
# braucht; Re muss 121 holen, Kontra 120 (siehe ``pimc.estimate``).
_LEVEL_POINTS = {0: 120, 1: 151, 2: 181, 3: 211, 4: 240}
_ANNOUNCE_CACHE: dict[str, int | None] = {}


def _sampled_announce(view: dict, levels: list[int]) -> int | None:
    """Hoechste erlaubte Ansage, deren Erfolgschance (Stichproben) hoch genug ist; ``None`` = nicht ansagen."""
    gt, cfg, seat = _game_type(view), _cfg(view), view["seat"]
    if gt is not GameType.NORMAL or view.get("weddingSeat") is not None or not view.get("myParty") \
            or _is_poverty_game(view):
        return None
    hand = _hand(view)
    plays = [Play(p["seat"], Card.from_dict(p["card"])) for p in view["currentTrick"]]
    key = "A|" + "|".join([str(seat), ",".join(sorted(c.id for c in hand)), ",".join(f"{p.seat}{p.card.id}" for p in plays),
                           str(len(view.get("playedTricks", []))), ",".join(map(str, levels)),
                           ",".join(str(a["level"]) + a["party"] for a in view["announcements"]), _tune_key()])
    if key in _ANNOUNCE_CACHE:
        return _ANNOUNCE_CACHE[key]
    mem = Memory(view, plays)
    known = known_parties(view, plays)
    unseen = [Card(face[1], face[0], i) for face, n in mem.unseen.items() for i in range(n)]
    re_played = {p.seat for t in view.get("playedTricks", []) for p in
                 (Play(q["seat"], Card.from_dict(q["card"])) for q in t["plays"]) if p.card.face == _QUEEN_CLUBS}
    re_played |= {p.seat for p in plays if p.card.face == _QUEEN_CLUBS}
    probs = pimc.estimate(seat, hand, plays, unseen, dict(enumerate(view["handCounts"])), mem.voids, mem.kind_of,
                          {s for s in range(4) if s != seat and known[s] == "re"},
                          {s for s in range(4) if s != seat and known[s] == "kontra"}, re_played, gt, cfg,
                          bool(view["ruleOptions"].get("second_dulle_wins")), TUNE["announce_samples"], key,
                          dict(mem.points), view["turn"] if view["turn"] is not None else 0,
                          {lvl: _LEVEL_POINTS[lvl] for lvl in levels if lvl in _LEVEL_POINTS},
                          _history(view, plays) if TUNE["infer"] else None, TUNE["infer_w"])
    choice = None
    if probs:
        for lvl in sorted(probs):
            if probs[lvl] >= (TUNE["announce_p0"] if lvl == 0 else TUNE["announce_p1"]):
                choice = lvl
    if len(_ANNOUNCE_CACHE) > 512:
        _ANNOUNCE_CACHE.clear()
    _ANNOUNCE_CACHE[key] = choice
    return choice


def choose_card(view: dict, playable_ids: list[str]) -> str:
    seat, gt, cfg = view["seat"], _game_type(view), _cfg(view)
    second = bool(view["ruleOptions"].get("second_dulle_wins"))
    cands = [Card.from_id(i) for i in playable_ids]
    plays = [Play(p["seat"], Card.from_dict(p["card"])) for p in view["currentTrick"]]
    mem = Memory(view, plays)
    known = known_parties(view, plays)
    mine = view["myParty"]
    st = lambda c: strength(c, gt, cfg)                                  # kleiner = staerker
    hand = _hand(view)
    suit_len = lambda c: sum(h.suit == c.suit and not is_trump(h, gt, cfg) for h in hand)
    # abwerfen: Fehlfarbe vor Trumpf, wenig Augen, schwach; kurze Farben zuerst (Chance, farbfrei zu werden)
    weakest_cheapest = lambda c: (is_trump(c, gt, cfg), c.value, suit_len(c) if (TUNE["short_suit"] and not is_trump(c, gt, cfg)) else 0, -st(c))
    others = [s for s in range(4) if s != seat]
    opponents = [s for s in others if known[s] != mine]                 # Gegner ODER (noch) unbekannt
    if TUNE["pimc"]:
        sampled = _sampled_choice(view, cands, plays, mem, known, second)
        if sampled is not None:
            return sampled

    if not plays:                                                        # Ausspielen
        side = [c for c in cands if not is_trump(c, gt, cfg)]
        sure = [c for c in side if c.value > 0 and is_master(c, opponents, mem, second)] if TUNE["lead_master"] else []
        if sure:                                                         # hoechste Karte ihrer Farbe: Augen sichern
            return max(sure, key=lambda c: (c.value, suit_len(c), c.id)).id
        trumps = [c for c in cands if is_trump(c, gt, cfg)]
        my_trumps = len(trumps)
        if trumps and my_trumps >= 5 and TUNE["lead_trump"]:                                    # trumpfstark: Gegner ausstechen lassen
            master = [c for c in trumps if is_master(c, opponents, mem, second)]
            if master:
                return min(master, key=st).id if my_trumps >= 7 else max(master, key=st).id
        if side:
            def lead_risk(c: Card) -> tuple:
                opp_void = TUNE["lead_risk"] and any(c.suit in mem.voids[o] for o in opponents)
                ally_void = TUNE["lead_risk"] and any(known[o] == mine and c.suit in mem.voids[o] for o in others)
                return (opp_void, -ally_void, c.value, -st(c))
            return min(side, key=lead_risk).id
        return min(cands, key=weakest_cheapest).id

    lead = lead_kind(plays[0].card, gt, cfg)
    behind_all = [(seat + k) % 4 for k in range(1, 4 - len(plays))]       # Sitze, die nach mir noch spielen
    behind = [s for s in behind_all if known[s] != mine]
    last = not behind_all
    winner_seat = _winner_seat(plays, gt, cfg, second)
    winner_card = next(p.card for p in plays if p.seat == winner_seat)
    points = sum(p.card.value for p in plays)
    ally_wins = known[winner_seat] is not None and known[winner_seat] == mine

    def wins(c: Card) -> bool:
        return _winner_seat(plays + [Play(seat, c)], gt, cfg, second) == seat

    def secure(c: Card) -> bool:
        return not behind or not threatened(c, lead, behind, mem, second)

    winners = [c for c in cands if wins(c)]
    if ally_wins:
        if last or (secure(winner_card) if TUNE["ally_secure"] else True) or (not TUNE["ally_secure"] and is_trump(winner_card, gt, cfg) and st(winner_card) <= 4):                                  # Partner gewinnt sicher: schmieren
            return max(cands, key=lambda c: (c.value, not is_trump(c, gt, cfg), st(c))).id
        safe = [c for c in winners if secure(c)]
        if safe and points >= 8:                                         # Partner koennte ueberstochen werden
            return max(safe, key=st).id
        return min(cands, key=weakest_cheapest).id

    if winners:
        safe = [c for c in winners if secure(c)] if TUNE["safe_win"] else [c for c in winners if last]
        weakest = max(safe or winners, key=st)                           # schwaechste (sichere) gewinnende Karte
        spendy = is_trump(weakest, gt, cfg) and st(weakest) <= 3         # Dulle / hohe Damen
        if safe:
            if last or not spendy or points + weakest.value >= 10:
                return weakest.id
        elif points + weakest.value >= 10:                               # unsicher, aber lohnend: stark stechen
            return min(winners, key=st).id
    return min(cands, key=weakest_cheapest).id


# --- Aktionswahl --------------------------------------------------------------------------------

def choose_action(view: dict) -> Action | None:
    seat = view["seat"]
    acts = {a["type"]: a for a in view["legalActions"]}
    if "declare" in acts:                       # Vorbehalt nur fuer die Hochzeit (beide Kreuz-Damen) bzw. die Armut
        return Declare(seat, _queens_clubs(view) == 2 or _wants_poverty(view))
    if "resolve" in acts:                       # Solo nie; Armut nur ohne Hochzeitsblatt
        return Resolve(seat, acts["resolve"].get("stage") == "poverty" and _queens_clubs(view) < 2)
    if "baptize" in acts:
        choices = acts["baptize"]["choices"]
        if "wedding" in choices:
            return Baptize(seat, "wedding")
        if "poverty" in choices:
            return Baptize(seat, "poverty")
        return Baptize(seat, _solo_choice(view, choices))
    if "poverty_pass" in acts:
        return PovertyPass(seat, tuple(_poverty_pass_ids(view, acts["poverty_pass"]["cards"])))
    if "poverty_offer" in acts:
        return PovertyOffer(seat, _accepts_poverty(view))
    if "poverty_return" in acts:
        return PovertyReturn(seat, tuple(_poverty_return_ids(view, acts["poverty_return"]["cards"])))
    if "announce" in acts and view["mandatoryAnnouncementSeat"] != seat:
        levels = acts["announce"]["levels"]
        if TUNE["announce"] == "pimc" and _game_type(view) is GameType.NORMAL and view.get("weddingSeat") is None \
                and not _is_poverty_game(view):
            level = _sampled_announce(view, levels)
            if level is not None:
                return Announce(seat, level)
        elif 0 in levels and _wants_announce(view):
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
