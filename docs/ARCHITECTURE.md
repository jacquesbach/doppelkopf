# Architektur

Ein Überblick, wie die Anwendung aufgebaut ist und warum. Zum Einstieg in den Code, zum Verständnis von Entscheidungen und als Landkarte für Änderungen.
Die Schnittstellen im Einzelnen: [API.md](API.md). Die umgesetzten Regeln: [DDV_REGELMATRIX.md](DDV_REGELMATRIX.md).

## Das Wichtigste in fünf Sätzen

1. Der **Server entscheidet alles**. Der Browser schickt Absichten („spiele diese Karte“), der Server prüft sie gegen den Regelkern und schickt jedem Teilnehmer nur seine eigene **Sicht** zurück.
2. Der **Regelkern** ist reines Python ohne Flask, Datenbank oder Netzwerk. Alles andere hängt an ihm, nicht umgekehrt.
3. Eine **Tischschicht** verwaltet pro Tisch Zustand, Versionen, Bots und Zeitabläufe. Sie spricht nur mit schmalen Schnittstellen (Speicher, Veröffentlichung), kennt also kein SQL und kein Socket.IO.
4. **SQLite** hält Tische und Spielstände, **Socket.IO** verteilt Änderungen, **flüchtige Dinge** (Chat, Online-Status, Zähler der Begrenzungen) liegen nur im Arbeitsspeicher.
5. Das Backend ist **ein einziger Prozess**. Das macht vieles einfach (Sperren, Bot-Schleifen) und ist die wichtigste Grenze beim Skalieren.

## Gesamtbild

```
 Browser (Svelte 5)                       nginx (frontend-Container)              Flask (backend-Container)
 ┌────────────────────┐   HTTP /api        ┌─────────────────────┐   HTTP        ┌─────────────────────────────┐
 │ Seiten, Komponenten│ ─────────────────▶ │ statische Dateien   │ ────────────▶ │ routes / game_api /         │
 │ lib/: API, Socket, │   WebSocket        │ Proxy /api          │   WebSocket   │ community / ops / lab       │
 │ Zustand eines      │ ◀════════════════▶ │ Proxy /socket.io    │ ◀═══════════▶ │      │                      │
 │ Tisches (Store)    │   /socket.io       │ CSP, Cache, gzip    │               │      ▼                      │
 └────────────────────┘                    └─────────────────────┘               │ table/  (Tischschicht)      │
                                                                                 │  Service · Bots · Runner    │
                                                                                 │      │                      │
                                                                                 │      ▼                      │
                                                                                 │ rules/  (Regelkern, rein)   │
                                                                                 │      │                      │
                                                                                 │      ▼                      │
                                                                                 │ SQLite (Volume /data)       │
                                                                                 └─────────────────────────────┘
```

Im Browser spricht die App nur mit demselben Ursprung (`/api`, `/socket.io`). Dadurch braucht der Betrieb kein CORS für die eigene Seite und keine Cookies.

## Backend (`backend/app/`)

| Paket / Datei | Aufgabe |
|---|---|
| `rules/` | **Regelkern.** Karten, Trumpfordnungen, Bedienpflicht, Stichwertung, Vorbehaltsabfrage (Pflicht-/Lustsolo, Hochzeit, Armut), Ansagen und Absagen, Wertung mit Sonderpunkten, Spielrunde (24 Normalspiele + 4 Pflichtsoli), Bockrunden, zuschaltbare Regeln (`options.py`), Sichten je Sitz. Zustandsmaschine `apply_action(state, action)`. |
| `table/` | **Tischschicht.** `state.py`: `TableState` (4 Sitze, Regelprofil, Runde, laufendes Spiel, Bot-Übernahme-Uhr). `service.py`: `TableService` (Aktion prüfen, Bots rechnen, Spielende buchen, speichern). `bots.py`, `pimc.py`: Bots. `runner.py`: getaktete Bot-Schleife. `chat.py`: flüchtiger Chat. `store.py`: Schnittstelle des Speichers. |
| `routes.py`, `services.py` | Räume: anlegen, beitreten, bereit, Bots, verlassen, Platz-Code, Wiedereinstieg, öffentliche Liste. |
| `game_api.py` | Spielrouten: Regeln, Start, Aktion, Sicht, Protokoll, Chat, Bot-Übernahme. |
| `community/` | Vorschläge, Daumen, Captcha, Chat-Sprüche, Statistik je Tisch, Betreiber-Anmeldung, Begrenzungen (`ratelimit.py`). SQL nur in `sql.py`, HTTP in `api.py`. |
| `ops/` | Betreiber: Seiteneinstellungen und Banner, Live-Übersicht und Eingriffe, Auswertungen, Fehler-Log, Systemstatus. |
| `lab/` | Test-Tisch: Szenarien, Vorlagen, Aufbau eines präparierten Tisches. |
| `guard.py` | Zugangsschutz im Arbeitsspeicher: neue Tische, Fehlversuche, Raten unbekannter Codes. |
| `seatcode.py` | Platz-Codes (HMAC, nicht gespeichert). |
| `presence.py` | Freiwilliger Online-Status, nur im Arbeitsspeicher. |
| `housekeeping.py` | „Hausmeister“: räumt alle 10 Minuten verwaiste Tische, alte Fehler und alte Zähler auf. |
| `db_access.py`, `models.py` | Anbindung an SQLAlchemy und Socket.IO (bewusst dünn), Tabellen. |
| `__init__.py` | `create_app`: verdrahtet alles, Socket.IO-Ereignisse, Fehlerbehandlung. |

### Der Regelkern

- **Rein und deterministisch.** Der Kern mischt nie selbst: Er bekommt die Kartenreihenfolge von außen; gemischt wird in `dealing.py` mit `secrets.SystemRandom`, in Tests mit festem Zufallsgenerator. Das macht Spiele reproduzierbar und Tests einfach.
- **Eine Zustandsmaschine.** `Phase` (Vorbehaltsabfrage, Taufe, Armut, Spiel, beendet, Neugabe …) und `Action`-Typen (`Declare`, `Resolve`, `Baptize`, `PlayCard`, `Announce`, `DeclareSchweinchen`, `PovertyPass/Offer/Return`). `legal_actions(state, seat)` sagt, was ein Sitz jetzt darf; die Oberfläche richtet sich ausschließlich danach.
- **Versionen und Idempotenz.** Jede Aktion kann mit `expected_version` und `action_id` kommen. Eine veraltete Version wird abgelehnt, eine doppelt gesendete Aktion wird ohne Wirkung bestätigt (wichtig bei wackeligem Netz).
- **Sichten statt Zustand.** `player_view` zeigt nur die eigene Hand und öffentlich Bekanntes. `spectator_view` zeigt nie Hände, `bot_view` liefert Bots das, was auch ein Mensch am Platz wüsste (inklusive der öffentlichen Stiche). Verdeckte Parteien (Stille Hochzeit) und verdeckt abgegebene Armutskarten bleiben verdeckt.
- **Optionen.** Zuschaltbare Regeln stehen in `options.py` mit Text, Gruppe, Standard und Abhängigkeiten. `rule_schema()` liefert daraus das Formular der Oberfläche; es gibt keine zweite Liste im Frontend.

### Die Tischschicht

- **`TableService`** führt jede Aktion in festen Schritten aus: Sperre je Tisch → Version prüfen → Regelkern → Bots rechnen (im ungetakteten Modus sofort) → fertige Spiele buchen und Neugabe erledigen → speichern mit **optimistischer Versionssperre**.
- **Getaktete Bots.** Im Betrieb (`paced=True`) spielt der **`BotRunner`** pro Tisch höchstens eine Schleife: warten (Bedenkzeit), genau einen Zug spielen, an alle veröffentlichen, wiederholen. Wartet der Tisch auf Menschen, beobachtet die Schleife deren Untätigkeit (Bot-Übernahme). Die Schleife endet sofort, wenn niemand eingreifen muss, ein Tisch darf also beliebig lange stehen.
- **Bot-Übernahme.** Die Inaktivitätsuhr steht **im Spielstand** (`table.touched`, `table.warning`), nicht im Speicher der Schleife; sie übersteht Neustarts. Die Host-Einstellung (nie, 1, 2, 3, 5, 10 oder 30 Minuten) gilt für den Tisch, jeder Spieler kann für sich ablehnen („Entscheidung merken“). Bei nur einem Menschen am Tisch gibt es keine Übernahme.
- **Verlassen heißt Bot übernimmt.** Es gibt kein „Aufgeben“. Der Sitz bleibt dem Spieler zugeordnet, seine Punkte zählen weiter, jede Aktion holt den Platz zurück.
- **Sperren.** Pro Tisch gibt es eine Sperre im Prozess; zusätzlich schützt die Versionsprüfung beim Speichern vor verlorenen Aktualisierungen.
- **Neugabe.** Übernimmt bei Armut niemand die Karten, gibt die Tischschicht neu (`redeal_if_needed`). Der Regelkern bleibt dabei ohne Zufall.

### Die Bots

- **Grundstrategie** (`bots.py`): regelkonforme Heuristik über `bot_view`, mit **Gedächtnis**: ungesehene Karten, nachgewiesene Leerfarben und Trumpf je Mitspieler, Augen je Sitz.
- **Durchrechnen** (`pimc.py`, Normalspiele): Die ungesehenen Karten werden regelkonform zufällig auf die Mitspieler verteilt (Handgrößen, Leerfarben, bekannte Kreuz-Damen), und jede erlaubte Karte wird in vielen solchen Stichproben zu Ende gespielt. Gewählt wird die Karte mit den meisten erwarteten Augen für die eigene Partei. Ergebnisse werden je Spielstand zwischengespeichert.
- **Ansagen** per Stichproben: Re/Kontra ab 75 % Gewinnchance, Absagen ab 85 % Erfolgschance. Die Schwellen wurden im Selbstspiel abgestimmt.
- **Armut, Solo, Hochzeit** nutzen die Heuristik (Armut: Anmelden mit höchstens 3 Trümpfen, Übernehmen ab 6 Trümpfen bzw. ab 5 mit Kreuz-Dame).
- **Messung.** Im Selbstspiel schlagen die Bots die frühere gedächtnislose Strategie deutlich (je 500 Spiele mit DDV-Regeln: Punkte +404 : −404, Siege 523 : 476). Ein Schätzer der Parteizugehörigkeit aus dem Spielverhalten brachte keinen messbaren Gewinn bei doppelter Rechenzeit und ist abgeschaltet (`TUNE["infer"]`). Reproduzieren: `python3 -m tools.bot_tournament` (siehe [DEVELOPMENT.md](DEVELOPMENT.md#bots-messen)).
- **Rechenzeit** im Mittel rund 50 ms je Aktion, deutlich unter der Bedenkzeit.
- **Bekannte Grenzen:** einfaches Gegnermodell (alle spielen die Grundstrategie), kein Durchrechnen bei Solo und Hochzeit, keine freiwilligen Soli.
- **Takt am Tisch:** Bedenkzeit 1,0 bis 1,7 s, Vorbehaltsantwort 1,7 s, 3,0 s nach der letzten Antwort bis zur ersten Karte, 2,4 s Pause nach einem Stich. Im Spiel mit **genau einem Menschen** wartet der Server nach jedem Stich auf „Nächster Stich“ (`POST /continue`).

### Datenhaltung

| Tabelle | Inhalt | Lebensdauer |
|---|---|---|
| `room`, `member` | Tisch (Code, Passwort-Hash, Regeln, Host) und Mitglieder (Name, Rolle, Token-Hash) | bis zur Aufräumung (12 h ohne Aktivität) |
| `game_snapshot` | kompletter Spielzustand eines Tisches als JSON, mit Versionsnummer | mit dem Tisch |
| `game_history` | Ergebnis je Spiel (Protokoll) | mit dem Tisch |
| `table_log`, `game_event` | anonyme Statistik (ohne Namen) | `table_log` unbegrenzt, `game_event` 400 Tage |
| `suggestion`, `suggestion_vote` | Verbesserungsvorschläge und Daumen (Browser-Kennung als Hash) | bis zur Moderation |
| `phrase`, `setting` | Chat-Sprüche, Seiteneinstellungen | dauerhaft |
| `error_entry` | Fehler-Log | 30 Tage, höchstens 300 Einträge |

Einzelheiten und Datenschutz: [PRIVACY.md](PRIVACY.md). Neue Spalten werden beim Start ergänzt (`_ensure_columns`), es gibt kein Migrationswerkzeug.

### Echtzeit

- Nach jeder Änderung veröffentlicht der **Publisher** an jedes Mitglied seine **eigene** Sicht (`game:state`) in dessen Socket-Raum; Raumänderungen kommen als `room:state`, Chat als `chat:message`.
- Ein Client abonniert einen Tisch mit `room:watch` (Code + Token). Nach jedem Wiederverbinden sendet er es erneut.
- **Versionen** verhindern, dass ältere Sichten neuere überschreiben. Bei `version_conflict` lädt die App die Sicht neu.
- **Zusätzlich zu Socket.IO** fragt die App den Tisch alle 3 Sekunden per HTTP ab (und prüft alle 5 Sekunden die Verbindung). Der Tisch gilt als online, solange Socket **oder** HTTP funktioniert. So bleiben Spiele auch hinter Netzen spielbar, die WebSockets stören.
- **Socket.IO prüft den Origin-Header strikt.** Deshalb steht `CORS_ORIGINS` im Betrieb auf `*`. Die Sicherheit hängt an den Tokens, nicht an Cookies oder am Origin.

### Zugang und Sicherheit

| Baustein | Funktionsweise |
|---|---|
| Sitzungs-Token | zufällig, im Browser (`localStorage`); in der Datenbank nur der SHA-256-Hash. Bots haben Tokens, die nie ausgegeben werden. |
| Tisch-Passwort | optional, mindestens 6 Zeichen, mit Werkzeug gehasht |
| Platz-Code | Wiedereinstieg auf einem anderen Gerät: HMAC aus `SECRET_KEY`, Tisch-Code und Sitzdaten, 40 Bit, **nicht gespeichert** |
| Zugangsschutz (`guard.py`) | neue Tische je Adresse und Stunde, Fehlversuche je Adresse und Tisch, Raten unbekannter Tisch-Codes. Nur im Arbeitsspeicher. |
| Betreiber-Anmeldung | Passwort aus `ADMIN_PASSWORD`; Token zufällig, nur Hash und Ablauf im Arbeitsspeicher (2 h, höchstens 20 Sitzungen); Neustart beendet alle |
| Captcha | selbst gebaut: Server erzeugt eine verzerrte Vektorgrafik, das Token (HMAC) enthält die Antwort nur als Hash, gilt 10 Minuten und genau einmal |
| CSP und Header | in `deploy/nginx.conf`: nur eigene Skripte, Schriften, Bilder und Verbindungen |
| Lecktests | `tests/service/test_view_leaks.py` prüft nach jeder Aktion ganzer Spiele, dass keine Sicht fremde Hände enthält |

Mehr: [../SECURITY.md](../SECURITY.md).

## Frontend (`src/`)

| Ordner | Inhalt |
|---|---|
| `pages/` | Seiten: Start, Tisch anlegen, Beitreten, Lobby, Tisch, Regeln, Admin, Impressum/Datenschutz, 404 |
| `components/game/` | Spieltisch: `GameTable`, `Hand`, `DecisionPanel` (Vorbehalt, Solo, Taufe), `ActionBar` (Ansagen), `ResultDialog`, `PovertyPanel`, `TakeoverDialog`, `InfoDialogs` … |
| `components/cards/` | Karten, Kartenrücken und Farbsymbole als Inline-SVG |
| `components/ui/`, `community/`, `admin/` | Dialog, Seitenrahmen, Regelformular, öffentliche Tische; Vorschläge, Online-Status; Reiter des Betreiber-Backends |
| `lib/` | Logik ohne Oberfläche: `api.js`, `socket.js`, `router.js`, `sessions.js`, `table.svelte.js` (Zustand eines Tisches), `view.js`, `events.js`, `selection.js`, `friends.js`, `seo.js` … |
| `content/` | Texte der Start- und Regelseite |
| `styles/` | Design-Grundlage (Neubrutalism) |

- **Svelte 5 + Vite.** Es gibt keinen zweiten Router oder Zustandsverwalter: `nav.svelte.js` ist ein kleiner History-Router, `table.svelte.js` hält den Zustand eines Tisches (Version, Sicht, Verbindungsstatus).
- **Die Oberfläche rechnet keine Regeln.** Spielbare Karten, Ansagestufen und Dialoge folgen aus `game.legalActions`. Bei Regeländerungen im Kern ändert sich die Oberfläche meist nicht.
- **Keine Bilddateien im Spiel.** Logo, Karten, Symbole und Illustrationen sind SVG/CSS. Schriften kommen lokal über `@fontsource` (keine Anfragen an Google).
- **Touch:** Auf Geräten ohne Maus wählt der erste Tipp eine Karte aus, der zweite spielt sie (`selection.js`).
- **Dark Mode** gilt nur am Tisch und wird im Browser gemerkt.
- **SEO beim Build:** `scripts/seo-build.mjs` erzeugt je Seite eine HTML-Datei mit eigenem Titel, Beschreibung und canonical-Adresse, außerdem `robots.txt` und `sitemap.xml`; die Domain stammt aus `SITE_URL`.

## Auslieferung (`deploy/`, `Dockerfile.frontend`, `docker-compose.yml`)

- **Frontend-Image:** Node baut die Seite (`npm run build` inklusive SEO-Build), nginx liefert sie aus. Die Vorlage `deploy/nginx.conf` setzt per `envsubst` den Backend-Port ein.
- nginx leitet `/api` und `/socket.io` (mit WebSocket-Upgrade) an das Backend, setzt Sicherheits-Header und Content-Security-Policy, liefert unbekannte Adressen mit echtem Status 404, setzt `noindex` für nicht öffentliche Seiten und schreibt Zugriffsprotokolle **mit gekürzten IP-Adressen**.
- **Backend-Image:** Python 3.12, Start mit `python run.py` (ein Prozess, Threading-Modus). Daten im Volume `doppelkopf-data`.
- Der Backend-Port ist standardmäßig nur auf `127.0.0.1` gebunden (`BACKEND_BIND`). Den Rest der Absicherung (HTTPS, Firewall) übernimmt der Betreiber, siehe [DEPLOYMENT.md](DEPLOYMENT.md).

## Entscheidungen und Abwägungen

| Entscheidung | Begründung |
|---|---|
| Kein Konto, nur Token und Platz-Code | Datensparsamkeit und niedrige Einstiegshürde. Preis: Wer Browserdaten verliert, braucht den Platz-Code; einzelne Personen lassen sich nicht sperren. |
| Ein Prozess, SQLite | Einfach zu betreiben und zu verstehen; genügt für viele gleichzeitige Tische. Preis: Skalieren heißt größerer Server, nicht mehr Instanzen. |
| Regelkern ohne Zufall und ohne Framework | Gut testbar (Zufallsspiele mit Invarianten), unabhängig von Webtechnik. |
| Sichten je Teilnehmer, nie der ganze Zustand | Fremde Hände verlassen den Server nie, auch nicht versehentlich. |
| Chat und Online-Status nur im Arbeitsspeicher | Nichts davon muss dauerhaft gespeichert werden. Preis: Ein Neustart leert beides. |
| Zeit-Uhren im Spielstand statt in der Hintergrundschleife | Übernahme-Countdown übersteht Neustarts. |
| „Verlassen“ = Bot übernimmt, kein Aufgeben | Aufgeben ist im Doppelkopf nicht vorgesehen und würde die Wertung der anderen verfälschen. |
| Selbst gebautes Captcha statt Fremddienst | Keine Daten an Dritte. Preis: schützt vor Massen-Spam, nicht vor gezielten Angreifern; dafür gibt es die Moderation. |
| Betreiberangaben nicht im Repository | Wer den Code lädt, bekommt nicht das Impressum eines anderen; die Texte gehören zum Code, die Angaben zur Installation. |
