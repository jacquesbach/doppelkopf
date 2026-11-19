# Doppelkopf – Backend

Flask-API, Socket.IO und ein reiner Python-Regelkern (DDV-Turnierspielregeln, Stand 21.02.2026) für das Svelte-Frontend.

## Lokal starten

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

API: `http://localhost:8181/api` (Port über `BACKEND_PORT`, siehe `../.env.example`) · Health-Check: `/api/health` · Beschreibung aller Routen: [`../docs/API.md`](../docs/API.md).

## Aufbau

| Paket | Aufgabe |
|---|---|
| `app/rules/` | Regelkern ohne Flask/DB: Karten, Trumpf, Vorbehalte, Ansagen, Wertung, Spielrunde, optionale Regeln |
| `app/table/` | Tischschicht: Zustand, Service mit Versionsprüfung/Idempotenz, Bots, Chat, Speicher-Schnittstelle |
| `app/game_api.py` | HTTP-Routen für Regeln, Start, Zug, Sicht, Protokoll, Chat |
| `app/routes.py`, `app/services.py` | Räume: anlegen, beitreten, bereit, Bots, verlassen |
| `app/db_access.py`, `app/models.py` | SQLAlchemy-/Socket.IO-Anbindung (dünn) |

## Tests

```bash
cd backend
python -m unittest discover -s tests/rules -t .     # Regelkern (ohne Flask lauffähig)
python -m unittest discover -s tests/service -t .   # Tischschicht + HTTP mit In-Memory-Speicher
python -m pytest -q tests/test_api_flow.py tests/test_rooms.py tests/test_community.py   # echte App (benötigt requirements.txt)
```

## Sicherheit und Betrieb

- Raumpasswörter werden mit Werkzeug gehasht; Sitzungs-Tokens sind zufällig, in der Datenbank steht nur der SHA-256-Hash.
- Bots handeln ausschließlich serverseitig; ihre Tokens werden nie ausgegeben.
- Die Spielsicht enthält nie fremde Hände oder verdeckte Parteien (Stille Hochzeit bleibt bis Spielende verdeckt).
- `APP_ENV=production` verlangt `SECRET_KEY`. CORS-Origins konfigurieren (`CORS_ORIGINS`, kommagetrennt; `*` erlaubt alle). Hinter dem nginx-Proxy auf
  beliebigem Host/Port **`*` setzen**: Socket.IO prüft den Origin strikt, sonst bleibt die Live-Verbindung aus (Anzeige „Offline“).
- Schreibzugriffe: Sperre pro Raum im Prozess + optimistische Versionssperre. Mehrere Worker benötigen eine Message-Queue für Socket.IO.
- Der Tisch-Chat liegt nur im Arbeitsspeicher (letzte 100 Nachrichten pro Raum, 200 Zeichen, eine Nachricht je 0,8 s).
