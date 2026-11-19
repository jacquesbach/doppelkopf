# Betrieb und Deployment

Alle Einstellungen (Geheimnisse, Ports) stehen an **einer** Stelle: in der Datei `.env`. Lokal legst du sie selbst an
(Vorlage `.env.example`), auf dem Server schreibt sie GitHub Actions bei jedem Deploy aus den **GitHub-Secrets und -Variablen**.
Die `.env` kommt nie ins Git.

| Datei | Zweck |
|---|---|
| `.env.example` | Vorlage mit allen Einstellungen und Erklärung |
| `docker-compose.yml` | startet Backend + Frontend, liest Ports und Geheimnisse aus `.env` |
| `deploy/nginx.conf` | nginx-Vorlage des Frontends (Backend-Port kommt aus `BACKEND_PORT`) |
| `.github/workflows/build-and-test.yml` | Tests bei Pull Requests (und als Vorstufe des Deploys) |
| `.github/workflows/deploy.yml` | **die Deploy-Datei**: Tests, dann Upload per SSH und `docker compose up` auf dem Server |

## Einstellungen

| Name | Art | Standard | Bedeutung |
|---|---|---|---|
| `SECRET_KEY` | **Secret** | – (Pflicht) | signiert Captcha und Betreiber-Anmeldung. Mind. 32 Zeichen: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ADMIN_PASSWORD` | **Secret** | leer = `/admin` aus | Passwort des Betreiber-Backends, mind. 10 Zeichen |
| `SSH_HOST` | **Secret** | – (Pflicht) | Adresse deines Servers |
| `SSH_USER` | **Secret** | – (Pflicht) | Benutzer für den Deploy (muss `docker` ausführen dürfen) |
| `SSH_PRIVATE_KEY` | **Secret** | – (Pflicht) | privater Schlüssel nur für den Deploy |
| `SSH_KNOWN_HOSTS` | **Secret** | – (Pflicht) | Fingerabdruck des Servers (schützt vor falschem Server) |
| `FRONTEND_PORT` | Variable | `8080` | öffentlicher Port der Website |
| `BACKEND_PORT` | Variable | `8181` | Port des Backends (nginx, Healthcheck und `npm run dev` nutzen denselben Wert) |
| `BACKEND_BIND` | Variable | `127.0.0.1` | `127.0.0.1` = Backend-Port nur auf dem Server selbst; `0.0.0.0` = von außen erreichbar |
| `DEPLOY_PATH` | Variable | `/opt/doppelkopf` | Zielordner auf dem Server |
| `SSH_PORT` | Variable | `22` | SSH-Port des Servers |
| `CORS_ORIGINS` | Variable | `*` | erlaubte Browser-Ursprünge (hinter dem Proxy `*` lassen) |
| `COMPOSE_PROJECT_NAME` | Variable | `doppelkopf` | bestimmt den Namen des Daten-Volumes (`<name>_doppelkopf-data`) |

> **Läuft schon eine Installation?** Dann trage bei `COMPOSE_PROJECT_NAME` den bisherigen Projektnamen ein
> (`docker volume ls` zeigt `<name>_doppelkopf-data`), sonst startet die Datenbank leer.

## Was GitHub ignorieren soll (`.gitignore`, liegt bei)

- **Geheimnisse:** `.env`, `.env.*` (außer `.env.example`), `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `deploy_key*`
- **Daten:** `backend/instance/`, `*.sqlite`, `*.sqlite3`, `*.db` (Spielernamen, Vorschläge, Statistik)
- **Erzeugtes:** `node_modules/`, `dist/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.venv/`, `test-results/`, `playwright-report/`, `*.log`, `*.zip`
- **Persönliches:** `.vscode/`, `.idea/`, `.DS_Store`, `.claude/`

Committen solltest du `package-lock.json` (einmal `npm install` lokal ausführen). Der Build nutzt dann `npm ci` und bleibt reproduzierbar.

## 1. Server vorbereiten (einmalig)

Voraussetzungen: Linux-Server mit **Docker + Compose-Plugin**, `rsync` und `curl`.

```bash
# Benutzer für den Deploy (Beispiel Debian/Ubuntu)
sudo adduser --disabled-password deploy
sudo usermod -aG docker deploy           # darf Docker bedienen
sudo mkdir -p /opt/doppelkopf && sudo chown deploy:deploy /opt/doppelkopf
sudo apt install -y rsync curl
```

## 2. SSH-Schlüssel nur für den Deploy

Auf deinem Rechner (nicht auf dem Server):

```bash
ssh-keygen -t ed25519 -f deploy_key -C "github-actions-deploy" -N ""
ssh-copy-id -i deploy_key.pub deploy@DEINE-SERVER-ADRESSE        # oder .pub-Inhalt in ~deploy/.ssh/authorized_keys
ssh-keyscan -p 22 DEINE-SERVER-ADRESSE > known_hosts_server       # Fingerabdruck des Servers
ssh-keygen -lf known_hosts_server                                 # mit dem Fingerabdruck auf dem Server vergleichen
```

Der **Inhalt** von `deploy_key` wird das Secret `SSH_PRIVATE_KEY`, der von `known_hosts_server` das Secret `SSH_KNOWN_HOSTS`.
Danach `deploy_key`, `deploy_key.pub` und `known_hosts_server` lokal löschen (sie stehen auch in der `.gitignore`).

## 3. GitHub einrichten

1. Repository auf GitHub anlegen und das Projekt hochladen (`git init`, `git add .`, `git commit`, `git push`). Prüfe vorher mit `git status`, dass keine `.env` dabei ist.
2. **Settings → Environments → New environment → `production`.** Dort optional „Required reviewers“ einschalten, dann wartet jeder Deploy auf deine Freigabe.
3. In diesem Environment (oder unter **Settings → Secrets and variables → Actions**) die **Secrets** aus der Tabelle anlegen und bei Bedarf die **Variablen** (`FRONTEND_PORT`, `BACKEND_PORT`, …). Nicht gesetzte Variablen nehmen den Standardwert.
4. **Actions → Deploy → Run workflow** startet den ersten Deploy. Danach läuft er bei jedem Push auf `main`.

Der Ablauf von `deploy.yml`: Tests → Eingaben prüfen → SSH → Dateien per `rsync` nach `DEPLOY_PATH` → `.env` (Rechte 600) schreiben →
`docker compose up -d --build --wait` → Gesundheitstest `/api/health` → alte Images löschen.

## Betrieb

```bash
cd /opt/doppelkopf
docker compose ps                         # Zustand
docker compose logs -f --tail=100         # Protokolle
docker compose restart backend            # Neustart
```

**Sicherung der Datenbank** (Tische, Vorschläge, Sprüche, Statistik liegen im Volume):

```bash
docker run --rm -v doppelkopf_doppelkopf-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/doko-$(date +%F).tgz -C /data .
```

**Zurückrollen:** auf GitHub den letzten guten Commit wiederherstellen (`git revert`) und pushen – der Deploy baut den alten Stand neu. Die Daten bleiben im Volume.

## HTTPS und Proxy

Die Website lauscht auf `FRONTEND_PORT` ohne HTTPS. Für HTTPS setzt du einen Proxy auf dem Server davor, z. B. Caddy:

```
doko.example.de {
    reverse_proxy 127.0.0.1:8080
}
```

`deploy/nginx.conf` übernimmt dann die Besucheradresse aus `X-Forwarded-For`, wenn der Proxy im Docker-Netz (172.16.0.0/12) ankommt.
Liegt dein Proxy in einem anderen Adressbereich, passe `set_real_ip_from` in der Datei an – sonst gelten die Begrenzungen
(Vorschläge, Admin-Login) für alle Besucher gemeinsam.

## Fehlersuche

| Meldung | Ursache |
|---|---|
| `Secret … fehlt` | Secret nicht (oder im falschen Environment) angelegt |
| `Host key verification failed` | `SSH_KNOWN_HOSTS` passt nicht zu `SSH_HOST`/`SSH_PORT` |
| `permission denied … docker.sock` | Deploy-Benutzer nicht in der Gruppe `docker` |
| `rsync: command not found` | `rsync` auf dem Server installieren |
| `required variable SECRET_KEY is missing` | `.env` fehlt/leer (nur lokal; im Deploy schreibt der Workflow sie) |
| Tisch zeigt dauerhaft „Offline“ | `CORS_ORIGINS` nicht `*` hinter einem Proxy, oder Proxy leitet `/socket.io/` nicht mit Websocket-Upgrade weiter |
