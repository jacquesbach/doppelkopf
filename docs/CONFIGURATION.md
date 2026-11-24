# Konfiguration

Alle Einstellungen eines Betreibers stehen an **einer** Stelle: in der Datei `.env` im Projektordner. Docker Compose liest sie
automatisch. Vorlage mit Erklärungen: [`.env.example`](../.env.example).

- **Lokal und bei Weg A** (von Hand) legst du die `.env` selbst an: `cp .env.example .env`.
- **Bei Weg B** (GitHub Actions) schreibt der Deploy die `.env` bei jedem Lauf neu auf den Server, aus den GitHub-Secrets und -Variablen
  (Tabelle unten). Änderungen an der `.env` auf dem Server selbst gehen dann beim nächsten Deploy verloren.
- Die `.env` enthält Geheimnisse und kommt nie ins Git (`.gitignore`).

Dieses Dokument listet alle Einstellungen. Wie du sie setzt, steht in [DEPLOYMENT.md](DEPLOYMENT.md).

## 1. Einstellungen in der `.env`

| Name | Pflicht | Standard | Wirkt bei | Bedeutung |
|---|---|---|---|---|
| `SECRET_KEY` | **ja** | – | Start | Geheimer Schlüssel, mindestens 32 Zeichen. Erzeugen: `python3 -c "import secrets; print(secrets.token_hex(32))"`. Signiert Captcha und Betreiber-Anmeldung, berechnet die Platz-Codes und pseudonymisiert die Daumen-Kennungen. Ohne Wert startet `docker compose` nicht. Siehe [Schlüssel wechseln](#schlüssel-wechseln). |
| `ADMIN_PASSWORD` | nein | leer | Start | Passwort für das Betreiber-Backend `/admin`. **Leer = Backend abgeschaltet.** Mit `APP_ENV=production` mindestens 10 Zeichen, sonst startet das Backend nicht. |
| `APP_ENV` | nein | `production` | Start | `production` verlangt einen gesetzten `SECRET_KEY` und die Mindestlänge des Admin-Passworts. Lokal ohne Docker nicht setzen. |
| `SITE_URL` | empfohlen | `https://doppelkopf.cc` | **Build** | Adresse der Website mit `https://`, ohne Pfad und ohne `/` am Ende. Daraus entstehen canonical-Links, `sitemap.xml`, `robots.txt` und die Link-Vorschau. Ändern erfordert einen neuen Build (`docker compose up -d --build`). |
| `FRONTEND_PORT` | nein | `8080` | Start | Port der Website auf dem Server. Der nginx-Container hört intern immer auf 80. |
| `BACKEND_PORT` | nein | `8181` | Start | Port des Backends. nginx, Healthcheck und der Vite-Entwicklungsproxy nutzen denselben Wert. |
| `BACKEND_BIND` | nein | `127.0.0.1` | Start | Adresse, auf der der Server den Backend-Port öffnet. `127.0.0.1` = nur der Server selbst (empfohlen, Besucher gehen über das Frontend). `0.0.0.0` = von außen erreichbar. |
| `CORS_ORIGINS` | nein | `*` | Start | Erlaubte Browser-Ursprünge, durch Komma getrennt. Hinter dem nginx-Proxy `*` lassen: Socket.IO prüft den Ursprung strikt, sonst zeigt der Tisch dauerhaft „Offline“. Die Sicherheit hängt am Sitzungs-Token, nicht an Cookies. |
| `CREATE_PER_HOUR` | nein | `30` | Start | Wie viele neue Tische eine Besucheradresse pro Stunde anlegen darf. |
| `VITE_API_BASE_URL` | nein | `/api` | **Build** | Basis-URL der API, die das Frontend einliest. `/api` = gleicher Ursprung (nginx bzw. Vite-Proxy). Nur ändern, wenn das Backend woanders liegt. |
| `COMPOSE_PROJECT_NAME` | nein | `doppelkopf` | Start | Name des Docker-Projekts. Bestimmt den Namen des Daten-Volumes `<name>_doppelkopf-data`. **Bei einer laufenden Installation nicht ändern**, sonst startet die Datenbank leer (siehe unten). |
| `APP_VERSION` | nein | leer | Start | Anzeige im Systemstatus des Betreiber-Backends. Beim Deploy setzt die Action den Git-Stand (7 Zeichen). Von Hand: z. B. `git rev-parse --short HEAD`. |
| `DEPLOYED_AT` | nein | leer | Start | Zeitpunkt der Installation (UTC, ISO-Format) für den Systemstatus. Beim Deploy automatisch. |

„Wirkt bei **Build**“ heißt: Der Wert wird beim Bauen des Frontend-Images in die Dateien eingesetzt. Nach einer Änderung brauchst du
`docker compose up -d --build`. Alle anderen Werte lesen die Container beim Start (`docker compose up -d` genügt).

### Was Docker Compose zusätzlich setzt

Diese Werte stehen in `docker-compose.yml` und sind keine Einstellungen für dich:

| Name | Wert | Zweck |
|---|---|---|
| `DATABASE_URL` | `sqlite:////data/doppelkopf.sqlite3` | Datenbankdatei im Volume `doppelkopf-data` |
| `TRUST_PROXY` | `1` | Das Backend nimmt für Begrenzungen die letzte Adresse aus `X-Forwarded-For` (nginx setzt sie) |
| `NGINX_ENVSUBST_FILTER` | `BACKEND_PORT` | nginx setzt nur diese Variable in die Konfigurationsvorlage ein |

### Schlüssel wechseln

Wenn du `SECRET_KEY` änderst, passiert Folgendes (Spielstände und Tische bleiben erhalten):

- Alle Betreiber werden abgemeldet.
- Offene Captchas werden ungültig.
- **Alle Platz-Codes ändern sich.** Spieler, die ihren Platz auf einem anderen Gerät zurückholen wollten, brauchen den neuen Code.
- Daumen bei Verbesserungsvorschlägen werden anders pseudonymisiert. Wer vorher abgestimmt hat, kann erneut abstimmen.

### Daten-Volume und Projektname

Die Datenbank liegt im Docker-Volume `<COMPOSE_PROJECT_NAME>_doppelkopf-data`. Mit `docker volume ls` siehst du es. Ändert sich der
Projektname (oder der Ordnername, wenn die Variable fehlt), legt Compose ein neues, leeres Volume an. Die alten Daten sind nicht weg,
aber nicht mehr eingebunden. Darum bei einer bestehenden Installation den bisherigen Namen eintragen.

## 2. Backend ohne Docker (`python run.py`)

`backend/run.py` liest diese Umgebungsvariablen. Ohne sie läuft das Backend im Entwicklungsmodus.

| Name | Standard | Bedeutung |
|---|---|---|
| `SECRET_KEY` | `dev-only-change-me` | Mit `APP_ENV=production` Pflicht (das Backend startet sonst nicht). |
| `DATABASE_URL` | `sqlite:///doppelkopf.sqlite3` | Relativ zum Ordner `backend/instance/`. |
| `CORS_ORIGINS` | `http://localhost:5173` | Kommagetrennt, `*` erlaubt alle. |
| `ADMIN_PASSWORD` | leer | Leer = `/admin` aus. |
| `TRUST_PROXY` | aus | `1` = Besucheradresse aus `X-Forwarded-For` (nur hinter einem vertrauenswürdigen Proxy). |
| `CREATE_PER_HOUR` | `30` | Neue Tische je Adresse und Stunde. |
| `BACKEND_PORT` (oder `PORT`) | `8181` | Port. |
| `FLASK_DEBUG` | aus | `1` schaltet den Debugger ein. Nie auf einem Server. |
| `APP_VERSION`, `DEPLOYED_AT` | leer | Anzeige im Systemstatus. |

Für das Frontend im Entwicklungsmodus (`npm run dev`) liest Vite zusätzlich `BACKEND_PORT` und `SITE_URL` aus der Umgebung oder
aus der `.env` im Projektordner.

## 3. GitHub-Secrets und -Variablen (Weg B)

Anlegen unter *Settings → Environments → production* (oder *Settings → Secrets and variables → Actions*). **Secrets** sind verschlüsselt
und nach dem Speichern nicht mehr lesbar, **Variablen** sind sichtbar. Nicht gesetzte Variablen nehmen den Standardwert.

### Secrets

| Name | Pflicht | Bedeutung |
|---|---|---|
| `SSH_HOST` | ja | Adresse deines Servers (Domain oder IP). |
| `SSH_USER` | ja | Benutzer für den Deploy. Er muss Docker bedienen dürfen (Gruppe `docker`). |
| `SSH_PRIVATE_KEY` | ja | Inhalt des privaten Schlüssels, der nur für den Deploy gedacht ist. |
| `SSH_KNOWN_HOSTS` | ja | Fingerabdruck deines Servers (Ausgabe von `ssh-keyscan`). Schützt vor einem falschen Server. |
| `SECRET_KEY` | ja | Siehe oben. Mindestens 32 Zeichen, kein `'` und kein Zeilenumbruch. |
| `ADMIN_PASSWORD` | nein | Siehe oben. Mindestens 10 Zeichen, kein `'` und kein Zeilenumbruch. Leer = Admin-Backend aus. |

### Variablen

| Name | Standard | Bedeutung |
|---|---|---|
| `SSH_PORT` | `22` | SSH-Port des Servers. |
| `DEPLOY_PATH` | `/opt/doppelkopf` | Zielordner auf dem Server. Absoluter Pfad, nur `A-Z a-z 0-9 . _ / -`. |
| `FRONTEND_PORT` | `8080` | Siehe oben (nur Ziffern). |
| `BACKEND_PORT` | `8181` | Siehe oben (nur Ziffern). |
| `BACKEND_BIND` | `127.0.0.1` | Siehe oben. |
| `CORS_ORIGINS` | `*` | Siehe oben. |
| `CREATE_PER_HOUR` | `30` | Siehe oben (nur Ziffern). |
| `COMPOSE_PROJECT_NAME` | `doppelkopf` | Siehe oben. |
| `SITE_URL` | `https://doppelkopf.cc` | Siehe oben. Der Deploy bricht ab, wenn der Wert nicht mit `https://` beginnt oder einen Pfad hat. |
| `LEGAL_NAME` | – | Impressum: Vor- und Nachname (bzw. Firma). |
| `LEGAL_STREET` | – | Impressum: Straße und Hausnummer (kein Postfach). |
| `LEGAL_CITY` | – | Impressum: PLZ und Ort, z. B. `50667 Köln`. |
| `LEGAL_EMAIL` | – | Impressum und Datenschutz: E-Mail-Adresse. |
| `LEGAL_COUNTRY` | `Deutschland` | Land der Anschrift. |
| `LEGAL_PHONE` | leer | Telefonnummer (empfohlen als zweiter Kontaktweg). |
| `LEGAL_VAT_ID` | leer | Umsatzsteuer-ID, nur falls vorhanden. |
| `LEGAL_HOSTING_PROVIDER` | leer | Datenschutz: Hosting-Anbieter. |
| `LEGAL_HOSTING_REGION` | leer | Datenschutz: Standort des Servers, z. B. `Frankfurt am Main, Deutschland`. |
| `LEGAL_REGISTRAR` | leer | Datenschutz: Domain-Registrar. |

`LEGAL_NAME`, `LEGAL_STREET`, `LEGAL_CITY` und `LEGAL_EMAIL` gehören zusammen: Entweder setzt du alle vier oder keine. Sind nur einige
gesetzt, bricht der Deploy ab. Sind keine gesetzt, zeigen Impressum und Datenschutzerklärung markierte Testdaten.

Der Deploy schreibt daraus die `.env` (siehe Tabelle 1) und die Datei `legal/legal.json`.

## 4. Betreiberangaben (`legal/legal.json`)

Name, Anschrift und E-Mail des Betreibers stehen bewusst **nicht im Code**, damit sie nicht öffentlich im Repository liegen und jeder Betreiber
seine eigenen Angaben einträgt. Sie stehen in der Datei `legal/legal.json` im Projektordner auf dem Server. nginx liefert sie unter
`/legal/legal.json` aus, die Seiten Impressum und Datenschutz laden sie beim Aufruf. Die Datei ist nicht im Git und nicht im Docker-Image.

Aufbau (Vorlage: [`deploy/legal.example.json`](../deploy/legal.example.json)):

```json
{
  "name": "Max Mustermann",
  "street": "Musterstraße 1",
  "city": "12345 Musterstadt",
  "country": "Deutschland",
  "email": "kontakt@example.com",
  "phone": "+49 123 4567890",
  "vatId": "",
  "hostingProvider": "Musterprovider",
  "hostingRegion": "Musterstadt",
  "registrar": "Musterregistrar"
}
```

- **Weg A:** Du legst die Datei selbst an (`legal/legal.json`).
- **Weg B:** Die Action erzeugt sie aus den `LEGAL_*`-Variablen. Eine Änderung braucht nur eine geänderte Variable und einen neuen Deploy.
- **Lokal mit `npm run dev`:** Datei nach `public/legal/legal.json` kopieren (liegt in der `.gitignore`).
- Fehlt die Datei, zeigen die Seiten deutlich markierte Testdaten („Max Mustermann“).

## 5. Einstellungen im Betreiber-Backend (Datenbank)

Diese Einstellungen änderst du im Browser unter `/admin` im Reiter **DESIGN**. Sie liegen in der Datenbank (Tabelle `setting`) und
überstehen Updates:

- Farben der Website (acht Farben, mit Kontrastwarnung),
- Hinweisbanner (Text bis 280 Zeichen, Art `info`/`warn`/`alert`, wegklickbar oder nicht),
- Vorgabe für den Tisch: hell oder dunkel (jeder Spieler kann am Tisch selbst umschalten),
- „Wer ist online“ (Freunde-Funktion) ein- oder ausschalten.

Die Chat-Sprüche pflegst du im Reiter **SPRÜCHE**. Die Bots stellst du im Reiter **BOTS** ein (Durchrechnen je Spielart, Ansage-Schwellen, Tempo;
Schlüssel `bot_tuning` in derselben Tabelle, siehe [OPERATIONS.md](OPERATIONS.md#bot-einstellungen)).

## 6. Fest eingebaute Werte

Diese Werte sind keine Einstellungen. Sie stehen im Code und lassen sich nur dort ändern.

| Wert | Datei |
|---|---|
| Tisch ohne Aktivität wird nach **12 Stunden** gelöscht, Prüfung alle 10 Minuten | `backend/app/housekeeping.py` |
| Bot-Übernahme nach Inaktivität: wählbar `nie`, 1, 2, 3 (Standard), 5, 10, 30 Minuten (Host), danach 30 s Countdown | `backend/app/table/state.py` |
| Tisch-Chat: letzte 100 Nachrichten je Tisch, höchstens 200 Zeichen, 0,8 s Abstand, nur im Arbeitsspeicher | `backend/app/table/chat.py` |
| Tisch-Passwort mindestens 6 Zeichen, Spielname höchstens 32 Zeichen | `backend/app/routes.py` |
| Zugangsschutz: 8 Fehlversuche je Adresse und Tisch in 10 Minuten, 20 verschiedene unbekannte Tisch-Codes je Adresse in 10 Minuten, dann Fehler 429 | `backend/app/guard.py` |
| Admin-Anmeldung: gültig 2 Stunden, höchstens 20 Sitzungen, 5 Fehlversuche je Adresse in 10 Minuten | `backend/app/community/admin_auth.py` |
| Verbesserungsvorschläge: 5 je Stunde und Adresse, 3 je Browser, Daumen 120 je Stunde, Captcha 60 je Stunde | `backend/app/community/api.py` |
| Liste „offene Tische“: nur wartende Tische mit Aktivität in den letzten 90 Sekunden, höchstens 30 | `backend/app/routes.py` |
| Fehler-Log: höchstens 300 Einträge, Löschung nach 30 Tagen. Anonyme Spielzähler: Löschung nach 400 Tagen | `backend/app/ops/` |
| Online-Status: höchstens 100 beobachtete Freunde, 6 Einladungen je Minute | `backend/app/presence.py` |
| Tempo der Bots: 1,0 bis 1,7 s je Karte, 1,7 s je Vorbehalts-Antwort, 2,4 s nach einem Stich | `backend/app/table/service.py` |
| Docker-Protokolle: 3 Dateien à 2 MB je Container | `docker-compose.yml` |
| Content-Security-Policy und Cache-Regeln | `deploy/nginx.conf` |
