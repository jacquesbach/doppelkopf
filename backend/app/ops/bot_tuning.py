"""Bot-Einstellungen des Betreibers (Reiter BOTS im Betreiber-Backend): Katalog, Pruefung, Anwenden und Speichern.

Der Katalog beschreibt jede einstellbare Eigenschaft mit Text, Art, Grenzen und Standard; die Oberflaeche zeichnet ihr Formular daraus
(wie ``rule_schema`` bei den Regeln), es gibt keine zweite Liste im Frontend. Die Werte landen in ``bots.TUNE`` (Prozess-weit; der
Server laeuft als ein Prozess) bzw. beim Tempo in ``service.PACE``. Gespeichert wird ein JSON-Dokument mit **allen** Werten; beim Start
des Servers wird es angewendet, sobald der Betreiber einmal gespeichert hat. Ohne gespeicherten Stand gelten die Standardwerte im Code.

Die Standardwerte stammen aus ``bots.TUNE_DEFAULTS``, damit Katalog und Code nie auseinanderlaufen (ein Test prueft das).
"""
from __future__ import annotations

import copy
import json
import threading

from ..table import bots, service

TEMPO = {"schnell": 0.6, "normal": 1.0, "ruhig": 1.5, "sehr_ruhig": 2.0}


class BotTuningError(ValueError):
    def __init__(self, message: str, code: str = "bad_bot_tuning") -> None:
        super().__init__(message)
        self.code = code


def _flag(key: str, group: str, label: str, text: str, *, needs: str | None = None, note: str | None = None) -> dict:
    return {"key": key, "group": group, "kind": "bool", "label": label, "text": text, "needs": needs, "note": note}


def _number(key: str, group: str, label: str, text: str, low: int, high: int, step: int, unit: str, *,
            needs: str | None = None, note: str | None = None) -> dict:
    return {"key": key, "group": group, "kind": "number", "label": label, "text": text, "min": low, "max": high, "step": step,
            "unit": unit, "needs": needs, "note": note}


GROUPS = [
    {"id": "rechnen", "title": "Durchrechnen der Kartenwahl",
     "text": "Beim Durchrechnen verteilt der Bot die Karten, die er nicht sieht, zufällig (aber regelkonform) auf die Mitspieler und spielt "
             "jede erlaubte Karte in vielen solchen Verteilungen zu Ende. Er wählt die Karte mit den meisten erwarteten Augen für seine Partei. "
             "Der Bot kennt nie fremde Hände, nur öffentlich Bekanntes."},
    {"id": "ansagen", "title": "Ansagen (Re, Kontra, Absagen)",
     "text": "Im Normalspiel entscheidet der Bot per Stichprobe, ob er Re/Kontra oder eine Absage ansagt. In allen anderen Spielarten gilt "
             "eine feste Regel (nur Re/Kontra, früh, nach Handstärke)."},
    {"id": "tempo", "title": "Tempo", "text": "Wie schnell Bots am Tisch spielen. Die Rechenzeit ist davon unabhängig."},
    {"id": "grund", "title": "Grundstrategie (Rückfall)",
     "text": "Diese Regeln gelten immer dann, wenn nicht durchgerechnet wird: bei ausgeschaltetem Durchrechnen, bei Karten mit nur einer "
             "erlaubten Wahl und wenn keine passende Verteilung gefunden wird. Sie sind im Selbstspiel abgestimmt; Änderungen nur für Versuche."},
    {"id": "labor", "title": "Experimentell",
     "text": "Verfahren ohne nachgewiesenen Gewinn. Nur für Versuche gedacht."},
]

_RECHNEN, _ANSAGEN, _GRUND, _LABOR = "rechnen", "ansagen", "grund", "labor"

CATALOG: list[dict] = [
    _flag("pimc", _RECHNEN, "Durchrechnen insgesamt",
          "Hauptschalter. Aus: Die Bots spielen alle Karten nach festen Regeln (Grundstrategie), in jeder Spielart. Das spart Rechenzeit, spielt "
          "aber deutlich schwächer.",
          note="Im Normalspiel schlagen die Bots mit Durchrechnen die frühere Strategie klar (siehe Dokumentation, Abschnitt Bots)."),
    _flag("pimc_solo", _RECHNEN, "Durchrechnen im Solo",
          "Bei allen sieben Soli (Farben-, Damen-, Buben-, Fleischlos-Solo, Pflicht- und Lustsolo). Der Solist spielt öffentlich bekannt gegen drei.",
          needs="pimc", note="Messung: +0,48 ± 0,08 Punkte je Spiel gegenüber der festen Regel."),
    _flag("pimc_poverty", _RECHNEN, "Durchrechnen bei Armut",
          "Nach dem Kartentausch. Der Arme und sein Käufer sind Re. Die getauschten Karten kennen nur die beiden, die Bots rechnen ohne "
          "diese Kenntnis der anderen.",
          needs="pimc", note="Messung: +1,05 ± 0,15 Punkte je Spiel."),
    _flag("pimc_wedding", _RECHNEN, "Durchrechnen bei Hochzeit",
          "Der Spieler mit beiden Kreuz-Damen ist Re. Sein Partner ist, wer im ersten, zweiten oder dritten Stich zuerst einen fremden Stich "
          "gewinnt; sonst wird es ein Solo. Das bilden die Verteilungen nach. Nach der Klärung stehen die Parteien fest.",
          needs="pimc", note="Messung: +0,40 ± 0,12 Punkte je Spiel."),
    _flag("pimc_public", _RECHNEN, "Öffentlich Angesagtes nutzen",
          "Nach einer Schweinchen-Ansage liegen alle noch nicht gespielten Karo-Asse beim Ansager, bei einer Hochzeit alle noch nicht "
          "gespielten Kreuz-Damen. Das weiß jeder am Tisch; der Bot verteilt diese Karten deshalb nicht mehr zufällig.",
          needs="pimc", note="Messung: Hochzeit +0,10 Punkte gegenüber ohne (im Rauschen), Schweinchen neutral. Aus nur für Vergleiche."),
    _number("pimc_budget", _RECHNEN, "Rechenaufwand", "Wie viele Stichproben ein Bot je Zug rechnet (verteilt auf die erlaubten Karten, jede Karte "
            "mindestens 6, höchstens 40). Mehr ist genauer, braucht aber proportional mehr Rechenzeit.", 40, 400, 20, "Stichproben",
            needs="pimc", note="Standard 160: im Mittel rund 50 ms je Zug."),
    {"key": "announce", "group": _ANSAGEN, "kind": "choice", "label": "Art der Ansage-Entscheidung",
     "text": "„Stichprobe“: Im Normalspiel spielt der Bot seine Hand mehrfach durch und sagt an, wenn die Erfolgschance hoch genug ist. "
             "„Feste Regel“: Ansage nur von Re/Kontra, früh und nach Handstärke; keine Absagen.",
     "options": [{"value": "pimc", "label": "Stichprobe (Standard)"}, {"value": "legacy", "label": "Feste Regel"}], "needs": None,
     "note": None},
    _number("announce_p0", _ANSAGEN, "Schwelle für Re/Kontra", "Ab dieser Gewinnchance sagt ein Bot Re bzw. Kontra an. Höher = vorsichtiger.",
            50, 95, 1, "%", needs="announce"),
    _number("announce_p1", _ANSAGEN, "Schwelle für Absagen", "Ab dieser Chance, die Absage (keine 90 / 60 / 30 / schwarz) zu erreichen, sagt "
            "ein Bot sie an, jeweils die höchste, die reicht. Höher = vorsichtiger.", 60, 99, 1, "%", needs="announce"),
    _number("announce_samples", _ANSAGEN, "Stichproben je Ansage", "Wie oft der Bot die Hand für die Ansage-Entscheidung durchspielt. "
            "Mehr = verlässlicher, aber langsamer.", 8, 100, 2, "Stichproben", needs="announce"),
    {"key": "tempo", "group": "tempo", "kind": "choice", "label": "Spieltempo der Bots",
     "text": "Faktor auf alle Wartezeiten der Bots (Bedenkzeit, Vorbehaltsabfrage, Pause nach dem Stich). Gilt für alle Tische, auch laufende.",
     "options": [{"value": "schnell", "label": "Schnell (0,6×)"}, {"value": "normal", "label": "Normal (Standard)"},
                 {"value": "ruhig", "label": "Ruhig (1,5×)"}, {"value": "sehr_ruhig", "label": "Sehr ruhig (2×)"}], "needs": None,
     "note": None},
    _flag("lead_master", _GRUND, "Sichere Fehlkarten zuerst ausspielen",
          "Eine Fehlfarben-Karte mit Augen, die kein Gegner mehr überbieten kann (die höchste ihrer Farbe), wird zuerst ausgespielt, um Augen zu sichern."),
    _flag("lead_risk", _GRUND, "Risiko beim Ausspielen meiden",
          "Beim Ausspielen werden Farben vermieden, in denen ein Gegner nachweislich keine Karte mehr hat (er würde stechen); Farben, in denen der "
          "Partner leer ist, werden bevorzugt."),
    _flag("lead_trump", _GRUND, "Trumpfstark ausspielen",
          "Mit mindestens 5 Trümpfen spielt der Bot einen Trumpf aus, den kein Gegner mehr überbieten kann (bei 7 oder mehr Trümpfen den stärksten, sonst den schwächsten davon)."),
    _flag("ally_secure", _GRUND, "Partner nur bei sicherem Stich schmieren",
          "Gewinnt der Partner den Stich, gibt der Bot nur dann Augen dazu, wenn der Stich nicht mehr überstochen werden kann."),
    _flag("safe_win", _GRUND, "Sicher gewinnen bevorzugen",
          "Zum Gewinnen eines Stichs wird die schwächste Karte genommen, die auch gegen die Nachspieler hält."),
    _flag("short_suit", _GRUND, "Kurze Farben zuerst abwerfen",
          "Beim Abwerfen werden kurze Fehlfarben zuerst gewählt, damit man früh farbfrei wird und stechen kann."),
    _flag("infer", _LABOR, "Parteien aus dem Spielverhalten schätzen",
          "Der Bot schließt aus dem Verhalten der Mitspieler (Schmieren, Stechen) auf deren Partei und gewichtet die Verteilungen entsprechend.",
          needs="pimc", note="Im Selbstspiel kein messbarer Gewinn bei doppelter Rechenzeit."),
    _number("infer_w", _LABOR, "Stärke dieser Schätzung", "Gewicht, mit dem Verteilungen zählen, die zum Verhalten nicht passen "
            "(niedrig = starke Wirkung, 100 % = keine Wirkung).", 10, 100, 5, "%", needs="infer"),
    _flag("pimc_win", _LABOR, "Sieg statt Augen bewerten",
          "Die Karte wird nach der Siegchance der Partei (danach Augen) gewählt statt nach den erwarteten Augen.", needs="pimc",
          note="Nicht gemessen; Standard: aus."),
]
for _item in CATALOG:                       # "needs": der Schalter, von dem diese Einstellung abhaengt (Oberflaeche graut sie sonst aus)
    if _item["needs"]:
        _item["needs"] = {"key": _item["needs"], "value": "pimc" if _item["needs"] == "announce" else True}
BY_KEY = {item["key"]: item for item in CATALOG}
_PERCENT = {"announce_p0", "announce_p1", "infer_w"}      # im Dokument ganze Prozent, in ``bots.TUNE`` Anteile 0..1


def defaults() -> dict:
    values: dict = {}
    for item in CATALOG:
        if item["key"] == "tempo":
            values["tempo"] = "normal"
            continue
        raw = bots.TUNE_DEFAULTS[item["key"]]
        values[item["key"]] = round(raw * 100) if item["key"] in _PERCENT else raw
    return values


def _coerce(item: dict, value: object, strict: bool) -> object:
    """Einen Wert pruefen. ``strict``: Fehler melden; sonst Unbrauchbares durch den Standard ersetzen (der Aufrufer prueft ``KeyError``)."""
    kind = item["kind"]
    if kind == "bool":
        if isinstance(value, bool):
            return value
        raise ValueError(f"„{item['label']}“ muss an oder aus sein.")
    if kind == "choice":
        if any(value == o["value"] for o in item["options"]):
            return value
        raise ValueError(f"„{item['label']}“: ungültige Auswahl.")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        raise ValueError(f"„{item['label']}“ muss eine Zahl sein.")
    number = int(round(value))
    if not item["min"] <= number <= item["max"]:
        raise ValueError(f"„{item['label']}“ muss zwischen {item['min']} und {item['max']} {item['unit']} liegen.")
    return number


def normalize(raw: object) -> dict:
    """Gespeicherte/unvollstaendige Werte -> vollstaendiges, gueltiges Dokument (Unbrauchbares = Standard)."""
    data = raw if isinstance(raw, dict) else {}
    out = defaults()
    for key, item in BY_KEY.items():
        if key in data:
            try:
                out[key] = _coerce(item, data[key], False)
            except ValueError:
                pass
    return out


def validate_update(raw: object, current: dict) -> dict:
    """Eingabe des Betreibers pruefen (Teilmengen sind erlaubt, der Rest bleibt wie er ist); Fehler als ``BotTuningError``."""
    if not isinstance(raw, dict) or not isinstance(raw.get("values"), dict):
        raise BotTuningError("Ungültige Einstellungen.")
    merged = dict(current)
    for key, value in raw["values"].items():
        if key not in BY_KEY:
            raise BotTuningError(f"Unbekannte Einstellung „{key}“.")
        try:
            merged[key] = _coerce(BY_KEY[key], value, True)
        except ValueError as exc:
            raise BotTuningError(str(exc)) from None
    if merged["announce_p1"] < merged["announce_p0"]:
        raise BotTuningError("Die Schwelle für Absagen darf nicht unter der Schwelle für Re/Kontra liegen.")
    return normalize(merged)


def apply(values: dict) -> None:
    """Werte in den laufenden Prozess uebernehmen (``bots.TUNE``, Tempo) und die Zwischenspeicher der Bots leeren."""
    for key, value in normalize(values).items():
        if key == "tempo":
            service.PACE["factor"] = TEMPO[value]
        else:
            bots.TUNE[key] = value / 100 if key in _PERCENT else value
    bots._PIMC_CACHE.clear()
    bots._ANNOUNCE_CACHE.clear()


def schema() -> dict:
    return {"groups": copy.deepcopy(GROUPS), "items": copy.deepcopy(CATALOG), "defaults": defaults()}


class MemoryBotTuning:
    """Speicher fuer Tests: haelt das Dokument im Arbeitsspeicher."""

    def __init__(self, initial: object = None) -> None:
        self._data = normalize(initial)
        self._lock = threading.Lock()

    def get(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data)

    def put(self, data: dict) -> dict:
        with self._lock:
            self._data = normalize(data)
            return copy.deepcopy(self._data)

    def reset(self) -> dict:
        return self.put({})


def dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def loads(text: str | None) -> dict | None:
    """Gespeichertes Dokument oder ``None``, wenn noch nie gespeichert wurde (dann bleiben die Standardwerte im Code)."""
    if not text:
        return None
    try:
        return normalize(json.loads(text))
    except ValueError:
        return None
