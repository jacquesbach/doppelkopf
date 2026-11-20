# Implementierungsnotizen

Diese Notizen beschreiben den aktuellen Stand der Anwendung und ihre Prüfung.

---

## Meilenstein 1: DDV-Regelkern (neu)

- Neues Paket `backend/app/rules/` (reines Python, ohne Flask/DB/Socket.IO), Regelmatrix in `docs/DDV_REGELMATRIX.md`.
- Enthalten: Karten/Deck-Varianten, Trumpf- und Fehlfarbenreihenfolgen aller Spielarten, Bedienpflicht, Stichgewinner,
  Vorbehaltsabfrage mit Pflicht-/Lustsolo-Rangfolge, Vorführung, Hochzeit (Klärungsstich), Stille Hochzeit,
  Ansage-/Absagefristen inkl. Erwiderung, Wertung inkl. Sonderpunkten und Solo, Spielrunde (24 Normalspiele + 4 Pflichtsoli),
  Zustandsmaschine mit Versionsprüfung und Idempotenz, Spieler-/Bot-/Zuschauersicht, JSON-Serialisierung.
- Tests: `cd backend && python -m unittest discover -s tests/rules -t .` (144 Tests, laufen ohne Flask).
- Optionale Regeln (`rules/options.py`): 12 Optionen + Deck-Variante einzeln schaltbar, Defaults = Dulle/Karlchen/Fuchsjagd.
  `rule_schema()` liefert Texte, Gruppen, Defaults und Abhängigkeiten für die Einstellungsseite; Details und Annahmen B1–B7 in der Regelmatrix (Abschnitt 1b).
- Offene Entscheidungen A1–A6: siehe Regelmatrix, Abschnitt 3.



---

## Meilenstein 2: Service-Schicht (neu)

- `backend/app/table/` (flask-frei): `TableState` (4 Sitze + Profil + `RoundState` + laufendes Spiel), `TableService`
  (Aktion prüfen → Bots laufen lassen → Spielende buchen → speichern; Versionsprüfung, Idempotenz über `actionId`, Sperre pro Raum),
  `bots.py` (regelkonforme Grundstrategie über `bot_view`), `store.py` (Schnittstelle + Memory-Store).
- `backend/app/game_api.py`: HTTP-Routen für Regeln, Start, Zug, nächstes Spiel, Sicht, Historie; abhängig nur von kleinen Schnittstellen.
- `backend/app/db_access.py`: SQL-/Socket.IO-Umsetzung (bewusst dünn). `models.py`: `Room.settings_json`, `GameSnapshot.schema_version`.
- Sicherheit: Bots waren über ein aus dem Raumcode ableitbares Token ansprechbar → jetzt zufällige, nie ausgegebene Tokens und Abweisung
  von Bots in HTTP und Socket; globales `/history` (Raumcodes) entfernt; `debug=True` nur noch per `FLASK_DEBUG=1`; Produktion verlangt `SECRET_KEY`.
- API-Beschreibung: `docs/API.md`.

**Fehlerbehebung (Bot-Schleife hing nach Aktion des Menschen):** Die Hintergrundschleife hielt eine langlebige DB-Sitzung, deren
Identity-Map veraltete Zustände lieferte; Aktionen des Menschen (anderer Request) kamen nie an. Jetzt holt `BotRunner` vor jedem Lesen
eine frische Sitzung (`refresh=db.session.remove`), Wartetakt 2 s.

**Nachbesserungen nach dem ersten Test:** Ergebnis-Dialog öffnete sich bei jedem Nachladen erneut (jetzt pro Spiel gemerkt, kein `$effect`);
„Stiche ansehen“ zeigt alle 12 Stiche (neu: `game.tricks` nach Spielende); Gewinnernamen in Ergebnis und Protokoll; nicht spielbare Karten
bleiben unverändert (nur Cursor `not-allowed`); kurze Hinweisfenster für Vorbehalt, Solo, Hochzeit, Ansagen, Schweinchen, Doppelkopf,
Fuchs gefangen, Karlchen im letzten Stich (`game.events`, 4,5 s, Klick schließt).

**Verbindungsanzeige „Offline“ (Ursache + Fix):** Socket.IO prüft den `Origin`-Header strikt gegen `CORS_ORIGINS`
(`localhost:5173/8080`). Auf einem Server mit anderer Adresse/Port scheiterte die Socket-Verbindung still – der Tisch zeigte dauerhaft
„Offline“, und Server-Pushes (Bots, Lobby) kamen nur über das Nachladen an. Jetzt: `CORS_ORIGINS: "*"` im Compose-File (Socket und API;
Sicherheit hängt am Token, nicht an Cookies), und die Anzeige gilt als online, solange Socket **oder** HTTP-Abrufe (alle 3–5 s) funktionieren.

**Lobby:** Button „Austreten“ (Host übergibt den Tisch an den nächsten Spieler; letzter Mensch schließt den Tisch).
**Öffentliche Tische:** Host kann Sichtbarkeit beim Anlegen und in der Lobby ändern; Liste auf Startseite und „Beitreten“-Seite mit Regeln,
Plätzen und Passwortschloss; Aktualisierung alle 8 s.

### Prüfstand (ehrlich)
- Lokal ausgeführt und grün: 144 Regelkern-Tests (`tests/rules`), 34 Tests Tischschicht + HTTP mit In-Memory-Speicher (`tests/service`).
  Start: `cd backend && python -m unittest discover -s tests/rules -t . && python -m unittest discover -s tests/service -t .`
- `tests/test_api_flow.py` (neu, echte App) wurde nur mit einem **Wegwerf-Ersatz** für SQLAlchemy/Flask-SocketIO ausgeführt (4 Tests grün),
  die alten Raum-Tests ebenfalls. **Mit den echten Paketen aus `requirements.txt` bitte einmal `pytest` laufen lassen** (SQLAlchemy-
  `Query.update`, Socket.IO und DB-Sperre konnten hier nicht gegen die Originale geprüft werden).
- Nicht umgesetzt: Rate-Limiting, Wiedereintritt/Sitzübernahme nach Verbindungsabbruch, Zeitlimits, Mehrprozess-Broadcast (Message-Queue).

---

## Meilenstein 3: Frontend in Svelte (neu)

**Entscheidung:** Svelte 5 + Vite 7 ist das einzige JS-Framework.
Die Oberfläche ist im Neubrutalism-Stil (Tokens und Klassen nach <https://neubrutalism.com/#implementation>).
**Keine Bilddateien:** Logo, Karten, Farbsymbole, Kartenrücken und Illustrationen sind Inline-SVG bzw. CSS; Schriften (Syne, Space Grotesk, Inter,
Space Mono) kommen lokal über `@fontsource` (keine Anfragen an Google).

### Aufbau (`src/`)
- `pages/Landing.svelte`, `pages/Lobby.svelte`: Seiten im Neubrutalism-Design mit eigenen Komponenten-Styles (Präfix `nb-`; Schriften lokal über `@fontsource`, Daten und Aktionen aus dem Backend). Inhaltliche Korrekturen auf der Startseite:
  „Mit / ohne Neuner“ (DDV-Standard hat Neuner), „zweite Dulle sticht“, „Training“ statt „Offline“, keine Aussage zu einstellbarer Bot-Stärke.
  Lobby: „TISCH #CODE“ statt der Beispielnummer, Überschrift mit Tisch-Code, echte Spieler-Slots (Host/Bot/bereit/leer + Einladungslink kopieren),
  Hausregel-Etiketten aus den Raumeinstellungen, echter Chat, Start nur für den Host wenn 4 Spieler bereit sind, Bots als Lückenfüller, „Tisch verlassen“.
- `pages/CreateTable.svelte`, `JoinTable.svelte`: Regeln aus `/rule-schema` (`components/ui/RuleForm.svelte`, Abhängigkeiten `requires` werden erzwungen),
  Sofort-Partie gegen KI (`/neu?ki=1`: Tisch anlegen → Bots → Start).
- `components/game/`: `GameTable` (Sitze relativ zu mir, Stich als Kreuz, Hand), `DecisionPanel` (gesund/Vorbehalt, Pflicht-/Lustsolo, Taufe),
  `ActionBar` (Ansagen, Schweinchen), `ResultDialog`, `InfoDialogs` (Stand, letzter Stich, Protokoll, Chat).
  **Die Oberfläche rechnet keine Regeln:** erlaubte Karten, Ansagestufen und Dialoge kommen aus `game.legalActions`.
- `components/cards/`: `PlayingCard`, `CardBack`, `SuitIcon` (Inline-SVG).
- `lib/` (reines JS, ohne Browser testbar): `api.js`, `socket.js`, `sessions.js`, `router.js`, `cards.js`, `labels.js`, `view.js`;
  `table.svelte.js` (Zustand eines Tisches), `nav.svelte.js` (History-Router), `services.js` (Instanzen).
- Echtzeit: `socket.io-client`; nach jedem Verbinden wird `room:watch` erneut gesendet. Versionsnummern verhindern, dass ältere Sichten neuere überschreiben.
  Bei `version_conflict` lädt die App die Sicht neu.
- Deployment: nginx liefert das Frontend und proxyt `/api` und `/socket.io` zum Backend (gleicher Ursprung, kein CORS).

### Backend-Ergänzungen in diesem Meilenstein
Tisch-Chat (`app/table/chat.py`, HTTP + Socket.IO), `POST /rooms/<code>/leave`, sortierte Hand in `player_view`, `baptismKind` in der Sicht.
Die alte Engine `game_engine.py` samt ihrer Tests wurde entfernt.

### Prüfstand (ehrlich)
- Lokal ausgeführt und grün: 146 Regelkern-Tests, 36 Tests Tischschicht/HTTP, 11 Frontend-Logik-Tests (`npm test`, `node --test`).
- `npm run check:svelte` (eigenes Skript, nur Syntax: JS in `<script>`, Blockbalance, Ausdrücke, Tag-Balance) war grün.
- **Nicht ausgeführt:** `npm install`, Svelte-Kompilierung, `vite build`, Playwright, Sicht im Browser. In der Entwicklungsumgebung war der Paketzugriff gesperrt.
  Bitte einmal `npm install && npm test && npm run build` laufen lassen und die Seiten im Browser ansehen; Compiler-Warnungen
  (z. B. ungenutzte CSS-Selektoren in den übernommenen Komponenten) sind zu erwarten und unkritisch.
- Ebenfalls nicht gegen die echten Pakete geprüft: `tests/test_api_flow.py`/`test_rooms.py` (SQLAlchemy, Flask-SocketIO) – bitte mit `pytest` laufen lassen.
- Impressum/Datenschutz: Texte in `src/pages/Legal.svelte`, Betreiberangaben aus `legal/legal.json` (vom Deploy aus den GitHub-Variablen `LEGAL_*` erzeugt; ohne Datei markierte Testdaten). Die Datenschutzerklärung beschreibt den Ist-Zustand des Codes (localStorage-Schlüssel, Tisch-Daten, Vorschläge, Protokolle) und muss bei neuen Funktionen mitgepflegt werden.
- SEO: `src/lib/seo.js` (Titel/Beschreibung/robots je Seite), `scripts/seo-build.mjs` (je Seite HTML, `robots.txt`, `sitemap.xml` beim Build), `/regeln` als Inhaltsseite, `deploy/nginx.conf` (404-Status, noindex, Cache, gzip, IP-gekürzte Protokolle).

---

## Meilenstein 4 (Teil 1): Spielgefühl, Bot-KI, Wiedereintritt (neu)

**Karten und Optik**
- Klassische Spielkarten als Inline-SVG (weiß, Index oben links/unten rechts, Pips für 9/10, Rahmen für K/D/B, Ass mit großem Symbol);
  Kartenrücken mit Rautenmuster. Das Neobrutalism-Design gilt für die Oberfläche, nicht für die Karten.
- Logo: Fächer aus vier Spielkarten mit den vier Kartenfarben (♣ ♠ schwarz, ♥ ♦ Korall), auch als Favicon.
- Display-Schrift: Space Grotesk 700 statt Syne 800 (schmaler, bricht das responsive Layout nicht mehr).

**Getaktete Bots** (`table/runner.py`, `TableService.paced`)
- Bots spielen einzeln im Hintergrund mit Bedenkzeit; jeder Zug wird sofort an alle gepusht. Nach einem Stich 2,4 s Pause.
- Der beendete Stich bleibt mit Gewinner auf dem Tisch (`lastTrick`), Karten fliegen aus der Richtung ihres Spielers ein.
- Im Spiel gegen Bots (genau ein Mensch) wartet der Server nach jedem Stich auf **„Nächster Stich“** (`POST /continue`).
- Tests laufen ohne Wartezeit (`paced=False` bzw. synchroner Runner).

**Verlassen / Aufgeben – Entscheidung**
- Es gibt **kein „Aufgeben“** (im Doppelkopf nicht vorgesehen, würde die Wertung der anderen verfälschen).
- **„Verlassen“ während der Runde = Bot übernimmt den Sitz** (`/away`). Der Sitz bleibt dem Spieler zugeordnet; seine Punkte zählen
  weiter für ihn, bis er zurückkehrt (jede Aktion oder `/back` holt den Platz zurück). So kann die Runde für alle regulär enden.
- Offen (bewusst noch nicht gebaut): „Runde vorzeitig beenden“ per Abstimmung; Wertung dann nur die bis dahin gebuchten Spiele.

**Wiedereintritt**
- Gleiches Gerät: Token im Browser (wie bisher). Anderes Gerät: `POST /rejoin` mit Name (+ Passwort), nur für nicht verbundene Spieler.
- Inaktivität: Siehe „Bot-Übernahme“ in Teil 2 (Host-Einstellung, Countdown). Wer zurückkommt, übernimmt den Platz automatisch zurück.
- Grenze: Wer Raumcode und Passwort kennt, kann einen *getrennten* Sitz übernehmen (für Freundesrunden gedacht).

**Bot-KI mit Gedächtnis und Durchrechnen** (`table/bots.py`, `table/pimc.py`)
- `bot_view` liefert zusätzlich die gespielten Stiche (öffentlich, jeder am Tisch hat sie gesehen). Daraus baut der Bot sein **Gedächtnis**:
  ungesehene Karten, nachgewiesene Leerfarben/Trumpf je Mitspieler, Augen je Sitz.
- **Durchrechnen** (Normalspiel): ungesehene Karten werden regelkonform (Handgrößen, Leerfarben, bekannte Kreuz-Damen) zufällig auf die
  Mitspieler verteilt; jede erlaubte Karte wird in vielen solchen Stichproben zu Ende gespielt, gewählt wird die mit den meisten
  erwarteten Augen für die eigene Partei. Ergebnisse werden je Spielstand zwischengespeichert (Bedenkzeit-Schleife ruft die KI mehrfach).
- **Ansagen** per Stichproben: Re/Kontra ab 75 % Gewinnchance, Absagen („keine 90/60/30“, schwarz) ab 85 % Erfolgschance.
  Die Schwellen sind per Selbstspiel abgestimmt (0,65/0,75/0,85 und 0,7/0,85/0,95 verglichen).
- Solo, Hochzeit und Rückfall nutzen weiter die Heuristik (jetzt mit „sicher/unsicher“ aus dem Gedächtnis).
- **Messung** (Selbstspiel, neue Bots Sitze 0/2 gegen die alte Grundstrategie auf 1/3, dieselben Verteilungen in beiden Zuordnungen):
  | Variante | Ergebnis |
  |---|---|
  | nur Gedächtnis-Heuristik, 3200 Spiele | ≈ ±0 (kein messbarer Vorteil) |
  | + Ansagen per Stichproben, 1000 Spiele | +320 : −320 Punkte (alte feste Ansageregel: −48 : +48) |
  | + Kartenwahl per Stichproben + Ansagen, DDV, 500 Spiele | +404 : −404 Punkte, Siege 523 : 476 |
  | dasselbe mit allen Hausregeln, 500 Spiele | +290 : −290 Punkte, Siege 515 : 485 |
  Ausprobiert und verworfen: Trumpf aktiv ausspielen (schadete), Sieg-Wahrscheinlichkeit statt Augen als Zielgröße (schwächer).
- **Parteizugehörigkeit:** Die Wahrscheinlichkeit steckt im Durchrechnen: Die Stichproben verteilen die ungesehenen Karten (also auch die
  Kreuz-Damen) regelkonform auf die Mitspieler, unter Berücksichtigung dessen, was sicher feststeht (Ansagen, gespielte Damen,
  nachgewiesene Leerfarben, Kontra-Beweis durch Fehlkarte auf Trumpf). Aus dem Spielverhalten wird sie zusätzlich geschätzt
  (`pimc.history_weight`, Schalter `TUNE["infer"]`): Stichproben, in denen die bisherigen Karten eines Mitspielers zur Grundstrategie
  passen, zählen mehr. Selbstspiel-Test (2 × 800 Spiele, Variante gegen Variante): +76 bzw. −60 Punkte Unterschied, also **kein messbarer
  Gewinn** bei doppelter Rechenzeit. Standardmäßig deshalb **aus**; die Bots spielen nicht nach dem einfachen Modell, deshalb sagt ihr
  Verhalten wenig über die Partei.
  Nachmessen: `cd backend && python3 -m tools.bot_tournament 250 1 ddv pimc=1 announce=pimc` (Dauer: einige Minuten).
- Rechenzeit: im Mittel ca. 50 ms je Bot-Aktion (Spitzen einige 100 ms), liegt innerhalb der Bedenkzeit von 1–1,7 s.
- Grenzen: Gegner-Modell ist einfach (alle spielen die Grundstrategie), Solo/Hochzeit ohne Durchrechnen, keine freiwilligen Soli.

**Fehlerbehebung (Bot-Schleife hing nach Aktion des Menschen):** Die Hintergrundschleife hielt eine langlebige DB-Sitzung, deren
Identity-Map veraltete Zustände lieferte; Aktionen des Menschen (anderer Request) kamen nie an. Jetzt holt `BotRunner` vor jedem Lesen
eine frische Sitzung (`refresh=db.session.remove`), Wartetakt 2 s.

**Nachbesserungen nach dem ersten Test:** Ergebnis-Dialog öffnete sich bei jedem Nachladen erneut (jetzt pro Spiel gemerkt, kein `$effect`);
„Stiche ansehen“ zeigt alle 12 Stiche (neu: `game.tricks` nach Spielende); Gewinnernamen in Ergebnis und Protokoll; nicht spielbare Karten
bleiben unverändert (nur Cursor `not-allowed`); kurze Hinweisfenster für Vorbehalt, Solo, Hochzeit, Ansagen, Schweinchen, Doppelkopf,
Fuchs gefangen, Karlchen im letzten Stich (`game.events`, 4,5 s, Klick schließt).

**Verbindungsanzeige „Offline“ (Ursache + Fix):** Socket.IO prüft den `Origin`-Header strikt gegen `CORS_ORIGINS`
(`localhost:5173/8080`). Auf einem Server mit anderer Adresse/Port scheiterte die Socket-Verbindung still – der Tisch zeigte dauerhaft
„Offline“, und Server-Pushes (Bots, Lobby) kamen nur über das Nachladen an. Jetzt: `CORS_ORIGINS: "*"` im Compose-File (Socket und API;
Sicherheit hängt am Token, nicht an Cookies), und die Anzeige gilt als online, solange Socket **oder** HTTP-Abrufe (alle 3–5 s) funktionieren.

**Lobby:** Button „Austreten“ (Host übergibt den Tisch an den nächsten Spieler; letzter Mensch schließt den Tisch).
**Öffentliche Tische:** Host kann Sichtbarkeit beim Anlegen und in der Lobby ändern; Liste auf Startseite und „Beitreten“-Seite mit Regeln,
Plätzen und Passwortschloss; Aktualisierung alle 8 s.

## Meilenstein 4 (Teil 2): Feinschliff und Bot-Übernahme (neu)

**Logo mit Flip-Animation** (`ui/Logo.svelte`): Beim Überfahren (oder Fokussieren) des Logo-Links ziehen sich die vier Karten zu einem
Stapel zusammen, der Stapel dreht sich um (Kartenrücken mit Rautenmuster) und beim Verlassen zurück und wieder auf. Reines CSS
(Transitions mit gestaffelten Verzögerungen, Drehpunkte in viewBox-Koordinaten), bei `prefers-reduced-motion` ohne Animation.

**Chat-Hinweise:** Neue Nachrichten anderer Spieler erscheinen im selben Hinweisfenster wie Ansagen („Chat · Anna“, Text auf 70 Zeichen
mit „…“ gekürzt) mit Schaltfläche **ANTWORTEN**, die den Chat mit fokussiertem Eingabefeld öffnet. Der CHAT-Button zeigt einen Zähler
ungelesener Nachrichten. Bei offenem Chat, für eigene Nachrichten und beim Nachladen des Verlaufs gibt es keinen Hinweis.

**Ergebnis nach dem letzten Stich:** Das Ergebnisfenster wird 4,5 s zurückgehalten; der letzte Stich bleibt mit Gewinnerrahmen und
„X gewinnt den letzten Stich (n Augen)“ sichtbar, „ERGEBNIS JETZT ANZEIGEN“ überspringt die Wartezeit. Nicht bei Neuladen eines
beendeten Spiels (`justFinished` erkennt nur den Übergang). **Dritter Button „NÄCHSTES SPIEL“** (bzw. „NEUE RUNDE STARTEN“ für den
Host am Rundenende) neben „Ergebnis anzeigen“ und „Stiche ansehen“, wenn das Ergebnisfenster geschlossen ist.

**Bot-Übernahme bei Inaktivität (neu gedacht)** – Entscheidung und Begründung:
- *Host-Einstellung statt Einstellung pro Spieler:* Der Tisch einigt sich auf eine Regel (z. B. „5 Minuten“ oder „nie“, wenn nebenbei geredet
  wird); der Host kann sie auch **während der Runde** ändern. Zusätzlich darf jeder Spieler **für sich** ablehnen („Entscheidung merken“ im
  Countdown-Dialog bzw. Häkchen im STAND-Fenster, bleibt über Runden erhalten). So gewinnt immer die vorsichtigere Einstellung.
- *Countdown-Dialog:* Nach der eingestellten Zeit ohne Änderung am Tisch sieht der wartende Spieler „Bist du noch da?“ mit 30-Sekunden-
  Countdown, „WEITERSPIELEN“ (+ Haken „Entscheidung merken“) und „Bot jetzt übernehmen lassen“. Die anderen sehen „Anna reagiert nicht –
  ein Bot übernimmt in n s“. Läuft er ab, spielt ein Bot den Sitz (`autoplay`, wie beim Verlassen).
- *Nie bei einem einzigen Menschen:* Spielt ein Mensch allein gegen Bots (oder sind alle anderen Menschen weg), wartet der Tisch beliebig
  lange; die Überwachungsschleife endet sofort (keine Wartetakte, keine DB-Last).
- *Auswahl:* nie · 1 · 2 · 3 (Standard) · 5 · 10 · 30 Minuten (`TAKEOVER_CHOICES`), Lobby und STAND-Fenster.
- *Technik:* Die Inaktivitätsuhr steht im Spielstand (`table.touched`, von `TableService._save` bei jeder Änderung gesetzt; `table.warning` =
  `{seat, until}`), nicht im Speicher der Hintergrundschleife – sie übersteht Neustarts und das Ende der Schleife. `TableService.watch_tick`
  entscheidet (Countdown starten / Bot einsetzen), der `BotRunner` ruft es im Wartetakt auf. Die frühere „45 s getrennt“-Regel entfällt: Sie
  konnte Spieler mit schlafendem Browser-Tab ungewollt ersetzen. Ein getrennter Spieler wird jetzt nach Einstellung + 30 s ersetzt.
- *Tische schließen:* `housekeeping.py` löscht Räume (samt Spielstand, Protokoll, Chat), an denen 12 Stunden lang nichts passiert ist
  (angelegt/beigetreten/letzte Spielzustandsänderung), alle 10 Minuten; **keine** Bot-Übernahme. Der Zeitraum ist `TABLE_MAX_IDLE_HOURS`.

### Prüfstand (ehrlich)
- Grün: 146 Regelkern-, 81 Service-Tests (inkl. 19 neue zur Bot-Übernahme mit künstlicher Uhr, 3 neue HTTP-Tests), 21 Frontend-Logik-Tests.
- Logo-Animation: in echtem Chrome (statisch gerendertes HTML/CSS) als Bildfolge geprüft: Fächer → Stapel → Umdrehen → Rücken → zurück.
- **Nicht** ausgeführt: `npm install`, Svelte-Compiler/Build und Browser-Sicht der übrigen Änderungen (Chat-Hinweis, Ergebnis-Verzögerung,
  Countdown-Dialog), echter Socket.IO-/SQLAlchemy-Betrieb. Bitte `pytest` mit den echten Paketen laufen lassen (neu: `tests/test_rooms.py`,
  Spalte `takeover_seconds`, `housekeeping.close_idle_rooms`) und einen Spielabend zu viert testen.

### Nächste Schritte
1. Browser-Test, Feinschliff (Karten-Größen mobil, Tastatur), ggf. Tempo-Einstellung (schnell/normal/langsam) pro Tisch.
2. Abstimmung „Runde beenden“, freiwillige Soli für Bots, besseres Gegner-Modell.

## Meilenstein 4 (Teil 3): Vorschläge und Betreiber-Backend (neu)
- **Vorschläge:** Link-Karte unter „Diese Tische suchen Mitspieler“ (`pages/Landing.svelte`) öffnet `components/community/SuggestionsModal.svelte`:
  Liste (beliebteste zuerst), Formular (Titel 4–80, Beschreibung 10–500 Zeichen, keine Links), Captcha, Daumen (einer je Browser, zweiter Klick nimmt ihn zurück).
- **Captcha:** selbst gebaut, ohne Fremddienst und ohne Bilddatei: Server erzeugt eine verzerrte Vektorgrafik; das Token (`nonce.exp.antwort-mac.sig`, HMAC mit `SECRET_KEY`)
  enthält die Antwort nur als Hash, gilt 10 Minuten und genau einmal. Dazu Honigtopf-Feld, Begrenzungen je Adresse/Browser und Textprüfung vor dem Captcha.
  **Ehrlich:** das hält Massen-Spam und einfache Skripte ab, aber keine gezielten Angreifer mit Texterkennung; für diesen Fall bleibt die Moderation (Ausblenden/Löschen).
- **Daumen-Grenze:** „ein Daumen je Nutzer“ gilt je Browser (zufällige Kennung im `localStorage`, serverseitig nur als Hash). Wer Browserdaten löscht, kann erneut abstimmen –
  ohne Konten ist das nicht zu verhindern.
- **Betreiber-Backend** (`/admin`, Passwort `ADMIN_PASSWORD`, sonst abgeschaltet; Token 8 Std. im `sessionStorage`; 5 Fehlversuche je 10 Min.):
  Tische (Menschen, aktiv/inaktiv, seit wann), Statistik (Tische gesamt und 24 Std./7/30 Tage; nur gegen Bots vs. mit Menschen; je 1–4 Menschen;
  Dauer in Minuten und Spiele je Tisch als Ø/Median/Max und Verteilung; neue Tische je Tag), Sprüche (hinzufügen, bearbeiten, löschen, Reihenfolge), Vorschläge (ausblenden, bearbeiten, löschen).
- **Statistik-Quelle:** Tabelle `table_log` (je angelegtem Tisch), unabhängig von der 12-Stunden-Abräumung. Statistikfehler werden protokolliert und stören das Spiel nie.
  „Nur gegen Bots“ = genau ein Mensch beim Rundenstart; „Spielzeit“ = erster Start bis letzte Aktion.
- **Chat-Sprüche** kommen jetzt vom Server (`GET /api/phrases`); die acht mitgelieferten werden einmalig eingetragen, bei Ausfall gilt die eingebaute Liste.
- Aufbau: flask-freie Logik in `backend/app/community/*` (Captcha, Texte, Vorschläge, Sprüche, Statistik, Tischübersicht, Anmeldung, Begrenzung), SQL nur in `community/sql.py`, HTTP in `community/api.py`.

### Prüfstand (ehrlich)
- Grün: 118 Service-Tests (36 neu: Captcha, Begrenzung, Texte, Vorschläge/Daumen, Sprüche, Anmeldung, Statistik, Tischübersicht und alle HTTP-Routen mit Speicher-Stores), 30 Frontend-Logik-Tests (9 neu), Svelte-Syntaxcheck (um `{@html}` erweitert).
  Die Captcha-Grafik wurde in echtem Chrome gerendert und ist lesbar.
- **Nicht** ausgeführt: SQL-Schicht und Verdrahtung in `create_app` (SQLAlchemy/flask-cors fehlen hier) – dafür liegt `backend/tests/test_community.py` bereit, bitte mit `pytest` laufen lassen;
  Svelte-Build und Browser-Sicht von Modal und Admin-Seite.

## Design-Anpassungen für DOPPELKOPF.CC (neu)
- Name: Der Kurztitel neben dem Logo lautet überall „DOPPELKOPF.CC“ ohne gelben Kasten (Startseite, Formularseiten, Lobby, Spieltisch), ebenso `<title>`, Web-App-Manifest und die Fußzeilen.
  Auf schmalen Telefonen (≤ 480 px) schrumpfen Name und Logo stufenlos, ab ≤ 380 px darf der Kopf notfalls zweizeilig umbrechen; bei 320–1000 px per Chrome-Messung (Ersatzschrift) weder Überlauf noch Überlappung.
- Startseite: Der gelbe Hervorhebungskasten sitzt jetzt am Wort „DOPPELKOPF.“; „OHNE SCHNICKSCHNACK.“ steht ohne Kasten darunter (auf kleinen Displays kleinere Schrift, damit der Kasten nicht über den Rand ragt).
- Kartenillustration: Die drei Beschriftungen („Die Alte“, „Höchster Trumpf“, „Re // Kontra“) sind entfernt; die Symbole sitzen mittig in der Karte. Nicht mehr benötigte CSS-Regeln wurden gelöscht.
- Nicht geprüft: Darstellung mit der echten Schrift „Space Grotesk“ und im Svelte-Build (kein Compiler hier).

## GitHub-Tauglichkeit und Deployment (neu)
- `.gitignore` neu (Geheimnisse, Datenbanken, Build-/Cache-Ordner, Archive); in einer Testkopie mit echtem `git add -A` geprüft: `.env`, `*.sqlite3`, Schlüssel, `node_modules`, `dist`, `*.zip` bleiben draußen.
- **Eine Konfigurationsstelle:** `.env` (Vorlage `.env.example`; `backend/.env.example` entfällt). Ports `FRONTEND_PORT=8080`, `BACKEND_PORT=8181` gelten für Compose, nginx (Vorlage `deploy/nginx.conf`
  mit `${BACKEND_PORT}`), Backend-Healthcheck, `run.py` und den Vite-Entwicklungsproxy. Der Backend-Port ist standardmäßig nur auf `127.0.0.1` offen (`BACKEND_BIND`).
- `docker-compose.yml` verlangt `SECRET_KEY` (bricht sonst mit Hinweis ab), setzt `APP_ENV=production`, Neustart-Richtlinie, Healthchecks (`/api/health`) und wartet mit `depends_on`.
- `.github/workflows/deploy.yml`: Tests (wiederverwendet aus `build-and-test.yml`) → Eingabeprüfung → SSH (Fingerabdruck fest vorgegeben) → `rsync` → `.env` aus Secrets/Variablen (Rechte 600) →
  `docker compose up -d --build --wait` → Gesundheitstest. `build-and-test.yml` prüft zusätzlich `docker compose config` und baut beide Images. Anleitung: `docs/DEPLOYMENT.md`.
- **Geprüft:** YAML-Syntax aller drei Dateien, `docker compose config` mit/ohne Variablen und Sonderzeichen in Werten, die Eingabeprüfung des Deploys mit gültigen und ungültigen Werten, die `.gitignore`.
- **Nicht geprüft:** der Workflow auf GitHub selbst, SSH/rsync gegen einen echten Server, Bau der Docker-Images und das Start-Verhalten der nginx-Vorlage (kein Docker-Daemon bzw. Netz hier).
  Ein erster Deploy per „Run workflow“ zeigt Fehler im Protokoll; Hinweise in `docs/DEPLOYMENT.md` („Fehlersuche“).

## Mobile Tischansicht

- **Karten:** `PlayingCard.svelte` zeigt Karten unter ca. 70 px Breite (per Container-Query, also vor allem am Handy) mit großem Eck-Index und einem großen Symbol statt vieler kleiner Punkte. Breitere Karten bleiben unverändert.
- **Hand:** Am Handy passen 12 Karten mit gut der Hälfte Überlappung genau in die Bildschirmbreite (`--card-w` in `GameTable.svelte`).
- **Zwei Tipps zum Spielen (nur Touch-Geräte):** `Hand.svelte` erkennt per `(hover: none) and (pointer: coarse)`, ob es ein Touch-Gerät ist. Erster Tipp wählt die Karte aus (sie ragt heraus), ein zweiter Tipp auf dieselbe Karte spielt sie. Tipp daneben oder Ende des Zugs hebt die Auswahl auf. Mit Maus genügt ein Klick. Die Logik steht als reine Funktionen in `src/lib/selection.js` (Tests: `tests/selection.test.js`).
- **Aufbau:** Schlanker Kopf (Spielart, CHAT, MENÜ mit den übrigen Knöpfen), Mitspieler mit kleinem Kartenfächer, Stichfläche als Kasten, eigene Leiste, einklappbare Ansagen (`ActionBar.svelte`), Hand unten.
- **Kartenrücken:** Neubrutalism-Design (Gelb mit Korallen-Streifen, schwarze Konturen, Raute), identisch auf Handy und Desktop. `CardBack.svelte` vergibt je Instanz eine eigene Muster-ID; eine gemeinsame ID wäre ins Leere gelaufen, sobald die erste Instanz in einem ausgeblendeten Bereich steht.

---

## Hausregel „Armut“ (neu)

Zuschaltbar als Option `poverty` (Gruppe „Hausregeln“, Standard aus). Ablauf: **Vorbehalt → Armut anmelden → 3 Karten verdeckt abgeben → reihum Käufer
fragen → Käufer gibt 3 beliebige Karten zurück → Normalspiel** (`GameKind.POVERTY`) mit **Armem + Käufer automatisch als Re** gegen die anderen beiden.
Übernimmt niemand die Armut, wird **neu gegeben** (gleicher Geber, das Spiel zählt nicht).

- **Regelkern** (`backend/app/rules/game.py`): neue Phasen `poverty_pass`, `poverty_offer`, `poverty_return`; Aktionen `PovertyPass`, `PovertyOffer`, `PovertyReturn`;
  Phase `redeal` (der Regelkern mischt nie; `table/state.py: redeal_if_needed` gibt neu und wird nach jeder Aktion im `TableService` aufgerufen),
  Zustand `poverty_seat/_cards/_queue/_buyer/_received`, `redeal_seat` (alte gespeicherte Spiele ohne diese Felder laden weiter). Anmelden über `baptize "poverty"` (einziger
  Vorbehalt) oder die Stufe `poverty` der Vorbehaltsklärung (mehrere Vorbehalte; nach Pflicht- und Lustsolo). Entscheidungen und Annahmen: `docs/DDV_REGELMATRIX.md` B8.
- **Datenschutz:** Die abgegebenen Karten stehen weder im Protokoll noch in öffentlichen Sichten; nur der Arme sieht sie (`povertyPassed`), nur der Käufer sieht, welche
  Karten neu sind (`received`). Das Ergebnis des Tauschs bleibt verdeckt.
- **Bots** (`backend/app/table/bots.py`): melden Armut an (höchstens 3 Trümpfe, nicht bei Hochzeitsblatt), geben alle Trümpfe ab (aufgefüllt mit den wertlosesten
  Fehlkarten), übernehmen ab 6 Trümpfen (ab 5 mit Kreuz-Dame) und geben die schwächsten Fehlkarten zurück. In einer Armut kennen sie die Parteien
  (Armer + Käufer = Re); die Stichproben-KI (`pimc`) rechnet mit Kreuz-Damen-Parteien und bleibt dort aus (Heuristik).
- **Oberfläche:** Dialog „Armut anmelden/übernehmen“, Karten in der Hand markieren (`PovertyPanel.svelte`, Hand-Modus `pick`, Markierung „NEU“), Hinweise
  (`events.js`), Marken „Armut“/„Übernahme“ am Sitz.
- **Tests:** `backend/tests/rules/test_poverty.py` (30), `backend/tests/service/test_poverty_bots.py`, `test_poverty_redeal.py`, erweiterte Lauf-/Parser-Tests; `tests/lib.test.js`, `tests/selection.test.js`.
- **Nicht geprüft:** `vite build` und das Rendern der Svelte-Komponenten im Browser (nur der Syntaxcheck `npm run check:svelte` lief); bitte einmal am Handy und am Desktop ausprobieren.

**Armut-Oberfläche:** Gewählte Karten verlassen die Hand und fliegen ins Armuts-Fenster (`PovertyPanel`, Svelte `crossfade` in
`src/lib/fly.js`); ein ✕ an der Karte nimmt sie zurück auf die Hand. Der Käufer sieht dort die übernommenen Karten klein. Nach der
Rückgabe öffnet sich beim Armen einmal je Spiel `PovertyGotDialog` mit den neuen Karten (Server: `game.povertyGot`, nur für den Armen).
Das „NEU“-Siegel gilt nur noch beim Käufer, solange er zurückgibt.

## Test-Tisch (Betreiber-Bereich, Tab „TEST-TISCH“) (neu)

Zweck: Situationen prüfen, auf die man im echten Spiel lange warten müsste (Armut, Hochzeit, Schweinchen, Endspiel,
Ergebnis-Dialog, Pflichtsolo, Bockrunde …) – und das auch für künftige Änderungen an Regeln und Design.

- **Gleicher Code wie der echte Tisch:** Ein Test-Tisch ist ein gewöhnlicher Raum (`Room.lab_spec_json` ≠ NULL markiert ihn) mit
  gewöhnlichem `TableState`, `TableService`, Bots, `BotRunner`, Socket.IO-Sichten und derselben Oberfläche. Es gibt keinen
  Sonderweg im Spiel; nur der Aufbau ist anders (`app/lab/scenario.py::build_lab_table`): Die Kartenreihenfolge wird so gebaut
  (`rigged_order`), dass jeder Platz die gewünschten Karten bekommt; der Rest wird zufällig verteilt.
- **Szenario = reine Daten:** Regeln (alle Hausregeln, Blatt mit/ohne Neunen), Geber, Karten je Platz, Besetzung (Bot oder selbst
  gespielt), Rundenstand (gespielte Normalspiele, Bockspiele, Pflichtsolo-Status, Punkte) und „Vorspielen“ (die Bots spielen für alle
  Plätze bis zum Spielbeginn bzw. bis zu N Stichen, z. B. für Endspiel oder Ergebnis-Dialog). Fertige Vorlagen: `app/lab/presets.py`.
- **Plätze wechseln:** Jeder selbst gespielte Platz hat ein eigenes Sitzungs-Token (nur der Betreiber bekommt sie). Die Leiste „TEST“
  (`LabBar.svelte`, unten links am Tisch) tauscht das Token und lädt neu – so lässt sich Armut als Armer *und* als Käufer testen.
  „Szenario neu starten“ baut denselben Tisch erneut auf (gleiche Karten, gleiche Besetzung).
- **Abgrenzung:** nie öffentlich, nie in der Statistik (kein `TableLog`), keine Bot-Übernahme (`takeover = 0`), im Betreiber-Überblick mit
  „Test“ markiert; der Hausmeister räumt sie nach 12 Stunden Leerlauf ab, oder man löscht sie im Tab.
- **Sicherheit:** alle Routen unter `/api/admin/lab/...` verlangen das Betreiber-Token (wie die übrigen `/admin`-Routen).
- **Tests:** `backend/tests/service/test_lab.py` (Prüfung, Kartenbau, Vorlagen, Armut aus beiden Sichten, Neugabe, HTTP-Schicht),
  `tests/lab.test.js` (Editor-Logik).
- **Neue Spalte:** `room.lab_spec_json` (wird beim Start automatisch ergänzt, `_ensure_columns`).

## Tischlayout (Stich, Sitze)
Stich als überlappendes Kreuz (z-index = Spielreihenfolge, links/rechts quer, harter Schatten). Vier Plätze an den vier Seiten: Gegner-Stapel am Rand (Handy: etwa zur Hälfte angeschnitten, Desktop: voll sichtbar), Beschriftung ohne Kasten (links/rechts gekippt), eigene Hand als Fächer. Status steht über dem Stich.
Handy: Hand beginnt am unteren Bildschirmrand (Karten 5:8 gestreckt, unten angeschnitten); NEU-Etikett hängt an der Karte im gekippten Rahmen; Tischmitte ohne Rahmen/Schatten; kein gelber Rahmen am Stichgewinner.
