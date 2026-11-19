# Backend-API (Stand Meilenstein 3)

Alle Pfade unter `/api`. **Authentifizierung:** Sitzungs-Token im Header `X-Session-Token` (bei POST alternativ als `token` im JSON-Body).
Der **Sitz** eines Handelnden ergibt sich ausschließlich aus dem Token. `seat`/`memberId` im Body werden ignoriert.
**Bots** authentifizieren sich nie über HTTP (sie handeln serverseitig).

## Regeln (Lobby)
| Methode, Pfad | Wer | Zweck |
|---|---|---|
| `GET /rule-schema` | alle | `{"options":[{id, group, default, label, description, requires}]}` für die Einstellungsseite |
| `POST /rooms` `{name, password?, settings?}` | alle | Raum anlegen; `settings` = `{"sharp_doppelkopf": bool, "dulle": bool, ...}` (fehlende Schlüssel = Default) |
| `POST /rooms/<code>/settings` `{settings}` | Host, nicht während einer Runde | Regeln ändern; Antwort `{settings, profileId}` |

`room` (in allen Raumantworten und `room:state`) enthält zusätzlich `settings`, `profileId` (`ddv_tsr_2026` / `house_no_nines` / `custom`) und `isOfficialDdv`.
Ungültige Optionen → `400` mit `code` (`unknown_option`, `invalid_option_value`, `invalid_option_combination`).

## Raum
| Methode, Pfad | Wer | Zweck |
|---|---|---|
| `POST /rooms/<code>/join` `{name, role?, password?}` | alle | beitreten (`role`: `player`/`spectator`) → `{room, token, memberId}` |
| `GET /rooms/<code>` | alle (Token optional) | Raum; mit Token wird `isMe` gesetzt und die Anwesenheit aktualisiert |
| `POST /rooms/<code>/ready` `{ready}` | Spieler | Bereitschaft |
| `POST /rooms/<code>/bots` | Host, vor dem Start | füllt **alle** freien Plätze mit Bots |
| `GET /rooms/public` | – | Öffentliche Tische mit freien Plätzen: `{rooms: [{code, host, players, playerCount, hasPassword, settings, isOfficialDdv, createdAt}]}`. Nur Tische im Wartezustand, an denen sich in den letzten 90 s ein Mensch gemeldet hat (max. 30) |
| `POST /rooms/<code>/visibility` `{public}` | Host | Tisch öffentlich (Tischliste) oder privat (nur per Link) stellen. `POST /rooms` nimmt dafür `public: true` an; `room.isPublic` steht in jeder Raumsicht |
| `POST /rooms/<code>/rejoin` `{name, password?}` | alle | **Platz zurückholen** (anderes Gerät, gelöschter Browserspeicher): Name eines *nicht verbundenen* Spielers + ggf. Passwort → neues `{room, token, memberId}`; das alte Token wird ungültig. `404` kein Spieler mit dem Namen, `409` Spieler ist gerade verbunden |
| `POST /rooms/<code>/leave` | Mitglied | Tisch verlassen. `409`, solange eine Runde läuft (Spieler). Host-Wechsel auf den ältesten Spieler; ohne Menschen wird der Raum geschlossen: `{left, closed}` |
| `GET /rooms/<code>/chat` | Mitglied (auch Zuschauer) | `{messages:[{id, memberId, name, text, ts}]}` (letzte 100) |
| `POST /rooms/<code>/chat` `{text}` | Mitglied (auch Zuschauer) | Nachricht senden; `400` leer/zu lang (>200), `429` `rate_limited` (< 0,8 s Abstand) → `201 {message}` |

## Spiel
| Methode, Pfad | Wer | Zweck |
|---|---|---|
| `POST /rooms/<code>/start` | Host | Runde starten (4 bereite Spieler; Regeln aus dem Raum). Auch nach beendeter Runde für eine neue. `201 {version, view}` |
| `GET /rooms/<code>/game` | Mitglied | eigene Sicht `{version, table, game}` |
| `POST /rooms/<code>/action` `{type, ..., expectedVersion?, actionId?}` | Spieler | Spielzug (siehe unten). `200 {version, duplicate, view}` |
| `POST /rooms/<code>/continue` | Spieler | „Nächster Stich“: nur im Spiel gegen Bots (genau ein Mensch). Davor wartet der Botbetrieb (`table.holding = true`) |
| `POST /rooms/<code>/away` | Spieler | Tisch verlassen, **während die Runde läuft**: ein Bot spielt den Sitz weiter (`seats[i].autoplay = true`), der Sitz bleibt dem Spieler zugeordnet |
| `POST /rooms/<code>/stay` `{remember?}` | Spieler | „Weiterspielen“: beendet den Countdown der Bot-Übernahme und startet die Inaktivitätsuhr neu. `remember: true` = für diesen Spieler nie Bot-Übernahme (bleibt über Runden), `false` = wieder zulassen, fehlt = unverändert |
| `POST /rooms/<code>/takeover` `{seconds}` | Host | Bot-Übernahme bei Inaktivität: `0` (nie), `60`, `120`, `180` (Standard), `300`, `600`, `1800`. Auch in der Lobby und während der Runde; `room.botTakeover` zeigt den Wert |
| `POST /rooms/<code>/back` | Spieler | Platz vom Bot zurückholen. Jede eigene Aktion tut das auch |
| `POST /rooms/<code>/next` | Spieler | nächstes Spiel der Runde geben (erst nach beendetem Spiel) |
| `GET /rooms/<code>/history` | Mitglied | `{games:[{gameNumber, kind, gameType, soloSeat, winner, seatDeltas, multiplier, bockTriggers, totals, roundFinished, ...}]}` |

Entfernt gegenüber Meilenstein 0: `/play`, `/announce`, globales `/history` (listete Raumcodes aller Räume).

### Aktionen (`type`)
`declare {reservation: bool}` · `resolve {accept: bool}` · `baptize {choice: "wedding" | "solo_clubs" | ...}` ·
`play_card {cardId}` · `announce {level: 0..4}` (0 = Re/Kontra, 1–4 = keine 90/60/30/schwarz) · `schweinchen {}`.
Hausregel Armut (`ruleOptions.poverty`): `baptize {choice: "poverty"}` bzw. `resolve {accept}` in der Stufe `poverty` · `poverty_pass {cardIds: [3 IDs]}` ·
`poverty_offer {accept: bool}` · `poverty_return {cardIds: [3 IDs]}`.
Welche Aktionen gerade erlaubt sind, steht in `game.legalActions` der eigenen Sicht (inkl. erlaubter Karten und Ansage-Stufen).
`expectedVersion` (Version aus der letzten Sicht) schützt vor veralteten Zügen; `actionId` (≤ 64 Zeichen) macht Wiederholungen idempotent
(`duplicate: true`, keine zweite Wirkung, keine zweite Benachrichtigung).

### Sicht (`view`)
`{version, table: {seats, mySeat, gameNumber, finished, profileId, deckVariant, ruleOptions, round: {dealer, normalGamesPlayed, pflichtsoloDone, totals, bockRemaining, results, next?}}, game: {...}}`.
`game` ist `player_view` (eigene Hand, `myParty`, `legalActions`) bzw. `spectator_view` (nie Hände, nie verdeckte Parteien).
Für die Oberfläche relevante Felder in `game`: `hand` (bereits sortiert: Trümpfe nach Stärke, dann Fehlfarben ♣♠♥♦), `legalActions`,
`baptismKind` (`pflichtsolo`/`pflichtsolo_forced`/`lustsolo`, `null` = einziger Vorbehalt: Hochzeit oder Solo), `currentTrick`, `lastTrick`,
`announcements`, `tricksWon`, `handCounts`, `mandatoryAnnouncementSeat`.
Armut: Phasen `poverty_pass` → `poverty_offer` → `poverty_return`; `game.poverty = {seat, buyer, offerSeat}` (Armut-Anmelder, Käufer, wer gerade gefragt wird);
`legalActions`: `poverty_pass {count, cards}`, `poverty_offer`, `poverty_return {count, cards, received}` (`received` = soeben erhaltene Karten, nur dem Käufer);
Beide Armut-Partner sind Re (`clarified` von Beginn an gesetzt). Ohne Käufer gibt der Tisch sofort neu (gleicher Geber, gleiche Spielnummer);
`table.redeals` zählt die Neuwürfe dieses Spiels, `table.redealSeat` nennt den Armen, dessen Armut niemand wollte.
`game.povertyPassed` (nur der Arme, solange gefragt wird: seine abgelegten Karten); `kind: "poverty"` bzw. `baptize`-Auswahl `"poverty"`.
Nach Spielende werden Stiche, Parteien und Wertung aufgedeckt. Die Stille Hochzeit bleibt bis Spielende verdeckt.

### Fehlercodes
`403` keine/ungültige Sitzung, Zuschauer, nicht am Tisch · `404` kein Spiel · `400` `bad_request`/`unknown_action`/… ·
`409` Regelverstoß (`not_your_turn`, `must_follow`, `wrong_phase`, `mandatory_announcement`, `announcement_too_late`, `game_running`, `round_finished`, …) ·
`409` `version_conflict` mit aktueller `version` · `429` `rate_limited` (Chat).

### Getakteter Botbetrieb
Bots spielen **nicht** innerhalb des Requests, sondern einzeln im Hintergrund (je Zug eine neue `game:state`-Version):
Bedenkzeit 1,0–1,7 s je Karte, 0,9 s für Vorbehalt/Taufe/Ansage, 2,4 s nach einem vollständigen Stich.
Bei Inaktivität übernimmt ein Bot (`autoplay`) – aber nur, wenn der Host es nicht abgeschaltet hat (`table.takeover`, 0 = nie), der Spieler
nicht abgelehnt hat (`seats[i].noTakeover`) und mindestens zwei Menschen selbst am Tisch spielen (ein Mensch allein gegen Bots wird nie ersetzt).
Ist ein Mensch länger als `table.takeover` Sekunden ohne Änderung am Tisch an der Reihe, läuft ein Countdown von 30 s
(`table.takeoverWarning = {seat, remaining}` in der Sicht aller); danach übernimmt der Bot. Jede Änderung am Tisch, `/stay` oder ein Zug beendet den
Countdown. Kommt der Spieler zurück, übernimmt er wieder. Tische ohne Aktivität werden nach 12 Stunden geschlossen (gelöscht).
`view.table.holding` und `view.table.seats[i].autoplay` steuern die Oberfläche; `view.game.lastTrick` bleibt nach dem Stich sichtbar.

### Ereignisse und Stiche in der Sicht
- `game.events`: öffentliche Ereignisse des laufenden Spiels, aufsteigende `id`: `reservation`, `solo`, `wedding`, `wedding_clarified`,
  `poverty` (`seat`), `poverty_taken` (`seat` = Armer, `buyer`), `poverty_void` (`seat`; erscheint nur kurz, danach beginnt das Protokoll des neuen Blatts von vorn), `announce` (`party`, `level`), `schweinchen`, `doppelkopf` (`points`), `fox_caught` (`seat` = Fänger, `victim`),
  `charlie_last_trick`. „Fuchs gefangen“ wird nur gemeldet, wenn beide Kreuz-Damen gespielt sind oder eine Hochzeit geklärt ist (sonst würde es verdeckte
  Parteien verraten); die Wertung am Spielende nennt ihn immer.
- Nach Spielende zusätzlich `game.tricks` (alle Stiche in Spielreihenfolge) und `game.reSeats`; das Spielprotokoll enthält `reSeats` je Spiel.

## Socket.IO
Client sendet `room:watch {code, token}` (Bots/ungültige Tokens werden abgewiesen). Server sendet
`room:state` (Raum, ohne `isMe`), `game:state` (**eigene** Sicht `{version, table, game}`, nur an `member:<id>`), `chat:message` (Chat-Nachricht an alle am Tisch), `room:error`.
Hinweis: Die Form von `game:state` hat sich geändert (vorher `{game, version}`).

## Vorschläge, Sprüche und Betreiber (`/api/...`)
Alle Fehler: `{"error": "Text", "code": "..."}`. Die Browser-Kennung (`X-Client-Id`, 8–64 Zeichen `A-Za-z0-9_-`) wird nur als HMAC-Hash gespeichert.

**Öffentlich**
- `GET /captcha` → `{token, svg}`. Das Token ist signiert, 10 Minuten gültig und einmal verwendbar (auch nach falscher Antwort). 60 Abrufe/Std. je Adresse.
- `GET /phrases` → `{phrases: [{id, text}]}` in der vom Betreiber festgelegten Reihenfolge (Chat-Auswahl).
- `GET /suggestions` → `{suggestions: [{id, title, description, createdAt, votes, voted}]}`, beliebteste zuerst (Gleichstand: älterer zuerst); `voted` nur mit `X-Client-Id`.
- `POST /suggestions` `{title, description, captchaToken, captchaAnswer, website}` → 201 `{suggestion}`. Titel 4–80, Beschreibung 10–500 Zeichen, keine Links.
  `website` ist ein Honigtopf (muss leer sein). Texte werden **vor** dem Captcha geprüft, damit ein Tippfehler das Captcha nicht verbraucht.
  Fehlercodes: `captcha_wrong|expired|used|malformed`, `links_not_allowed`, `duplicate` (409), `rate_limited` (429; 5/Std. je Adresse, 3/Std. je Browser).
- `POST /suggestions/<id>/vote` (Header `X-Client-Id` nötig) → `{votes, voted}`; ein zweiter Aufruf nimmt den Daumen zurück. 404 bei unbekannten/ausgeblendeten Vorschlägen. 120/Std. je Adresse.

**Betreiber** (Umgebungsvariable `ADMIN_PASSWORD`; ohne sie antworten alle `/admin/...`-Routen mit 503 `admin_disabled`)
- `GET /admin/status` → `{enabled}`; `POST /admin/login` `{password}` → `{token, expiresIn}` (8 Std.; 5 Fehlversuche je 10 Min. und Adresse, dann 429).
- Alle weiteren Routen mit `Authorization: Bearer <token>` (sonst 401):
  - `GET /admin/tables` → offene Tische: `code, status, state (active|idle), idleSeconds, activeSince, createdAt, startedAt, lastActivityAt, humans, bots, connectedHumans, spectators, againstBotsOnly, isPublic, hasPassword, game`; dazu `count, activeCount, humansTotal, connectedTotal`. „Aktiv“ = letzte Aktion vor höchstens 5 Minuten.
  - `GET /admin/stats` → `tablesTotal, tablesStarted, tablesNeverStarted, last24h/7d/30d, againstBotsOnly|withHumans {tables, minutes{avg,median,max}, games{…}}, byHumans {1..4}, minutes, games, gamesBuckets, gamesTotal, roundsTotal, perDay[14]`.
  - `GET|POST /admin/phrases`, `PUT|DELETE /admin/phrases/<id>`, `POST /admin/phrases/<id>/move {direction: up|down}`.
  - `GET /admin/suggestions` (inkl. ausgeblendete, mit `status`), `POST /admin/suggestions/<id>/status {status: visible|hidden}`, `PUT /admin/suggestions/<id> {title, description}`, `DELETE /admin/suggestions/<id>`.
  - **Test-Tisch** (Szenario-Labor, siehe `IMPLEMENTATION_NOTES.md`):
    - `GET /admin/lab/presets` → `{presets: [{id, title, description, scenario}]}`.
    - `POST /admin/lab/tables {scenario}` → 201 `{code, version, seats: [{seat, memberId, name, isBot, token|null}]}`; Token nur für Plätze, die der Betreiber selbst spielt. Szenario: `{settings, dealer 0–3, hands {"0": ["Q♣", …]}, seats [{name, bot}] ×4, round {normalGamesPlayed, bockRemaining, pflichtsoloDone[4], totals[4]}, advance none|playing|tricks, tricks}`. Nicht angegebene Karten werden zufällig verteilt; Fehler → 400 `bad_scenario` bzw. Regelfehler.
    - `POST /admin/lab/tables/<code>/reset {scenario?}` → Tisch neu aufbauen (ohne `scenario`: gespeichertes Szenario; die Besetzung bleibt). `POST /admin/lab/tables/<code>/open` → neue Tokens für die eigenen Plätze. `DELETE /admin/lab/tables/<code>`. `GET /admin/lab/tables` → Liste.

## Betrieb
- `ADMIN_PASSWORD` schaltet das Betreiber-Backend (`/admin` im Frontend) frei; `APP_ENV=production` verlangt dafür mindestens 10 Zeichen.
  `TRUST_PROXY=1` (hinter nginx) nimmt für die Begrenzungen die letzte Adresse aus `X-Forwarded-For`.
- Statistik: je angelegtem Tisch ein Eintrag `table_log` (Zeiten, Menschen/Bots, Spiele, Runden) – bleibt bestehen, auch wenn der Tisch nach 12 Stunden abgeräumt wird.
  Die mitgelieferten acht Sprüche werden einmalig beim ersten Start eingetragen (Marker `setting.phrases_seeded`); wer alle löscht, bekommt sie nicht zurück.
- `APP_ENV=production` verlangt ein gesetztes `SECRET_KEY`. Der Flask-Debugger läuft nur mit `FLASK_DEBUG=1`.
- Spielstand pro Raum als JSON in `GameSnapshot` (`schema_version` 2); Altstände (Meilenstein 0) werden ignoriert.
  Neue Spalten (`room.settings_json`, `game_snapshot.schema_version`) ergänzt `create_app` bei bestehenden SQLite-Dateien automatisch.
- Schreibzugriffe: Sperre pro Raum im Prozess + optimistische Versionssperre in der Datenbank.
