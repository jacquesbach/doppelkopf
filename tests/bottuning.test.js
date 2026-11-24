// Betreiber-Backend, Reiter BOTS: Hilfsfunktionen fuer das Formular.
import test from "node:test";
import assert from "node:assert/strict";
import {
  changedKeys, groupedItems, isActive, isDefault, normalizeBots, problem, problems, updatePayload, valueText,
} from "../src/lib/botTuning.js";

const schema = normalizeBots({
  groups: [{ id: "a", title: "A", text: "x" }, { id: "b", title: "B", text: "y" }, { id: "leer", title: "L", text: "z" }],
  items: [
    { key: "pimc", group: "a", kind: "bool", label: "Durchrechnen", needs: null },
    { key: "pimc_solo", group: "a", kind: "bool", label: "Solo", needs: { key: "pimc", value: true } },
    { key: "announce", group: "b", kind: "choice", label: "Ansage", needs: null, options: [{ value: "pimc", label: "Stichprobe" }, { value: "legacy", label: "Feste Regel" }] },
    { key: "announce_p0", group: "b", kind: "number", label: "Schwelle", min: 50, max: 95, unit: "%", needs: { key: "announce", value: "pimc" } },
    { key: "announce_p1", group: "b", kind: "number", label: "Absagen", min: 60, max: 99, unit: "%", needs: { key: "announce", value: "pimc" } },
  ],
  values: { pimc: true, pimc_solo: true, announce: "pimc", announce_p0: 75, announce_p1: 85 },
  defaults: { pimc: true, pimc_solo: true, announce: "pimc", announce_p0: 75, announce_p1: 85 },
});

test("Antwort des Servers: kaputte oder fehlende Teile werden leer", () => {
  for (const raw of [null, undefined, "x", 3, {}, { items: "no", groups: 5, values: [] }]) {
    const s = normalizeBots(raw);
    assert.deepEqual(s.items, []);
    assert.deepEqual(s.groups, []);
    assert.equal(typeof s.values, "object");
  }
});

test("Gruppen: Reihenfolge des Servers, leere Gruppen entfallen", () => {
  assert.deepEqual(groupedItems(schema).map((g) => [g.group.id, g.items.map((i) => i.key)]),
    [["a", ["pimc", "pimc_solo"]], ["b", ["announce", "announce_p0", "announce_p1"]]]);
});

test("Abhaengigkeiten: Untereinstellungen sind nur mit ihrem Hauptschalter wirksam", () => {
  const solo = schema.items[1];
  assert.equal(isActive(solo, { pimc: true }), true);
  assert.equal(isActive(solo, { pimc: false }), false);
  assert.equal(isActive(schema.items[3], { announce: "legacy" }), false);
  assert.equal(isActive(schema.items[0], {}), true);
});

test("Aenderungen: nur abweichende Werte gehen als Teilmenge an den Server", () => {
  const values = { ...schema.values, pimc_solo: false, announce_p0: 80 };
  assert.deepEqual(changedKeys(values, schema.values).sort(), ["announce_p0", "pimc_solo"]);
  assert.deepEqual(updatePayload(values, schema.values), { values: { pimc_solo: false, announce_p0: 80 } });
  assert.deepEqual(updatePayload(schema.values, schema.values), { values: {} });
  assert.equal(isDefault("pimc_solo", values, schema.defaults), false);
  assert.equal(isDefault("pimc", values, schema.defaults), true);
});

test("Pruefung: gleiche Grenzen wie der Server", () => {
  const p0 = schema.items[3];
  assert.equal(problem(p0, 75), "");
  assert.match(problem(p0, 40), /zwischen 50 und 95 %/);
  assert.match(problem(p0, NaN), /Zahl/);
  assert.match(problem(p0, "75"), /Zahl/);
  assert.equal(problem(schema.items[0], true), "");
  assert.deepEqual(problems(schema, schema.values), []);
  assert.match(problems(schema, { ...schema.values, announce_p0: 90, announce_p1: 80 }).join(" "), /nicht unter/);
});

test("Anzeige der Werte", () => {
  assert.equal(valueText(schema.items[0], true), "an");
  assert.equal(valueText(schema.items[0], false), "aus");
  assert.equal(valueText(schema.items[2], "legacy"), "Feste Regel");
  assert.equal(valueText(schema.items[3], 75), "75 %");
});
