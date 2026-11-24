# Schnittstellen (HTTP und Socket.IO)

Referenz für alle Routen des Backends. Alle Pfade liegen unter **`/api`** (im Betrieb leitet nginx `/api` und `/socket.io` an das Backend). Die Oberfläche nutzt genau diese Schnittstelle, es gibt keine versteckten Wege.

- [Grundlagen](#grundlagen) · [Tische (Räume)](#tische-räume) · [Spiel](#spiel) · [Spielzüge](#spielzüge-actiontype) · [Sicht](#die-sicht-view) · [Socket.IO](#socketio)
- [Vorschläge, Sprüche, Einstellungen](#vorschläge-sprüche-einstellungen) · [Betreiber](#betreiber-admin) · [Test-Tisch](#test-tisch-adminlab) · [Zugangsschutz und Begrenzungen](#zugangsschutz-und-begrenzungen)

## Grundlagen

**Authentifizierung.** Wer am Tisch sitzt, hat ein **Sitzungs-Token** (bei `POST /rooms` und `…/join` zurückgegeben). Es wird im Header `X-Session-Token` gesendet.
Bei den meisten `POST`-Routen darf es alternativ als `token` im JSON-Body stehen; die Tabellen unten nennen Ausnahmen. Die Oberfläche sendet beides.
Der **Sitz** eines Handelnden ergibt sich ausschließlich aus dem Token; `seat` oder `memberId` im Body werden ignoriert. **Bots** authentifizieren sich nie über HTTP oder Socket (sie handeln serverseitig, ihre Tokens werden nie ausgegeben).

**Betreiber** senden `Authorization: Bearer <Betreiber-Token>` (siehe [Betreiber](#betreiber-admin)).

**Browser-Kennung.** Für Daumen und Vorschläge sendet der Browser `X-Client-Id` (8–64 Zeichen aus `A-Za-z0-9_-`). Sie wird serverseitig nur als HMAC-Hash gespeichert.

**Format.** JSON in beide Richtungen. Namen sind höchstens 32 Zeichen, Tisch-Codes 6 Zeichen (Groß-/Kleinschreibung egal). Fehler haben die Form `{"error": "Text", "code": "…"}` (der `code` fehlt bei einfachen Fehlern).

**Statuscodes.**

| Code | Bedeutung |
|---|---|
| `400` | ungültige Eingabe (`bad_request`, `unknown_action`, `unknown_option`, `invalid_option_value`, `invalid_option_combination`, `bad_scenario` …) |
| `401` | Betreiber-Token fehlt oder ist abgelaufen |
| `403` | keine oder ungültige Sitzung, falsches Passwort oder falscher Platz-Code, Zuschauer, fehlende Berechtigung (z. B. nicht Host) |
| `404` | Tisch, Spiel, Vorschlag oder Spieler nicht gefunden |
| `409` | Regelverstoß oder falscher Zustand (`not_your_turn`, `must_follow`, `wrong_phase`, `mandatory_announcement`, `announcement_too_late`, `game_running`, `round_finished` …), `version_conflict` (mit aktueller `version`), Tisch voll |
| `429` | Begrenzung erreicht (`rate_limited`, zu viele Versuche) |
| `503` | `admin_disabled`: `ADMIN_PASSWORD` ist nicht gesetzt |

### Gesundheit

| Route | Zweck |
|---|---|
| `GET /health` | `{"status":"ok","service":"doppelkopf-multiplayer"}`. Für Docker-Healthcheck und Überwachung. Keine Anmeldung. |

## Tische (Räume)

**Regeln und Einstellungen**

| Route | Wer | Zweck |
|---|---|---|
| `GET /rule-schema` | alle | `{"options":[{id, group, default, label, description, requires}]}`: alle zuschaltbaren Regeln für das Formular. Gruppen: `popular`, `pub` |
| `POST /rooms/<code>/settings` `{settings}` | Host, nicht während einer Runde | Regeln ändern → `{settings, profileId}`. `409` während einer Runde |
| `POST /rooms/<code>/takeover` `{seconds}` | Host | Bot-Übernahme bei Inaktivität: `0` (nie), `60`, `120`, `180` (Standard), `300`, `600`, `1800`. Auch in der Lobby und während der Runde → `{seconds}` |

`settings` ist ein Objekt aus Regel-ID und Wert, z. B. `{"dulle": true, "karlchen": true, "sharp_doppelkopf": false}` (`sharp_doppelkopf: true` = Spiel ohne Neuner); fehlende Schlüssel gelten als Standard. Die Regeln und ihre Abhängigkeiten stehen in [DDV_REGELMATRIX.md](DDV_REGELMATRIX.md#1b-zuschaltbare-regeln).
Jede Raumantwort enthält `settings`, `profileId` (`ddv_tsr_2026`, `house_no_nines` oder `custom`) und `isOfficialDdv`.

**Anlegen, beitreten, verlassen**

| Route | Wer | Zweck |
|---|---|---|
| `POST /rooms` `{name, password?, settings?, public?}` | alle | Tisch anlegen → `201 {room, token, memberId}`. Passwort mindestens 6 Zeichen. `429` bei zu vielen neuen Tischen je Adresse |
| `POST /rooms/<code>/join` `{name, role?, password?}` | alle | beitreten (`role`: `player` oder `spectator`) → `201 {room, token, memberId}`. `403` Passwort falsch, `404` unbekannter Tisch, `409` Tisch voll oder Spiel läuft (dann als Zuschauer), `429` zu viele Versuche |
| `GET /rooms/<code>` | alle; Token (Header) optional | Raum. Mit Token wird `isMe` gesetzt und die Anwesenheit aktualisiert |
| `POST /rooms/<code>/ready` `{token, ready}` | Spieler | Bereitschaft. **Token nur im Body** |
| `POST /rooms/<code>/bots` `{token}` | Host, vor dem Start | füllt **alle** freien Plätze mit Bots. **Token nur im Body** |
| `POST /rooms/<code>/leave` | Mitglied | Tisch verlassen → `{left, closed}`. `409`, solange eine Runde läuft (Spieler). Host-Wechsel auf den ältesten Spieler; ohne Menschen wird der Tisch geschlossen |
| `GET /rooms/public` | alle | offene Tische mit freien Plätzen: `{rooms:[{code, host, players, playerCount, hasPassword, settings, isOfficialDdv, createdAt}]}`. Nur wartende Tische, an denen sich in den letzten 90 s ein Mensch gemeldet hat (höchstens 30) |
| `POST /rooms/<code>/visibility` `{public}` | Host | Tisch öffentlich (Tischliste) oder privat (nur per Link) stellen |

`room` (in jeder Raumantwort und im Socket-Ereignis `room:state`): `code, status (waiting|playing), settings, profileId, isOfficialDdv, hasPassword, isPublic, botTakeover, players[{id, name, role, ready, isHost, connected, isBot, isMe}], playerCount, spectatorCount, canStart`.

**Zugang auf anderen Geräten**

| Route | Wer | Zweck |
|---|---|---|
| `GET /rooms/<code>/seat-code` | Spieler | eigener Platz-Code `{code: "ABCD-EFGH"}` (berechnet, nicht gespeichert) |
| `GET /rooms/<code>/seat-codes` | Host | `{seats:[{name, code}]}` der menschlichen Spieler, um einen verlorenen Code weiterzugeben |
| `POST /rooms/<code>/rejoin` `{name, seatCode, password?}` | alle | **Platz zurückholen** (anderes Gerät, gelöschter Browserspeicher): Name eines *nicht verbundenen* Spielers + Platz-Code (+ ggf. Passwort) → neues `{room, token, memberId}`, das alte Token wird ungültig. `403` Passwort oder Code falsch, `404` kein Spieler mit dem Namen, `409` Spieler ist gerade verbunden, `429` zu viele Fehlversuche |

**Chat** (nur im Arbeitsspeicher)

| Route | Wer | Zweck |
|---|---|---|
| `GET /rooms/<code>/chat` | Mitglied, auch Zuschauer | `{messages:[{id, memberId, name, text, ts}]}` (letzte 100) |
| `POST /rooms/<code>/chat` `{text}` | Mitglied, auch Zuschauer | Nachricht senden → `201 {message}`. `400` leer oder länger als 200 Zeichen, `429 rate_limited` bei weniger als 0,8 s Abstand |

## Spiel

| Route | Wer | Zweck |
|---|---|---|
| `POST /rooms/<code>/start` | Host | Runde starten (vier Spieler, alle bereit). Auch nach beendeter Runde für eine neue → `201 {version, view, message}`. `409` bei fehlenden Spielern oder wenn noch nicht alle bereit sind |
| `GET /rooms/<code>/game` | Mitglied | eigene Sicht `{version, table, game}` |
| `POST /rooms/<code>/action` `{type, …, expectedVersion?, actionId?}` | Spieler | Spielzug (siehe [Spielzüge](#spielzüge-actiontype)) → `200 {version, duplicate, view}` |
| `POST /rooms/<code>/next` | Spieler | nächstes Spiel der Runde geben (erst nach beendetem Spiel) |
| `POST /rooms/<code>/continue` | Spieler | „Nächster Stich“. Nur im Spiel gegen Bots (genau ein Mensch); davor wartet der Botbetrieb (`table.holding = true`) |
| `POST /rooms/<code>/away` | Spieler | Platz verlassen, **während die Runde läuft**: ein Bot spielt weiter (`seats[i].autoplay = true`); der Sitz bleibt dem Spieler zugeordnet |
| `POST /rooms/<code>/back` | Spieler | Platz vom Bot zurückholen. Jede eigene Aktion tut das auch |
| `POST /rooms/<code>/stay` `{remember?}` | Spieler | „Weiterspielen“: beendet den Countdown der Bot-Übernahme und startet die Inaktivitätsuhr neu. `remember: true` = für diesen Spieler nie Bot-Übernahme (bleibt über Runden), `false` = wieder zulassen, fehlt = unverändert |
| `GET /rooms/<code>/history` | Mitglied | `{games:[{gameNumber, kind, gameType, soloSeat, winner, seatDeltas, multiplier, bockTriggers, totals, roundFinished, reSeats, …}]}` |

`expectedVersion` (Version aus der letzten Sicht) schützt vor veralteten Zügen (`409 version_conflict`). `actionId` (≤ 64 Zeichen) macht Wiederholungen idempotent: Die zweite Zustellung liefert `duplicate: true`, hat keine zweite Wirkung und löst keine zweite Benachrichtigung aus.

### Spielzüge (`action.type`)

| `type` | Parameter | Bedeutung |
|---|---|---|
| `declare` | `reservation: bool` | Vorbehaltsabfrage: gesund oder Vorbehalt |
| `resolve` | `accept: bool` | Vorbehaltsstufe klären (Pflichtsolo, Lustsolo, Hochzeit, Armut …) |
| `baptize` | `choice` (`wedding`, `solo_clubs`, …, `poverty`) | Vorbehalt „taufen“, also die Art nennen |
| `play_card` | `cardId` | Karte spielen |
| `announce` | `level` 0–4 | 0 = Re/Kontra, 1–4 = keine 90 / 60 / 30 / schwarz |
| `schweinchen` | – | Schweinchen ansagen (Option `schweinchen`) |
| `poverty_pass` | `cardIds` (3) | Armut: Karten verdeckt abgeben |
| `poverty_offer` | `accept: bool` | Armut: Käufer entscheidet |
| `poverty_return` | `cardIds` (3) | Armut: Käufer gibt drei Karten zurück |

Welche Aktionen gerade erlaubt sind, steht in `game.legalActions` der eigenen Sicht (inklusive erlaubter Karten und Ansage-Stufen). Die Oberfläche richtet sich ausschließlich danach.

### Die Sicht (`view`)

```
{ version,
  table: { seats[{seat, memberId, name, isBot, autoplay, noTakeover}], mySeat, gameNumber, gameRecorded, holding,
           takeover, takeoverWarning{seat, remaining}, redeals, redealSeat, finished, profileId, deckVariant,
           ruleOptions, round{dealer, normalGamesPlayed, pflichtsoloDone, totals, bockRemaining, results, next?} },
  game: { … } }
```

`game` ist die **`player_view`** (eigene Hand, `myParty`, `legalActions`) bzw. die **`spectator_view`** (nie Hände, nie verdeckte Parteien). Wichtige Felder:

- `hand`: bereits sortiert (Trümpfe nach Stärke, dann Fehlfarben ♣ ♠ ♥ ♦), `legalActions`, `currentTrick`, `lastTrick` (bleibt nach dem Stich sichtbar), `announcements`, `tricksWon`, `handCounts`, `mandatoryAnnouncementSeat`.
- `baptismKind`: `pflichtsolo`, `pflichtsolo_forced`, `lustsolo`; `null` bedeutet: einziger Vorbehalt (Hochzeit oder Solo).
- Nach Spielende werden Stiche (`game.tricks`, alle in Spielreihenfolge), Parteien (`game.reSeats`) und Wertung aufgedeckt. Die **Stille Hochzeit** bleibt bis Spielende verdeckt.
- **Armut:** Phasen `poverty_pass` → `poverty_offer` → `poverty_return`. `game.poverty = {seat, buyer, offerSeat}` (Anmelder, Käufer, wer gerade gefragt wird). `legalActions` enthält `poverty_pass {count, cards}`, `poverty_offer`, `poverty_return {count, cards, received}` (`received` = soeben erhaltene Karten, nur für den Käufer). Anmelder und Käufer sind von Beginn an Re. Nimmt niemand die Armut, gibt der Tisch sofort neu (gleicher Geber, gleiche Spielnummer); `table.redeals` zählt die Neuwürfe, `table.redealSeat` nennt den Armen.
  `game.povertyPassed` (nur der Arme, solange gefragt wird: seine abgegebenen Karten) und `game.povertyGot` (nur der Arme, nach der Rückgabe: die drei Karten des Käufers) sind **nur** für den Betroffenen sichtbar.
- **Ereignisse** (`game.events`, aufsteigende `id`): `reservation`, `solo`, `wedding`, `wedding_clarified`, `poverty` (`seat`), `poverty_taken` (`seat`, `buyer`), `poverty_void` (`seat`; erscheint nur kurz), `announce` (`party`, `level`), `schweinchen`, `doppelkopf` (`points`), `fox_caught` (`seat` = Fänger, `victim`), `charlie_last_trick`.
  „Fuchs gefangen“ wird nur gemeldet, wenn beide Kreuz-Damen gespielt sind oder eine Hochzeit geklärt ist (sonst verriete es verdeckte Parteien); die Wertung am Spielende nennt ihn immer.

### Getakteter Botbetrieb

Bots spielen **nicht** innerhalb eines Requests, sondern einzeln im Hintergrund (je Zug eine neue Version, sofort an alle gepusht). Takt: Bedenkzeit 1,0 bis 1,7 s je Karte, 1,7 s für Vorbehalt/Taufe/Ansage, 3,0 s nach der letzten Vorbehaltsantwort bis zur ersten Karte, 2,4 s nach einem vollständigen Stich.

**Bot-Übernahme bei Inaktivität:** Ist ein Mensch länger als `table.takeover` Sekunden ohne Änderung am Tisch an der Reihe, läuft ein Countdown von 30 s (`table.takeoverWarning = {seat, remaining}` in der Sicht aller); danach spielt ein Bot den Sitz (`autoplay`). Das passiert nur, wenn der Host es nicht abgeschaltet hat (`table.takeover = 0`), der Spieler nicht abgelehnt hat (`seats[i].noTakeover`) und mindestens zwei Menschen am Tisch spielen. Jede Änderung am Tisch, `/stay` oder ein Zug beendet den Countdown. Kommt der Spieler zurück, übernimmt er wieder.
Tische ohne Aktivität werden nach 12 Stunden geschlossen (gelöscht).

## Socket.IO

Verbindung über `/socket.io` (derselbe Ursprung, WebSocket mit Polling als Rückfall).

| Richtung | Ereignis | Inhalt |
|---|---|---|
| Client → Server | `room:watch` `{code, token}` | Tisch abonnieren. Bots und ungültige Tokens werden abgewiesen (`room:error`). Nach jedem Wiederverbinden erneut senden |
| Server → Client | `room:state` | Raum (ohne `isMe`) |
| Server → Client | `game:state` | **eigene** Sicht `{version, table, game}`; nur an dieses Mitglied |
| Server → Client | `chat:message` | neue Chat-Nachricht, an alle am Tisch |
| Server → Client | `room:notice` `{message, closed}` | Hinweis des Betreibers; bei `closed: true` wird der Tisch danach gelöscht |
| Server → Client | `room:error` `{message}` | Fehler beim Abonnieren (ungültiger Tisch oder Token, oder die Verbindung gehört schon zu einer anderen Sitzung) |

Die Oberfläche verlässt sich nicht allein auf Socket.IO: Sie fragt den Tisch zusätzlich alle 3 Sekunden per `GET /rooms/<code>/game` ab. Eine Sicht mit niedrigerer `version` überschreibt nie eine neuere.

**Online-Status** (freiwillig, nur Arbeitsspeicher, vom Betreiber abschaltbar über `friendsEnabled`):

| Richtung | Ereignis | Inhalt |
|---|---|---|
| Client → Server | `presence:hello` `{code (10 Zeichen), name}` | sichtbar werden |
| Client → Server | `presence:watch` `{codes[≤ 100]}` | Freunde beobachten |
| Client → Server | `presence:invite` `{to, table, token}` | Freund an den eigenen Tisch einladen (gültiges Mitglieds-Token nötig, höchstens 6 je Minute) |
| Client → Server | `presence:goodbye` | unsichtbar werden |
| Server → Client | `presence:ready`, `presence:state` `{friends{code:{online,name}}}`, `presence:update` `{code, online, name}` | Zustand der Freunde |
| Server → Client | `presence:invite` `{from, table, hasPassword}`, `presence:invited` `{to, delivered}`, `presence:error` `{message}` | Einladungen und Fehler |

Wer nicht selbst mit `hello` sichtbar ist, kann niemanden beobachten.

## Vorschläge, Sprüche, Einstellungen

Alle ohne Anmeldung.

| Route | Zweck |
|---|---|
| `GET /captcha` | `{token, svg}`. Das Token ist signiert, 10 Minuten gültig und einmal verwendbar (auch nach falscher Antwort). 60 Abrufe je Stunde und Adresse |
| `GET /phrases` | `{phrases:[{id, text}]}` in der Reihenfolge des Betreibers (Chat-Schnellauswahl) |
| `GET /suggestions` | `{suggestions:[{id, title, description, createdAt, votes, voted}]}`, beliebteste zuerst (bei Gleichstand der ältere); `voted` nur mit `X-Client-Id` |
| `POST /suggestions` `{title, description, captchaToken, captchaAnswer, website}` | `201 {suggestion}`. Titel 4–80, Beschreibung 10–500 Zeichen, keine Links. `website` ist ein Honigtopf und muss leer sein. Texte werden **vor** dem Captcha geprüft (ein Tippfehler verbraucht es nicht). Fehlercodes: `captcha_wrong`, `captcha_expired`, `captcha_used`, `captcha_malformed`, `links_not_allowed`, `duplicate` (409), `rate_limited` (429; 5 je Stunde und Adresse, 3 je Stunde und Browser) |
| `POST /suggestions/<id>/vote` | Daumen (Header `X-Client-Id` nötig) → `{votes, voted}`. Ein zweiter Aufruf nimmt ihn zurück. `404` bei unbekannten oder ausgeblendeten Vorschlägen. 120 je Stunde und Adresse |
| `GET /site-settings` | öffentliche Seiteneinstellungen: Farben, Banner, Hell/Dunkel-Vorgabe, `friendsEnabled` |

## Betreiber (`/admin/…`)

Voraussetzung ist die Variable `ADMIN_PASSWORD`; ohne sie antworten alle `/admin/…`-Routen mit `503 admin_disabled`.

| Route | Zweck |
|---|---|
| `GET /admin/status` | `{enabled}` |
| `POST /admin/login` `{password}` | `{token, expiresIn}`. Das Token ist zufällig und gilt 2 Stunden; der Server hält nur dessen Hash im Arbeitsspeicher (höchstens 20 Sitzungen). 5 Fehlversuche je 10 Minuten und Adresse, dann `429` |
| `POST /admin/logout` | beendet diese Sitzung auf dem Server |
| `POST /admin/logout-all` | beendet alle Sitzungen → `{ended}` |

Alle weiteren Routen verlangen `Authorization: Bearer <token>` (sonst `401`). Ein Neustart des Backends beendet alle Sitzungen.

| Route | Zweck |
|---|---|
| `GET /admin/live` | Live-Übersicht (die Oberfläche fragt alle 3 s): `tables[]` (`code`, `state` = `running`, `waiting`, `finished` oder `idle`, `idleSeconds`, `humans`, `bots`, `connectedHumans`, `spectators`, `players[{name, isBot, isHost, connected}]`, `game{number, phase, tricks}`, `isPublic`, `hasPassword`, `isLab`) und Summen `count`, `running`, `waiting`, `idle`, `humansOnline`, `playingNow`, `botOnlyTables`, `spectatorsTotal`, `serverTime`. Test-Tische zählen nicht in die Summen |
| `POST /admin/live/<code>/message` `{message}` | Hinweis an alle am Tisch (Socket-Ereignis `room:notice {message, closed:false}`) |
| `POST /admin/live/<code>/close` `{message?}` | meldet `room:notice {message, closed:true}` und löscht den Tisch danach |
| `POST /admin/live/<code>/spectate` | `201 {code, memberId, token}`: Der Betreiber sitzt als sichtbarer Zuschauer „Betreiber“ am Tisch (ohne Hände) |
| `GET /admin/stats` | Statistik je Tisch: `tablesTotal`, `tablesStarted`, `tablesNeverStarted`, `last24h/7d/30d`, `againstBotsOnly` und `withHumans` (`tables`, `minutes{avg,median,max}`, `games{…}`), `byHumans{1..4}`, `gamesBuckets`, `gamesTotal`, `roundsTotal`, `perDay[14]` |
| `GET /admin/insights` | Auswertung: `perDay[30]{date, games}`, `byHour[24]`, `byWeekday[7]`, `peak{hour, weekday}`, `duration` und `durationWithHumans{count, avg, median, p90}` (Minuten; Pausen über 3 Stunden zählen nicht), `abort{tablesEnded, neverFinishedAGame, neverFinishedRate, rounds, roundsAborted, roundsAbortedRate}`, `gamesInPeriod`, `gamesTotal`, `since`. Zeiten in deutscher Zeit |
| `GET /admin/system` | `version`, `deployedAt` (aus `APP_VERSION`/`DEPLOYED_AT`), `startedAt`, `uptimeSeconds`, `python`, `db{kind, bytes, rows{…}}`, `runtime{botLoops, socketConnections, presenceOnline, disk, errors24h}` |
| `GET /admin/errors` | `{errors:[{id, source, where, kind, message, trace, count, firstAt, lastAt}]}` (gleiche Fehler zusammengezählt, höchstens 300, nach 30 Tagen gelöscht) |
| `DELETE /admin/errors/<id>` · `DELETE /admin/errors` | einen oder alle Einträge löschen → `{deleted}` |
| `GET /admin/site-settings` · `PUT /admin/site-settings` · `POST /admin/site-settings/reset` | Seiteneinstellungen lesen, setzen, zurücksetzen. `PUT {colors{bg, paper, yellow, coral, blue, green, lavender, orange: "#rrggbb"}, banner{enabled, text ≤ 280, tone: info|warn|alert, dismissible}, tableTheme: light|dark, friendsEnabled}`; ungültig → `400` mit Meldung |
| `GET /admin/bots` · `PUT /admin/bots` · `POST /admin/bots/reset` | Bot-Einstellungen. `GET` liefert `{values, defaults, groups[], items[]}` (der Katalog mit Texten, Grenzen und Abhängigkeiten zeichnet das Formular). `PUT {values{<Schlüssel>: Wert, …}}` setzt eine Teilmenge, gilt sofort und wird gespeichert; unbekannter Schlüssel, falsche Art, Wert außerhalb der Grenzen oder Absage-Schwelle unter Re/Kontra-Schwelle → `400` (`bad_bot_tuning`). `reset` stellt die Standardwerte her |
| `GET /admin/phrases` · `POST /admin/phrases` · `PUT /admin/phrases/<id>` · `DELETE /admin/phrases/<id>` · `POST /admin/phrases/<id>/move` `{direction: up|down}` | Chat-Sprüche pflegen |
| `GET /admin/suggestions` | alle Vorschläge, auch ausgeblendete (mit `status`) |
| `POST /admin/suggestions/<id>/status` `{status: visible|hidden}` · `PUT /admin/suggestions/<id>` `{title, description}` · `DELETE /admin/suggestions/<id>` | Vorschläge moderieren |
| `GET /admin/tables` | ältere Tischliste (`count`, `activeCount`, `humansTotal`, `connectedTotal`, `tables[]`); von der Oberfläche nicht mehr genutzt, `/admin/live` ist die Obermenge |

## Test-Tisch (`/admin/lab/…`)

Szenario-Labor für den Betreiber, ebenfalls mit Betreiber-Token. Hintergrund: [DEVELOPMENT.md](DEVELOPMENT.md#test-tisch-szenario-labor).

| Route | Zweck |
|---|---|
| `GET /admin/lab/presets` | `{presets:[{id, title, description, scenario}]}`: fertige Szenarien |
| `GET /admin/lab/tables` | Liste der Test-Tische |
| `POST /admin/lab/tables` `{scenario}` | `201 {code, version, seats:[{seat, memberId, name, isBot, token\|null}]}`. Das Token steht nur bei Plätzen, die der Betreiber selbst spielt |
| `POST /admin/lab/tables/<code>/reset` `{scenario?}` | Tisch neu aufbauen (ohne `scenario`: das gespeicherte; die Besetzung bleibt) |
| `POST /admin/lab/tables/<code>/open` | neue Tokens für die eigenen Plätze |
| `DELETE /admin/lab/tables/<code>` | Test-Tisch löschen |

Ein **Szenario** ist `{settings, dealer 0–3, hands {"0": ["Q♣", …]}, seats [{name, bot}] ×4, round {normalGamesPlayed, bockRemaining, pflichtsoloDone[4], totals[4]}, advance: none|playing|tricks, tricks}`.
Nicht angegebene Karten werden zufällig verteilt. Fehler: `400 bad_scenario` oder ein Regelfehler.

## Zugangsschutz und Begrenzungen

Alle Zähler liegen nur im Arbeitsspeicher und verschwinden beim Neustart. Die Besucheradresse stammt hinter dem Proxy aus `X-Forwarded-For` (`TRUST_PROXY=1`; IPv6 zählt je /64-Netz).

| Wo | Grenze |
|---|---|
| Neue Tische | `CREATE_PER_HOUR` (Standard 30) je Adresse und Stunde |
| Passwort, Platz-Code oder Name falsch | 8 Fehlversuche je Adresse und Tisch in 10 Minuten, danach `429`. Mitglieder des Tisches sind ausgenommen |
| Unbekannte Tisch-Codes | 20 verschiedene je Adresse in 10 Minuten. Je Code einmal gezählt, damit ein offener Tab eines beendeten Tisches niemanden sperrt |
| Tisch-Passwort | mindestens 6 Zeichen |
| Chat | 200 Zeichen, eine Nachricht je 0,8 s, 100 Nachrichten Verlauf |
| Vorschläge | 5 je Stunde und Adresse, 3 je Stunde und Browser; Daumen 120 je Stunde; Captcha 60 je Stunde |
| Betreiber-Anmeldung | 5 Fehlversuche je 10 Minuten und Adresse |
| Online-Status | 100 beobachtete Codes, 6 Einladungen je Minute |

Alle festen Werte und die zugehörigen Einstellungen: [CONFIGURATION.md](CONFIGURATION.md#6-fest-eingebaute-werte). Gespeicherte Daten: [PRIVACY.md](PRIVACY.md).
