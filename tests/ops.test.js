// Betreiber-Einstellungen, Hell/Dunkel am Tisch, Freunde ohne Konto, Vorbehalts-Nachlauf.
import test from "node:test";
import assert from "node:assert/strict";
import {
  COLOR_KEYS, DEFAULT_COLORS, applyColors, bannerKey, colorWarnings, contrastOnBlack, normalizeSettings,
} from "../src/lib/siteSettings.js";
import { THEME_KEY, effectiveTheme, readTheme, toggled, writeTheme } from "../src/lib/theme.js";
import {
  CODE_ALPHABET, FRIENDS_KEY, addFriend, applyPresence, cleanName, formatCode, friendLabel, generateCode,
  loadFriends, normalizeFriends, parseCode, removeFriend, saveFriends,
} from "../src/lib/friends.js";
import { REVEAL_MS, declarationsJustClosed, declaredAnswers } from "../src/lib/view.js";

const memory = () => {
  const data = new Map();
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => void data.set(k, String(v)),
    removeItem: (k) => void data.delete(k),
    data,
  };
};

test("Einstellungen: Standardwerte bei fehlender oder kaputter Antwort", () => {
  for (const raw of [null, undefined, "x", 5, {}, { colors: 3, banner: "no" }]) {
    const s = normalizeSettings(raw);
    assert.deepEqual(s.colors, DEFAULT_COLORS);
    assert.equal(s.banner.enabled, false);
    assert.equal(s.tableTheme, "light");
    assert.equal(s.friendsEnabled, true);
  }
});

test("Einstellungen: ungültige Farben und Banner ohne Text werden verworfen", () => {
  const s = normalizeSettings({
    colors: { yellow: "red", coral: "#ABCDEF", fremd: "#000000" },
    banner: { enabled: true, text: "   ", tone: "boom" },
    tableTheme: "neon",
    friendsEnabled: false,
  });
  assert.equal(s.colors.yellow, DEFAULT_COLORS.yellow);
  assert.equal(s.colors.coral, "#abcdef");
  assert.equal("fremd" in s.colors, false);
  assert.equal(s.banner.enabled, false);
  assert.equal(s.banner.tone, "info");
  assert.equal(s.tableTheme, "light");
  assert.equal(s.friendsEnabled, false);
});

test("Einstellungen: Bannertext wird auf Text und 280 Zeichen begrenzt", () => {
  const s = normalizeSettings({ banner: { enabled: true, text: `Wartung\n\n${"x".repeat(400)}`, tone: "warn" } });
  assert.equal(s.banner.enabled, true);
  assert.equal(s.banner.tone, "warn");
  assert.equal(s.banner.text.length, 280);
  assert.ok(!s.banner.text.includes("\n"));
});

test("Farben: nur abweichende Werte werden als CSS-Variablen gesetzt, Rest entfernt", () => {
  const props = new Map([["--nb-coral", "#123456"]]);
  const style = { setProperty: (k, v) => props.set(k, v), removeProperty: (k) => props.delete(k) };
  applyColors(style, { ...DEFAULT_COLORS, yellow: "#ff0000", coral: DEFAULT_COLORS.coral, blue: "javascript:alert(1)" });
  assert.equal(props.get("--nb-yellow"), "#ff0000");
  assert.equal(props.has("--nb-coral"), false);
  assert.equal(props.has("--nb-blue"), false);
  assert.equal(COLOR_KEYS.length, 8);
});

test("Farben: Kontrast-Warnung für sehr dunkle Farben", () => {
  assert.ok(contrastOnBlack("#ffffff") > 15);
  assert.ok(contrastOnBlack("#000000") < 1.1);
  assert.equal(colorWarnings(DEFAULT_COLORS).length, 0);
  assert.equal(colorWarnings({ ...DEFAULT_COLORS, blue: "#101030" }).length, 1);
});

test("Banner: Schlüssel ändert sich mit Text und Art", () => {
  const a = bannerKey({ text: "Wartung", tone: "warn" });
  assert.equal(a, bannerKey({ text: "Wartung", tone: "warn" }));
  assert.notEqual(a, bannerKey({ text: "Wartung 22 Uhr", tone: "warn" }));
  assert.notEqual(a, bannerKey({ text: "Wartung", tone: "alert" }));
});

test("Theme: Wahl des Besuchers vor Vorgabe des Betreibers, Standard hell", () => {
  assert.equal(effectiveTheme(null, "dark"), "dark");
  assert.equal(effectiveTheme("light", "dark"), "light");
  assert.equal(effectiveTheme("dark", "light"), "dark");
  assert.equal(effectiveTheme(undefined, undefined), "light");
  assert.equal(toggled("dark"), "light");
  assert.equal(toggled("light"), "dark");
});

test("Theme: Speichern, Lesen, kaputter Speicher", () => {
  const storage = memory();
  assert.equal(readTheme(storage), null);
  writeTheme(storage, "dark");
  assert.equal(storage.data.get(THEME_KEY), "dark");
  assert.equal(readTheme(storage), "dark");
  storage.setItem(THEME_KEY, "bunt");
  assert.equal(readTheme(storage), null);
  const broken = { getItem: () => { throw new Error("gesperrt"); }, setItem: () => { throw new Error("gesperrt"); } };
  assert.equal(readTheme(broken), null);
  assert.doesNotThrow(() => writeTheme(broken, "dark"));
});

test("Freundescode: Länge, Alphabet, Parsen", () => {
  let i = 0;
  const code = generateCode((n) => (i++ * 7) % n);
  assert.equal(code.length, 10);
  assert.ok([...code].every((ch) => CODE_ALPHABET.includes(ch)));
  assert.equal(generateCode().length, 10);
  assert.notEqual(generateCode(), generateCode());
  assert.equal(parseCode("abcde-fghjk"), "ABCDEFGHJK");
  assert.equal(parseCode(" ABCDE FGHJK "), "ABCDEFGHJK");
  for (const bad of ["ABCDEFGHJ", "ABCDEFGHJKL", "ABCDEFGHJ0", "ABCDEFGHJI", "", null, "<script>12"]) assert.equal(parseCode(bad), null);
  assert.equal(formatCode("ABCDEFGHJK"), "ABCDE-FGHJK");
  assert.equal(cleanName("  An\n na  "), "An na");
  assert.equal(cleanName("x".repeat(40)).length, 24);
});

test("Freunde: Speicher-Roundtrip, Standard ausgeschaltet, kaputte Daten", () => {
  const storage = memory();
  assert.deepEqual(loadFriends(storage), { enabled: false, code: "", name: "", friends: [] });
  const state = { enabled: true, code: "ABCDEFGHJK", name: "Anna", friends: [{ code: "MNPQRSTUVW", name: "Ben" }] };
  saveFriends(storage, state);
  assert.deepEqual(loadFriends(storage), state);
  saveFriends(storage, { enabled: false, code: "", name: "", friends: [] });
  assert.equal(storage.data.has(FRIENDS_KEY), false); // nichts übrig: Eintrag verschwindet
  for (const raw of ["{kaputt", "[]", "null", '{"enabled":true}', '{"enabled":true,"code":"ABCDEFGHJK"}']) {
    assert.equal(normalizeFriends(raw).enabled, false, raw); // ohne Code oder Namen nie „eingeschaltet“
  }
});

test("Freunde: doppelte, ungültige Codes und Obergrenze", () => {
  const n = normalizeFriends({
    enabled: true, code: "ABCDEFGHJK", name: "Anna",
    friends: [{ code: "mnpqr-stuvw", name: "Ben" }, { code: "MNPQRSTUVW" }, { code: "kurz" }, null],
  });
  assert.deepEqual(n.friends, [{ code: "MNPQRSTUVW", name: "Ben" }]);
  const own = "ABCDEFGHJK";
  assert.match(addFriend([], own, "kurz").error, /10 Zeichen/);
  assert.match(addFriend([], own, "ABCDE-FGHJK").error, /eigener Code/);
  const one = addFriend([], own, "MNPQR-STUVW", " Ben ");
  assert.deepEqual(one.friends, [{ code: "MNPQRSTUVW", name: "Ben" }]);
  assert.match(addFriend(one.friends, own, "MNPQRSTUVW").error, /schon eingetragen/);
  assert.deepEqual(removeFriend(one.friends, "MNPQRSTUVW"), []);
  const many = Array.from({ length: 50 }, (_, i) => ({ code: `AAAAAAAA${String(i + 10)}`, name: "" }));
  assert.match(addFriend(many, own, "MNPQRSTUVW").error, /höchstens 50/);
});

test("Freunde: Anzeigename und Online-Tabelle", () => {
  assert.equal(friendLabel({ code: "X", name: "Ben" }, { name: "Benny" }), "Ben");
  assert.equal(friendLabel({ code: "X", name: "" }, { name: "Benny" }), "Benny");
  assert.equal(friendLabel({ code: "X", name: "" }, undefined), "Freund");
  let live = applyPresence({}, { friends: { AAA: { online: true, name: "Ben" }, BBB: { online: false, name: "" } } });
  assert.deepEqual(live, { AAA: { name: "Ben" } });
  live = applyPresence(live, { code: "CCC", online: true, name: "Cem" });
  assert.deepEqual(Object.keys(live).sort(), ["AAA", "CCC"]);
  live = applyPresence(live, { code: "AAA", online: false });
  assert.deepEqual(Object.keys(live), ["CCC"]);
  assert.deepEqual(applyPresence(live, { friends: {} }), {}); // frischer Stand ersetzt alles
});

const view = (phase, declarations, gameNumber = 1) => ({ table: { gameNumber }, game: { phase, declarations } });

test("Vorbehaltsabfrage: Antworten bleiben nach dem Ende kurz sichtbar", () => {
  const query = view("reservation_query", ["healthy", "healthy", "healthy", null]);
  const playing = view("playing", ["healthy", "healthy", "healthy", "healthy"]);
  assert.equal(declarationsJustClosed(query, playing), true);
  assert.equal(declarationsJustClosed(playing, playing), false);
  assert.equal(declarationsJustClosed(null, playing), false);
  assert.equal(declarationsJustClosed(query, view("playing", ["healthy", "healthy", "healthy", "healthy"], 2)), false);
  assert.equal(declarationsJustClosed(query, view("reservation_query", ["healthy", null, null, null])), false);
  assert.ok(REVEAL_MS >= 3000);
});

test("Vorbehaltsabfrage: Liste in Abfrage- und Folgephasen, im Spiel nur im Nachlauf", () => {
  const d = ["healthy", "reservation", null, null];
  assert.deepEqual(declaredAnswers(view("reservation_query", d)), [{ seat: 0, d: "healthy" }, { seat: 1, d: "reservation" }]);
  for (const phase of ["reservation_resolution", "baptism", "poverty_pass", "poverty_offer", "poverty_return"])
    assert.equal(declaredAnswers(view(phase, d)).length, 2, phase);
  assert.deepEqual(declaredAnswers(view("playing", d)), []);
  assert.equal(declaredAnswers(view("playing", d), true).length, 2);
  assert.deepEqual(declaredAnswers(null), []);
});

test("Socket: Nachricht des Betreibers wird an den Handler gereicht", async () => {
  const { createRoomSocket } = await import("../src/lib/socket.js");
  const listeners = {};
  const fake = { on: (e, f) => (listeners[e] = f), emit() {}, removeAllListeners() {}, disconnect() {} };
  const got = [];
  createRoomSocket({ ioFactory: () => fake, origin: "x", code: "ABC234", token: "t", handlers: { onNotice: (n) => got.push(n) } });
  listeners["room:notice"]({ message: "Wartung", closed: true });
  assert.deepEqual(got, [{ message: "Wartung", closed: true }]);
});
