import test from "node:test";
import assert from "node:assert/strict";
import { isTouchPrimary, keepSelection, tapCard } from "../src/lib/selection.js";

test("Kartenauswahl: Maus spielt sofort, Touch erst beim zweiten Tipp", () => {
  assert.deepEqual(tapCard(null, "A-♦-0", false), { selected: null, play: "A-♦-0" });
  assert.deepEqual(tapCard("K-♦-0", "A-♦-0", false), { selected: null, play: "A-♦-0" });

  assert.deepEqual(tapCard(null, "A-♦-0", true), { selected: "A-♦-0", play: null });
  assert.deepEqual(tapCard("A-♦-0", "A-♦-0", true), { selected: null, play: "A-♦-0" });
  // anderer Tipp wechselt nur die Auswahl, spielt nichts
  assert.deepEqual(tapCard("A-♦-0", "K-♦-0", true), { selected: "K-♦-0", play: null });
});

test("Kartenauswahl: bleibt nur, solange die Karte spielbar ist", () => {
  assert.equal(keepSelection("A-♦-0", new Set(["A-♦-0", "K-♦-0"])), "A-♦-0");
  assert.equal(keepSelection("A-♦-0", new Set(["K-♦-0"])), null);
  assert.equal(keepSelection("A-♦-0", null), null);
  assert.equal(keepSelection(null, new Set(["A-♦-0"])), null);
});

test("Touch-Erkennung: nur Geräte ohne Hover und mit grobem Zeiger", () => {
  const win = (matches) => ({ matchMedia: (q) => ({ matches: matches && q.includes("hover: none") && q.includes("pointer: coarse") }) });
  assert.equal(isTouchPrimary(win(true)), true);
  assert.equal(isTouchPrimary(win(false)), false);
  assert.equal(isTouchPrimary({}), false);
  assert.equal(isTouchPrimary({ matchMedia: () => { throw new Error("x"); } }), false);
});
