# Betrieb

Diese Anleitung beschreibt, was du tust, wenn die Seite läuft: aktualisieren, sichern, überwachen, moderieren. Die Installation steht in
[DEPLOYMENT.md](DEPLOYMENT.md), alle Einstellungen in [CONFIGURATION.md](CONFIGURATION.md).

Alle Befehle laufen im Projektordner auf dem Server (Standard `/opt/doppelkopf`).

## Alltägliche Befehle

```bash
docker compose ps                          # Zustand beider Container (healthy?)
docker compose logs -f --tail=100          # Protokolle, Strg+C beendet die Anzeige
docker compose logs backend --since 1h     # nur das Backend, letzte Stunde
docker compose restart backend             # Backend neu starten
docker compose down                        # alles stoppen (Daten bleiben erhalten)
docker compose up -d                       # wieder starten
```

**Niemals** `docker compose down -v` ausführen, wenn du die Daten behalten willst: `-v` löscht das Daten-Volume mit der Datenbank.

## Aktualisieren

- **Weg A (von Hand):** `git pull && docker compose up -d --build`.
- **Weg B (GitHub Actions):** Push auf `main`. Die Pipeline testet und aktualisiert den Server. Scheitern die Tests, wird nichts deployt und die bisherige Version bleibt in Betrieb. Scheitert erst der Start, hilft die Fehlersuche in [DEPLOYMENT.md](DEPLOYMENT.md#fehlersuche).

**Was ein Update für Spieler bedeutet:** Das Backend startet neu. Die Spielstände liegen in der Datenbank und bleiben erhalten. Offene
Browser verbinden sich automatisch neu, Bots spielen weiter, sobald jemand am Tisch ist. **Nicht erhalten bleiben** Dinge, die nur im
Arbeitsspeicher liegen: der Tisch-Chat, die Online-Status-Liste („Wer ist online“), die Betreiber-Anmeldungen und die Zähler der
Begrenzungen. Kündige Wartung deshalb an: Im Reiter DESIGN einen Hinweisbanner setzen, im Reiter LIVE eine Nachricht an laufende Tische senden.

**Zurückrollen:** Den letzten guten Stand per `git revert` (oder `git checkout <Commit>` bei Weg A) wiederherstellen und neu bauen. Die Daten bleiben im Volume.
Neue Datenbankspalten werden beim Start automatisch ergänzt; sie stören ältere Versionen nicht.

## Sicherung und Wiederherstellung

**Was gesichert werden muss**

| Was | Wo | Hinweis |
|---|---|---|
| Datenbank | Docker-Volume `<COMPOSE_PROJECT_NAME>_doppelkopf-data`, Datei `doppelkopf.sqlite3` | enthält Tische, Spielstände, Vorschläge, Sprüche, Einstellungen, Statistik |
| `.env` | Projektordner | enthält `SECRET_KEY` und Passwort. **Getrennt und geschützt** aufbewahren. Bei Weg B liegen die Werte in GitHub. |
| `legal/legal.json` | Projektordner | bei Weg B aus den `LEGAL_*`-Variablen reproduzierbar |

Der Code selbst liegt auf GitHub. Der Tisch-Chat wird nie gespeichert.

### Sicherung erstellen (laufend, ohne Stopp)

Die SQLite-Datei lässt sich im laufenden Betrieb konsistent kopieren, wenn man die eingebaute Sicherungsfunktion nutzt:

```bash
cd /opt/doppelkopf
docker compose exec -T backend python -c "
import sqlite3
src = sqlite3.connect('/data/doppelkopf.sqlite3')
dst = sqlite3.connect('/data/backup.sqlite3')
src.backup(dst); dst.close(); src.close()"
docker compose cp backend:/data/backup.sqlite3 "./doko-$(date +%F).sqlite3"
docker compose exec -T backend rm /data/backup.sqlite3
chmod 600 "./doko-$(date +%F).sqlite3"
```

Eine tägliche Sicherung per Cron (`crontab -e`, Beispiel 4:30 Uhr, behält 14 Tage):

```cron
30 4 * * * cd /opt/doppelkopf && docker compose exec -T backend python -c "import sqlite3; s=sqlite3.connect('/data/doppelkopf.sqlite3'); d=sqlite3.connect('/data/backup.sqlite3'); s.backup(d)" && docker compose cp backend:/data/backup.sqlite3 /var/backups/doko-$(date +\%F).sqlite3 && docker compose exec -T backend rm /data/backup.sqlite3 && find /var/backups -name 'doko-*.sqlite3' -mtime +14 -delete
```

**Datenschutz:** Die Datenschutzerklärung verspricht, dass Tische nach spätestens 12 Stunden Inaktivität gelöscht werden. Eine Sicherung enthält
solche Tische (Spielnamen, Spielstand) länger. Halte die Aufbewahrung deshalb kurz (einige Tage bis zwei Wochen), schütze die Dateien
(Rechte 600, verschlüsselter Speicher) und erwähne Sicherungen bei Bedarf in der Datenschutzerklärung.

### Wiederherstellen

```bash
cd /opt/doppelkopf
docker compose down
docker run --rm -v doppelkopf_doppelkopf-data:/data -v "$PWD":/backup alpine \
  sh -c "cp /backup/doko-2026-01-31.sqlite3 /data/doppelkopf.sqlite3"
docker compose up -d
```

`doppelkopf_doppelkopf-data` ist der Volume-Name (`docker volume ls` zeigt ihn); die Datei `doko-…sqlite3` ist deine Sicherung.
Danach sind alle Tische auf dem Stand der Sicherung.

## Das Betreiber-Backend (`/admin`)

Erreichbar unter `https://deine-domain/admin`. Es ist nur aktiv, wenn `ADMIN_PASSWORD` gesetzt ist. Die Anmeldung gilt **2 Stunden**.
**ABMELDEN** beendet die Sitzung auf diesem Gerät (der Server verwirft das Token), **ALLE ABMELDEN** beendet alle Sitzungen auf allen Geräten.
Nach fünf falschen Passwörtern innerhalb von 10 Minuten sperrt der Server die Adresse kurz.

| Reiter | Was du dort tust |
|---|---|
| **LIVE** | Alle Tische in Echtzeit (alle 3 s): wartend, läuft, beendet, still. Mit Spielernamen, Verbindungsstatus und Fortschritt. Je Tisch: **Zuschauen** (du erscheinst für alle sichtbar als Zuschauer „Betreiber“ und siehst keine Handkarten), **Nachricht** an alle am Tisch, **Beenden** (optional mit Nachricht; löscht den Tisch). Oben Summen: Menschen online, laufende Spiele, Tische nur mit Bots, Zuschauer. |
| **STATISTIK** | Tische gesamt, neu in 24 Std./7/30 Tagen, nur gegen Bots oder mit Menschen, nach Zahl der Menschen, Dauer und Spiele je Tisch (Durchschnitt, Median, Maximum), neue Tische je Tag. |
| **AUSWERTUNG** | Spiele pro Tag (30 Tage), nach Uhrzeit und Wochentag, Spitzenzeit, Spieldauer (Durchschnitt, Median, 90 %), Abbruchquote (Tische, die nie ein Spiel beendeten; abgebrochene Runden). Zeiten in deutscher Zeit. |
| **SYSTEM** | Version und Zeitpunkt des letzten Deploys, Laufzeit, Python-Version, Datenbankgröße und Zeilenzahlen, freier Speicherplatz, offene Verbindungen, Bot-Schleifen, Fehler der letzten 24 Stunden. Darunter das **Fehler-Log** (gleiche Fehler zusammengezählt, Stacktrace, einzeln oder alle löschbar). |
| **DESIGN** | Farben der Website, Hinweisbanner (z. B. für Wartung), Vorgabe hell/dunkel für den Tisch, „Wer ist online“ ein- oder ausschalten. „Zurücksetzen“ stellt die Standardwerte wieder her. |
| **SPRÜCHE** | Klassiker-Sprüche für den Tisch-Chat hinzufügen, ändern, löschen und umsortieren. Die acht mitgelieferten Sprüche werden nur beim allerersten Start eingetragen. |
| **VORSCHLÄGE** | Eingereichte Verbesserungsvorschläge ansehen (mit Daumen), ausblenden, bearbeiten, löschen. Ausgeblendete sieht nur der Betreiber. |
| **TEST-TISCH** | Beliebige Spielsituationen für Tests aufbauen (siehe [DEVELOPMENT.md](DEVELOPMENT.md#test-tisch-szenario-labor)). Test-Tische sind nie öffentlich und zählen nicht in die Statistik. |

## Moderation

- **Verbesserungsvorschläge:** Das Formular am Ende der Website hat ein selbstgebautes Captcha, einen Honigtopf und Begrenzungen je Adresse und Browser.
  Das hält Massen-Spam ab, aber keine gezielten Angreifer. Unpassende Einträge blendest du im Reiter VORSCHLÄGE aus oder löschst sie.
  Ohne Konten lässt sich „ein Daumen je Nutzer“ nur je Browser durchsetzen.
- **Tisch-Chat:** Er ist flüchtig (nur im Arbeitsspeicher, nie in der Datenbank). Bei Missbrauch beendest du den Tisch im Reiter LIVE.
- **Betreiber-Eingriffe sind sichtbar:** Zuschauen erscheint in der Zuschauerliste, Nachrichten und das Beenden erhalten die Spieler als Hinweis.

## Überwachung

- **Gesundheit:** `GET /api/health` liefert `{"status":"ok"}`. Docker prüft das alle 15 Sekunden (`docker compose ps` zeigt `healthy`).
  Für Benachrichtigungen bei Ausfall kannst du einen externen Uptime-Dienst auf `https://deine-domain/api/health` richten. Das ist ein
  Dienst eines Dritten, der die Adresse abruft; er bekommt keine Spielerdaten.
- **Fehler:** Das Fehler-Log im Reiter SYSTEM zeigt unerwartete Fehler des Servers, auch aus der Bot-Schleife (maximal 300 Einträge, 30 Tage).
- **Speicherplatz:** Der Reiter SYSTEM zeigt freien Platz. Docker-Protokolle sind auf 3 Dateien à 2 MB je Container begrenzt. Alte Images räumt der Deploy auf
  (`docker image prune -f`).
- **Last:** Das Backend ist ein einzelner Prozess. Bots rechnen ihre Züge (im Mittel rund 50 ms je Aktion). Beobachte bei vielen gleichzeitigen Tischen
  die Antwortzeit und die CPU-Auslastung des Servers (`docker stats`).

## Aufräumen und Aufbewahrung

Das erledigt der „Hausmeister“ im Backend automatisch (alle 10 Minuten):

| Was | Wann gelöscht |
|---|---|
| Tisch samt Mitgliedern, Spielstand, Protokoll und Chat | 12 Stunden ohne Aktivität |
| Fehler-Log | nach 30 Tagen, höchstens 300 Einträge |
| Anonyme Spielzähler (für die Auswertung) | nach 400 Tagen |

Dauerhaft bleiben: die Statistik je angelegtem Tisch (Tisch-Code, Zeiten, Zahl der Menschen/Bots, Spiele, Runden; keine Namen), die
Verbesserungsvorschläge samt Daumen (pseudonymisiert), Sprüche und Einstellungen. Die Statistik lässt sich bei Bedarf in der Datenbank leeren:

```bash
docker compose exec backend python -c "
import sqlite3; c = sqlite3.connect('/data/doppelkopf.sqlite3'); c.execute('DELETE FROM table_log'); c.commit()"
```

(Vorher sichern. Die Auswertung im Reiter STATISTIK beginnt danach wieder bei null.) Eine Übersicht aller Daten: [PRIVACY.md](PRIVACY.md).

## Geheimnisse und Zugänge

| Was | Wie wechseln | Folgen |
|---|---|---|
| `ADMIN_PASSWORD` | Wert ändern, neu starten (`docker compose up -d`) bzw. deployen, dann im Admin **ALLE ABMELDEN** (oder Neustart) | alte Anmeldungen enden beim Neustart ohnehin |
| `SECRET_KEY` | Wert ändern, neu starten | siehe [CONFIGURATION.md](CONFIGURATION.md#schlüssel-wechseln): Platz-Codes ändern sich, Betreiber werden abgemeldet |
| SSH-Schlüssel des Deploys | neuen Schlüssel erzeugen, öffentlichen Teil auf dem Server eintragen, Secret `SSH_PRIVATE_KEY` ersetzen, alten Eintrag löschen | |

## Abhängigkeiten und Sicherheit

- **Dependabot** schlägt wöchentlich Updates für npm, pip und die GitHub Actions vor (`.github/dependabot.yml`). Die Tests laufen automatisch für jeden Vorschlag; erst nach grünen Tests mergen.
- **CodeQL** prüft den Code bei jedem Push und wöchentlich auf bekannte Schwachstellen-Muster.
- **Server:** Betriebssystem regelmäßig aktualisieren (`sudo apt update && sudo apt upgrade`). Docker startet die Container mit `restart: unless-stopped` nach einem Neustart des Servers selbst.
- **Zertifikate:** Caddy erneuert sie automatisch. Ist Port 80 oder 443 gesperrt, schlägt das fehl.

## Grenzen der Architektur

- Das Backend läuft als **ein Prozess** (Werkzeug-Server im Threading-Modus von Flask-SocketIO). Spielstände, Bot-Schleifen, Chat und Online-Status
  sind an diesen Prozess gebunden. Mehrere Instanzen hinter einem Lastverteiler sind **nicht** vorgesehen (dafür fehlen eine Nachrichtenwarteschlange für Socket.IO und gemeinsamer Zustand).
- Die Datenbank ist SQLite im Volume. Das genügt für viele gleichzeitige Tische, ist aber kein Cluster. Skalieren heißt: größerer Server.
- Ohne Konten gibt es keine Möglichkeit, einzelne Personen zu sperren. Schutz bieten die Begrenzungen je Adresse, die Tisch-Passwörter und das Beenden von Tischen.

## Häufige Aufgaben und Probleme

| Situation | Vorgehen |
|---|---|
| Backend ist `unhealthy` | `docker compose logs backend --tail=100` lesen. Häufig: `SECRET_KEY` fehlt oder `ADMIN_PASSWORD` zu kurz. |
| Spieler melden „Offline“ | `CORS_ORIGINS` auf `*` und Proxy mit WebSocket-Weiterleitung prüfen ([DEPLOYMENT.md](DEPLOYMENT.md#fehlersuche)). |
| Ein Tisch hängt oder ist verwaist | Im Reiter LIVE beenden. Nach 12 Stunden Stille verschwindet er ohnehin. |
| Spieler hat seinen Platz verloren (anderes Gerät) | Er braucht seinen **Platz-Code** (Tischmenü auf dem alten Gerät). Der Host des Tisches sieht die Codes aller Mitspieler und kann ihn weitergeben. Du als Betreiber kannst Codes nicht abrufen. |
| Admin-Login geht nicht | Passwort prüfen. Nach 5 Fehlversuchen kurz warten (10 Minuten). Ist `ADMIN_PASSWORD` leer, ist `/admin` aus. |
| Speicherplatz knapp | `docker system df`, `docker image prune -f`, alte Sicherungen löschen. |
| Alles zurücksetzen | Sicherung machen, dann `docker compose down -v` (**löscht die Datenbank**) und neu starten. |
