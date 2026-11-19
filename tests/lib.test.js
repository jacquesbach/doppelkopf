import test from "node:test";
import assert from "node:assert/strict";
import { makeView } from "./helpers.js";
import { cardId, parseCardId, rankLabel, cardName } from "../src/lib/cards.js";
import { announceLabel, scoreItemLabel, gameTypeLabel, kindLabel } from "../src/lib/labels.js";
import { matchRoute, buildPath, inviteLink } from "../src/lib/router.js";
import { createSessions } from "../src/lib/sessions.js";
import { ApiError, createApi, socketOrigin } from "../src/lib/api.js";
import { createRoomSocket } from "../src/lib/socket.js";
import * as V from "../src/lib/view.js";
import { chatToast, describeEvent, justFinished, newEvents, snippet } from "../src/lib/events.js";
import { TAKEOVER_OPTIONS, takeoverLabel } from "../src/lib/labels.js";
import { SPRUECHE } from "../src/lib/sprueche.js";

function memoryStorage() {
  const map = new Map();
  return { getItem: (k) => map.get(k) ?? null, setItem: (k, v) => map.set(k, v), removeItem: (k) => map.delete(k) };
}

test("Karten: ID, Parser, Beschriftungen", () => {
  const card = { rank: "10", suit: "♥", copy: 1 };
  assert.equal(cardId(card), "10-♥-1");
  assert.deepEqual(parseCardId("Q-♣-0"), { rank: "Q", suit: "♣", copy: 0 });
  assert.equal(parseCardId("kaputt"), null);
  assert.equal(rankLabel("Q"), "D");
  assert.equal(rankLabel("J"), "B");
  assert.equal(cardName(card), "Herz Zehn");
});

test("Labels: Ansagen, Wertungsposten, Spielarten", () => {
  assert.equal(announceLabel(0, "re"), "Re");
  assert.equal(announceLabel(0, "kontra"), "Kontra");
  assert.equal(announceLabel(2, "re"), "keine 60");
  assert.equal(scoreItemLabel("win"), "Gewonnen");
  assert.equal(scoreItemLabel("announced_re"), "Re angesagt");
  assert.equal(scoreItemLabel("called_kontra_no_30"), "Kontra: keine 30 angesagt");
  assert.equal(scoreItemLabel("beat_black"), "Absage „schwarz“ geschlagen");
  assert.equal(gameTypeLabel("solo_aces"), "Fleischloser");
  assert.equal(kindLabel("silent_wedding"), "Stille Hochzeit");
});

test("Router: Pfade erkennen und bauen", () => {
  assert.deepEqual(matchRoute("/"), { name: "landing" });
  assert.deepEqual(matchRoute("/neu/"), { name: "create" });
  assert.deepEqual(matchRoute("/beitreten/ab12"), { name: "join", code: "AB12" });
  assert.deepEqual(matchRoute("/tisch/XYZ9"), { name: "table", code: "XYZ9" });
  assert.deepEqual(matchRoute("/impressum"), { name: "legal", page: "impressum" });
  assert.equal(matchRoute("/gibtsnicht").name, "notfound");
  assert.equal(buildPath("table", { code: "AB12" }), "/tisch/AB12");
  assert.equal(inviteLink("https://doko.example", "AB12"), "https://doko.example/beitreten/AB12");
});

test("Sessions: pro Raum merken, Namen merken, kaputte Daten verkraften", () => {
  const storage = memoryStorage();
  const s = createSessions(storage);
  assert.equal(s.get("ab12"), null);
  s.set("ab12", { token: "t", memberId: 4 });
  assert.deepEqual(s.get("AB12"), { token: "t", memberId: 4 });
  s.remove("AB12");
  assert.equal(s.get("AB12"), null);
  s.rememberName("Jakob");
  assert.equal(s.lastName(), "Jakob");
  storage.setItem("doko.sessions.v1", "{kaputt");
  assert.equal(s.get("AB12"), null);
});

test("API: Header + Token im Body, Fehler werden zu ApiError", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    if (url.endsWith("/action"))
      return { ok: false, status: 409, json: async () => ({ error: "Veraltet", code: "version_conflict", version: 9 }) };
    return { ok: true, status: 200, json: async () => ({ ok: true }) };
  };
  const api = createApi({ baseUrl: "/api", fetchImpl });
  await api.setReady("AB12", "tok", true);
  assert.equal(calls[0].url, "/api/rooms/AB12/ready");
  assert.equal(calls[0].init.headers["X-Session-Token"], "tok");
  assert.equal(JSON.parse(calls[0].init.body).token, "tok");
  await assert.rejects(
    () => api.action("AB12", "tok", { type: "play_card", cardId: "A-♣-0" }, 3),
    (e) => e instanceof ApiError && e.isVersionConflict && e.version === 9 && e.status === 409,
  );
  const sent = JSON.parse(calls[1].init.body);
  assert.equal(sent.expectedVersion, 3);
  assert.ok(sent.actionId.length > 8);
  const offline = createApi({ fetchImpl: async () => { throw new Error("x"); } });
  await assert.rejects(() => offline.getRoom("AB12"), (e) => e.code === "network");
  assert.equal(socketOrigin("/api", { origin: "https://x.de" }), "https://x.de");
  assert.equal(socketOrigin("http://h:5000/api", null), "http://h:5000");
});

test("Socket: meldet sich bei jedem Verbinden an und leitet Ereignisse weiter", () => {
  const listeners = {};
  const emitted = [];
  const fake = {
    on: (name, fn) => (listeners[name] = fn),
    emit: (...a) => emitted.push(a),
    disconnect() { this.closed = true; },
    removeAllListeners() {},
  };
  const got = [];
  const sock = createRoomSocket({
    ioFactory: () => fake, origin: "", code: "AB12", token: "tok",
    handlers: { onGame: (v) => got.push(v), onStatus: (s) => got.push(s), onChat: (m) => got.push(m) },
  });
  listeners.connect();
  listeners.connect();
  assert.equal(emitted.length, 2);
  assert.deepEqual(emitted[0], ["room:watch", { code: "AB12", token: "tok" }]);
  listeners["game:state"]({ version: 2 });
  listeners["chat:message"]({ id: 1 });
  listeners.disconnect();
  assert.deepEqual(got, ["online", "online", { version: 2 }, { id: 1 }, "offline"]);
  sock.close();
  assert.ok(fake.closed);
});

test("View: Sitzpositionen relativ zu mir", () => {
  assert.equal(V.placementOf(2, 2), "bottom");
  assert.equal(V.placementOf(3, 2), "left");
  assert.equal(V.placementOf(0, 2), "top");
  assert.equal(V.placementOf(1, 2), "right");
  assert.equal(V.placementOf(1, null), "left");
});

test("View: Dialoge, Zugrecht und erlaubte Karten kommen vom Server", () => {
  const declare = makeView({
    game: { phase: "reservation_query", querySeat: 0, legalActions: [{ type: "declare", options: ["healthy", "reservation"] }] },
  });
  assert.equal(V.activeDialog(declare).type, "declare");
  assert.ok(V.isMyTurn(declare));
  const playing = makeView({
    mySeat: 1,
    game: { turn: 1, legalActions: [{ type: "play_card", cards: ["A-♣-0", "K-♣-1"] }, { type: "announce", levels: [0, 1] }] },
  });
  assert.equal(V.activeDialog(playing), null);
  assert.deepEqual([...V.playableIds(playing)], ["A-♣-0", "K-♣-1"]);
  assert.deepEqual(V.announceOptions(playing), [
    { level: 0, label: "Re" },
    { level: 1, label: "keine 90" },
  ]);
  const other = makeView({ mySeat: 0, game: { turn: 3 } });
  assert.ok(!V.isMyTurn(other));
  assert.equal(V.statusText(other), "Dirk ist am Zug.");
  const mandatory = makeView({ game: { turn: 0, mandatoryAnnouncementSeat: 2 } });
  assert.equal(V.actingSeat(mandatory), 2);
  assert.match(V.statusText(mandatory), /Cleo muss Re oder Kontra ansagen/);
});

test("View: Stich, Ansagen, Marken, Überschrift", () => {
  const view = makeView({
    mySeat: 0,
    game: {
      currentTrick: [{ seat: 3, card: { rank: "A", suit: "♦", copy: 0 } }],
      announcements: [
        { seat: 2, party: "re", level: 0 },
        { seat: 2, party: "re", level: 1 },
        { seat: 3, party: "kontra", level: 0 },
      ],
      schweinchenSeat: 1,
    },
  });
  assert.equal(V.trickBySeat(view)[3].rank, "A");
  assert.deepEqual(V.announcementsBySeat(view), { 2: "keine 90", 3: "Kontra" });
  assert.deepEqual(V.seatBadges(view, 0), ["Re"]);
  assert.deepEqual(V.seatBadges(view, 1), ["Geber", "Schweinchen"]);
  assert.equal(V.gameHeadline(view), "Spiel 3 · Normalspiel");
});

test("View: Rangliste mit gleichen Plätzen und Ergebnis-Zusammenfassung", () => {
  const view = makeView({
    table: { round: { totals: [3, -3, 3, -3] } },
    game: {
      phase: "finished",
      bockTriggers: ["zero_game"],
      score: {
        winner: "re",
        points: { re: 130, kontra: 110 },
        net: 3,
        multiplier: 2,
        seatDeltas: [3, -3, 3, -3],
        items: { re: [{ code: "win", points: 1 }, { code: "fox_caught", points: 1 }], kontra: [] },
      },
    },
  });
  const ranking = V.roundRanking(view);
  assert.deepEqual(ranking.map((r) => [r.name, r.rank]), [["Anna", 1], ["Cleo", 1], ["Ben", 3], ["Dirk", 3]]);
  const result = V.resultSummary(view);
  assert.equal(result.winnerLabel, "Re");
  assert.equal(result.items.re[1].label, "Fuchs gefangen");
  assert.equal(result.multiplier, 2);
  assert.deepEqual(result.bockTriggers, ["Nullspiel"]);
  assert.equal(V.resultSummary(makeView()), null);
});

test("View: gezeigter Stich – laufender, sonst der beendete mit Gewinner", () => {
  const card = (rank, suit) => ({ rank, suit, copy: 0 });
  const running = makeView({ game: { currentTrick: [{ seat: 1, card: card("A", "♣") }] } });
  assert.deepEqual(V.shownTrick(running), { plays: running.game.currentTrick, complete: false, winnerSeat: null });
  const lastTrick = { number: 2, winnerSeat: 3, points: 14, plays: [{ seat: 1, card: card("K", "♣") }] };
  const between = makeView({ game: { currentTrick: [], lastTrick } });
  assert.deepEqual(V.shownTrick(between), { plays: lastTrick.plays, complete: true, winnerSeat: 3 });
  assert.equal(V.shownTrick(makeView({ game: { phase: "reservation_query" } })).plays.length, 0);
  assert.equal(V.shownTrick(makeView()).complete, false);
});

test("View: Hold, Bot-Übernahme und Statustext", () => {
  const view = makeView({ table: { holding: true }, game: { turn: 2 } });
  assert.ok(V.isHolding(view));
  assert.match(V.statusText(view), /Nächster Stich/);
  assert.ok(!V.isHolding(makeView()));
  const away = makeView({ mySeat: 1 });
  away.table.seats[1].autoplay = true;
  assert.ok(V.myAutoplay(away));
  assert.ok(V.seatBadges(away, 1).includes("Bot übernimmt"));
  assert.ok(!V.myAutoplay(makeView({ mySeat: null })));
});

test("API: Weiter, Platz übergeben/zurückholen und Wiedereintritt", async () => {
  const calls = [];
  const api = createApi({
    fetchImpl: async (url, init) => (calls.push({ url, init }), { ok: true, status: 200, json: async () => ({}) }),
  });
  await api.continueGame("AB12", "t");
  await api.away("AB12", "t");
  await api.back("AB12", "t");
  await api.rejoin("AB12", { name: "Anna", password: "" });
  assert.deepEqual(calls.map((c) => c.url), [
    "/api/rooms/AB12/continue", "/api/rooms/AB12/away", "/api/rooms/AB12/back", "/api/rooms/AB12/rejoin",
  ]);
  assert.equal(JSON.parse(calls[3].init.body).name, "Anna");
  assert.equal(calls[3].init.headers["X-Session-Token"], undefined);
});

test("View: Gewinnernamen aus den Re-Sitzen", () => {
  const view = makeView();
  assert.deepEqual(V.partyNames(view, [0, 2], "kontra"), { re: ["Anna", "Cleo"], kontra: ["Ben", "Dirk"], winners: ["Ben", "Dirk"] });
  assert.deepEqual(V.partyNames(view, [1], "re").winners, ["Ben"]);
  assert.deepEqual(V.partyNames(view, [0, 1], null).winners, []);
  assert.deepEqual(V.partyNames(view, null, "re"), { re: [], kontra: [], winners: [] });
});

test("Ereignisse: nur neue, nie beim ersten Laden; Texte", () => {
  const ev = (id, type, extra = {}) => ({ id, type, ...extra });
  const a = makeView({ game: { events: [ev(2, "reservation", { seat: 1 })] } });
  const b = makeView({ game: { events: [ev(2, "reservation", { seat: 1 }), ev(5, "announce", { seat: 0, party: "re", level: 0 })] } });
  assert.deepEqual(newEvents(null, b), []);                       // erstes Laden: nichts nachreichen
  assert.deepEqual(newEvents(a, b).map((e) => e.id), [5]);
  assert.deepEqual(newEvents(b, b), []);
  const next = makeView({ table: { gameNumber: 4 }, game: { events: [ev(1, "reservation", { seat: 2 })] } });
  assert.equal(newEvents(b, next).length, 1);                     // neues Spiel: alles zeigen
  assert.match(describeEvent(b, b.game.events[1]).text, /Anna sagt Re an/);
  assert.match(describeEvent(b, ev(7, "announce", { seat: 3, party: "kontra", level: 1 })).text, /Dirk \(Kontra\).*keine 90/);
  assert.match(describeEvent(b, ev(8, "fox_caught", { seat: 0, victim: 1 })).text, /Anna fängt den Fuchs von Ben/);
  assert.match(describeEvent(b, ev(9, "doppelkopf", { seat: 2, points: 43 })).text, /43 Augen/);
  assert.match(describeEvent(b, ev(10, "solo", { seat: 1, gameType: "solo_queens" })).text, /Ben spielt Damen-Solo/);
  assert.equal(describeEvent(b, ev(11, "unbekannt")), null);
});

test("View: Hausregel-Etiketten", () => {
  const tags = V.activeRuleLabels({ sharp_doppelkopf: true, dulle: true, karlchen: false, fuchsjagd: true, schweinchen: true });
  assert.deepEqual(tags, ["Ohne Neuner", "Mit Dullen", "Ohne Karlchen", "Fuchsjagd", "Schweinchen"]);
  assert.deepEqual(V.activeRuleLabels(null), []);
});

test("Chat-Hinweis: Kurzfassung, Titel, Antworten-Aktion", () => {
  assert.equal(snippet("Hallo   du\nda"), "Hallo du da");
  assert.equal(snippet("x".repeat(70)), "x".repeat(70));
  const long = snippet("wort ".repeat(40));
  assert.ok(long.length <= 70 && long.endsWith("…"), long);
  assert.equal(snippet(null), "");
  const t = chatToast({ id: 7, name: "Anna", text: "Kommt ihr?" });
  assert.equal(t.key, "chat-7");
  assert.equal(t.kind, "chat");
  assert.equal(t.title, "Chat · Anna");
  assert.equal(t.text, "Kommt ihr?");
  assert.deepEqual(t.action, { label: "Antworten", kind: "chat" });
});

test("Spielende erkennen: nur beim Übergang im selben Spiel, nicht beim ersten Laden", () => {
  const playing = makeView({ game: { phase: "playing" } });
  const done = makeView({ game: { phase: "finished" } });
  assert.equal(justFinished(playing, done), true);
  assert.equal(justFinished(null, done), false);
  assert.equal(justFinished(done, done), false);
  const nextGame = makeView({ game: { phase: "finished" }, table: { gameNumber: 4 } });
  assert.equal(justFinished(playing, nextGame), false);
});

test("Bot-Übernahme: Countdown und Zuordnung des Dialogs", () => {
  assert.equal(V.countdownLeft(30, 1000, 1000), 30);
  assert.equal(V.countdownLeft(30, 1000, 11000), 20);
  assert.equal(V.countdownLeft(5, 0, 60000), 0);
  const none = makeView({ mySeat: 1 });
  assert.equal(V.takeoverWarning(none), null);
  assert.equal(V.isMyTakeoverWarning(none), false);
  const warned = makeView({ mySeat: 1, table: { takeoverWarning: { seat: 1, remaining: 25 } } });
  assert.equal(V.isMyTakeoverWarning(warned), true);
  const other = makeView({ mySeat: 2, table: { takeoverWarning: { seat: 1, remaining: 25 } } });
  assert.equal(V.isMyTakeoverWarning(other), false);
  assert.deepEqual(V.takeoverWarning(other), { seat: 1, remaining: 25 });
  const spectator = makeView({ mySeat: null, table: { takeoverWarning: { seat: 1, remaining: 25 } } });
  assert.equal(V.isMyTakeoverWarning(spectator), false);
});

test("Bot-Übernahme: Auswahl enthält „Nie“ und beschriftet Werte", () => {
  assert.deepEqual(TAKEOVER_OPTIONS[0], [0, "Nie"]);
  assert.equal(takeoverLabel(180), "3 Minuten");
  assert.equal(takeoverLabel(45), "45 s");
});

test("API: Übernahme-Endpunkte senden Sekunden bzw. remember", async () => {
  const calls = [];
  const api = createApi({
    baseUrl: "/api",
    fetchImpl: async (url, init) => (calls.push({ url, body: JSON.parse(init.body) }), { ok: true, json: async () => ({}) }),
  });
  await api.setTakeover("AB12", "tok", 300);
  await api.stay("AB12", "tok", true);
  await api.stay("AB12", "tok");
  assert.equal(calls[0].url, "/api/rooms/AB12/takeover");
  assert.equal(calls[0].body.seconds, 300);
  assert.equal(calls[1].url, "/api/rooms/AB12/stay");
  assert.equal(calls[1].body.remember, true);
  assert.equal("remember" in calls[2].body, false);
});

test("Chat-Sprüche: vollständig, eindeutig und sendbar (≤ 200 Zeichen, nicht leer)", () => {
  assert.equal(SPRUECHE.length, 8);
  assert.equal(new Set(SPRUECHE).size, SPRUECHE.length);
  for (const s of SPRUECHE) {
    assert.ok(s.trim().length > 0 && s.length <= 200, s);
    assert.equal(s, s.trim());
  }
  assert.ok(SPRUECHE.includes("Hinten sind die Enten fett."));
});
