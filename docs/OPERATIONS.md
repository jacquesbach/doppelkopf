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
| **BOTS** | Wie die Bots denken: Durchrechnen je Spielart (Solo, Armut, Hochzeit) ein- und ausschalten, öffentlich Angesagtes nutzen, Rechenaufwand, Schwellen für Ansagen, Spieltempo und Einstellungen der Grundstrategie. Jede Einstellung ist im Reiter erklärt. Änderungen gelten sofort an allen Tischen und bleiben nach einem Neustart erhalten; „Auf Standard zurücksetzen“ stellt die gemessenen Werte wieder her. Siehe [Bot-Einstellungen](#bot-einstellungen). |
| **DESIGN** | Farben der Website, Hinweisbanner (z. B. für Wartung), Vorgabe hell/dunkel für den Tisch, „Wer ist online“ ein- oder ausschalten. „Zurücksetzen“ stellt die Standardwerte wieder her. |
| **SPRÜCHE** | Klassiker-Sprüche für den Tisch-Chat hinzufügen, ändern, löschen und umsortieren. Die acht mitgelieferten Sprüche werden nur beim allerersten Start eingetragen. |
| **VORSCHLÄGE** | Eingereichte Verbesserungsvorschläge ansehen (mit Daumen), ausblenden, bearbeiten, löschen. Ausgeblendete sieht nur der Betreiber. |
| **TEST-TISCH** | Beliebige Spielsituationen für Tests aufbauen (siehe [DEVELOPMENT.md](DEVELOPMENT.md#test-tisch-szenario-labor)). Test-Tische sind nie öffentlich und zählen nicht in die Statistik. |


### Bot-Einstellungen

Der Reiter **BOTS** ändert `bots.TUNE` im laufenden Server (ein Prozess) und das Tempo der Bots. Der Stand liegt in der Tabelle `setting`
(Schlüssel `bot_tuning`, nicht Teil der öffentlichen Seiteneinstellungen) und wird beim Start wieder angewendet. Wurde nie gespeichert, gelten die
Standardwerte aus dem Code. Zum Vergleichen und Messen siehe [DEVELOPMENT.md](DEVELOPMENT.md#bots-messen).

| Einstellung | Standard | Bedeutung |
|---|---|---|
| **Durchrechnen der Kartenwahl** | | Beim Durchrechnen verteilt der Bot die Karten, die er nicht sieht, zufällig (aber regelkonform) auf die Mitspieler und spielt jede erlaubte Karte in vielen solchen Verteilungen zu Ende. Er wählt die Karte mit den meisten erwarteten Augen für seine Partei. Der Bot kennt nie fremde Hände, nur öffentlich Bekanntes. |
| Durchrechnen insgesamt | an | Hauptschalter. Aus: Die Bots spielen alle Karten nach festen Regeln (Grundstrategie), in jeder Spielart. Das spart Rechenzeit, spielt aber deutlich schwächer. Im Normalspiel schlagen die Bots mit Durchrechnen die frühere Strategie klar (siehe Dokumentation, Abschnitt Bots). |
| Durchrechnen im Solo | an | Bei allen sieben Soli (Farben-, Damen-, Buben-, Fleischlos-Solo, Pflicht- und Lustsolo). Der Solist spielt öffentlich bekannt gegen drei. Messung: +0,48 ± 0,08 Punkte je Spiel gegenüber der festen Regel. |
| Durchrechnen bei Armut | an | Nach dem Kartentausch. Der Arme und sein Käufer sind Re. Die getauschten Karten kennen nur die beiden, die Bots rechnen ohne diese Kenntnis der anderen. Messung: +1,05 ± 0,15 Punkte je Spiel. |
| Durchrechnen bei Hochzeit | an | Der Spieler mit beiden Kreuz-Damen ist Re. Sein Partner ist, wer im ersten, zweiten oder dritten Stich zuerst einen fremden Stich gewinnt; sonst wird es ein Solo. Das bilden die Verteilungen nach. Nach der Klärung stehen die Parteien fest. Messung: +0,40 ± 0,12 Punkte je Spiel. |
| Öffentlich Angesagtes nutzen | an | Nach einer Schweinchen-Ansage liegen alle noch nicht gespielten Karo-Asse beim Ansager, bei einer Hochzeit alle noch nicht gespielten Kreuz-Damen. Das weiß jeder am Tisch; der Bot verteilt diese Karten deshalb nicht mehr zufällig. Messung: Hochzeit +0,10 Punkte gegenüber ohne (im Rauschen), Schweinchen neutral. Aus nur für Vergleiche. |
| Rechenaufwand | 160 Stichproben | Wie viele Stichproben ein Bot je Zug rechnet (verteilt auf die erlaubten Karten, jede Karte mindestens 6, höchstens 40). Mehr ist genauer, braucht aber proportional mehr Rechenzeit. Standard 160: im Mittel rund 50 ms je Zug. |
| **Ansagen (Re, Kontra, Absagen)** | | Im Normalspiel entscheidet der Bot per Stichprobe, ob er Re/Kontra oder eine Absage ansagt. In allen anderen Spielarten gilt eine feste Regel (nur Re/Kontra, früh, nach Handstärke). |
| Art der Ansage-Entscheidung | Stichprobe | „Stichprobe“: Im Normalspiel spielt der Bot seine Hand mehrfach durch und sagt an, wenn die Erfolgschance hoch genug ist. „Feste Regel“: Ansage nur von Re/Kontra, früh und nach Handstärke; keine Absagen. |
| Schwelle für Re/Kontra | 75 % | Ab dieser Gewinnchance sagt ein Bot Re bzw. Kontra an. Höher = vorsichtiger. |
| Schwelle für Absagen | 85 % | Ab dieser Chance, die Absage (keine 90 / 60 / 30 / schwarz) zu erreichen, sagt ein Bot sie an, jeweils die höchste, die reicht. Höher = vorsichtiger. |
| Stichproben je Ansage | 30 Stichproben | Wie oft der Bot die Hand für die Ansage-Entscheidung durchspielt. Mehr = verlässlicher, aber langsamer. |
| **Tempo** | | Wie schnell Bots am Tisch spielen. Die Rechenzeit ist davon unabhängig. |
| Spieltempo der Bots | Normal | Faktor auf alle Wartezeiten der Bots (Bedenkzeit, Vorbehaltsabfrage, Pause nach dem Stich). Gilt für alle Tische, auch laufende. |
| **Grundstrategie (Rückfall)** | | Diese Regeln gelten immer dann, wenn nicht durchgerechnet wird: bei ausgeschaltetem Durchrechnen, bei Karten mit nur einer erlaubten Wahl und wenn keine passende Verteilung gefunden wird. Sie sind im Selbstspiel abgestimmt; Änderungen nur für Versuche. |
| Sichere Fehlkarten zuerst ausspielen | an | Eine Fehlfarben-Karte mit Augen, die kein Gegner mehr überbieten kann (die höchste ihrer Farbe), wird zuerst ausgespielt, um Augen zu sichern. |
| Risiko beim Ausspielen meiden | an | Beim Ausspielen werden Farben vermieden, in denen ein Gegner nachweislich keine Karte mehr hat (er würde stechen); Farben, in denen der Partner leer ist, werden bevorzugt. |
| Trumpfstark ausspielen | aus | Mit mindestens 5 Trümpfen spielt der Bot einen Trumpf aus, den kein Gegner mehr überbieten kann (bei 7 oder mehr Trümpfen den stärksten, sonst den schwächsten davon). |
| Partner nur bei sicherem Stich schmieren | an | Gewinnt der Partner den Stich, gibt der Bot nur dann Augen dazu, wenn der Stich nicht mehr überstochen werden kann. |
| Sicher gewinnen bevorzugen | an | Zum Gewinnen eines Stichs wird die schwächste Karte genommen, die auch gegen die Nachspieler hält. |
| Kurze Farben zuerst abwerfen | an | Beim Abwerfen werden kurze Fehlfarben zuerst gewählt, damit man früh farbfrei wird und stechen kann. |
| **Experimentell** | | Verfahren ohne nachgewiesenen Gewinn. Nur für Versuche gedacht. |
| Parteien aus dem Spielverhalten schätzen | aus | Der Bot schließt aus dem Verhalten der Mitspieler (Schmieren, Stechen) auf deren Partei und gewichtet die Verteilungen entsprechend. Im Selbstspiel kein messbarer Gewinn bei doppelter Rechenzeit. |
| Stärke dieser Schätzung | 50 % | Gewicht, mit dem Verteilungen zählen, die zum Verhalten nicht passen (niedrig = starke Wirkung, 100 % = keine Wirkung). |
| Sieg statt Augen bewerten | aus | Die Karte wird nach der Siegchance der Partei (danach Augen) gewählt statt nach den erwarteten Augen. Nicht gemessen; Standard: aus. |

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
