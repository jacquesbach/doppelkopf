import test from "node:test";
import assert from "node:assert/strict";
import {
  addCard, canAdd, clearHand, createLabSeats, editorFromPreset, emptyHands, faceLabel, firstHumanSeat, fitToDeck,
  handSize, newEditor, paletteFaces, readAdminToken, removeCard, toScenario, trumpCount, usedCount,
} from "../src/lib/lab.js";

const memory = () => {
  const data = new Map();
  return { getItem: (k) => data.get(k) ?? null, setItem: (k, v) => data.set(k, v), removeItem: (k) => data.delete(k) };
};

test("Palette: 24 Kartenbilder, ohne Neunen 20", () => {
  assert.equal(paletteFaces(false).length, 24);
  assert.equal(paletteFaces(true).length, 20);
  assert.ok(!paletteFaces(true).some((f) => f.startsWith("9")));
  assert.deepEqual(paletteFaces(false).slice(0, 6), ["A♣", "10♣", "K♣", "Q♣", "J♣", "9♣"]);
});

test("Kartenbeschriftung wie am Tisch (Dame = D, Bube = B)", () => {
  assert.equal(faceLabel("Q♣"), "D♣");
  assert.equal(faceLabel("J♦"), "B♦");
  assert.equal(faceLabel("10♥"), "10♥");
});

test("Karte hinzufügen: höchstens zwei je Bild, höchstens 12 (10) je Hand", () => {
  let hands = emptyHands();
  hands = addCard(hands, 0, "Q♣", false);
  hands = addCard(hands, 1, "Q♣", false);
  assert.equal(usedCount(hands, "Q♣"), 2);
  assert.equal(canAdd(hands, 2, "Q♣", false), false);
  assert.strictEqual(addCard(hands, 2, "Q♣", false), hands);
  for (const f of ["A♣", "10♣", "K♣", "J♣", "9♣", "A♠", "10♠", "K♠", "Q♠", "J♠", "9♠"]) hands = addCard(hands, 0, f, false);
  assert.equal(hands[0].length, 12);
  assert.equal(canAdd(hands, 0, "A♥", false), false);
  assert.equal(handSize(true), 10);
});

test("Karte entfernen und Hand leeren", () => {
  let hands = addCard(addCard(emptyHands(), 0, "A♦", false), 0, "A♦", false);
  hands = removeCard(hands, 0, 0);
  assert.deepEqual(hands[0], ["A♦"]);
  assert.deepEqual(clearHand(hands, 0)[0], []);
});

test("Wechsel auf das Blatt ohne Neunen entfernt Neunen und kürzt", () => {
  const hands = { ...emptyHands(), 0: ["9♣", "A♣", "K♣", "Q♣", "J♣", "10♣", "A♠", "K♠", "Q♠", "J♠", "10♠", "A♥"] };
  const fitted = fitToDeck(hands, true);
  assert.equal(fitted[0].length, 10);
  assert.ok(!fitted[0].includes("9♣"));
  assert.strictEqual(fitToDeck(hands, false), hands);
});

test("Trumpfzähler (Normalspiel mit Dulle)", () => {
  assert.equal(trumpCount("Q♣ J♦ 9♦ A♣ A♣ 10♣ K♣ A♠ 10♠ K♠ A♥ K♥".split(" ")), 3);
  assert.equal(trumpCount(["10♥", "10♥", "A♥"]), 2);
});

test("Szenario: leere Rundenwerte und Hände entfallen", () => {
  const editor = newEditor({ poverty: true });
  editor.hands[2] = ["A♦", "A♦"];
  editor.seats[1].bot = true;
  const s = toScenario(editor);
  assert.deepEqual(s.hands, { 2: ["A♦", "A♦"] });
  assert.deepEqual(s.round, {});
  assert.equal(s.advance, "none");
  assert.equal(s.tricks, 0);
  assert.equal(s.seats[1].bot, true);
  assert.equal(s.settings.poverty, true);
});

test("Szenario: Rundenwerte und Vorspielen werden übernommen", () => {
  const editor = newEditor();
  editor.round = { normalGamesPlayed: 5, bockRemaining: 4, pflichtsoloDone: [true, false, false, false] };
  editor.advance = "tricks";
  editor.tricks = 7;
  const s = toScenario(editor);
  assert.deepEqual(s.round, { normalGamesPlayed: 5, bockRemaining: 4, pflichtsoloDone: [true, false, false, false] });
  assert.deepEqual([s.advance, s.tricks], ["tricks", 7]);
  editor.advance = "playing";
  assert.equal(toScenario(editor).tricks, 0);
});

test("Vorlage → Editor → Szenario bleibt gleich", () => {
  const preset = {
    title: "Armut",
    scenario: {
      settings: { poverty: true }, dealer: 3,
      hands: { 0: ["Q♣", "J♦"], 1: ["A♦"] },
      seats: [{ name: "Du", bot: false }, { name: "Bot", bot: true }, {}, {}],
      round: { normalGamesPlayed: 23 }, advance: "tricks", tricks: 10,
    },
  };
  const editor = editorFromPreset(preset, { dulle: true, poverty: false });
  assert.deepEqual(editor.settings, { dulle: true, poverty: true });
  assert.equal(editor.dealer, 3);
  assert.deepEqual(editor.hands[0], ["Q♣", "J♦"]);
  assert.deepEqual(editor.hands[3], []);
  assert.equal(editor.seats[1].bot, true);
  assert.equal(editor.seats[2].name, "Platz 3");
  assert.equal(editor.round.normalGamesPlayed, 23);
  const back = toScenario(editor);
  assert.deepEqual(back.hands, { 0: ["Q♣", "J♦"], 1: ["A♦"] });
  assert.equal(back.title, "Armut");
});

test("Sitze des Test-Tisches: speichern, lesen, löschen, Codes groß", () => {
  const seats = createLabSeats(memory());
  assert.equal(seats.get("abc"), null);
  seats.set("abc", [{ seat: 0, token: "t" }]);
  assert.deepEqual(seats.get("ABC"), [{ seat: 0, token: "t" }]);
  seats.remove("ABC");
  assert.equal(seats.get("ABC"), null);
});

test("Sitze: kaputter Speicher stört nicht", () => {
  const broken = { getItem: () => "{kaputt", setItem: () => { throw new Error("voll"); } };
  const seats = createLabSeats(broken);
  assert.equal(seats.get("ABC"), null);
  assert.doesNotThrow(() => seats.set("ABC", []));
});

test("erster eigener Platz und Admin-Token", () => {
  assert.equal(firstHumanSeat([{ isBot: true }, { isBot: false, token: "a", seat: 1 }, { isBot: false, token: "b" }]).seat, 1);
  assert.equal(firstHumanSeat([{ isBot: true }]), null);
  const storage = memory();
  assert.equal(readAdminToken(storage), "");
  storage.setItem("doko.admin.v1", "x.y");
  assert.equal(readAdminToken(storage), "x.y");
  assert.equal(readAdminToken({ getItem: () => { throw new Error("gesperrt"); } }), "");
});
