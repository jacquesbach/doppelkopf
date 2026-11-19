# Doppelkopf Multiplayer

Doppelkopf im Browser nach den **DDV-Turnierspielregeln** (Stand 21.02.2026) mit zuschaltbaren Hausregeln, privaten Tischen per Einladungslink,
Bots als Mitspieler und Tisch-Chat.

- **Frontend:** Svelte 5 + Vite, Neubrutalism-Design, ausschließlich Text und Vektorgrafiken (Inline-SVG/CSS), lokal gebündelte Schriften.
- **Backend:** Flask, Flask-SocketIO, SQLite; der Regelkern (`backend/app/rules`) ist reines Python und vollständig getestet.
- Details zu Regeln: [`docs/DDV_REGELMATRIX.md`](docs/DDV_REGELMATRIX.md) · API: [`docs/API.md`](docs/API.md) · Betrieb: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) · Stand und Prüfstand: [`IMPLEMENTATION_NOTES.md`](IMPLEMENTATION_NOTES.md).

## Entwicklung

```bash
# Einstellungen (einmalig): Vorlage kopieren und SECRET_KEY eintragen, siehe .env.example
cp .env.example .env && set -a && source .env && set +a

# Backend (Terminal 1)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python run.py          # http://localhost:8181 (Port: BACKEND_PORT)

# Frontend (Terminal 2)
npm install
npm run dev                                                # http://localhost:5173 (Proxy für /api und /socket.io)
```

| Befehl | Zweck |
|---|---|
| `npm test` | Logik-Tests des Frontends (`node --test`, ohne Browser) |
| `npm run check:svelte` | schneller Syntaxcheck der `.svelte`-Dateien ohne Compiler |
| `npm run build` | Produktionsbuild nach `dist/` |
| `npm run test:e2e` | Playwright (benötigt laufendes Backend) |
| `cd backend && python -m unittest discover -s tests/rules -t .` | Regelkern-Tests |

## Mit Docker

```bash
cp .env.example .env             # SECRET_KEY (und ADMIN_PASSWORD) eintragen
docker compose up --build        # Frontend auf http://localhost:8080 (FRONTEND_PORT), Backend auf 127.0.0.1:8181 (BACKEND_PORT)
```

nginx liefert das Frontend aus und leitet `/api` und `/socket.io` an das Backend weiter (ein Ursprung, kein CORS).
Alle Geheimnisse und Ports stehen in der `.env` (Vorlage: [`.env.example`](.env.example)). Für den öffentlichen Betrieb außerdem
Impressum/Datenschutz in `src/pages/Legal.svelte` ausfüllen.

## Deployment mit GitHub Actions

Jeder Push auf `main` testet das Projekt und lädt es per SSH auf deinen Server ([`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)).
Einrichtung, Liste aller Secrets/Variablen, was Git ignoriert, Sicherung und HTTPS: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Betreiber-Backend

Unter `/admin` (Passwort aus `ADMIN_PASSWORD`; ohne die Variable ist es abgeschaltet) kannst du offene Tische sehen
(Menschen, aktiv/inaktiv seit wann), die Nutzungsstatistik ansehen, die Chat-Sprüche pflegen und Verbesserungsvorschläge moderieren:

```bash
ADMIN_PASSWORD="ein-langes-passwort" python run.py          # lokal
ADMIN_PASSWORD="ein-langes-passwort" docker compose up -d   # Docker (TRUST_PROXY ist dort schon gesetzt)
```

## Lizenz

Siehe [LICENSE](LICENSE).
