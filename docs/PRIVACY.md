# Datenschutz im Code: Was gespeichert wird

Eine technische Übersicht für Entwickler und Betreiber: welche Daten die Software wo, wie lange und warum hält. Sie ist die Grundlage der Datenschutzerklärung
(`src/pages/Legal.svelte`, erreichbar unter `/datenschutz`) und ersetzt sie nicht. Keine Rechtsberatung.

**Leitidee:** Es wird nur gespeichert, was für das Spiel nötig ist. Kein Konto, keine Cookies, kein Tracking, keine Fremddienste (Schriften und Captcha liegen lokal bzw. sind selbst gebaut).

## Auf dem Server (Datenbank, SQLite)

| Tabelle | Daten | Zweck | Löschung |
|---|---|---|---|
| `room` | Tisch-Code, Anlagezeit, Status, Hash des Tisch-Passworts (falls gesetzt), Host, Regeln, öffentlich ja/nein, Einstellung der Bot-Übernahme | Tisch betreiben | nach 12 h ohne Aktivität; sofort beim Beenden durch Host oder Betreiber |
| `member` | Spielname (≤ 32 Zeichen, frei wählbar), Rolle (Spieler/Zuschauer), Bereit, Bot ja/nein, Verbindungsstatus, Zeit der letzten Aktivität, **SHA-256-Hash** des Sitzungs-Tokens | Plätze zuordnen, Wiedereinstieg | mit dem Tisch |
| `game_snapshot` | kompletter Spielzustand als JSON (Karten, Ansagen, Stand), Versionsnummer | Spiel fortsetzen, Neustart überstehen | mit dem Tisch |
| `game_history` | Ergebnis je beendetem Spiel | Protokoll am Tisch | mit dem Tisch |
| `table_log` | Tisch-Code, Zeitpunkte (Anlage, Start, letzte Aktivität), Zahl Menschen/Bots, Zahl Spiele/Runden | Statistik für den Betreiber | **bleibt** (keine Namen, keine Inhalte) |
| `game_event` | Zeitpunkt, Dauer und Zahl der Menschen je beendetem Spiel | Auswertungen (Spitzenzeiten, Dauer, Abbruchquote) | nach 400 Tagen |
| `suggestion` | Titel und Beschreibung eines Vorschlags, Status | Rückmeldungen sammeln | bis der Betreiber ausblendet/löscht |
| `suggestion_vote` | **Hash** der zufälligen Browser-Kennung, Vorschlag, Zeit | ein Daumen je Browser | mit dem Vorschlag |
| `phrase` | Chat-Sprüche (vom Betreiber gepflegt) | Schnell-Sprüche im Chat | dauerhaft (Betreiber) |
| `setting` | Farben, Banner, Vorgaben (Hell/Dunkel, Online-Status ein/aus) | Betreiber-Einstellungen | dauerhaft (Betreiber) |
| `error_entry` | Zeit, Quelle, Pfad **ohne Parameter**, Fehlerart, gekürzte Meldung, Stacktrace, Zähler | Fehlersuche | nach 30 Tagen, höchstens 300 Einträge |

Nicht in der Datenbank: IP-Adressen, Chat-Nachrichten, Passwörter im Klartext, Sitzungs-Tokens im Klartext, Platz-Codes.

## Nur im Arbeitsspeicher des Servers

Alles hier verschwindet bei einem Neustart des Backends.

| Was | Inhalt | Dauer |
|---|---|---|
| Tisch-Chat | die letzten 100 Nachrichten je Tisch (≤ 200 Zeichen) | bis Tisch-Ende oder Neustart |
| Zugangsschutz (`guard.py`) | Zähler je IP-Adresse (IPv6: /64-Netz) und gegebenenfalls Tisch-Code: neue Tische, Fehlversuche, unbekannte Codes | höchstens eine Stunde bzw. 10 Minuten |
| Vorschlags-Begrenzung (`ratelimit.py`) | Zähler je IP-Adresse und je Browser-Kennung (als Hash) | letzte Stunde |
| Betreiber-Anmeldung | Hash des Tokens und Ablaufzeit; Fehlversuche je IP | 2 Stunden bzw. 10 Minuten |
| Online-Status (`presence.py`) | Freundescode, Anzeigename, Verbindungskennung, Codes der Freunde. Nur, wenn die Person es selbst einschaltet. | solange verbunden |
| Captcha | nichts: der Server hält keinen Zustand, die Antwort steckt als Hash im signierten Token | 10 Minuten, einmal gültig |

Der **Platz-Code** wird bei Bedarf aus `SECRET_KEY`, Tisch-Code und Sitzdaten berechnet und nirgends gespeichert.

## Im Browser der Besucher

| Schlüssel | Speicher | Inhalt | Wann |
|---|---|---|---|
| `doko.sessions.v1` | localStorage | Sitzungs-Token je Tisch | nach Beitritt oder Anlegen |
| `doko.name.v1` | localStorage | zuletzt benutzter Spielname | nach Beitritt oder Anlegen |
| `doko.client.v1` | localStorage | zufällige Kennung für Daumen | beim ersten Daumen oder Vorschlag |
| `doko.theme.v1` | localStorage | Wahl Hell/Dunkel am Tisch | nach Umschalten |
| `doko.friends.v1` | localStorage | Freundescode, Anzeigename, Freundesliste | nur wenn der Online-Status eingeschaltet wurde |
| `doko.banner.closed` | sessionStorage | Hinweisbanner geschlossen | nach Klick, endet mit dem Tab |
| `doko.admin.v1` | sessionStorage | Betreiber-Token | nur beim Betreiber, endet mit dem Tab |
| `doko.lab.v1` | localStorage | Plätze der Test-Tische | nur beim Betreiber |

Es werden **keine Cookies** gesetzt. Die Einträge dienen den vom Besucher gewünschten Funktionen und enthalten keine Daten, die ihn identifizieren.

## Protokolle auf dem Server

- **nginx-Zugriffsprotokoll:** IP-Adresse **gekürzt** (IPv4 ohne letzte Zahl, IPv6 ohne die letzten 80 Bit), Zeit, Pfad, Status, Datenmenge, User-Agent. Docker begrenzt die Protokolle auf 3 Dateien à 2 MB je Container, ältere Einträge werden überschrieben.
- **Backend-Protokoll** (`docker compose logs backend`): Betriebsmeldungen und Fehler. Bei technischen Fehlern können volle IP-Adressen vorkommen. Es wird ebenfalls rotiert.
- Der vorgeschaltete **Proxy** (z. B. Caddy) ist Sache des Betreibers. Er sollte keine Zugriffsprotokolle mit vollen IP-Adressen schreiben, sonst stimmt die Datenschutzerklärung nicht (Caddy tut das standardmäßig nicht).
- **Sicherungen** der Datenbank enthalten Tische länger, als es die 12-Stunden-Regel verspricht. Kurze Aufbewahrung und Zugriffsschutz: siehe [OPERATIONS.md](OPERATIONS.md#sicherung-und-wiederherstellung).

## Wer sieht was?

| Wer | Sieht |
|---|---|
| Mitspieler | Spielnamen, öffentliche Spielinformationen (gespielte Karten, Ansagen, Stand), Chat. **Nie** fremde Handkarten. |
| Zuschauer | wie Mitspieler, aber ohne jede Hand |
| Besucher einer **öffentlichen** Tischliste | Tisch-Code, Spielnamen der Sitzenden, Regeln, freie Plätze |
| Betreiber (nach Anmeldung) | Live-Übersicht mit Tisch-Code, Spielnamen, Verbindungsstatus; Zuschauen (sichtbar als „Betreiber“, ohne Hände), Nachrichten senden, Tisch beenden; Statistik ohne Personenbezug; Fehler-Log |
| Gastgeber | die Platz-Codes seiner Mitspieler (zum Weitergeben bei Verlust) |

## Checkliste für Änderungen

Bevor eine Änderung mit Datenbezug gemerged wird:

1. **Wird etwas Neues gespeichert** (Datenbank, Browser, Arbeitsspeicher, Protokoll)? Dann diese Datei, die Datenschutzerklärung in `src/pages/Legal.svelte` und, wenn es den Betrieb betrifft, [OPERATIONS.md](OPERATIONS.md) anpassen.
2. **Geht etwas an Dritte?** (Fremde Schriften, Analyse, Einbettungen, externe Dienste.) Das ist nicht vorgesehen. Wenn doch: Erklärung erweitern, Content-Security-Policy in `deploy/nginx.conf` anpassen, Rechtsgrundlage und gegebenenfalls Einwilligung klären.
3. **Gibt es eine Löschfrist?** Jede neue Tabelle braucht eine Aufräumregel (Hausmeister in `housekeeping.py`) oder eine Begründung, warum sie dauerhaft bleibt.
4. **Landen personenbezogene Angaben im Fehler-Log?** Pfade ohne Parameter, keine Anfrageinhalte, keine Namen.
5. **Neue Sichten?** Lecktest (`tests/service/test_view_leaks.py`) ergänzen.
6. **IP-Adressen** gehören nie in die Datenbank. Zähler leben im Arbeitsspeicher und verschwinden von selbst.

## Offene Punkte

- `table_log` wird nicht automatisch aufgeräumt (es enthält keine personenbezogenen Daten). Wer es begrenzen will, leert es nach Bedarf, siehe [OPERATIONS.md](OPERATIONS.md#aufräumen-und-aufbewahrung).
- Die Betreiberangaben im Impressum und Angaben zu Hoster und Region kommen aus `legal/legal.json` ([CONFIGURATION.md](CONFIGURATION.md#4-betreiberangaben-legallegaljson)). Ob der Vertrag zur Auftragsverarbeitung mit dem Hoster besteht, muss jeder Betreiber selbst sicherstellen.
