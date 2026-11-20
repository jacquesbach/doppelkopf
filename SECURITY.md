# Sicherheit

## Eine Sicherheitslücke melden

Bitte melde Sicherheitslücken **nicht** als öffentliches Issue. Nutze stattdessen die private Meldung von GitHub:

**Repository → Reiter „Security“ → „Report a vulnerability“**
(<https://github.com/jacquesbach/doppelkopf/security/advisories/new>)

Beschreibe möglichst genau, was du gefunden hast, wie man es nachvollziehen kann und welche Auswirkung du erwartest (Adresse, Schritte, Browser).
Ich antworte so schnell, wie es neben dem Projekt möglich ist, und melde mich, sobald die Lücke behoben ist. Auf Wunsch nenne ich dich in den Hinweisen zur Korrektur.

Das Projekt befindet sich in der **Beta-Phase** und wird von einer Einzelperson in der Freizeit gepflegt. Eine feste Reaktionszeit kann ich nicht zusagen.

Bitte teste nur an deiner **eigenen Installation** oder in einem Maß, das den Betrieb von www.doppelkopf.cc und andere Spieler nicht stört (keine Überlastungstests, kein Durchprobieren fremder Tische).

## Unterstützte Version

Es gibt nur den aktuellen Stand des Zweigs `main`. Korrekturen erscheinen dort.

## Was geschützt werden soll

- **Fremde Handkarten und verdeckte Informationen** verlassen den Server nie (jede Sicht wird je Teilnehmer erzeugt).
- **Zugang zu einem Tisch** nur mit gültigem Token, Platz-Code oder Tisch-Passwort.
- **Das Betreiber-Backend** nur mit dem Betreiber-Passwort.
- **Datensparsamkeit:** keine IP-Adressen, keine Chat-Texte in der Datenbank.

Besonders interessant für Meldungen: Datenlecks in Sichten, Umgehung der Zugangsprüfung oder der Begrenzungen, Zugriff auf das Betreiber-Backend ohne Anmeldung, Einschleusen von Skripten (XSS), Umgehung der Content-Security-Policy.

## Das Sicherheitsmodell im Überblick

| Thema | Umsetzung |
|---|---|
| Autorisierung | Der Server prüft jede Aktion gegen den Regelkern; der Browser schickt nur Absichten |
| Sitzungen | Zufälliges Token je Platz; in der Datenbank steht nur der SHA-256-Hash. Bots sind über HTTP und Socket.IO nicht ansprechbar |
| Wiedereinstieg | Platz-Code (HMAC aus `SECRET_KEY`, nicht gespeichert) |
| Tisch-Passwort | mindestens 6 Zeichen, gehasht |
| Brute-Force | Begrenzungen je Adresse für neue Tische, falsche Passwörter/Codes, unbekannte Tisch-Codes, Vorschläge, Betreiber-Anmeldung |
| Betreiber | Passwort aus der Umgebung (mindestens 10 Zeichen), Token 2 Stunden gültig, nur Hash im Arbeitsspeicher, „Alle abmelden“ |
| Eingaben | Längen- und Zeichenprüfung für Namen, Chat, Vorschläge; Ausgabe über Svelte (automatisch maskiert) |
| Browser-Schutz | Content-Security-Policy (u. a. `frame-ancestors 'none'`), `X-Content-Type-Options` in `deploy/nginx.conf`; keine Cookies |
| Netz | Backend nur auf `127.0.0.1` gebunden (`BACKEND_BIND`); HTTPS über einen vorgeschalteten Proxy |
| Abhängigkeiten | Dependabot (npm, pip, GitHub Actions) und CodeQL |
| Tests | Lecktests prüfen nach jeder Aktion ganzer Spiele, dass keine Sicht fremde Karten enthält |

## Bekannte Grenzen

- Ohne Konten gibt es keine Sperre einzelner Personen. Schutz bieten Begrenzungen je Adresse und die Moderation.
- Wer Tisch-Code und Passwort kennt, kann einen **getrennten** Sitz übernehmen (gedacht für Freundesrunden).
- Das selbst gebaute Captcha hält Massen-Spam ab, aber keine gezielten Angreifer.
- Docker veröffentlicht Ports an der Firewall `ufw` vorbei. Betreiber öffnen in der Firewall des Anbieters nur 22, 80 und 443 ([docs/DEPLOYMENT.md](docs/DEPLOYMENT.md#ports-und-firewall)).
- Hinter einem Proxy außerhalb des privaten Docker-Netzes muss `set_real_ip_from` in `deploy/nginx.conf` angepasst werden, sonst teilen sich alle Besucher die Begrenzungen.

## Für Betreiber

- `SECRET_KEY` und `ADMIN_PASSWORD` lang und zufällig wählen und geheim halten (`.env` mit Rechten 600, bei Weg B als GitHub-Secrets).
- Betriebssystem, Docker und Abhängigkeiten aktuell halten; Dependabot-Vorschläge nach grünen Tests übernehmen.
- Nur 22, 80 und 443 nach außen öffnen, SSH mit Schlüssel statt Passwort.

Weitere Hinweise: [docs/OPERATIONS.md](docs/OPERATIONS.md) und [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#zugang-und-sicherheit).
