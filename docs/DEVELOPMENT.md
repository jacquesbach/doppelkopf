# Entwicklung

Diese Anleitung ist für alle, die am Code arbeiten: Umgebung einrichten, Tests ausführen, Änderungen sauber machen.
Den Aufbau erklärt [ARCHITECTURE.md](ARCHITECTURE.md), die Schnittstellen [API.md](API.md), die Regeln [DDV_REGELMATRIX.md](DDV_REGELMATRIX.md).

## Voraussetzungen

- **Node.js 20.19 oder neuer** (die CI und die Docker-Images nutzen 22) mit npm (Frontend)
- **Python 3.12** (die Docker-Images nutzen 3.12; der Regelkern läuft auch mit neueren Versionen)
- Optional: Docker mit Compose-Plugin, um den ganzen Stack wie im Betrieb zu starten

## Lokal starten

```bash
# 1. Backend (Terminal 1)
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                      # http://localhost:8181/api/health

# 2. Frontend (Terminal 2, im Projektordner)
npm install
npm run dev                        # http://localhost:5173
```

Im Entwicklungsmodus leitet Vite `/api` und `/socket.io` an das Backend weiter (`vite.config.js`). Der Port kommt aus `BACKEND_PORT`
(Standard 8181). Ohne gesetzte Variablen startet das Backend im Entwicklungsmodus mit einem festen Entwicklungsschlüssel (in Produktion, `APP_ENV=production`, verweigert es den Start damit); Datenbank ist `backend/instance/doppelkopf.sqlite3`.
Wer das Betreiber-Backend ausprobieren will, setzt vor dem Start `ADMIN_PASSWORD` (mindestens 10 Zeichen):

```bash
ADMIN_PASSWORD=mein-langes-passwort python run.py
```

Alle Variablen: [CONFIGURATION.md](CONFIGURATION.md). Den ganzen Stack wie im Betrieb startest du mit `docker compose up --build` (siehe [DEPLOYMENT.md](DEPLOYMENT.md#weg-a-von-hand-mit-docker-compose)).

## Tests

| Befehl | Was geprüft wird | Wo |
|---|---|---|
| `npm test` | Logik des Frontends (Router, API-Client, Sitzungen, Karten, Online-Status, Regelformular, Test-Tisch-Editor, SEO, Texte). Ohne Browser, mit `node --test`. | `tests/` |
| `npm run check:svelte` | Syntaxcheck aller `.svelte`-Dateien (Skriptblöcke, Block- und Tag-Balance). Kein Ersatz für den Compiler. | `scripts/check-svelte.mjs` |
| `npm run build` | Produktionsbuild; der Svelte-Compiler meldet echte Fehler | `dist/` |
| `npm run test:e2e` | Browser-Test mit Playwright (Chromium). Einmalig `npx playwright install chromium`. | `e2e/` |
| `cd backend && python -m unittest discover -s tests/rules -t .` | Regelkern, läuft ganz ohne Flask und Datenbank | `backend/tests/rules/` |
| `cd backend && python -m unittest discover -s tests/service -t .` | Tischschicht, Bots, HTTP-Schicht mit Speicher-Stores, Betreiber-Logik, Datenlecks | `backend/tests/service/` |
| `cd backend && python -m pytest -q tests/test_api_flow.py tests/test_rooms.py tests/test_community.py` | Echte App mit Flask-SQLAlchemy und SQLite (braucht `requirements.txt`) | `backend/tests/` |

Zusätzlich gibt es `backend/tests/test_access.py` (Zugangsschutz mit echter Datenbank). Die Datei läuft mit `pytest`, ist aber bewusst noch nicht
in der CI-Liste. Wer am Zugang arbeitet, führt sie von Hand aus: `python -m pytest -q tests/test_access.py`.

Die **CI** (`.github/workflows/build-and-test.yml`) läuft bei jedem Pull Request nach `main`, per Hand („Run workflow“) und als erste Stufe des Deploys bei einem Push auf `main`. Sie führt aus: Frontend (Syntaxcheck, Tests, Build), Backend (Regelkern, Tischschicht, pytest) und einen Docker-Job
(`docker compose config`, Images bauen, Stack starten, `scripts/smoke-test.sh`). Ein Pull Request sollte grün sein, bevor er gemerged wird.

**Wie die Tests aufgebaut sind**

- Der **Regelkern** ist reines Python und wird fast ausschließlich über kleine, lesbare Spielsituationen getestet (`tests/rules/fixtures.py`). Daneben laufen Zufallsspiele: ganze Runden mit
  Bots, die nach jeder Aktion Invarianten prüfen (Kartenzahl, Punktesumme 240 Augen, Nullsumme der Wertung).
- Die **Tischschicht** wird mit Speicher-Stores statt der Datenbank und mit künstlicher Uhr getestet. Bot-Pausen werden dabei übersprungen (`paced=False` bzw. synchroner Runner).
- `test_view_leaks.py` spielt ganze Spiele (auch mit Armut und Bot-Übernahme) und prüft nach **jeder** Aktion, dass keine Sicht (Spieler, Zuschauer, Unbekannter, Socket) fremde Handkarten oder verdeckte Karten enthält. Er ist das Sicherheitsnetz für alles, was Sichten verändert.
- Im Frontend liegt die Logik in reinem JavaScript unter `src/lib/` und wird mit `node --test` geprüft. Svelte-Komponenten rechnen keine Regeln; sie zeigen, was `legalActions` des Servers erlaubt.

## Konventionen

- **Sprache:** Oberfläche, Kommentare, Commit-Nachrichten und Dokumentation sind auf Deutsch. Bezeichner im Code sind Englisch.
- **Regeln gehören in den Regelkern** (`backend/app/rules`) und nirgends sonst. Weder Tischschicht noch Oberfläche duplizieren Regeln.
- **Server ist maßgeblich.** Der Client schickt nur Absichten; der Server prüft alles und sendet nur, was der Empfänger sehen darf.
- **Kein Zugriff auf fremde Hände.** Neue Felder in Sichten (`player_view`, `spectator_view`, `bot_view`, Publisher) brauchen einen Eintrag im Lecktest.
- **Datensparsamkeit:** Neue gespeicherte Daten oder neue Browser-Einträge brauchen einen Vermerk in [PRIVACY.md](PRIVACY.md) **und** eine Anpassung der Datenschutzerklärung in `src/pages/Legal.svelte`.
- **Formatierung:** Prettier (`npm run format`) für `src/` und `tests/`. Python nach PEP 8, Zeilen bis etwa 120 Zeichen.
- **Datenbank-Änderungen:** Neue Spalten in `models.py` mit `server_default`, und in `_ensure_columns` (`backend/app/__init__.py`) eintragen. Das ergänzt sie beim Start in bestehenden Datenbanken (kein Migrationswerkzeug nötig).
- **Gespeicherte Spielstände** sind versioniert (`GameSnapshot.schema_version`). Neue Felder im Spielzustand brauchen einen Standardwert, damit alte Spiele weiter laden.

## Typische Aufgaben

### Eine Spielregel ändern oder hinzufügen

1. Die Regel in den **DDV-Turnierspielregeln** (TSR) nachlesen und den Abschnitt notieren.
2. Im Regelkern umsetzen. Eine neue **zuschaltbare** Regel kommt in `backend/app/rules/options.py` (Option mit Text, Gruppe, Standard, ggf. `requires`). Das Regelformular der Oberfläche entsteht daraus von selbst (`GET /api/rule-schema`).
3. Einen **Test** in `backend/tests/rules/` schreiben, der die Regel an einer Spielsituation zeigt.
4. [DDV_REGELMATRIX.md](DDV_REGELMATRIX.md) ergänzen: Abschnitt der TSR, Umsetzung, Annahmen. Wenn die Regel Texte betrifft: `src/content/rules.js` (Regelseite) und gegebenenfalls `src/lib/labels.js`.
5. Prüfen, ob Bots die Regel kennen müssen (`backend/app/table/bots.py`) und ob eine Sicht neue Felder braucht.
6. Alle Tests laufen lassen.

### Eine Route hinzufügen

Route in `routes.py`, `game_api.py` oder dem passenden Unterpaket (`community/api.py`, `ops/api.py`, `lab/api.py`) anlegen. Zugriffsprüfung (Token, Betreiber-Token, Begrenzung) **nicht vergessen**.
Logik nach Möglichkeit in flaskfreie Module legen und dort testen; die Route bleibt dünn. Danach [API.md](API.md) ergänzen. Ein HTTP-Test gehört in `tests/service/test_http_api.py` oder in das passende Testmodul.

### Das Frontend erweitern

- Neue Seite: Datei in `src/pages/`, Pfad in `src/lib/router.js` und `src/App.svelte`, SEO-Angaben in `src/lib/seo.js`, bei einer öffentlichen Seite zusätzlich in `scripts/seo-build.mjs` und in `deploy/nginx.conf`
  (sonst liefert nginx 404, und der Smoke-Test schlägt fehl).
- Reine Logik gehört nach `src/lib/*.js` mit Test unter `tests/`, nicht in die Komponente.
- Das Design folgt Neubrutalism: dicke Konturen, harte Schatten, Klassen mit Präfix `nb-`/`nx-`, Grundlage in `src/styles/global.css`. Karten sind Inline-SVG, es gibt keine Bilddateien für Spielelemente.

### Bots messen

Das Bot-Turnier lässt zwei Versionen gegeneinander auf denselben Kartenverteilungen spielen (neue Bots auf den Sitzen 0 und 2, die frühere Grundstrategie auf 1 und 3):

```bash
cd backend
python3 -m tools.bot_tournament 250 1 ddv                 # Verteilungen, Zufallssaat, Regelsatz (ddv | alle | ohne9)
python3 -m tools.bot_tournament 250 1 ddv pimc=1 announce=pimc
# gezielt eine Spielart messen (Verteilungen werden zurechtgerückt, siehe tools/scenarios.py)
python3 -m tools.bot_tournament 200 1 ddv pimc=1 announce=pimc spielart=solo a.pimc_solo=1 b.pimc_solo=0
```

`spielart=` kennt `solo`, `wedding`, `poverty` und `schweinchen`; `a.name=wert` bzw. `b.name=wert` setzt eine Einstellung nur für eine Seite (hier: Durchrechnen im Solo an gegen aus, sonst gleich).

Ausgegeben werden die Punktesumme beider Seiten und die Zahl gewonnener Spiele. Mehrere hundert Spiele dauern einige Minuten. Die frühere Strategie liegt als Vergleich in `backend/tests/service/legacy_bots.py`.

## Test-Tisch (Szenario-Labor)

Für Situationen, auf die man im echten Spiel lange warten müsste (Armut, Hochzeit, Schweinchen, Endspiel, Ergebnis-Dialog, Pflichtsolo, Bockrunde), gibt es im Betreiber-Backend den Reiter **TEST-TISCH**.

- Ein Test-Tisch ist ein **gewöhnlicher Tisch** mit demselben Regelkern, derselben Tischschicht, denselben Bots und derselben Oberfläche. Er unterscheidet sich nur im Aufbau: Die Kartenreihenfolge wird so gebaut, dass jeder Platz die gewünschten Karten bekommt.
- Ein **Szenario** ist reine Daten (JSON): Regeln, Geber, Karten je Platz, Besetzung (Bot oder selbst gespielt), Rundenstand und „Vorspielen“ (Bots spielen bis zum Spielbeginn oder bis zu N Stichen). Fertige Vorlagen: `backend/app/lab/presets.py` (z. B. Armut aus beiden Sichten, Hochzeit, Schweinchen, Endspiel, Ergebnis-Dialog, Pflichtsolo, Bockrunde, leerer Tisch).
- Jeder selbst gespielte Platz hat ein eigenes Token. Die Leiste „TEST“ unten links am Tisch wechselt den Platz; „Szenario neu starten“ baut denselben Tisch erneut auf.
- Test-Tische sind **nie öffentlich**, zählen **nicht** in die Statistik, haben keine Bot-Übernahme und werden nach 12 Stunden Leerlauf entfernt.
- Alle Routen liegen unter `/api/admin/lab/…` und verlangen das Betreiber-Token. Der Browser merkt sich die Plätze der Test-Tische im `localStorage` (`doko.lab.v1`, nur beim Betreiber).

Tests: `backend/tests/service/test_lab.py`, `tests/lab.test.js`.

## Veröffentlichen

- Änderungen über einen Pull Request nach `main`. Nach dem Merge deployt die Pipeline automatisch, wenn Weg B eingerichtet ist ([DEPLOYMENT.md](DEPLOYMENT.md#weg-b-automatisch-mit-github-actions)).
- Die Version in der Oberfläche (Reiter SYSTEM) kommt aus `APP_VERSION` (bei Weg B der Git-Commit) und `DEPLOYED_AT`.
- Abhängigkeitsupdates kommen von Dependabot als Pull Requests.

## Bekannte Eigenheiten

- `requirements.txt` enthält `gunicorn` und `eventlet`. Beide werden vom aktuellen Betrieb **nicht** genutzt: Das Backend läuft als einzelner Prozess im Threading-Modus (`python run.py`).
- Im Repository liegt keine `package-lock.json`. Wer reproduzierbare Frontend-Builds will, führt einmal `npm install` aus und committet die Datei.
- Alte, vor dem Spielzustand-Format 2 gespeicherte Spiele werden ignoriert (`schema_version`).
