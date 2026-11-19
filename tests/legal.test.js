import test from "node:test";
import assert from "node:assert/strict";
import { DEMO_LEGAL, LEGAL_URL, addressLines, loadLegal, mailHref, normalizeLegal } from "../src/lib/legal.js";

const valid = {
  name: "Erika Beispiel", street: "Hauptstraße 5", city: "50667 Köln", country: "Deutschland",
  email: "kontakt@beispiel.de", phone: "+49 221 123456", hostingProvider: "Oracle Cloud Infrastructure",
  hostingRegion: "Frankfurt am Main, Deutschland", registrar: "GoDaddy",
};

test("normalizeLegal übernimmt vollständige Angaben und markiert sie nicht als Demo", () => {
  const out = normalizeLegal(valid);
  assert.equal(out.demo, false);
  assert.equal(out.name, "Erika Beispiel");
  assert.equal(out.registrar, "GoDaddy");
  assert.equal(out.vatId, "");
});

test("normalizeLegal: fehlt ein Pflichtfeld oder ist die Eingabe kaputt, gelten die markierten Testdaten", () => {
  for (const key of ["name", "street", "city", "email"]) assert.equal(normalizeLegal({ ...valid, [key]: "  " }).demo, true, key);
  for (const raw of [null, undefined, "text", 42, [], {}]) assert.equal(normalizeLegal(raw).demo, true);
  assert.equal(normalizeLegal({}).name, DEMO_LEGAL.name);
});

test("normalizeLegal: Land hat einen Standard; Steuerzeichen und Überlänge werden entschärft", () => {
  assert.equal(normalizeLegal({ ...valid, country: "" }).country, "Deutschland");
  const out = normalizeLegal({ ...valid, name: "Erika\nBeispiel\u0000", street: "x".repeat(500) });
  assert.equal(out.name, "Erika Beispiel");
  assert.equal(out.street.length, 200);
  assert.equal(normalizeLegal({ ...valid, phone: 12345 }).phone, "");   // nur Text wird übernommen
});

test("mailHref: nur echte Adressen werden zum mailto-Link", () => {
  assert.equal(mailHref("kontakt@beispiel.de"), "mailto:kontakt@beispiel.de");
  assert.equal(mailHref("a b@c.de"), null);
  assert.equal(mailHref('x"onmouseover="y@z.de'), null);
  assert.equal(mailHref("kein-at-zeichen"), null);
});

test("addressLines: Name, Straße, Ort, Land", () => {
  assert.deepEqual(addressLines(normalizeLegal(valid)), ["Erika Beispiel", "Hauptstraße 5", "50667 Köln", "Deutschland"]);
});

const response = (body, { ok = true, type = "application/json" } = {}) => ({
  ok,
  headers: { get: (name) => (name.toLowerCase() === "content-type" ? type : null) },
  json: async () => body,
});

test("loadLegal liest /legal/legal.json", async () => {
  let asked;
  const out = await loadLegal(async (url) => ((asked = url), response(valid)));
  assert.equal(asked, LEGAL_URL);
  assert.equal(out.demo, false);
  assert.equal(out.email, "kontakt@beispiel.de");
});

test("loadLegal: Datei fehlt (404), HTML statt JSON (Dev-Server) oder Netzwerkfehler → Testdaten", async () => {
  assert.equal((await loadLegal(async () => response({}, { ok: false }))).demo, true);
  assert.equal((await loadLegal(async () => response(valid, { type: "text/html" }))).demo, true);
  assert.equal((await loadLegal(async () => { throw new Error("offline"); })).demo, true);
  assert.equal((await loadLegal(async () => ({ ok: true, headers: { get: () => "application/json" }, json: async () => { throw new Error("kaputt"); } }))).demo, true);
});

test("Testdaten sind eindeutig als solche erkennbar und unveränderlich", () => {
  assert.equal(DEMO_LEGAL.demo, true);
  assert.match(DEMO_LEGAL.email, /example\.com$/);
  assert.throws(() => { "use strict"; DEMO_LEGAL.name = "x"; }, TypeError);
});
