# Deployment: Installation auf einem Server

Diese Anleitung bringt die Website auf einen eigenen Linux-Server, mit eigener Domain und HTTPS.
Alle Variablen erklärt [CONFIGURATION.md](CONFIGURATION.md), den laufenden Betrieb [OPERATIONS.md](OPERATIONS.md).

## Überblick

Die Anwendung besteht aus zwei Docker-Containern (`docker-compose.yml`):

| Container | Aufgabe | Port |
|---|---|---|
| `frontend` | nginx: liefert die Website aus und leitet `/api` und `/socket.io` an das Backend weiter | `FRONTEND_PORT` (Standard 8080) |
| `backend` | Flask: Spielregeln, Tische, Bots, Datenbank (SQLite im Volume `doppelkopf-data`) | `BACKEND_PORT` (Standard 8181), nur auf `127.0.0.1` |

Für den öffentlichen Betrieb kommt ein **Proxy mit HTTPS** davor (hier Caddy, der Zertifikate selbst besorgt):

```
Besucher ──▶ Caddy (80/443, HTTPS) ──▶ frontend (nginx, 8080) ──▶ backend (Flask, 8181) ──▶ SQLite-Volume
```

**Was du brauchst**

- Einen Linux-Server (getestet mit Debian/Ubuntu) mit **Docker Engine und Compose-Plugin** ([Installationsanleitung](https://docs.docker.com/engine/install/)). Ein kleiner Server genügt: Das Backend ist ein einzelner Prozess mit SQLite.
- Eine **Domain**, die auf den Server zeigt (für HTTPS).
- Für Weg B zusätzlich ein GitHub-Repository mit diesem Code (Fork oder eigene Kopie).

Es gibt zwei Wege zur Installation. Beide führen zum selben Ergebnis:

| | Weg A: von Hand | Weg B: GitHub Actions |
|---|---|---|
| Aufwand beim Einrichten | gering | höher (SSH-Schlüssel, Secrets) |
| Update | `git pull` und ein Befehl auf dem Server | automatisch bei jedem Push auf `main`, nach erfolgreichen Tests |
| Geeignet für | Ausprobieren, kleine Installationen | dauerhafter Betrieb |

---

## Weg A: Von Hand mit Docker Compose

### 1. Code auf den Server holen

```bash
sudo mkdir -p /opt/doppelkopf && sudo chown "$USER": /opt/doppelkopf
git clone https://github.com/jacquesbach/doppelkopf.git /opt/doppelkopf
cd /opt/doppelkopf
```

(Statt `git clone` geht auch ein Download des Repositorys als ZIP.)

### 2. Einstellungen anlegen (`.env`)

```bash
cp .env.example .env
python3 -c "import secrets; print(secrets.token_hex(32))"     # Ausgabe als SECRET_KEY verwenden
nano .env
```

Trage mindestens ein:

- `SECRET_KEY`: der erzeugte Wert (Pflicht, sonst startet nichts),
- `ADMIN_PASSWORD`: ein langes Passwort (mindestens 10 Zeichen) für `/admin`, oder leer lassen, dann ist das Betreiber-Backend aus,
- `SITE_URL`: deine Adresse, z. B. `https://spiel.example.de` (mit `https://`, ohne `/` am Ende).

Alle weiteren Werte haben brauchbare Standardwerte, siehe [CONFIGURATION.md](CONFIGURATION.md). Die Datei enthält Geheimnisse:

```bash
chmod 600 .env
```

### 3. Impressum und Datenschutz (Betreiberangaben)

```bash
mkdir -p legal
cp deploy/legal.example.json legal/legal.json
nano legal/legal.json
```

Trage deine Angaben ein (Hinweise im Abschnitt [Impressum und Datenschutzerklärung](#impressum-und-datenschutzerklärung)).
Ohne diese Datei läuft die Seite mit markierten Testdaten.

### 4. Starten

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8080/api/health
```

Der erste Start baut beide Images und dauert einige Minuten. `docker compose ps` zeigt am Ende beide Container als `healthy`.
Die Antwort von `/api/health` lautet `{"service":"doppelkopf-multiplayer","status":"ok"}`.

Die Seite läuft jetzt auf Port 8080 **ohne HTTPS**. Weiter geht es mit [Domain und HTTPS](#domain-und-https).

### 5. Aktualisieren

```bash
cd /opt/doppelkopf
git pull
docker compose up -d --build
```

Die Spielstände bleiben erhalten (sie liegen im Volume). Laufende Spiele werden beim Neustart des Backends kurz unterbrochen und
danach fortgesetzt. Vorher am besten eine [Sicherung](OPERATIONS.md#sicherung-und-wiederherstellung) machen und den Hinweisbanner im
Betreiber-Backend nutzen, wenn viel los ist.

---

## Weg B: Automatisch mit GitHub Actions

Jeder Push auf `main` startet die Pipeline [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml):

1. **Tests:** Frontend (Syntaxcheck, Tests, Build), Backend (Regelkern, Tischschicht, echte App) und der ganze Docker-Stack mit einem Smoke-Test.
2. **Eingaben prüfen:** Fehlende oder ungültige Secrets und Variablen brechen mit einer Fehlermeldung ab.
3. **SSH-Verbindung** zum Server (mit festem Fingerabdruck), Dateien per `rsync` nach `DEPLOY_PATH`.
4. **`.env` schreiben** (Rechte 600) aus den Secrets und Variablen. **`legal/legal.json`** aus den `LEGAL_*`-Variablen; sind keine gesetzt, wird eine vorhandene Datei auf dem Server entfernt (bei Weg B also nicht von Hand pflegen).
5. **`docker compose up -d --build --wait`**, danach Gesundheitstest `/api/health` und Smoke-Test der Seiten.
6. Alte Images aufräumen, SSH-Schlüssel entfernen.

Zwei Deploys laufen nie gleichzeitig; ein laufender wird nicht abgebrochen.

### 1. Server vorbereiten (einmalig)

Benutzer für den Deploy anlegen (Beispiel Debian/Ubuntu):

```bash
sudo adduser --disabled-password deploy
sudo usermod -aG docker deploy                       # darf Docker bedienen
sudo mkdir -p /opt/doppelkopf && sudo chown deploy:deploy /opt/doppelkopf
sudo apt install -y rsync curl                       # beides braucht der Deploy auf dem Server
```

Docker Engine mit Compose-Plugin muss installiert sein (siehe oben).

### 2. SSH-Schlüssel nur für den Deploy

Auf **deinem Rechner** (nicht auf dem Server):

```bash
ssh-keygen -t ed25519 -f deploy_key -C "github-actions-deploy" -N ""
ssh-copy-id -i deploy_key.pub deploy@DEINE-SERVER-ADRESSE     # oder den Inhalt von deploy_key.pub in ~deploy/.ssh/authorized_keys
ssh-keyscan -p 22 DEINE-SERVER-ADRESSE > known_hosts    # Fingerabdruck des Servers
ssh-keygen -lf known_hosts                              # mit dem Fingerabdruck auf dem Server vergleichen
```

Der **Inhalt** von `deploy_key` wird das Secret `SSH_PRIVATE_KEY`, der Inhalt von `known_hosts` das Secret `SSH_KNOWN_HOSTS`.
Danach `deploy_key`, `deploy_key.pub` und `known_hosts` lokal löschen (sie stehen auch in der `.gitignore`).

### 3. GitHub einrichten

1. Repository auf GitHub anlegen und den Code hochladen (`git init`, `git add .`, `git commit`, `git push`). Prüfe vorher mit `git status`, dass keine `.env` dabei ist.
   Führe einmal `npm install` aus und committe die entstehende `package-lock.json`: Damit baut Docker mit `npm ci` reproduzierbar.
2. **Settings → Environments → New environment → `production`.** Dort kannst du „Required reviewers“ einschalten, dann wartet jeder Deploy auf deine Freigabe.
3. In diesem Environment (oder unter *Settings → Secrets and variables → Actions*) die **Secrets** und die nötigen **Variablen** anlegen.
   Die vollständige Liste mit Standardwerten steht in [CONFIGURATION.md](CONFIGURATION.md#3-github-secrets-und--variablen-weg-b).
   Mindestens nötig: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `SSH_KNOWN_HOSTS`, `SECRET_KEY` und für den öffentlichen Betrieb `SITE_URL` und die `LEGAL_*`-Variablen.
4. **Actions → Deploy → Run workflow** startet den ersten Deploy. Danach läuft er bei jedem Push auf `main`.

Pull Requests lösen nur die Tests aus (`build-and-test.yml`), keinen Deploy.

Bei Fehlern zeigt das Protokoll des Laufs die Ursache. Häufige Fälle stehen unter [Fehlersuche](#fehlersuche).

---

## Domain und HTTPS

Die Website lauscht auf `FRONTEND_PORT` ohne HTTPS. Für den öffentlichen Betrieb brauchst du eine Domain und einen Proxy mit Zertifikat.

### DNS

Beim Domain-Anbieter einen `A`-Eintrag (und bei IPv6 einen `AAAA`-Eintrag) für `@` auf die öffentliche IP des Servers anlegen und
einen `CNAME`-Eintrag `www` auf `@`. Änderungen brauchen bis zu einigen Stunden.

### Ports und Firewall

- Öffne in der Firewall deines Anbieters (Security List, Security Group, Cloud-Firewall) nur **22** (SSH), **80** und **443**.
- `FRONTEND_PORT` (8080) und `BACKEND_PORT` (8181) sollen von außen **nicht** erreichbar sein. Das Backend ist standardmäßig nur auf `127.0.0.1` offen (`BACKEND_BIND`).
- **Achtung:** Docker setzt eigene Firewall-Regeln und umgeht dabei Programme wie `ufw`. Ein von Docker veröffentlichter Port ist deshalb auch dann erreichbar, wenn `ufw` ihn sperrt. Verlasse dich auf die Firewall des Anbieters.
- Beispiel Oracle Cloud: In der *Security List* bzw. Netzwerksicherheitsgruppe Eingangsregeln für TCP 80 und 443 aus `0.0.0.0/0` anlegen. Bei den Ubuntu-Images von Oracle blockiert zusätzlich die Firewall auf dem Server: `sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT`, dasselbe für `443`, dann `sudo netfilter-persistent save`.

### Proxy mit HTTPS: Caddy

[Caddy](https://caddyserver.com/docs/install) besorgt und erneuert Zertifikate selbst, leitet `http` auf `https` um und reicht WebSockets durch.
`/etc/caddy/Caddyfile`:

```
doppelkopf.example.de {
    reverse_proxy 127.0.0.1:8080
    header Strict-Transport-Security "max-age=31536000"
}

www.doppelkopf.example.de {
    redir https://doppelkopf.example.de{uri} permanent
}
```

Danach `sudo systemctl reload caddy`. Hinweise:

- Die Weiterleitung von `www` auf die Hauptadresse ist wichtig: Suchmaschinen sollen nur **eine** Adresse sehen (`SITE_URL`).
- Den `Strict-Transport-Security`-Header erst eintragen, wenn HTTPS sicher läuft.
- Caddy schreibt standardmäßig keine Zugriffsprotokolle. Nutzt du einen anderen Proxy, schalte dessen Zugriffsprotokoll mit vollen IP-Adressen
  ab oder kürze die Adressen, sonst stimmt die Datenschutzerklärung nicht (Abschnitt 2).
- **Andere Proxys** (nginx, Traefik …) müssen WebSocket-Verbindungen für `/socket.io/` durchreichen (`Upgrade`/`Connection`-Header)
  und die Besucheradresse in `X-Forwarded-For` setzen.
- `deploy/nginx.conf` übernimmt die Besucheradresse aus `X-Forwarded-For`, wenn der Proxy aus einem privaten Docker-Netz (`172.16.0.0/12`)
  ankommt. Liegt dein Proxy in einem anderen Adressbereich, passe `set_real_ip_from` in dieser Datei an. Sonst gelten die Begrenzungen
  (Neue Tische, Vorschläge, Admin-Anmeldung) für alle Besucher gemeinsam.

### Danach

`SITE_URL` auf die endgültige Adresse setzen (in `.env` bzw. als GitHub-Variable) und neu bauen/deployen. Die Adresse wird beim Bauen in
die Seiten eingesetzt (canonical-Links, Sitemap, Link-Vorschau).

---

## Impressum und Datenschutzerklärung

**Warum nicht im Code?** Wer das Projekt herunterlädt, soll nicht das Impressum eines anderen bekommen, und Name und Anschrift des Betreibers
sollen nicht öffentlich im Repository stehen. Deshalb gilt:

| Was | Wo es steht | Wer pflegt es |
|---|---|---|
| **Texte** von Impressum und Datenschutzerklärung | im Repository (`src/pages/Legal.svelte`). Sie beschreiben, was die *Software* tut (Speicherung, Protokolle, Vorschläge …) | gehört zum Code, ändert sich nur, wenn sich die Software ändert |
| **Betreiberangaben** (Name, Anschrift, E-Mail, Hoster, Registrar) | nur in der Datei `legal/legal.json` auf dem Server (Weg A: von Hand, Weg B: aus den `LEGAL_*`-Variablen) | jeder Betreiber für seine eigene Installation |

Die Datei und ihre Felder beschreibt [CONFIGURATION.md](CONFIGURATION.md#4-betreiberangaben-legallegaljson). Wer das Projekt forkt, bekommt die
Texte, aber keine Angaben. Ohne `legal.json` zeigen die Seiten deutlich markierte **Testdaten**, und der Deploy gibt eine Warnung aus.

**Vor dem Livegang prüfen (kein Rechtsrat):**

- **Impressum:** Name, ladungsfähige Anschrift (kein Postfach) und E-Mail sind Pflicht (§ 5 DDG). Viele Stellen empfehlen zusätzlich eine
  Telefonnummer oder einen zweiten Kontaktweg. Ob ein rein privates Angebot überhaupt impressumspflichtig ist, hängt vom Einzelfall ab.
- **Hosting-Vertrag:** Die Datenschutzerklärung sagt, dass mit dem Hoster ein Vertrag zur Auftragsverarbeitung (Art. 28 DSGVO) besteht.
  Prüfe, dass das bei deinem Anbieter zutrifft, und wähle möglichst einen Standort in der EU.
- **Eigene Änderungen:** Nutzt du etwas, das die Erklärung nicht nennt (zum Beispiel Statistik- oder Fehlerdienste, die du ergänzt),
  muss der Text erweitert werden. Siehe [PRIVACY.md](PRIVACY.md).
- Texte, die du für verbindlich hältst, lässt du am besten von einer fachkundigen Stelle prüfen.

---

## Nach dem Deploy prüfen

1. `curl http://127.0.0.1:8080/api/health` auf dem Server liefert `status: ok`.
2. Im Browser die Adresse öffnen: Startseite lädt, `/regeln`, `/impressum` und `/datenschutz` zeigen **deine** Angaben (nicht „Max Mustermann“).
3. Auf der Startseite die **Sofort-Partie gegen KI** starten und ein paar Karten spielen. In der Lobby steht „LIVE“, am Tisch erscheint kein Etikett „OFFLINE“.
4. Browser-Konsole (F12): keine Meldungen zu blockierten Ressourcen (Content-Security-Policy).
5. Mit dem Handy und einem zweiten Gerät einem Tisch beitreten.
6. `/admin` öffnen, mit `ADMIN_PASSWORD` anmelden: Reiter **SYSTEM** zeigt Version und Zeitpunkt des Deploys.
7. Optional: den Smoke-Test von Hand laufen lassen: `bash scripts/smoke-test.sh http://127.0.0.1:8080` (prüft Seiten, 404-Status, noindex, robots.txt, sitemap.xml, Cache und gzip).

## Suchmaschinen

Die Seite bringt bereits mit: je Seite eigener Titel, Beschreibung und canonical-Adresse, Klartext-Inhalt auch ohne JavaScript,
die Regeln-Seite `/regeln` als inhaltliche Einstiegsseite, `robots.txt` und `sitemap.xml` (nur Startseite und Regeln), `noindex` für
Tisch, Beitreten, Admin, Impressum und Datenschutz, echten Statuscode 404 für unbekannte Adressen, schema.org-Angaben, Favicons, Manifest,
gzip und langes Caching. Das erzeugt `scripts/seo-build.mjs` beim Build (Domain aus `SITE_URL`).

Einmalig einrichten:

- [Google Search Console](https://search.google.com/search-console): Property-Typ *Domain*, den angezeigten `TXT`-Eintrag beim DNS-Anbieter anlegen, dann
  *Sitemaps* → `https://deine-domain/sitemap.xml` einreichen. Mit *URL-Prüfung* die Adressen `/` und `/regeln` testen und die Indexierung beantragen.
- [Bing Webmaster Tools](https://www.bing.com/webmasters): Seite aus der Search Console importieren (Bing speist auch DuckDuckGo und andere).
- Link-Vorschau prüfen: Adresse in einen Messenger einfügen. Das Bild liegt in `public/og-image.png` (Quelle `og-image.svg`).

Bis eine neue Seite in den Ergebnissen erscheint, vergehen erfahrungsgemäß Tage bis Wochen. Hilfreich sind Links von anderen Seiten, etwa
von der GitHub-Projektseite (Feld *Website*) und aus Foren oder Vereinsseiten.

## Fehlersuche

| Meldung / Beobachtung | Ursache |
|---|---|
| `SECRET_KEY fehlt - in .env eintragen` | `.env` fehlt oder `SECRET_KEY` ist leer (Weg A). Bei Weg B: Secret fehlt oder liegt im falschen Environment. |
| `Secret … fehlt` im Deploy-Protokoll | Secret nicht (oder im falschen Environment) angelegt |
| `SECRET_KEY ist zu kurz` | Mindestens 32 Zeichen verwenden |
| `ADMIN_PASSWORD braucht mindestens 10 Zeichen` | Passwort verlängern oder leer lassen |
| `Host key verification failed` | `SSH_KNOWN_HOSTS` passt nicht zu `SSH_HOST`/`SSH_PORT` |
| `permission denied … docker.sock` | Deploy-Benutzer ist nicht in der Gruppe `docker` |
| `rsync: command not found` | `rsync` auf dem Server installieren |
| `SITE_URL muss mit https:// beginnen …` | Variable mit Pfad, Schrägstrich am Ende oder ohne `https://` |
| `Impressum unvollständig, es fehlen die Variablen …` | `LEGAL_NAME`, `LEGAL_STREET`, `LEGAL_CITY`, `LEGAL_EMAIL`: alle oder keine setzen |
| Impressum zeigt „TESTDATEN“ | `LEGAL_*` nicht gesetzt (oder im falschen Environment) bzw. `legal/legal.json` fehlt auf dem Server |
| Backend startet nicht, Log: `ADMIN_PASSWORD muss in Produktion mindestens 10 Zeichen …` | Passwort zu kurz |
| Backend startet nicht, Log: `In Produktion muss SECRET_KEY gesetzt sein` | `SECRET_KEY` leer |
| Tisch zeigt dauerhaft „Offline“ | `CORS_ORIGINS` ist hinter einem Proxy nicht `*`, oder der Proxy leitet `/socket.io/` nicht mit WebSocket-Upgrade weiter |
| Alle Besucher teilen sich Begrenzungen („Zu viele Tische/Versuche“) | Proxy liegt nicht im Bereich `172.16.0.0/12`: `set_real_ip_from` in `deploy/nginx.conf` anpassen |
| Nach einem Update ist die Datenbank leer | `COMPOSE_PROJECT_NAME` bzw. Ordnername hat sich geändert, das alte Volume ist nicht eingebunden (siehe [CONFIGURATION.md](CONFIGURATION.md#daten-volume-und-projektname)) |
| Smoke-Test: `… liefert 404 statt 200` | Seite ist im Router, aber nicht in `deploy/nginx.conf` eingetragen (oder der Build lief ohne `scripts/seo-build.mjs`) |
| Seite lädt, Bilder oder Schrift fehlen, Konsole nennt „Content Security Policy“ | Eine Ressource kommt nicht vom eigenen Server. `deploy/nginx.conf` (`$csp`) prüfen |
| `docker compose up` bricht beim Bauen ab | `docker compose build --no-cache` und die Fehlermeldung lesen. Häufig: kein Platz oder kein Netz auf dem Server |
