# DDV-Regelmatrix

Diese Übersicht zeigt, **welche Regeln der DDV-Turnierspielregeln (TSR) die Software umsetzt**, wo im Code, durch welche Tests, und wo sie bewusst abweicht oder etwas nicht umsetzt.
Sie ist die Grundlage für alle Regelfragen und wird bei jeder Regeländerung mitgepflegt ([DEVELOPMENT.md](DEVELOPMENT.md#eine-spielregel-ändern-oder-hinzufügen)).

- **Grundlage:** Turnier-Spielregeln (TSR) des Deutschen Doppelkopf-Verbandes e. V., **Stand 21.02.2026** (veröffentlicht auf [doko-verband.de](https://doko-verband.de)). Die Paragraphennummern unten beziehen sich auf diese Fassung.
- **Abgleich:** Die für das Spiel relevanten Abschnitte der TSR wurden mit dieser Matrix verglichen (Stand der Prüfung: November 2026). Bei Änderungen der TSR sind die Paragraphennummern erneut zu prüfen. Die Hinweise der Regelkommission vom April 2026 betreffen Platztausch, Mischen und Abheben sowie das Einpassen nach Regelverstößen. Sie ändern nichts an den hier umgesetzten Spielregeln.
- **Unabhängig:** Das Projekt steht in keiner Verbindung zum DDV. Die TSR dienen als Regelgrundlage; für Turniere gelten allein die Originale. Bei Abweichungen gilt die TSR.
- **Code:** `backend/app/rules/` (reines Python, ohne Flask und Datenbank). **Tests:** `backend/tests/rules/`, derzeit **177 Tests** (`cd backend && python -m unittest discover -s tests/rules -t .`).

Status: ✅ umgesetzt und getestet · 🟡 umgesetzt mit Auslegung (siehe Abschnitt 2) · ➖ nicht umgesetzt · ⛔ am digitalen Tisch gegenstandslos

## 1. Regelmatrix

| TSR | Regel | Modul | Test | Status |
|---|---|---|---|---|
| 2.2 | 48 Karten (A,10,K,Q,J,9 je Farbe doppelt), 240 Augen; Werte 11/10/4/3/2/0 | `cards.py` | `DeckTests` | ✅ |
| 2.2 (Variante) | 40 Karten ohne Neunen, 10 Handkarten: nur als Hausprofil, nicht DDV-konform | `profile.py`, `cards.py` | `DeckTests`, Simulation | 🟡 A1 |
| 2.3.4 | Normalspiel: Trumpf = ♥10, 4 Damen, 4 Buben, ♦A,10,K,9 (26 Karten) | `trump.py` | `TrumpOrderTests` | ✅ |
| 2.3.5 | Farbsolo (♣/♠/♥/♦): Trumpffarbe ersetzt Karo; ♥-Solo 24 Trümpfe | `trump.py` | `test_hearts_solo…`, `test_trump_counts…` | ✅ |
| 2.3.6 | Damensolo / Bubensolo: 8 Trümpfe, ♥10 ist normale Karte | `trump.py` | `test_queen_and_jack_solo` | ✅ |
| 2.3.7 | Fleischloser: kein Trumpf | `trump.py` | `test_aces_solo…` | ✅ |
| 3.3.7 | Geben 3-3-3-3 ab linkem Nachbarn des Gebers | `dealing.py` | `test_deal_three_by_three…` | ✅ |
| 3.3 | Mischen: gleichverteilt (`secrets.SystemRandom`), ohne Verteilungsfilter | `dealing.py` | – | 🟡 A2 |
| 3.3.3, 3.3.4 | Gründlich mischen, vom rechten Nachbarn abheben lassen | – | – | ⛔ übernimmt der Algorithmus |
| 4.1.2–4.1.4 | Vorbehaltsabfrage reihum ab Sitz links vom Geber; keiner → Normalspiel; einer → Taufe | `game.py` | `ReservationTests` | ✅ |
| 4.1.5–4.1.7 | Mehrere Vorbehalte: erst „Pflichtsolo?“, dann „Lustsolo?“, erstes Ja gewinnt | `game.py` | `test_multiple_reservations…`, `test_first_yes…`, `test_lustsolo_stage…` | ✅ |
| 4.1.6 | Hochzeit kommt bei mehreren Vorbehalten nie zum Zuge | `game.py` | `test_wedding_never_chosen…` | ✅ |
| 4.1.6 (Lücke) | Mehrere Vorbehalte, niemand will ein Solo → Normalspiel | `game.py` | `test_everyone_declines…` | 🟡 A3 |
| 4.1.8 | Vorzeitige Taufe als Abkürzung | – | – | ➖ ohne Regelwirkung |
| 4.1.9, 4.2.3, 8.6 | Vorführung: fehlende Pflichtsoli = noch zu spielende Normalspiele → erster Spieler links vom Geber ohne Pflichtsolo muss solo; keine Abfrage | `round_rules.py`, `game.py` | `test_forced…`, `test_dealer_can_be_forced_last`, Rundensimulation | ✅ |
| 4.2.2 | Pflichtsolist spielt zum ersten Stich auf | `game.py` | `test_single_reservation…` | ✅ |
| 4.2.4/4.2.5 | Pflichtsolo in eigener Rubrik, zählt nicht zu den 24; derselbe Geber gibt neu (nach Vorführung der nächste) | `round_rules.py` | `RoundRuleTests` | ✅ |
| 4.3.1 | Lustsolo erst nach eigenem Pflichtsolo; linker Nachbar des Gebers spielt auf | `game.py` | `test_solo_after_pflichtsolo…` | ✅ |
| 4.3.2 | Lustsolo zählt als Normalspiel, Geber wechselt | `round_rules.py` | `test_lustsolo_counts…` | ✅ |
| 4.4 | Angemeldete Hochzeit nur mit beiden ♣D und als einziger Vorbehalt | `game.py` | `test_wedding_needs_both…` | ✅ |
| 4.4.3 | Klärungsstich: erster Stich eines Nicht-Hochzeiters (Stich 1–3), sonst Karo-Solo; zählt als Normalspiel, ersetzt kein Pflichtsolo | `game.py`, `round_rules.py` | `WeddingTests` | ✅ |
| 4.4.5 | Beide ♣D, „gesund“ → Stille Hochzeit (Solo-Wertung, Normalspiel-Fristen) | `game.py`, `scoring.py` | `test_silent_wedding…` | ✅ |
| 5.1.1 | Zum ersten Stich spielt aus, wer die Vorbehaltsabfrage begonnen hat (Sitz links vom Geber), außer beim Pflichtsolo; erst nach beendeter Abfrage und Taufe | `game.py` | `ReservationTests` | ✅ |
| 5.2 | Bedienpflicht (Trumpf/Fehlfarbe), sonst freie Wahl | `tricks.py` | `FollowTests` | ✅ |
| 5.3.3 | Stichgewinner; gleiche Karten: die zuerst gelegte (auch ♥10) | `tricks.py` | `TrickWinnerTests` | ✅ |
| 5.3.5 | Der zuletzt abgeschlossene Stich ist einsehbar (`lastTrick`), frühere nicht; alle Stiche erst nach Spielende | `game.py` (`_public`) | Simulation (`check_views`) | ✅ |
| 5.3.6, 5.3.7, 5.3.8 | Stiche einzeln einsammeln, verdeckt ablegen, Zählen deckt auf | – | – | ⛔ der Server führt die Stiche |
| 5.4 | Abkürzen (nur der Solospieler darf, Rest der Stiche an die Gegner) | – | – | ➖ jedes Spiel wird zu Ende gespielt |
| 5.5.1 | Parteiklärung öffentlich: Solo, Hochzeit, ♣D gespielt, Fehlkarte auf Trumpf, An-/Absage | `game.py` | `test_clarification_by_…` | ✅ |
| 6.2.2 | Erstansage mit ≥ 11 von 12 Handkarten | `announcements.py`, `profile.py` | `TimingTests` | ✅ |
| 6.3.4 | Absagen mit ≥ 10/9/8/7 Karten (keine 90/60/30/schwarz) | `announcements.py` | `test_absage_deadlines…` | ✅ |
| 6.4.1 | Ansage auch außerhalb des eigenen Zuges | `game.py` | `test_clarified_in_first_trick…` | ✅ |
| 4.4.4, 6.4.2 | Hochzeit: Erstansage erst nach dem Klärungsstich; Fristen −1/−2 bei Klärung in Stich 2/3 | `game.py`, `announcements.py` | `WeddingTests`, `WeddingShiftTests` | ✅ |
| 6.4.3 | Stufen überspringen nur, wenn alle übersprungenen noch zulässig; alle werden mitgewertet; Nachholen unzulässig | `announcements.py`, `scoring.py` | `test_jump_requires…`, `test_absagen_count_all_stages` | ✅ |
| 6.4.4 | Erwiderung (nur Re/Kontra) mit einer Karte weniger; verspätete Erwiderung sperrt eigene Absagen | `announcements.py` | `ReplyTests` | 🟡 A5 |
| 6.4.7 | Keine Wiederholung | `announcements.py` | `test_no_repetition` | ✅ |
| 6.3.1 | „schwarz“ = kein Stich (nicht 0 Augen; mit Neunen relevant) | `scoring.py` | `test_schwarz_by_tricks…`, `test_zero_points_but_one_trick…` | ✅ |
| 7.1.1/7.1.2 | Gewinnschwellen 121/120, bei Absage 151/181/211/alle Stiche, gegen Absage 90/60/30/1 Stich | `scoring.py` | `WinnerTests` | ✅ |
| 7.1.3 | Kein Sieger bei verfehlten Zielen: nur „gespielt“-Posten, (e)/(f), Sonderpunkte | `scoring.py` | `test_no_winner_scoring` | 🟡 A4 |
| 7.2.2 | Sieg 1; unter 90/60/30/schwarz je +1; Re/Kontra je +2; je Absagestufe +1; Absage geschlagen (120/90/60/30) +1 | `scoring.py` | `ValueTests`, Raster-Test | ✅ |
| 7.2.3 | Sonderpunkte nur im Normalspiel: gegen ♣D gewonnen, Doppelkopf (≥ 40 Augen im Stich), Fuchs gefangen; mit Spielpunkten verrechnet | `scoring.py` | `SpecialPointsTests` | ✅ |
| 7.2.3 (Karlchen) | Kreuz-Bube im letzten Stich: Die TSR nennt keinen Punktwert, umgesetzt ist 1 Sonderpunkt (Option `karlchen`, Standard an) | `scoring.py` | `SpecialPointOptionTests` | 🟡 A7 |
| 7.2.4 | Solo (auch Stille Hochzeit/Hochzeit-Solo): keine Sonderpunkte, Solist ×3, Gegner je einfach | `scoring.py` | `SoloTests`, `WeddingTests` | ✅ |
| 7.3.3 | Gerade-Ungerade-Regel | `scoring.py` | Raster-Test (Nullsumme, Parität) | ✅ |
| 8.5, 8.6 | Runde = 24 Normalspiele, dazu je Spieler ein Pflichtsolo | `round_rules.py` | `FullRoundSimulation` | ✅ |
| 8.5 (Zeit) | 100 Minuten Spielzeit je Runde, Streichen offener Spiele, Nachspielzeit | – | – | ➖ ohne Zeitlimit; eine Runde endet nach dem 24. Normalspiel |
| 9 | Regelverstöße, Reklamation, Strafpunkte | – | – | ⛔ Der Server lässt Verstöße nicht zu (keine Reklamation nötig). Strafpunkte sind ➖ nicht umgesetzt |
| 2 bis 3, 8.1 bis 8.4 | Turnierorganisation: Auslosung, Tischtausch, Spielzettel, Schiedsrichter | – | – | ⛔ nicht Teil des Spiels am Tisch |

## 1b. Zuschaltbare Regeln

Das Spiel kennt **14 Optionen** in zwei Gruppen (die Gruppe steht im Regelformular): **„Beliebte Regeln“** (`popular`, sechs Optionen) und **„Haus- und Kneipenregeln“** (`pub`, acht Optionen). Jede ist einzeln an- und abschaltbar (`RuleOptions` in `rules/options.py`; `rule_schema()` liefert Texte, Gruppen, Standardwerte und Abhängigkeiten für das Formular, `GET /api/rule-schema`).

Gewählt wird **vor Rundenbeginn**; Optionen und Deck-Variante bleiben während der Runde fest. Standard: **Dulle, Karlchen und Fuchsjagd an**, alles andere aus. Das Profil `ddv_tsr_2026` (48 Karten, Standardoptionen) gilt als DDV-konform; ohne Neunen heißt es `house_no_nines`, jede andere Kombination `custom` (`is_official_ddv` ist dann falsch).

| Option (Kennung) | Gruppe | Default | Wirkung | Modul | Tests |
|---|---|---|---|---|---|
| Dulle als Höchsttrumpf (`dulle`) | popular | **an** | ♥10 höchster Trumpf; aus: ♥10 ist normale Herz-Karte (Reihenfolge A,10,K,9, kein Trumpf) | `trump.py` | `DulleTests` |
| Ohne Neunen (`sharp_doppelkopf`) | popular | aus | Deck ohne Neunen, 10 Karten (= `DeckVariant`, keine `RuleOptions`-Option) | `options.py`, `profile.py` | `test_settings_mapping…` |
| Karlchen-Punkt (`karlchen`) | popular | **an** | Sonderpunkt: letzten Stich mit ♣-Bube gewinnen | `scoring.py` | `SpecialPointOptionTests` |
| Füchse jagen (`fuchsjagd`) | popular | **an** | Sonderpunkt: gegnerisches ♦-Ass fangen | `scoring.py` | `SpecialPointOptionTests` |
| Ansagepflicht nach dem ersten Stich (`mandatory_announcements`) | popular | aus | Gewinner des 1. Stichs muss Re/Kontra ansagen, bevor er weiterspielt (nur Normalspiel) | `game.py` | `MandatoryAnnouncementTests` |
| Solist kommt raus (`solo_leads`) | popular | aus | Solist eröffnet auch im Lustsolo (Pflichtsolo spielt nach TSR 4.2.2 ohnehin aus) | `game.py` | `SoloLeadsTests` |
| Gegnerisches Karlchen abfangen (`karlchen_caught`) | pub | aus | Sonderpunkt für das Abfangen des gegnerischen ♣-Buben im letzten Stich | `scoring.py` | `test_karlchen_caught…` |
| Schweinchen (`schweinchen`) | pub | aus | Wer beide ♦-Asse hält, kann sie per Aktion `DeclareSchweinchen` zu höchsten Trümpfen erklären | `trump.py`, `game.py` | `SchweinchenTests` |
| Armut (`poverty`) | pub | aus | Vorbehalt mit höchstens 3 Trümpfen: 3 Karten verdeckt abgeben, reihum Käufer fragen, Käufer gibt 3 beliebige Karten zurück; danach Normalspiel (`GameKind.POVERTY`) mit Armem + Käufer als Re; ohne Käufer wird neu gegeben | `game.py`, `bots.py` | `test_poverty.py`, `test_poverty_bots.py` |
| Bock nach Herz-Stich (`bock_heart_trick`) | pub | aus | Stich aus 4 Herz-Fehlkarten → nächste 4 Spiele ×2 | `game.py`, `round_rules.py` | `BockTests` |
| Bock nach Nullspiel (`bock_zero_game`) | pub | aus | Spiel endet mit 0 Punkten → nächste 4 Spiele ×2 | dto. | `BockTests` |
| Bock bei 120 zu 120 (`bock_120`) | pub | aus | beide Parteien genau 120 Augen → nächste 4 Spiele ×2 | dto. | `BockTests` |
| Zweite Dulle schlägt die erste (`second_dulle_wins`) | pub | aus | Beide Dullen im selben Stich: die zweite gewinnt (setzt `dulle` voraus) | `tricks.py` | `SecondDulleTests` |
| Ausnahme im letzten Stich (`second_dulle_wins_except_last`) | pub | aus | Im letzten Stich gewinnt die erste Dulle (setzt `second_dulle_wins` voraus) | `game.py` | `SecondDulleTests` |

Auslegungen zu den Optionen:
- **B1 Dulle aus:** ♥10 ist eine normale Herz-Karte (Fehlkarte bzw. Teil der Trumpffarbe im Herz-Solo).
- **B2 Nullspiel:** Das Spielergebnis (Re minus Kontra, vor Verdopplung) ist 0, z. B. 120:120 mit gegenseitiger „keine 90“-Absage. Es gibt keine Partei mit 0 Augen im Sinne von „schwarz“.
- **B3 Bockrunden:** Jede Bock-Regel löst pro Spiel höchstens einmal aus; Auslöser addieren sich (2 Auslöser = 8 Bockspiele, nacheinander, Faktor stets ×2). Jedes gespielte Spiel (auch Pflichtsolo/Vorführung) verbraucht ein Bockspiel; verdoppelt werden alle Spielpunkte des Spiels. Ein Bockspiel kann selbst neue Bockrunden auslösen.
- **B4 Pflichtansage:** Nur Normalspiel (nicht Solo, Hochzeit, Stille Hochzeit); entfällt, wenn die Partei des Gewinners bereits angesagt hat (auch durch den Partner). Der Gewinner kann sonst keine Karte spielen, bis er angesagt hat.
- **B5 Schweinchen:** Nur vor der eigenen ersten Karte und nur, wo ♦-Ass Trumpf ist (Normalspiel, Hochzeit, Karo-Solo). Erklärung ist öffentlich und gilt für den Rest des Spiels; gleiche Asse: das zuerst gelegte gewinnt. Das Fuchs-Sonderpunkt-Verhalten bleibt unverändert.
- **B6 Zweite Dulle:** Wirkt nur, wo die ♥10 tatsächlich Dulle ist (Option `dulle` an und ♥10 Trumpf, also nicht im Damen-/Bubensolo).
- **B8 Armut:** Nicht Teil der DDV-Regeln, daher nur als Hausregel (`poverty`). Ablauf und Entscheidungen:
  - *Voraussetzung:* höchstens 3 Trümpfe im Normalspiel (♥10 zählt nur mit Option `dulle`); wer mehr hat, bekommt „Armut“ nicht angeboten. Angemeldet wird sie als gewöhnlicher Vorbehalt und beim Taufen gewählt (`baptize {choice: "poverty"}`).
  - *Rangfolge bei mehreren Vorbehalten:* Pflichtsolo vor Lustsolo vor Armut; die Hochzeit kommt bei mehreren Vorbehalten ohnehin nie zum Zuge (TSR 4.1.6). Gefragt werden in der Armut-Stufe nur Vorbehalte mit höchstens 3 Trümpfen. Meldet niemand eine Armut an, gilt A3 (Normalspiel).
  - *Abgeben:* Der Arme legt immer genau 3 Karten verdeckt ab (auch Fehlfarben), damit die anderen die Trumpfzahl nicht kennen. Die Karten sind nur ihm sichtbar (`povertyPassed`), nicht dem Protokoll und nicht den anderen.
  - *Käufer:* Reihum im Uhrzeigersinn ab links vom Armen; der Erste, der zusagt, übernimmt. Er mischt die 3 Karten in sein Blatt (15 Karten) und gibt 3 beliebige Karten zurück (auch die soeben erhaltenen).
  - *Niemand übernimmt:* Das Blatt wird eingepackt und **neu gegeben**, derselbe Geber gibt noch einmal (Phase `redeal` im Regelkern, den Neuwurf macht die Tischschicht `redeal_if_needed`, weil der Regelkern nie mischt). Das abgebrochene Spiel zählt nicht: keine Spielnummer, kein Eintrag in der Runde, ein laufendes Bockspiel wird nicht verbraucht. Der Tisch meldet es mit `table.redeals`/`table.redealSeat`. Ein Bot übernimmt jede Armut (hat der Arme höchstens 3 Trümpfe, liegen mindestens 23 bei den anderen), ein Neugeben entsteht also nur, wenn Menschen ablehnen.
  - *Parteien:* Der Arme und der Käufer bilden **automatisch die Re-Partei**, die beiden anderen Kontra – unabhängig von den Kreuz-Damen (auch wenn ein Kontra-Spieler eine Kreuz-Dame hält und spielt, wird er dadurch nicht Re). Das ist für alle von Anfang an bekannt (`clarified`), die Wertung ist ein gewöhnliches Zwei-gegen-zwei (keine Solo-Wertung, Sonderpunkte wie im Normalspiel). Die Spielart heißt „Armut“ (`kind: "poverty"`).
  - *Spiel:* Normalspiel; Wertung, Ansagefristen und Bockrunden wie dort; die Pflichtansage (B4) gilt nicht. Buchung als Normalspiel (zählt zu den 24 Spielen, der Geber wechselt, kein Pflichtsolo).
- **B7 Karlchen fangen:** +1 je gegnerischem ♣-Buben im letzten Stich, der nicht selbst gewinnt; nur Normalspiel (Solo ohne Sonderpunkte).
- Unzulässige Kombinationen (Unteroption ohne Hauptoption) werden abgelehnt (`invalid_option_combination`).
- Die DDV-Konformität geht verloren, sobald eine Option vom Default abweicht (`profile.is_official_ddv`).

## 2. Auslegungen und Entscheidungen

Stellen, an denen die TSR nichts oder Mehrdeutiges sagt, und die Entscheidung der Software.

- **A1 Ohne-Neunen-Profil:** Fristen um die zwei fehlenden Karten verschoben (Erstansage ≥ 9 von 10, danach 8/7/6/5); Schwellen 121/151/181/211 unverändert. Die Kombination DDV-Profil + ohne Neunen wird abgelehnt (`validate_combination`).
- **A2 Verteilung:** gleichverteilt gemischt, keine Mindestqualität der Blätter. Ein Filter auf Mindestqualität wäre eine Hausregel und gehört nicht ins DDV-Profil.
- **A3 Mehrere Vorbehalte ohne Solo-Wunsch:** Nach 4.1.6 kann keine Hochzeit zum Zuge kommen; die TSR regelt den Fall „alle verneinen“ nicht. Umsetzung: Normalspiel; ein Spieler mit beiden ♣D spielt dann Stille Hochzeit (analog 4.4.5).
- **A4 Wertung ohne Sieger:** 7.1.3 verweist auf „7.2.2 (a) und (e, f)“. Umgesetzt: kein Grundwert, keine Ansage-/Absagepunkte, aber „unter 90/60/30/schwarz gespielt“ für die Partei, die den Gegner so gehalten hat, plus (e)/(f) und Sonderpunkte, netto verrechnet. Eine zweite Quelle (vereinfachte Kurzregeln) stützt diese Lesart. Gegenprüfung mit den Schiedsrichterhilfen des DDV steht aus.
- **A5 Erwiderung:** „notwendig war“ bedeutet die Mindestkartenzahl der höchsten Gegenansage, nicht die tatsächlich gehaltene Kartenzahl.
- **A6 Gleiche Karten im Stich:** Es gewinnt die zuerst gelegte (5.3.3), auch bei der ♥10.
- **A7 Karlchen:** 7.2.3 nennt den Kreuz-Buben im letzten Stich als Sonderpunkt, gibt aber keine Zahl an. Umgesetzt ist 1 Sonderpunkt wie bei den übrigen Sonderpunkten. Die Option `karlchen` ist standardmäßig an.

### Auslegungen der zuschaltbaren Regeln

- **B1 Dulle aus:** Die ♥10 ist eine normale Herz-Karte (Fehlkarte, im Herz-Solo Teil der Trumpffarbe).
- **B2 Nullspiel:** Das Spielergebnis (Re minus Kontra, vor Verdopplung) ist 0, z. B. 120:120 mit gegenseitiger „keine 90“-Absage. Es gibt keine Partei mit 0 Augen im Sinne von „schwarz“.
- **B3 Bockrunden:** Jede Bock-Regel löst pro Spiel höchstens einmal aus; Auslöser addieren sich (zwei Auslöser = acht Bockspiele, nacheinander, Faktor stets ×2). Jedes gespielte Spiel (auch Pflichtsolo/Vorführung) verbraucht ein Bockspiel; verdoppelt werden alle Spielpunkte des Spiels. Ein Bockspiel kann selbst neue Bockrunden auslösen.
- **B4 Pflichtansage:** Nur im Normalspiel (nicht Solo, Hochzeit, Stille Hochzeit); entfällt, wenn die Partei des Gewinners bereits angesagt hat (auch durch den Partner). Der Gewinner kann sonst keine Karte spielen, bis er angesagt hat.
- **B5 Schweinchen:** Nur vor der eigenen ersten Karte und nur, wo ♦-Ass Trumpf ist (Normalspiel, Hochzeit, Karo-Solo). Die Erklärung ist öffentlich und gilt für den Rest des Spiels; gleiche Asse: das zuerst gelegte gewinnt. Das Verhalten des Fuchs-Sonderpunkts bleibt unverändert.
- **B6 Zweite Dulle:** Wirkt nur, wo die ♥10 tatsächlich Dulle ist (Option `dulle` an und ♥10 Trumpf, also nicht im Damen- oder Bubensolo).
- **B7 Karlchen fangen:** +1 je gegnerischem ♣-Buben im letzten Stich, der nicht selbst gewinnt; nur im Normalspiel (Solo ohne Sonderpunkte).
- **B8 Armut** (nicht Teil der DDV-Regeln, daher nur als Hausregel `poverty`):
  - *Voraussetzung:* höchstens 3 Trümpfe im Normalspiel (die ♥10 zählt nur mit Option `dulle`); wer mehr hat, bekommt „Armut“ nicht angeboten. Angemeldet wird sie als gewöhnlicher Vorbehalt und beim Taufen gewählt (`baptize {choice: "poverty"}`).
  - *Rangfolge bei mehreren Vorbehalten:* Pflichtsolo vor Lustsolo vor Armut; die Hochzeit kommt bei mehreren Vorbehalten ohnehin nie zum Zuge (TSR 4.1.6). Gefragt werden in der Armut-Stufe nur Vorbehalte mit höchstens 3 Trümpfen. Meldet niemand eine Armut an, gilt A3.
  - *Abgeben:* Der Arme legt immer genau 3 Karten verdeckt ab (auch Fehlfarben), damit die anderen die Trumpfzahl nicht kennen. Die Karten sind nur ihm sichtbar (`povertyPassed`), nicht im Protokoll und nicht für die anderen.
  - *Käufer:* Reihum im Uhrzeigersinn ab links vom Armen; wer als Erster zusagt, übernimmt. Er mischt die 3 Karten in sein Blatt (15 Karten) und gibt 3 beliebige Karten zurück (auch die soeben erhaltenen).
  - *Niemand übernimmt:* Das Blatt wird eingepackt und **neu gegeben**; derselbe Geber gibt noch einmal (Phase `redeal` im Regelkern; den Neuwurf macht die Tischschicht mit `redeal_if_needed`, weil der Regelkern nie mischt). Das abgebrochene Spiel zählt nicht: keine Spielnummer, kein Eintrag in der Runde, ein laufendes Bockspiel wird nicht verbraucht. Der Tisch meldet es mit `table.redeals` und `table.redealSeat`. Ein Bot übernimmt jede Armut, ein Neugeben entsteht also nur, wenn Menschen ablehnen.
  - *Parteien:* Der Arme und der Käufer bilden **automatisch die Re-Partei**, die beiden anderen Kontra, unabhängig von den Kreuz-Damen. Das ist von Anfang an bekannt (`clarified`); die Wertung ist ein gewöhnliches Zwei-gegen-zwei (keine Solo-Wertung, Sonderpunkte wie im Normalspiel). Die Spielart heißt „Armut“ (`kind: "poverty"`).
  - *Spiel:* Normalspiel; Wertung, Ansagefristen und Bockrunden wie dort; die Pflichtansage (B4) gilt nicht. Es zählt zu den 24 Normalspielen, der Geber wechselt, kein Pflichtsolo.
- Unzulässige Kombinationen (Unteroption ohne Hauptoption) werden abgelehnt (`invalid_option_combination`).
- Die DDV-Konformität geht verloren, sobald eine Option vom Standard abweicht (`profile.is_official_ddv`). Die Schnittstelle meldet das als `isOfficialDdv` und `profileId`; die Oberfläche zeigt die gewählten Regeln als Etiketten in Lobby und Tischliste.

## 3. Was bewusst nicht umgesetzt ist

| Thema | TSR | Begründung |
|---|---|---|
| Abkürzen durch den Solospieler | 5.4 | Jedes Spiel wird zu Ende gespielt. Für ein Online-Spiel ohne Schiedsrichter bringt Abkürzen kaum Zeitgewinn und würde Reklamationen nötig machen. |
| Zeitlimit und Streichen offener Spiele | 8.5 | Am privaten Tisch gibt es keine Turnierzeit. Die Runde endet nach dem 24. Normalspiel. Ersatzweise ersetzt eine Bot-Übernahme untätige Spieler (kein Teil der TSR). |
| Regelverstöße, Reklamation, Strafpunkte | 9 | Der Server lässt Verstöße gar nicht zu (Bedienpflicht, Ansagefristen, Reihenfolge werden geprüft). Es gibt keinen Schiedsrichter und keine Strafpunkte. |
| Mischen und Abheben | 3.3.3, 3.3.4 | Das Mischen übernimmt der Algorithmus. |
| Turnierorganisation | 2, 3, 8.1 bis 8.4 | Auslosung, Platztausch, Spielzettel und Schiedsrichter gehören nicht zum Spiel am Tisch. |

Dazu kommen Funktionen, die es in der TSR nicht gibt und die als zuschaltbare Regeln oder Betriebsfunktionen umgesetzt sind: Hausregeln (Abschnitt 1b), Bots, Bot-Übernahme bei Inaktivität.

## 4. Einstieg in den Code

Zentrale Schnittstelle des Regelkerns (`backend/app/rules/`):

- `new_game(...)` und `new_round(...)` erzeugen Spiel und Runde. Der Kern mischt nie selbst; die Kartenreihenfolge kommt von außen (`dealing.py`).
- `apply_action(state, action, expected_version=, action_id=)` ist die einzige Zustandsänderung (transaktional, mit Versionsprüfung und Idempotenz). Aktionen: `Declare`, `Resolve`, `Baptize`, `PlayCard`, `Announce`, `DeclareSchweinchen`, `PovertyPass`, `PovertyOffer`, `PovertyReturn`.
- `legal_actions(state, seat)` nennt, was ein Sitz jetzt darf. Oberfläche und Bots richten sich danach.
- `player_view`, `bot_view` und `spectator_view` erzeugen die Sichten (nie fremde Hände). `GameState.to_dict` und `from_dict` serialisieren.
- `RoundState`, `next_setup` und `record_game` führen die Runde (Geber, Pflichtsoli, Bockrunden, Punkte).

Architektur im Überblick: [ARCHITECTURE.md](ARCHITECTURE.md#der-regelkern).

## 5. Pflege

- Ändert der DDV die TSR, vergleicht man die betroffenen Abschnitte mit der Tabelle, passt Code, Tests und Matrix an und aktualisiert Stand und Datum oben. Die TSR nennt ihre Änderungen im Abschnitt 11 („Inkrafttreten und Änderungshistorie“). Zuletzt geändert wurde 5.3.8 (gültig ab 1. März 2026).
- Jede neue Regel bekommt eine Zeile (TSR-Abschnitt, Modul, Test, Status) und, wenn sie auslegungsbedürftig ist, einen Eintrag in Abschnitt 2.
- Bei Zweifeln an der Auslegung hilft die Regelkommission des DDV (Kontakt auf [doko-verband.de](https://doko-verband.de)).
