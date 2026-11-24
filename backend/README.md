# Doppelkopf: Backend

Flask-API und Socket.IO mit einem reinen Python-Regelkern (DDV-Turnierspielregeln, Stand 21.02.2026). Es bedient das Svelte-Frontend im Wurzelordner.
Die ausführliche Dokumentation liegt in [`../docs/`](../docs/); diese Datei ist der Einstieg für den Backend-Ordner.

## Lokal starten

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

- API: `http://localhost:8181/api` (Port über `BACKEND_PORT`), Gesundheitstest `GET /api/health`.
- Datenbank (Entwicklung): `backend/instance/doppelkopf.sqlite3`, wird beim Start angelegt. Mit `DATABASE_URL` lässt sich ein anderer Pfad wählen.
- Betreiber-Backend ausprobieren: vor dem Start `ADMIN_PASSWORD=<mindestens 10 Zeichen>` setzen.
- Das Frontend startest du im Wurzelordner mit `npm run dev` (Vite leitet `/api` und `/socket.io` an dieses Backend).

Alle Variablen: [`../docs/CONFIGURATION.md`](../docs/CONFIGURATION.md). Routen und Ereignisse: [`../docs/API.md`](../docs/API.md).

## Aufbau

| Pfad | Aufgabe |
|---|---|
| `app/rules/` | **Regelkern** ohne Flask und Datenbank: Karten, Trumpf, Vorbehalte, Ansagen, Wertung, Spielrunde, zuschaltbare Regeln, Sichten |
| `app/table/` | **Tischschicht:** Zustand, `TableService` (Versionsprüfung, Idempotenz), Bots (`bots.py`, `pimc.py`), getakteter `BotRunner`, Chat, Speicher-Schnittstelle |
| `app/routes.py`, `app/services.py` | Tische: anlegen, beitreten, bereit, Bots, verlassen, Platz-Code, Wiedereinstieg |
| `app/game_api.py` | Spielrouten: Regeln, Start, Zug, Sicht, Protokoll, Chat, Bot-Übernahme |
| `app/community/` | Vorschläge und Daumen, Captcha, Chat-Sprüche, Statistik, Betreiber-Anmeldung, Begrenzungen |
| `app/ops/` | Betreiber: Seiteneinstellungen, Live-Übersicht, Auswertungen, Fehler-Log, Systemstatus |
| `app/lab/` | Test-Tisch für Betreiber |
| `app/guard.py`, `app/seatcode.py`, `app/presence.py` | Zugangsschutz, Platz-Codes, freiwilliger Online-Status |
| `app/housekeeping.py` | räumt verwaiste Tische und alte Einträge auf |
| `app/db_access.py`, `app/models.py` | SQLAlchemy- und Socket.IO-Anbindung (bewusst dünn), Tabellen |
| `tools/bot_tournament.py`, `tools/scenarios.py` | Bot-Turnier: Selbstspiel zum Messen der Bot-Stärke, auch gezielt je Spielart (Solo, Armut, Hochzeit, Schweinchen) |
| `tests/` | `rules/` (Regelkern), `service/` (Tischschicht, HTTP, Bots), `test_*.py` (echte App mit Datenbank) |

Die Regel „Fachlogik ohne Framework“ gilt durchgehend: Regelkern, Tischschicht und Teile von `community/` und `ops/` kennen weder Flask noch SQL. Das SQL steht in `sql.py` bzw. `db_access.py`.
Mehr dazu: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

## Tests

```bash
cd backend
python -m unittest discover -s tests/rules -t .      # Regelkern (177 Tests), ohne Flask lauffähig
python -m unittest discover -s tests/service -t .    # Tischschicht, Bots, HTTP mit Speicher-Stores (262 Tests)
python -m pytest -q tests/test_api_flow.py tests/test_rooms.py tests/test_community.py   # echte App (braucht requirements.txt)
python -m pytest -q tests/test_access.py             # Zugangsschutz mit Datenbank (noch nicht in der CI)
```

Die Zahlen sind der Stand zum Zeitpunkt dieser Doku. Hinweise zu Teststrategie und Konventionen: [`../docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md).

## Sicherheit und Betrieb in Kürze

- Raumpasswörter sind gehasht (Werkzeug, mindestens 6 Zeichen). Sitzungs-Tokens sind zufällig; in der Datenbank steht nur der SHA-256-Hash. Bots handeln ausschließlich serverseitig, ihre Tokens werden nie ausgegeben.
- Die Spielsicht enthält nie fremde Hände oder verdeckte Parteien (die Stille Hochzeit bleibt bis Spielende verdeckt). `tests/service/test_view_leaks.py` prüft das nach jeder Aktion ganzer Spiele.
- `APP_ENV=production` verlangt ein gesetztes `SECRET_KEY` (und, falls gesetzt, ein `ADMIN_PASSWORD` mit mindestens 10 Zeichen).
- `CORS_ORIGINS` ist kommagetrennt; `*` erlaubt alle. Hinter dem nginx-Proxy auf beliebigem Host und Port **`*` setzen**: Socket.IO prüft den Origin strikt, sonst bleibt die Live-Verbindung aus (Anzeige „Offline“). Die Sicherheit hängt an den Tokens, nicht an Cookies.
- `TRUST_PROXY=1` hinter einem Proxy: Die Besucheradresse für die Begrenzungen kommt aus `X-Forwarded-For`.
- Schreibzugriffe: Sperre je Tisch im Prozess und optimistische Versionssperre beim Speichern. Das Backend läuft **als ein Prozess** (Threading-Modus); mehrere Worker bräuchten eine Message-Queue für Socket.IO und gemeinsamen Zustand.
- Der Tisch-Chat liegt nur im Arbeitsspeicher (100 Nachrichten je Tisch, 200 Zeichen, eine Nachricht je 0,8 s).
- Der Flask-Debugger läuft nur mit `FLASK_DEBUG=1`.
- Neue Spalten in bestehenden SQLite-Dateien ergänzt `create_app` beim Start automatisch (`_ensure_columns`); es gibt kein Migrationswerkzeug.

Weiteres: [`../SECURITY.md`](../SECURITY.md), [`../docs/PRIVACY.md`](../docs/PRIVACY.md).

## Docker

Das `Dockerfile` baut ein Image mit Python 3.12, das `python run.py` startet (Port `BACKEND_PORT`, Daten im Volume unter `/data`). Zusammen mit dem Frontend-Image startet `docker compose up -d --build` im Wurzelordner den ganzen Stack, siehe [`../docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md).
