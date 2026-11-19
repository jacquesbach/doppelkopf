import test from "node:test";
import assert from "node:assert/strict";
import { createApi } from "../src/lib/api.js";
import { getClientId } from "../src/lib/clientId.js";
import { matchRoute, buildPath } from "../src/lib/router.js";
import { formatDuration, formatMinutes, formatNumber, percent } from "../src/lib/format.js";
import { applyVote, formProblem, rankSuggestions, trimmedLength } from "../src/lib/suggestions.js";

function memoryStorage() {
  const map = new Map();
  return { getItem: (k) => map.get(k) ?? null, setItem: (k, v) => map.set(k, v) };
}

test("Router: /admin führt zur Betreiber-Seite", () => {
  assert.deepEqual(matchRoute("/admin"), { name: "admin" });
  assert.deepEqual(matchRoute("/admin/"), { name: "admin" });
  assert.equal(buildPath("admin"), "/admin");
  assert.equal(matchRoute("/admin/etwas").name, "notfound");
});

test("Browser-Kennung: bleibt stabil, passt zum Server-Format, übersteht gesperrten Speicher", () => {
  const storage = memoryStorage();
  const id = getClientId(storage);
  assert.match(id, /^[A-Za-z0-9_-]{8,64}$/);
  assert.equal(getClientId(storage), id);
  storage.setItem("doko.client.v1", "!!kaputt!!");
  assert.notEqual(getClientId(storage), "!!kaputt!!");
  const locked = { getItem() { throw new Error("gesperrt"); }, setItem() { throw new Error("gesperrt"); } };
  const a = getClientId(locked);
  assert.match(a, /^[A-Za-z0-9_-]{8,64}$/);
  assert.equal(getClientId(locked), a);
});

test("Vorschläge: beliebteste zuerst, bei Gleichstand der ältere", () => {
  const items = [
    { id: 1, votes: 1, createdAt: 50 },
    { id: 2, votes: 3, createdAt: 90 },
    { id: 3, votes: 1, createdAt: 10 },
  ];
  assert.deepEqual(rankSuggestions(items).map((i) => i.id), [2, 3, 1]);
  assert.deepEqual(items.map((i) => i.id), [1, 2, 3], "Eingabe bleibt unverändert");
});

test("Vorschläge: Daumen aktualisiert Zähler und Reihenfolge", () => {
  const items = [
    { id: 1, votes: 2, voted: false, createdAt: 1 },
    { id: 2, votes: 2, voted: false, createdAt: 2 },
  ];
  const after = applyVote(items, 2, { votes: 3, voted: true });
  assert.deepEqual(after.map((i) => [i.id, i.votes, i.voted]), [[2, 3, true], [1, 2, false]]);
  const back = applyVote(after, 2, { votes: 2, voted: false });
  assert.deepEqual(back.map((i) => i.id), [1, 2]);
});

test("Vorschläge: Formularprüfung wie im Backend", () => {
  assert.match(formProblem("ab", "Das ist lang genug."), /Titel/);
  assert.match(formProblem("Guter Titel", "kurz"), /Beschreibung/);
  assert.equal(formProblem("Guter Titel", "Das ist lang genug."), null);
  assert.equal(trimmedLength("  a   b \n c "), 5);
  assert.match(formProblem("    x   ", "Das ist lang genug."), /Titel/, "Leerraum zählt nicht");
});

test("API: Kennung und Bearer-Token werden als Header gesendet", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    return { ok: true, json: async () => ({}) };
  };
  const api = createApi({ baseUrl: "/api", fetchImpl, clientId: () => "kennung-12345" });
  await api.suggestions();
  await api.voteSuggestion(7);
  await api.adminStats("tok.abc");
  await api.adminEditPhrase("tok.abc", 3, "Neu");
  await api.captcha();
  assert.equal(calls[0].init.headers["X-Client-Id"], "kennung-12345");
  assert.equal(calls[1].url, "/api/suggestions/7/vote");
  assert.equal(calls[1].init.method, "POST");
  assert.equal(calls[1].init.headers["X-Client-Id"], "kennung-12345");
  assert.equal(calls[2].init.headers.Authorization, "Bearer tok.abc");
  assert.equal(calls[2].init.headers["X-Client-Id"], undefined);
  assert.equal(calls[3].init.method, "PUT");
  assert.deepEqual(JSON.parse(calls[3].init.body), { text: "Neu" });
  assert.equal(calls[4].init.headers["X-Client-Id"], undefined);
});

test("API: Fehlercode des Servers kommt an (Captcha)", async () => {
  const fetchImpl = async () => ({ ok: false, status: 400, json: async () => ({ error: "Das Captcha stimmt nicht.", code: "captcha_wrong" }) });
  const api = createApi({ fetchImpl });
  await assert.rejects(api.submitSuggestion({ title: "x" }), (e) => e.code === "captcha_wrong" && e.status === 400);
});

test("Anzeigehilfen: Dauer, Minuten, Zahlen, Prozent", () => {
  assert.equal(formatDuration(5), "5 Sek.");
  assert.equal(formatDuration(125), "2 Min.");
  assert.equal(formatDuration(3600), "1 Std.");
  assert.equal(formatDuration(3660 * 2), "2 Std. 2 Min.");
  assert.equal(formatDuration(86400 * 2 + 3600), "2 T. 1 Std.");
  assert.equal(formatDuration(-5), "0 Sek.");
  assert.equal(formatMinutes(45), "45");
  assert.equal(formatMinutes(12.34), "12,3");
  assert.equal(formatMinutes(250.6), "251");
  assert.equal(formatNumber(1234567), "1.234.567");
  assert.equal(percent(1, 4), "25 %");
  assert.equal(percent(0, 0), "–");
});
