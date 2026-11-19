"""Fertige Szenarien fuer den Test-Tisch (Vorlagen; im Admin-Formular frei aenderbar).

Alle Haende sind vollstaendige 12-Karten-Blaetter (Spiel mit Neunen), sofern nicht anders angegeben.
Die Armut-Blaetter: ARM (3 Truempfe), STARK (9 Truempfe), MITTEL_A (8) und MITTEL_B (6).
"""
from __future__ import annotations

ARM = "Q♣ J♦ 9♦ A♣ A♣ 10♣ K♣ A♠ 10♠ K♠ A♥ K♥"
STARK = "10♥ 10♥ Q♣ Q♠ Q♠ Q♥ J♣ J♣ A♦ 9♣ 9♣ 9♠"
MITTEL_A = "Q♥ Q♦ J♠ J♥ A♦ 10♦ K♦ 9♦ 10♣ A♠ A♥ 9♥"
MITTEL_B = "Q♦ J♠ J♥ J♦ 10♦ K♦ K♣ 10♠ K♠ 9♠ K♥ 9♥"

# Hochzeit: Sitz 1 hat beide Kreuz-Damen. Normalspiel: je eine Kreuz-Dame bei Sitz 1 und 2 (Re = 1, 2).
HOCHZEIT = {
    0: "Q♠ Q♠ J♣ J♣ A♦ A♦ A♣ A♣ 10♣ 10♣ K♣ K♣",
    1: "Q♣ Q♣ 10♥ 10♥ J♦ J♦ A♠ A♠ 10♠ 10♠ K♠ K♠",
    2: "Q♥ Q♥ J♠ J♠ 10♦ 10♦ 9♣ 9♣ A♥ A♥ K♥ K♥",
    3: "Q♦ Q♦ J♥ J♥ K♦ K♦ 9♦ 9♦ 9♠ 9♠ 9♥ 9♥",
}
NORMAL = {**HOCHZEIT,
          1: "Q♣ Q♥ 10♥ 10♥ J♦ J♦ A♠ A♠ 10♠ 10♠ K♠ K♠",
          2: "Q♣ Q♥ J♠ J♠ 10♦ 10♦ 9♣ 9♣ A♥ A♥ K♥ K♥"}


def _seats(*bots: bool, names: tuple[str, ...] = ()) -> list[dict]:
    out = []
    for i, bot in enumerate(bots):
        name = names[i] if i < len(names) and names[i] else (f"Bot {i + 1}" if bot else f"Platz {i + 1}")
        out.append({"name": name, "bot": bot})
    return out


def _hands(*texts: str) -> dict:
    return {str(i): t.split() for i, t in enumerate(texts) if t}


PRESETS: list[dict] = [
    {"id": "armut_arm", "title": "Armut – du bist der Arme",
     "description": "Platz 1 hat nur 3 Trümpfe. Melde Vorbehalt an, sage Armut an, wähle drei Karten zum Weitergeben. "
                    "Bot 2 hat 9 Trümpfe und übernimmt.",
     "scenario": {"settings": {"poverty": True}, "dealer": 3,
                  "hands": _hands(ARM, STARK, MITTEL_A, MITTEL_B),
                  "seats": _seats(False, True, True, True, names=("Du (arm)", "Bot (Käufer)"))}},
    {"id": "armut_kaeufer", "title": "Armut – du nimmst sie mit",
     "description": "Bot 4 ist arm und gibt drei Karten ab. Du (Platz 1) wirst als Erster gefragt, hast 9 Trümpfe, "
                    "nimmst die Karten und gibst drei zurück.",
     "scenario": {"settings": {"poverty": True}, "dealer": 2,
                  "hands": _hands(STARK, MITTEL_A, MITTEL_B, ARM),
                  "seats": _seats(False, True, True, True, names=("Du (Käufer)", "", "", "Bot (arm)"))}},
    {"id": "armut_neugabe", "title": "Armut – niemand nimmt sie (Neugabe)",
     "description": "Bot 4 ist arm, die Plätze 1 bis 3 spielst du: Lehne an jedem Platz ab – danach wird neu gegeben.",
     "scenario": {"settings": {"poverty": True}, "dealer": 2,
                  "hands": _hands(MITTEL_A, MITTEL_B, STARK, ARM),
                  "seats": _seats(False, False, False, True, names=("Platz 1", "Platz 2", "Platz 3", "Bot (arm)"))}},
    {"id": "armut_alle", "title": "Armut – alle vier Plätze selbst",
     "description": "Platz 3 ist arm, Platz 4 hat 9 Trümpfe. Du spielst alle Plätze und wechselst zwischen ihnen.",
     "scenario": {"settings": {"poverty": True}, "dealer": 3,
                  "hands": _hands(MITTEL_A, MITTEL_B, ARM, STARK),
                  "seats": _seats(False, False, False, False, names=("Platz 1", "Platz 2", "Platz 3 (arm)", "Platz 4 (Käufer)"))}},
    {"id": "hochzeit", "title": "Hochzeit",
     "description": "Du (Platz 2) hältst beide Kreuz-Damen und meldest Vorbehalt „Hochzeit“ an.",
     "scenario": {"dealer": 3, "hands": {str(k): v.split() for k, v in HOCHZEIT.items()},
                  "seats": _seats(True, False, True, True, names=("", "Du (Hochzeiter)"))}},
    {"id": "schweinchen", "title": "Schweinchen",
     "description": "Du (Platz 1) hältst beide Karo-Asse; die Hausregel Schweinchen ist an.",
     "scenario": {"settings": {"schweinchen": True}, "dealer": 3,
                  "hands": {"0": "A♦ A♦ Q♣ Q♠ J♣ 10♥ K♦ A♣ A♠ 10♣ K♠ 9♣".split()},
                  "seats": _seats(False, True, True, True, names=("Du",))}},
    {"id": "damensolo", "title": "Starke Hand (Solo ansagen)",
     "description": "Du (Platz 1) hast sechs Damen und zwei Dullen: Melde Vorbehalt an und sage ein Solo an.",
     "scenario": {"dealer": 3,
                  "hands": {"0": "Q♣ Q♣ Q♠ Q♠ Q♥ Q♦ 10♥ 10♥ A♣ A♠ 10♣ K♥".split()},
                  "seats": _seats(False, True, True, True, names=("Du",))}},
    {"id": "normal_re_kontra", "title": "Normalspiel mit festen Parteien",
     "description": "Re sind Platz 2 und 3 (Kreuz-Damen), Kontra Platz 1 und 4. Du spielst alle vier Plätze.",
     "scenario": {"dealer": 3, "hands": {str(k): v.split() for k, v in NORMAL.items()},
                  "seats": _seats(False, False, False, False)}},
    {"id": "endspiel", "title": "Endspiel (10 Stiche vorgespielt)",
     "description": "Normalspiel, die Bots haben zehn Stiche vorgespielt: Du (Platz 1) spielst die letzten zwei.",
     "scenario": {"dealer": 3, "hands": {str(k): v.split() for k, v in NORMAL.items()},
                  "seats": _seats(False, True, True, True, names=("Du",)), "advance": "tricks", "tricks": 10}},
    {"id": "ergebnis", "title": "Ergebnis-Dialog (Spiel fertig vorgespielt)",
     "description": "Das Spiel ist komplett vorgespielt: Du siehst Ergebnis, Wertung und „Nächstes Spiel“.",
     "scenario": {"dealer": 3, "hands": {str(k): v.split() for k, v in NORMAL.items()},
                  "seats": _seats(False, True, True, True, names=("Du",)), "advance": "tricks", "tricks": 12}},
    {"id": "pflichtsolo", "title": "Vorgeführtes Pflichtsolo",
     "description": "Es fehlt nur noch ein Normalspiel und Platz 4 hat sein Pflichtsolo noch nicht gespielt: "
                    "Er wird vorgeführt.",
     "scenario": {"dealer": 0, "round": {"normalGamesPlayed": 23, "pflichtsoloDone": [True, True, True, False]},
                  "hands": {"3": "Q♣ Q♠ Q♥ Q♦ J♣ J♠ J♥ J♦ A♦ 10♥ A♣ A♠".split()},
                  "seats": _seats(True, True, True, False, names=("", "", "", "Du (Platz 4)"))}},
    {"id": "bockrunde", "title": "Bockrunde",
     "description": "Zufällige Karten, vier Bockspiele offen (Punkte doppelt) – zum Prüfen der Bock-Anzeige.",
     "scenario": {"settings": {"bock_120": True}, "dealer": 0, "round": {"bockRemaining": 4},
                  "seats": _seats(False, True, True, True, names=("Du",))}},
    {"id": "zufall", "title": "Leerer Tisch (alles zufällig)",
     "description": "Zufällig verteilte Karten, alle vier Plätze von dir – Ausgangspunkt für eigene Szenarien.",
     "scenario": {"dealer": 0, "seats": _seats(False, False, False, False)}},
]


def preset_list() -> list[dict]:
    return [dict(p, scenario=dict(p["scenario"])) for p in PRESETS]
