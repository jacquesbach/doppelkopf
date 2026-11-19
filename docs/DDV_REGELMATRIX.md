# DDV-Regelmatrix (Meilenstein 1)

Grundlage: DDV-Turnierspielregeln (TSR), Stand 21.02.2026. Paragraphennummern bitte bei der Abnahme gegen das Original prüfen.
Code: `backend/app/rules/` (reines Python, ohne Flask/DB). Tests: `backend/tests/rules/` (144 Tests, `python -m unittest discover -s tests/rules -t .`).

Status: ✅ umgesetzt und getestet · 🟡 umgesetzt mit Annahme/Auslegung (siehe Entscheidungen) · ⏭ später (Service/UI) · ⛔ am digitalen Tisch gegenstandslos

## 1. Regelmatrix

| TSR | Regel | Modul | Test | Status |
|---|---|---|---|---|
| 2.2 | 48 Karten (A,10,K,Q,J,9 je Farbe doppelt), 240 Augen; Werte 11/10/4/3/2/0 | `cards.py` | `DeckTests` | ✅ |
| 2.2 (Variante) | 40 Karten ohne Neunen, 10 Handkarten – nur als Hausprofil | `profile.py`, `cards.py` | `DeckTests`, Simulation | 🟡 A1 |
| 2.3.4 | Normalspiel: Trumpf = ♥10, 4 Damen, 4 Buben, ♦A,10,K,9 (26 Karten) | `trump.py` | `TrumpOrderTests` | ✅ |
| 2.3.5 | Farbsolo (♣/♠/♥/♦): Trumpffarbe ersetzt Karo; ♥-Solo 24 Trümpfe | `trump.py` | `test_hearts_solo…`, `test_trump_counts…` | ✅ |
| 2.3.6 | Damensolo / Bubensolo: 8 Trümpfe, ♥10 ist normale Karte | `trump.py` | `test_queen_and_jack_solo` | ✅ |
| 2.3.7 | Fleischloser: kein Trumpf | `trump.py` | `test_aces_solo…` | ✅ |
| 3.3.7 | Geben 3-3-3-3 ab linkem Nachbarn des Gebers | `dealing.py` | `test_deal_three_by_three…` | ✅ |
| 3.3 | Mischen: fair, ohne Verteilungsfilter | `dealing.py` | – | 🟡 A2 |
| 4.1.2–4.1.4 | Vorbehaltsabfrage reihum ab Sitz links vom Geber; keiner → Normalspiel; einer → Taufe | `game.py` | `ReservationTests` | ✅ |
| 4.1.5–4.1.7 | Mehrere Vorbehalte: erst „Pflichtsolo?“, dann „Lustsolo?“, erstes Ja gewinnt | `game.py` | `test_multiple_reservations…`, `test_first_yes…`, `test_lustsolo_stage…` | ✅ |
| 4.1.6 | Hochzeit kommt bei mehreren Vorbehalten nie zum Zuge | `game.py` | `test_wedding_never_chosen…` | ✅ |
| 4.1.6 (Lücke) | Mehrere Vorbehalte, niemand will ein Solo → Normalspiel | `game.py` | `test_everyone_declines…` | 🟡 A3 |
| 4.1.8 | Vorzeitige Taufe als Abkürzung | – | – | ⏭ (UI-Abkürzung, ohne Regelwirkung) |
| 4.1.9, 4.2.3 | Vorführung: fehlende Pflichtsoli = noch zu spielende Normalspiele → erster Spieler links vom Geber ohne Pflichtsolo muss solo; keine Abfrage | `round_rules.py`, `game.py` | `test_forced…`, `test_dealer_can_be_forced_last`, Rundensimulation | ✅ |
| 4.2.2 | Pflichtsolist spielt zum ersten Stich auf | `game.py` | `test_single_reservation…` | ✅ |
| 4.2.4/4.2.5 | Pflichtsolo in eigener Rubrik, zählt nicht zu den 24; derselbe Geber gibt neu (nach Vorführung der nächste) | `round_rules.py` | `RoundRuleTests` | ✅ |
| 4.3.1 | Lustsolo erst nach eigenem Pflichtsolo; linker Nachbar des Gebers spielt auf | `game.py` | `test_solo_after_pflichtsolo…` | ✅ |
| 4.3.2 | Lustsolo zählt als Normalspiel, Geber wechselt | `round_rules.py` | `test_lustsolo_counts…` | ✅ |
| 4.4 | Angemeldete Hochzeit nur mit beiden ♣D und als einziger Vorbehalt | `game.py` | `test_wedding_needs_both…` | ✅ |
| 4.4.3 | Klärungsstich: erster Stich eines Nicht-Hochzeiters (Stich 1–3), sonst Karo-Solo; zählt als Normalspiel, ersetzt kein Pflichtsolo | `game.py`, `round_rules.py` | `WeddingTests` | ✅ |
| 4.4.5 | Beide ♣D, „gesund“ → Stille Hochzeit (Solo-Wertung, Normalspiel-Fristen) | `game.py`, `scoring.py` | `test_silent_wedding…` | ✅ |
| 5.1.1 | Sitz links vom Geber spielt auf (außer Pflichtsolo) | `game.py` | `ReservationTests` | ✅ |
| 5.2 | Bedienpflicht (Trumpf/Fehlfarbe), sonst freie Wahl | `tricks.py` | `FollowTests` | ✅ |
| 5.3.3 | Stichgewinner; gleiche Karten: die zuerst gelegte (auch ♥10) | `tricks.py` | `TrickWinnerTests` | ✅ |
| 5.3.5 | Letzter Stich einsehbar, frühere nicht | `game.py` (`_public`) | Simulation (`check_views`) | ✅ |
| 5.5.1 | Parteiklärung öffentlich: Solo, Hochzeit, ♣D gespielt, Fehlkarte auf Trumpf, An-/Absage | `game.py` | `test_clarification_by_…` | ✅ |
| 6.2.2 | Erstansage mit ≥ 11 von 12 Handkarten | `announcements.py`, `profile.py` | `TimingTests` | ✅ |
| 6.3.4 | Absagen mit ≥ 10/9/8/7 Karten (keine 90/60/30/schwarz) | `announcements.py` | `test_absage_deadlines…` | ✅ |
| 6.4.1 | Ansage auch außerhalb des eigenen Zuges | `game.py` | `test_clarified_in_first_trick…` | ✅ |
| 6.4.2 | Hochzeit: Ansagen erst nach Klärungsstich; Fristen −1/−2 bei Klärung in Stich 2/3 | `game.py`, `announcements.py` | `WeddingTests`, `WeddingShiftTests` | ✅ |
| 6.4.3 | Stufen überspringen nur, wenn alle übersprungenen noch zulässig; alle werden mitgewertet; Nachholen unzulässig | `announcements.py`, `scoring.py` | `test_jump_requires…`, `test_absagen_count_all_stages` | ✅ |
| 6.4.4 | Erwiderung (nur Re/Kontra) mit einer Karte weniger; verspätete Erwiderung sperrt eigene Absagen | `announcements.py` | `ReplyTests` | 🟡 A5 |
| 6.4.7 | Keine Wiederholung | `announcements.py` | `test_no_repetition` | ✅ |
| 6.3.1 | „schwarz“ = kein Stich (nicht 0 Augen; mit Neunen relevant) | `scoring.py` | `test_schwarz_by_tricks…`, `test_zero_points_but_one_trick…` | ✅ |
| 7.1.1/7.1.2 | Gewinnschwellen 121/120, bei Absage 151/181/211/alle Stiche, gegen Absage 90/60/30/1 Stich | `scoring.py` | `WinnerTests` | ✅ |
| 7.1.3 | Kein Sieger bei verfehlten Zielen: nur „gespielt“-Posten, (e)/(f), Sonderpunkte | `scoring.py` | `test_no_winner_scoring` | 🟡 A4 |
| 7.2.2 | Sieg 1; unter 90/60/30/schwarz je +1; Re/Kontra je +2; je Absagestufe +1; Absage geschlagen (120/90/60/30) +1 | `scoring.py` | `ValueTests`, Raster-Test | ✅ |
| 7.2.3 | Sonderpunkte nur im Normalspiel: gegen ♣D gewonnen, Doppelkopf (≥ 40), Fuchs gefangen, Karlchen im letzten Stich; mit Spielpunkten verrechnet | `scoring.py` | `SpecialPointsTests` | ✅ |
| 7.2.4 | Solo (auch Stille Hochzeit/Hochzeit-Solo): keine Sonderpunkte, Solist ×3, Gegner je einfach | `scoring.py` | `SoloTests`, `WeddingTests` | ✅ |
| 7.3.3 | Gerade-Ungerade-Regel | `scoring.py` | Raster-Test (Nullsumme, Parität) | ✅ |
| 8.5 | Runde = 24 Normalspiele (+ 4 Pflichtsoli) | `round_rules.py` | `FullRoundSimulation` | ✅ |
| 8.5 (Zeit) | Spielzeitbegrenzung, Streichen offener Spiele | – | – | ⏭ |
| 9 | Regelverstöße, Strafpunkte, Reklamation | – | – | ⛔ Server lässt Verstöße nicht zu; Strafpunkte nicht umgesetzt |

## 1b. Optionale Regeln (gängige Varianten / Hausregeln)

Alle Optionen sind einzeln an- und abschaltbar (`RuleOptions`, `rule_schema()` liefert Texte/Gruppen/Defaults für die Oberfläche, `settings_from_dict()` nimmt das Einstellungsobjekt entgegen). Gewählt wird **vor Rundenbeginn**; Optionen und Deck-Variante bleiben während der Runde fest (sie stehen in `RoundState` und `GameState`). Defaults = **Spiel mit Dullen, Karlchen, Fuchsjagd**. Deck + Defaults = Profil `ddv_tsr_2026` (48 Karten) bzw. `house_no_nines` (40 Karten); jede andere Kombination heißt `custom`.

| Option (Kennung) | Gruppe | Default | Wirkung | Modul | Tests |
|---|---|---|---|---|---|
| Dulle als Höchsttrumpf (`dulle`) | gängig | **an** | ♥10 höchster Trumpf; aus: ♥10 ist normale Herz-Karte (Reihenfolge A,10,K,9, kein Trumpf) | `trump.py` | `DulleTests` |
| Ohne Neunen (`sharp_doppelkopf`) | gängig | aus | Deck ohne Neunen, 10 Karten (= `DeckVariant`, keine `RuleOptions`-Option) | `options.py`, `profile.py` | `test_settings_mapping…` |
| Karlchen-Punkt (`karlchen`) | gängig | **an** | Sonderpunkt: letzten Stich mit ♣-Bube gewinnen | `scoring.py` | `SpecialPointOptionTests` |
| Füchse jagen (`fuchsjagd`) | gängig | **an** | Sonderpunkt: gegnerisches ♦-Ass fangen | `scoring.py` | `SpecialPointOptionTests` |
| Ansagepflicht nach dem ersten Stich (`mandatory_announcements`) | gängig | aus | Gewinner des 1. Stichs muss Re/Kontra ansagen, bevor er weiterspielt (nur Normalspiel) | `game.py` | `MandatoryAnnouncementTests` |
| Solist kommt raus (`solo_leads`) | gängig | aus | Solist eröffnet auch im Lustsolo (Pflichtsolo spielt nach TSR 4.2.2 ohnehin aus) | `game.py` | `SoloLeadsTests` |
| Gegnerisches Karlchen abfangen (`karlchen_caught`) | Hausregel | aus | Sonderpunkt für gegnerischen ♣-Buben im letzten Stich  | `scoring.py` | `test_karlchen_caught…` |
| Schweinchen (`schweinchen`) | Hausregel | aus | Wer beide ♦-Asse hält, kann sie per Aktion `DeclareSchweinchen` zu höchsten Trümpfen erklären | `trump.py`, `game.py` | `SchweinchenTests` |
| Bock nach Herz-Stich (`bock_heart_trick`) | Hausregel | aus | Stich aus 4 Herz-Fehlkarten → nächste 4 Spiele ×2 | `game.py`, `round_rules.py` | `BockTests` |
| Bock nach Nullspiel (`bock_zero_game`) | Hausregel | aus | Spiel endet mit 0 Punkten → nächste 4 Spiele ×2 | dto. | `BockTests` |
| Bock bei 120 zu 120 (`bock_120`) | Hausregel | aus | beide Parteien genau 120 Augen → nächste 4 Spiele ×2 | dto. | `BockTests` |
| Zweite Dulle schlägt die erste (`second_dulle_wins`) | Hausregel | aus | Beide Dullen im selben Stich: die zweite gewinnt (setzt `dulle` voraus) | `tricks.py` | `SecondDulleTests` |
| Ausnahme im letzten Stich (`second_dulle_wins_except_last`) | Hausregel | aus | Im letzten Stich gewinnt die erste Dulle (setzt `second_dulle_wins` voraus) | `game.py` | `SecondDulleTests` |

Annahmen zu den Optionen (bitte bestätigen):
- **B1 Dulle aus:** ♥10 ist eine normale Herz-Karte (Fehlkarte bzw. Teil der Trumpffarbe im Herz-Solo).
- **B2 Nullspiel:** Das Spielergebnis (Re minus Kontra, vor Verdopplung) ist 0, z. B. 120:120 mit gegenseitiger „keine 90“-Absage. Es gibt keine Partei mit 0 Augen im Sinne von „schwarz“.
- **B3 Bockrunden:** Jede Bock-Regel löst pro Spiel höchstens einmal aus; Auslöser addieren sich (2 Auslöser = 8 Bockspiele, nacheinander, Faktor stets ×2). Jedes gespielte Spiel (auch Pflichtsolo/Vorführung) verbraucht ein Bockspiel; verdoppelt werden alle Spielpunkte des Spiels. Ein Bockspiel kann selbst neue Bockrunden auslösen.
- **B4 Pflichtansage:** Nur Normalspiel (nicht Solo, Hochzeit, Stille Hochzeit); entfällt, wenn die Partei des Gewinners bereits angesagt hat (auch durch den Partner). Der Gewinner kann sonst keine Karte spielen, bis er angesagt hat.
- **B5 Schweinchen:** Nur vor der eigenen ersten Karte und nur, wo ♦-Ass Trumpf ist (Normalspiel, Hochzeit, Karo-Solo). Erklärung ist öffentlich und gilt für den Rest des Spiels; gleiche Asse: das zuerst gelegte gewinnt. Das Fuchs-Sonderpunkt-Verhalten bleibt unverändert.
- **B6 Zweite Dulle:** Wirkt nur, wo die ♥10 tatsächlich Dulle ist (Option `dulle` an und ♥10 Trumpf, also nicht im Damen-/Bubensolo).
- **B7 Karlchen fangen:** +1 je gegnerischem ♣-Buben im letzten Stich, der nicht selbst gewinnt; nur Normalspiel (Solo ohne Sonderpunkte).
- Unzulässige Kombinationen (Unteroption ohne Hauptoption) werden abgelehnt (`invalid_option_combination`).
- Die DDV-Konformität geht verloren, sobald eine Option vom Default abweicht (`profile.is_official_ddv`).

## 2. Entscheidungen und Annahmen (bitte bestätigen)

- **A1 Ohne-Neunen-Profil:** Fristen um die zwei fehlenden Karten verschoben (Erstansage ≥ 9 von 10, danach 8/7/6/5); Schwellen 121/151/181/211 unverändert. Eine Kombination DDV-Profil + ohne Neunen wird abgelehnt (`validate_combination`).
- **A2 Verteilung:** fair gemischt, keine Mindestqualität der Blätter. Ein Filter auf Mindestqualität wäre eine Hausregel und gehört nicht ins DDV-Profil.
- **A3 Mehrere Vorbehalte ohne Solo-Wunsch:** nach 4.1.6 kann keine Hochzeit zum Zuge kommen; die TSR regelt den Fall (alle verneinen) nicht. Umsetzung: Normalspiel; ein Doppel-♣D-Halter spielt dann Stille Hochzeit (analog 4.4.5).
- **A4 Wertung ohne Sieger:** 7.1.3 verweist im Wortlaut auf „7.2.2 (a) und (e, f)“. Umgesetzt: kein Grundwert, keine Ansage-/Absagepunkte, aber „unter 90/60/30/schwarz gespielt“ für die Partei, die den Gegner so gehalten hat, plus (e)/(f) und Sonderpunkte, netto verrechnet. Eine zweite Quelle (vereinfachte Kurzregeln) stützt diese Lesart. Bitte mit DDV-Schiedsrichterhilfen gegenprüfen.
- **A5 Erwiderung:** „notwendig war“ = Mindestkartenzahl der höchsten Gegenansage (nicht die tatsächlich gehaltene Kartenzahl).
- **A6 Spielhistorie:** minimal: `GameState.log` (Ereignisse), `RoundState.results` (Ergebnis je Spiel). Umfang für Meilenstein 2 festlegen.

## 3. Schnittstelle für Meilenstein 2

`new_game(...)`, `apply_action(state, Declare|Resolve|Baptize|PlayCard|Announce, expected_version=, action_id=)` (transaktional, Versionsprüfung, Idempotenz), `legal_actions(state, seat)`, `player_view` / `bot_view` / `spectator_view`, `GameState.to_dict/from_dict`, `RoundState`, `next_setup`, `record_game`.
