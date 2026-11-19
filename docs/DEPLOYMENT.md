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
| `scripts/smoke-test.sh` | prüft nach dem Start (CI und Deploy) Seiten, 404-Status, noindex, robots.txt, sitemap.xml, Cache und gzip |
| `scripts/seo-build.mjs` | erzeugt beim Build je Seite eine HTML-Datei sowie `robots.txt` und `sitemap.xml` (Domain aus `SITE_URL`) |
| `deploy/legal.example.json` | Beispiel für die Betreiberangaben (Impressum/Datenschutz) |

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
| `SITE_URL` | Variable | `https://doppelkopf.cc` | Domain der Website, mit `https://`, ohne `/` am Ende. Daraus entstehen canonical-Links, `sitemap.xml`, `robots.txt` und die Link-Vorschau |
| `LEGAL_NAME` | Variable | – | Impressum: Vor- und Nachname (bzw. Firma). **Pflicht**, sobald eine der `LEGAL_*`-Pflichtangaben gesetzt ist |
| `LEGAL_STREET` | Variable | – | Impressum: Straße und Hausnummer (**Pflicht**, kein Postfach) |
| `LEGAL_CITY` | Variable | – | Impressum: PLZ und Ort, z. B. `50667 Köln` (**Pflicht**) |
| `LEGAL_EMAIL` | Variable | – | Impressum und Datenschutz: E-Mail-Adresse (**Pflicht**) |
| `LEGAL_COUNTRY` | Variable | `Deutschland` | Land der Anschrift |
| `LEGAL_PHONE` | Variable | leer | Telefonnummer (empfohlen als zweiter Kontaktweg, siehe unten) |
| `LEGAL_VAT_ID` | Variable | leer | Umsatzsteuer-ID, nur falls vorhanden |
| `LEGAL_HOSTING_PROVIDER` | Variable | leer | Datenschutz: Hosting-Anbieter, z. B. `Hetzner` |
| `LEGAL_HOSTING_REGION` | Variable | leer | Datenschutz: Standort des Servers, z. B. `Frankfurt am Main, Deutschland` (Region deiner Oracle-Instanz) |
| `LEGAL_REGISTRAR` | Variable | leer | Datenschutz: Domain-Registrar, z. B. `GoDaddy` |

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

Der Ablauf von `deploy.yml`: Tests (Frontend, Backend, Start des ganzen Stacks mit Smoke-Test) → Eingaben prüfen → SSH → Dateien per `rsync` nach
`DEPLOY_PATH` → `.env` (Rechte 600) schreiben → `legal/legal.json` aus den `LEGAL_*`-Variablen schreiben →
`docker compose up -d --build --wait` → Gesundheitstest `/api/health` → Smoke-Test der Seiten (`scripts/smoke-test.sh`) → alte Images löschen.

## Impressum und Datenschutzerklärung (Betreiberangaben)

**Warum nicht im Code?** Wer das Projekt von GitHub herunterlädt, soll nicht dein Impressum (Name und Anschrift) bekommen, und dein
Name und deine Adresse sollen nicht öffentlich im Repository stehen. Deshalb ist der Aufbau so:

| Was | Wo es steht | Wer es pflegt |
|---|---|---|
| **Texte** von Impressum und Datenschutzerklärung | im Repository (`src/pages/Legal.svelte`). Sie beschreiben, was die *Software* tut (Cookies, Speicherung, Protokolle, Vorschläge) | gehört zum Code; ändert sich nur, wenn sich die Software ändert |
| **Betreiberangaben** (Name, Anschrift, E-Mail, Hoster, Registrar) | **nur** in deinen GitHub-**Variablen** `LEGAL_*`. Der Deploy macht daraus die Datei `legal/legal.json` auf dem Server | jeder Betreiber für seine eigene Installation |

Der Ablauf bei jedem Deploy: GitHub Actions liest die `LEGAL_*`-Variablen, erzeugt mit `jq` die Datei `$DEPLOY_PATH/legal/legal.json`
und legt sie auf den Server. nginx liefert sie unter `/legal/legal.json` aus, die Seiten Impressum und Datenschutz laden sie beim Aufruf.
Die Datei ist nicht im Git, nicht im Docker-Image und wird beim Hochladen (`rsync --delete`) nicht gelöscht.
Eine Änderung der Angaben braucht nur eine geänderte Variable und einen neuen Deploy (Actions → Deploy → Run workflow), kein neues Bauen.

**Wer das Projekt forkt oder herunterlädt**, bekommt die Texte, aber keine Angaben. Er legt eigene Variablen an. Ohne sie zeigen die Seiten
deutlich markierte **Testdaten** („Max Mustermann“), und der Deploy gibt eine Warnung aus. Damit steht nie versehentlich ein fremdes
Impressum auf einer Seite. Die Datenschutzerklärung muss ein Betreiber mit anderem Hosting oder anderen Funktionen selbst prüfen und
gegebenenfalls in `Legal.svelte` anpassen.

**Variablen anlegen:** Settings → Environments → `production` → *Environment variables* (oder Settings → Secrets and variables → Actions →
*Variables*). Mindestens `LEGAL_NAME`, `LEGAL_STREET`, `LEGAL_CITY`, `LEGAL_EMAIL`. Fehlt eine davon, während andere gesetzt sind,
bricht der Deploy mit einer Fehlermeldung ab.

Für die Angaben in deinem Fall:

| Variable | Beispielwert |
|---|---|
| `LEGAL_HOSTING_PROVIDER` | `Oracle Cloud Infrastructure` |
| `LEGAL_HOSTING_REGION` | die Region deiner Instanz, z. B. `Frankfurt am Main, Deutschland` (in der Oracle-Konsole unter *Region* sichtbar) |
| `LEGAL_REGISTRAR` | `GoDaddy` |

Lokal ausprobieren: `deploy/legal.example.json` nach `legal/legal.json` (Docker) bzw. `public/legal/legal.json` (`npm run dev`) kopieren
und anpassen. Beide Ordner sind in der `.gitignore`.

**Vor dem Livegang prüfen (kein Rechtsrat):**
- **Impressum:** Name, ladungsfähige Anschrift (kein Postfach) und E-Mail sind Pflicht (§ 5 DDG). Viele Stellen empfehlen zusätzlich eine
  Telefonnummer oder ein anderes direktes Kommunikationsmittel. Ob ein rein privates Angebot überhaupt impressumspflichtig ist, hängt
  vom Einzelfall ab; im Zweifel ein Impressum führen.
- **Hosting-Vertrag:** Die Datenschutzerklärung sagt, dass mit dem Hoster ein Vertrag zur Auftragsverarbeitung (Art. 28 DSGVO) besteht. Bei
  Oracle ist die Auftragsverarbeitung Teil der Cloud-Vereinbarung; prüfe in deinem Konto, dass sie gilt, und wähle eine EU-Region.
- **Fehlt etwas, das du nutzt** (zum Beispiel Statistik- oder Fehlerdienste, die du später ergänzt), muss der Text erweitert werden.
- Texte, die du für verbindlich hältst, lässt du am besten von einer fachkundigen Stelle prüfen.

## Domain, HTTPS und Suchmaschinen

**1. DNS bei GoDaddy** (Domain → *DNS verwalten*): `A`-Eintrag `@` auf die öffentliche IP deines Oracle-Servers, `CNAME`-Eintrag `www`
auf `@`. Änderungen brauchen bis zu einigen Stunden.

**2. Ports in Oracle Cloud öffnen:** Im Netzwerk (VCN) der Instanz in der *Security List* bzw. Netzwerksicherheitsgruppe Eingangsregeln
für TCP **80** und **443** aus `0.0.0.0/0` anlegen. Bei Ubuntu-Images von Oracle blockiert zusätzlich die Firewall auf dem Server; dort
`sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT` und dasselbe für `443` ausführen und mit
`sudo netfilter-persistent save` dauerhaft speichern.

**3. HTTPS mit Caddy** (holt Zertifikate selbst, leitet `http` auf `https` um und reicht WebSockets durch). `/etc/caddy/Caddyfile`:

```
doppelkopf.cc {
    reverse_proxy 127.0.0.1:8080
    header Strict-Transport-Security "max-age=31536000"
}

www.doppelkopf.cc {
    redir https://doppelkopf.cc{uri} permanent
}
```

Die Weiterleitung von `www` auf die Hauptadresse ist wichtig: Suchmaschinen sollen nur **eine** Adresse sehen (`SITE_URL`).
Den `Strict-Transport-Security`-Header erst eintragen, wenn HTTPS sicher läuft. Caddy schreibt standardmäßig keine Zugriffsprotokolle.
Nutzt du stattdessen einen anderen Proxy, schalte dessen Zugriffsprotokoll mit vollen IP-Adressen ab oder kürze die Adressen, damit die
Datenschutzerklärung stimmt.

**4. `SITE_URL`** als GitHub-Variable setzen (Standard ist `https://doppelkopf.cc`) und neu deployen.

**5. Google und Bing anmelden** (einmalig):
- [Google Search Console](https://search.google.com/search-console): Property-Typ *Domain* wählen, den angezeigten `TXT`-Eintrag bei GoDaddy anlegen,
  dann *Sitemaps* → `https://doppelkopf.cc/sitemap.xml` einreichen. Mit *URL-Prüfung* die Adressen `/` und `/regeln` testen und
  *Indexierung beantragen*.
- [Bing Webmaster Tools](https://www.bing.com/webmasters): Seite aus der Search Console importieren. Bing speist auch DuckDuckGo und andere.
- Prüfen, ob die Link-Vorschau stimmt: Adresse in einen Messenger einfügen. Das Bild liegt in `public/og-image.png` (Quelle `og-image.svg`).

**Was die Seite für Suchmaschinen schon mitbringt:** je Seite eigener Titel, Beschreibung und canonical-Adresse; Klartext-Inhalt auch ohne JavaScript;
die Regeln-Seite `/regeln` als inhaltliche Einstiegsseite; `robots.txt` und `sitemap.xml` (nur Startseite und Regeln); `noindex` für Tisch,
Beitreten, Admin, Impressum und Datenschutz; echter Statuscode 404 für unbekannte Adressen; schema.org-Angaben (WebSite, WebApplication);
Favicon in allen Größen, Manifest, gzip und langes Caching der Dateien. Bis eine neue Seite in den Ergebnissen erscheint, vergehen
erfahrungsgemäß Tage bis Wochen. Wie weit oben sie steht, hängt dann von Inhalt und Verlinkung ab: ein Link von der GitHub-Projektseite
(Feld *Website*) und aus Foren hilft.

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
| `SITE_URL muss mit https:// beginnen …` | Variable mit Pfad, Schrägstrich am Ende oder ohne `https://` |
| `Impressum unvollständig, es fehlen die Variablen …` | `LEGAL_NAME`, `LEGAL_STREET`, `LEGAL_CITY`, `LEGAL_EMAIL`: alle oder keine setzen |
| Impressum zeigt „TESTDATEN“ | `LEGAL_*`-Variablen nicht gesetzt (oder im falschen Environment), oder `legal/legal.json` fehlt auf dem Server |
| Smoke-Test: `… liefert 404 statt 200` | Seite im Router, aber nicht in `deploy/nginx.conf` eingetragen (oder Build ohne `scripts/seo-build.mjs`) |
| Tisch zeigt dauerhaft „Offline“ | `CORS_ORIGINS` nicht `*` hinter einem Proxy, oder Proxy leitet `/socket.io/` nicht mit Websocket-Upgrade weiter |
