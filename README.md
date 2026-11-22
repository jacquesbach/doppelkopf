# Doppelkopf

[![Build & Test](https://github.com/jacquesbach/doppelkopf/actions/workflows/build-and-test.yml/badge.svg)](https://github.com/jacquesbach/doppelkopf/actions/workflows/build-and-test.yml)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-blue.svg)](LICENSE)
![Status: Beta](https://img.shields.io/badge/Status-Beta-orange.svg)

**Doppelkopf im Browser: kostenlos, ohne Registrierung, mit Freunden an einem Tisch.**
Live unter [doppelkopf.cc](https://www.doppelkopf.cc). Dieses Repository enthält den vollständigen Quellcode der Website,
sodass du sie auch selbst betreiben kannst.

- **Kein Konto, keine Cookies, kein Tracking.** Zum Spielen genügt ein frei gewählter Spielname.
- **Mehrspieler in Echtzeit.** Du eröffnest einen Tisch, teilst den Link und spielst zu viert. Freie Plätze füllen Bots.
- **Regeln nach den DDV-Turnierspielregeln** (Stand 21.02.2026), dazu zuschaltbare Haus- und Kneipenregeln.
- **Datensparsam.** Es wird nur gespeichert, was für das Spiel nötig ist. Ein Tisch ohne Aktivität wird nach 12 Stunden gelöscht.
- **Selbst betreibbar.** Ein `docker compose up` genügt, optional mit automatischem Deploy über GitHub Actions.

> **Status: Beta.** Das Spiel ist vollständig spielbar, es kann aber noch Fehler und Ecken und Kanten geben.
> Rückmeldungen sind willkommen: über das Formular für Verbesserungsvorschläge am Ende der Website oder als
> [Issue](https://github.com/jacquesbach/doppelkopf/issues).

Das Projekt ist unabhängig und steht in keiner Verbindung zum Deutschen Doppelkopf-Verband e. V. (DDV).
Dessen Turnierspielregeln dienen als Regelgrundlage.


![Screenshot](https://i.imgur.com/Wn4qigq.png)


## Inhalt

- [Funktionen](#funktionen)
- [Schnellstart](#schnellstart)
- [Auf einem Server installieren](#auf-einem-server-installieren)
- [Konfiguration](#konfiguration)
- [Betrieb](#betrieb)
- [Entwicklung und Tests](#entwicklung-und-tests)
- [Projektaufbau](#projektaufbau)
- [Technik im Überblick](#technik-im-überblick)
- [Datenschutz und Sicherheit](#datenschutz-und-sicherheit)
- [Dokumentation](#dokumentation)
- [Mitwirken und Lizenz](#mitwirken-und-lizenz)

## Funktionen

**Spielen**

- Tische mit Einladungslink (Tisch-Code), optional mit Passwort. Ein Tisch kann in der Liste „offene Tische“ erscheinen, wenn er Mitspieler sucht.
- Vier Spieler, dazu Zuschauer (sie sehen nie Handkarten). Leere Plätze besetzen Bots; ein Spiel allein gegen Bots geht auch.
- Alle Spielarten der DDV-Regeln: Normalspiel, Hochzeit und Stille Hochzeit, Pflicht- und Lustsolo (Farb-, Damen-, Buben-Solo, Fleischloser), An- und Absagen mit Fristen und die Sonderpunkte (Doppelkopf, Fuchs, Karlchen, gegen die Kreuz-Damen).
- Zuschaltbare Regeln: ohne Neunen (40 Karten), Dulle, Schweinchen, Armut, Bockrunden, Ansagepflicht und weitere (siehe [Regelmatrix](docs/DDV_REGELMATRIX.md)).
- Bots mit Gedächtnis, die ungesehene Karten durchrechnen. Sie übernehmen auch Plätze, wenn jemand die Verbindung verliert oder nicht mehr reagiert (einstellbar).
- Tisch-Chat mit Klassiker-Sprüchen, Spielprotokoll, „Letzter Stich“ und Stiche ansehen nach dem Spiel.
- Platz zurückholen auf einem anderen Gerät mit einem Platz-Code. Heller und dunkler Tisch. Am Desktop passt der Spieltisch genau ins Browserfenster (kein Scrollen), am Handy ebenso; Bedienung am Handy mit zweifachem Tippen.
- Optional und freiwillig: „Wer ist online“ mit Freundescode, ohne Konto (standardmäßig aus).

**Betreiber** (`/admin`, nur mit Passwort)

- Live-Übersicht der Tische, Zuschauen, Nachricht senden, Tisch beenden.
- Statistik und Auswertungen (Spiele pro Tag, Spitzenzeiten, Spieldauer, Abbruchquote), Systemstatus und Fehler-Log.
- Design (Farben, Banner, Hell/Dunkel-Vorgabe), Chat-Sprüche, Moderation der Verbesserungsvorschläge.
- Test-Tisch: beliebige Spielsituationen (Armut, Hochzeit, Endspiel …) gezielt aufbauen und prüfen.

## Schnellstart

### Lokal ausprobieren mit Docker

Voraussetzung: Docker mit Compose-Plugin.

```bash
git clone https://github.com/jacquesbach/doppelkopf.git
cd doppelkopf
cp .env.example .env
# Trage in .env einen SECRET_KEY ein. Erzeugen:  python3 -c "import secrets; print(secrets.token_hex(32))"
docker compose up -d --build
```

Danach läuft die Seite auf <http://localhost:8080>. Ohne `ADMIN_PASSWORD` in der `.env` ist das Betreiber-Backend abgeschaltet.
Impressum und Datenschutz zeigen so lange markierte Testdaten, bis du eigene Angaben hinterlegst
(siehe [Deployment](docs/DEPLOYMENT.md#impressum-und-datenschutzerklärung)).

### Entwickeln ohne Docker

Voraussetzungen: Python 3.12 und Node.js 22 (mindestens 20.19).

```bash
# Terminal 1: Backend (läuft ohne weitere Einstellungen auf http://localhost:8181)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py

# Terminal 2: Frontend (http://localhost:5173, leitet /api und /socket.io an das Backend weiter)
npm install
npm run dev
```

Mehr dazu in der [Entwicklungsanleitung](docs/DEVELOPMENT.md).

## Auf einem Server installieren

Es gibt zwei Wege. Beide laufen mit Docker Compose.

| Weg | Wann sinnvoll | Anleitung |
|---|---|---|
| **A. Von Hand** | erster Start, Ausprobieren | [DEPLOYMENT.md, Weg A](docs/DEPLOYMENT.md#weg-a-von-hand-mit-docker-compose) |
| **B. Automatisch mit GitHub Actions** | dauerhafter Betrieb: jeder Push auf `main` testet und aktualisiert den Server | [DEPLOYMENT.md, Weg B](docs/DEPLOYMENT.md#weg-b-automatisch-mit-github-actions) |

Der Kurzablauf von Weg A auf einem Linux-Server mit Docker:

```bash
git clone https://github.com/jacquesbach/doppelkopf.git /opt/doppelkopf && cd /opt/doppelkopf
cp .env.example .env && nano .env          # SECRET_KEY, ADMIN_PASSWORD, SITE_URL eintragen
mkdir -p legal && cp deploy/legal.example.json legal/legal.json && nano legal/legal.json   # Impressum
docker compose up -d --build
curl http://127.0.0.1:8080/api/health      # {"service":"doppelkopf-multiplayer","status":"ok"}
```

Für den öffentlichen Betrieb kommt davor ein Proxy mit HTTPS (z. B. Caddy) und ein DNS-Eintrag auf deine Domain.
Das beschreibt [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) Schritt für Schritt, einschließlich Firewall, Impressum und Suchmaschinen.

So sieht der Betrieb aus:

```
Besucher ──HTTPS──▶ Proxy (Caddy, Port 443) ──▶ Container "frontend" (nginx, Port 8080)
                                                    ├─ liefert die Website aus
                                                    └─ leitet /api und /socket.io an ▶ Container "backend" (Flask, Port 8181)
                                                                                         └─ SQLite-Datei im Volume "doppelkopf-data"
```

## Konfiguration

Alle Einstellungen stehen in **einer** Datei, der `.env` (Vorlage: [`.env.example`](.env.example)). Sie kommt nie ins Git.
Beim automatischen Deploy schreibt GitHub Actions sie aus deinen GitHub-Secrets und -Variablen auf den Server.

Die wichtigsten Einstellungen:

| Name | Pflicht | Standard | Bedeutung |
|---|---|---|---|
| `SECRET_KEY` | ja | – | Geheimer Schlüssel (mindestens 32 Zeichen). Signiert Captcha und Admin-Anmeldung und berechnet Platz-Codes. |
| `ADMIN_PASSWORD` | nein | leer | Passwort für `/admin` (mindestens 10 Zeichen). Leer schaltet das Betreiber-Backend ab. |
| `SITE_URL` | empfohlen | `https://doppelkopf.cc` | Adresse der Website (mit `https://`, ohne `/` am Ende). Für canonical-Links, `sitemap.xml`, `robots.txt` und Link-Vorschau. |
| `FRONTEND_PORT` | nein | `8080` | Port der Website auf dem Server. |
| `BACKEND_PORT` | nein | `8181` | Port des Backends. |
| `BACKEND_BIND` | nein | `127.0.0.1` | `127.0.0.1` = Backend nur lokal erreichbar (empfohlen). |
| `CREATE_PER_HOUR` | nein | `30` | Neue Tische je Besucheradresse und Stunde. |
| `COMPOSE_PROJECT_NAME` | nein | `doppelkopf` | Bestimmt den Namen des Daten-Volumes. Bei bestehender Installation nicht ändern. |

Dazu kommen die **Betreiberangaben** für Impressum und Datenschutzerklärung (`legal/legal.json`, auf dem Server aus den
GitHub-Variablen `LEGAL_*` erzeugt). Sie stehen bewusst nicht im Repository.

Alle Variablen mit Erklärung, die GitHub-Secrets und -Variablen sowie fest eingebaute Werte (Grenzen, Zeiten):
[docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Betrieb

```bash
cd /opt/doppelkopf
docker compose ps                          # Zustand
docker compose logs -f --tail=100          # Protokolle
docker compose restart backend             # Neustart (Spielstände bleiben erhalten)
git pull && docker compose up -d --build   # Aktualisieren (bei Weg A)
```

- **Daten** liegen in der SQLite-Datei im Docker-Volume `doppelkopf-data`. Sicherung und Wiederherstellung: [docs/OPERATIONS.md](docs/OPERATIONS.md#sicherung-und-wiederherstellung).
- **Betreiber-Backend** unter `/admin`: Live-Übersicht, Statistik, Fehler-Log, Design, Moderation. Erklärung der Reiter: [docs/OPERATIONS.md](docs/OPERATIONS.md#das-betreiber-backend-admin).
- **Ein Prozess.** Das Backend läuft bewusst als ein einziger Prozess (Spielstände, Bots und Socket.IO). Mehrere Instanzen hinter einem Lastverteiler werden nicht unterstützt.

## Entwicklung und Tests

| Befehl | Zweck |
|---|---|
| `npm test` | Logik-Tests des Frontends (`node --test`, ohne Browser) |
| `npm run check:svelte` | Syntaxcheck der `.svelte`-Dateien |
| `npm run build` | Produktionsbuild nach `dist/` |
| `npm run test:e2e` | Browser-Test mit Playwright (startet den Vite-Server selbst) |
| `cd backend && python -m unittest discover -s tests/rules -t .` | Regelkern (läuft ohne Flask) |
| `cd backend && python -m unittest discover -s tests/service -t .` | Tischschicht, HTTP, Bots, Betreiber-Logik |
| `cd backend && python -m pytest -q tests/test_*.py` | Tests mit echter App und Datenbank (braucht `requirements.txt`) |

GitHub Actions führt die Tests bei jedem Pull Request aus (`.github/workflows/build-and-test.yml`) und startet zusätzlich den
ganzen Docker-Stack mit einem Smoke-Test. Details, Konventionen und Hinweise zum Test-Tisch: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Projektaufbau

```
.
├── src/                   Frontend (Svelte 5 + Vite)
│   ├── pages/             Seiten: Start, Tisch anlegen, Beitreten, Lobby, Tisch, Regeln, Admin, Impressum, Datenschutz
│   ├── components/        game/ (Spieltisch), cards/ (Karten als SVG), ui/, community/, admin/
│   ├── lib/               Logik ohne Oberfläche: API-Client, Socket, Router, Zustand eines Tisches, Texte
│   ├── content/           Texte der Start- und Regelseite
│   └── styles/            Design-Grundlage (Neubrutalism)
├── backend/               Flask, Flask-SocketIO, SQLAlchemy (SQLite)
│   ├── app/rules/         Regelkern (reines Python): Karten, Trumpf, Vorbehalt, Ansagen, Wertung, Runde, Optionen
│   ├── app/table/         Tischschicht: Zustand, Service, Bots, Chat
│   ├── app/community/     Vorschläge, Captcha, Chat-Sprüche, Statistik, Admin-Anmeldung
│   ├── app/ops/           Betreiber: Einstellungen, Live-Übersicht, Auswertungen, Fehler-Log, Systemstatus
│   ├── app/lab/           Test-Tisch für Betreiber
│   ├── tools/             Bot-Turnier (Selbstspiel zum Messen der Bot-Stärke)
│   └── tests/             rules/ (Regelkern), service/ (Tischschicht), pytest-Tests mit echter App
├── tests/                 Frontend-Tests (node --test)
├── e2e/                   Playwright-Test
├── deploy/                nginx-Vorlage und Beispiel für die Betreiberangaben
├── scripts/               Svelte-Syntaxcheck, SEO-Build, Smoke-Test
├── docs/                  Dokumentation
├── .github/workflows/     Tests, Deploy, CodeQL
├── docker-compose.yml     Backend + Frontend
└── .env.example           Vorlage aller Einstellungen
```

## Technik im Überblick

- **Frontend:** Svelte 5, Vite 7, `socket.io-client`. Karten, Logo und Symbole sind selbst gezeichnete Vektorgrafiken (Inline-SVG), die Schriften werden lokal ausgeliefert (keine Anfragen an Drittanbieter).
- **Backend:** Flask, Flask-SocketIO im Threading-Modus, SQLAlchemy mit SQLite. Der **Regelkern ist reines Python** ohne Flask und Datenbank und vollständig getestet. Er prüft jeden Zug.
- **Die Oberfläche rechnet keine Regeln.** Welche Karten erlaubt sind, kommt vom Server (`legalActions`). So kann niemand durch Manipulation im Browser schummeln.
- **Persönliche Sichten.** Jeder Spieler bekommt nur seine eigene Sicht auf das Spiel. Fremde Handkarten verlassen den Server nie. Tests prüfen das über ganze Spiele.
- **Echtzeit** über Socket.IO, Zugriffe per HTTP mit Sitzungs-Token. Versionsnummern und Wiederholungsschutz verhindern doppelte oder veraltete Züge.

Mehr dazu: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Datenschutz und Sicherheit

- Kein Benutzerkonto, keine Cookies, keine Drittdienste, kein Tracking. Server-Protokolle enthalten nur gekürzte IP-Adressen.
- Spielname, Tisch-Code, Spielstand und Chat bleiben nur so lange gespeichert, wie der Tisch besteht (spätestens 12 Stunden nach der letzten Aktivität).
- Die **Datenschutzerklärung** steht in der Website (`/datenschutz`, Quelltext `src/pages/Legal.svelte`). Wer neue Funktionen baut, die mehr speichern oder verarbeiten, muss sie mitpflegen. Eine Übersicht für Entwickler und Betreiber: [docs/PRIVACY.md](docs/PRIVACY.md).
- Schutz vor Missbrauch: Begrenzungen für neue Tische und Beitrittsversuche, Platz-Code beim Wiedereinstieg, kurze Admin-Sitzungen, Content-Security-Policy.
- **Sicherheitslücken** bitte vertraulich melden: siehe [SECURITY.md](SECURITY.md).

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Installation auf einem Server, GitHub Actions, HTTPS, Domain, Impressum, Suchmaschinen, Fehlersuche |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Alle Variablen, Secrets, `legal.json` und fest eingebaute Werte |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Laufender Betrieb: Aktualisieren, Sicherung, Admin-Backend, Wartung |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Entwicklungsumgebung, Tests, Konventionen, Änderungen vornehmen |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Aufbau von Frontend, Backend und Regelkern, Datenfluss, Entscheidungen |
| [docs/API.md](docs/API.md) | HTTP- und Socket.IO-Schnittstelle |
| [docs/DDV_REGELMATRIX.md](docs/DDV_REGELMATRIX.md) | Abgleich mit den DDV-Turnierspielregeln, Optionen und Annahmen |
| [docs/PRIVACY.md](docs/PRIVACY.md) | Welche Daten wo und wie lange gespeichert werden (für Entwickler und Betreiber) |
| [backend/README.md](backend/README.md) | Backend: starten, Aufbau, Tests |
| [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Mitwirken, Sicherheitsmeldungen, Verhaltensregeln |

## Mitwirken und Lizenz

Fehlerberichte, Verbesserungsvorschläge und Pull Requests sind willkommen. Wie das geht, steht in [CONTRIBUTING.md](CONTRIBUTING.md).
Das Projekt steht unter der [MIT-Lizenz](LICENSE).
