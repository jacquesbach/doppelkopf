// Test-Tisch (Betreiber): reine Hilfsfunktionen für Szenario-Editor und Sitzwechsel. Keine Oberfläche, gut testbar.
import { rankLabel } from "./cards.js";

export const SUIT_ORDER = ["♣", "♠", "♥", "♦"];
export const RANK_ORDER = ["A", "10", "K", "Q", "J", "9"];
export const ADMIN_TOKEN_KEY = "doko.admin.v1"; // gleiche Kennung wie in Admin.svelte (sessionStorage)
const LAB_KEY = "doko.lab.v1";

export const handSize = (sharp) => (sharp ? 10 : 12);
export const faceLabel = (face) => `${rankLabel(face.slice(0, -1))}${face.slice(-1)}`;
export const isRed = (face) => face.endsWith("♥") || face.endsWith("♦");

/** Alle Kartenbilder des Blatts (Reihen = Farben, Spalten = Werte); ohne Neunen entfällt die letzte Spalte. */
export function paletteFaces(sharp) {
  const ranks = sharp ? RANK_ORDER.filter((r) => r !== "9") : RANK_ORDER;
  return SUIT_ORDER.flatMap((suit) => ranks.map((rank) => `${rank}${suit}`));
}

export const emptyHands = () => ({ 0: [], 1: [], 2: [], 3: [] });

export function usedCount(hands, face) {
  return Object.values(hands).reduce((n, cards) => n + cards.filter((c) => c === face).length, 0);
}

export function canAdd(hands, seat, face, sharp) {
  return hands[seat].length < handSize(sharp) && usedCount(hands, face) < 2;
}

export function addCard(hands, seat, face, sharp) {
  if (!canAdd(hands, seat, face, sharp)) return hands;
  return { ...hands, [seat]: [...hands[seat], face] };
}

export function removeCard(hands, seat, index) {
  return { ...hands, [seat]: hands[seat].filter((_, i) => i !== index) };
}

export const clearHand = (hands, seat) => ({ ...hands, [seat]: [] });

/** Beim Wechsel auf das Blatt ohne Neunen: Neunen entfernen und auf 10 Karten kürzen. */
export function fitToDeck(hands, sharp) {
  if (!sharp) return hands;
  return Object.fromEntries(
    Object.entries(hands).map(([seat, cards]) => [seat, cards.filter((c) => !c.startsWith("9")).slice(0, handSize(true))]),
  );
}

/** Trümpfe einer Hand im Normalspiel (Damen, Buben, Karo, Herz-Zehn) – zur Orientierung, z. B. für die Armut (≤ 3). */
export function trumpCount(cards) {
  return cards.filter((c) => c[0] === "Q" || c[0] === "J" || c.endsWith("♦") || c === "10♥").length;
}

export function newEditor(defaults = {}) {
  return {
    title: "",
    settings: { ...defaults },
    dealer: 0,
    hands: emptyHands(),
    seats: [0, 1, 2, 3].map((i) => ({ name: `Platz ${i + 1}`, bot: false })),
    round: { normalGamesPlayed: 0, bockRemaining: 0, pflichtsoloDone: [false, false, false, false] },
    advance: "none",
    tricks: 0,
  };
}

/** Editor-Zustand aus einer Vorlage des Servers (`defaults` = Standardwerte aller Regeln). */
export function editorFromPreset(preset, defaults = {}) {
  const s = preset.scenario ?? {};
  const base = newEditor({ ...defaults, ...(s.settings ?? {}) });
  const hands = emptyHands();
  for (const [seat, cards] of Object.entries(s.hands ?? {})) hands[Number(seat)] = [...cards];
  return {
    ...base,
    title: preset.title ?? "",
    dealer: s.dealer ?? 0,
    hands,
    seats: base.seats.map((d, i) => ({ name: s.seats?.[i]?.name ?? d.name, bot: !!s.seats?.[i]?.bot })),
    round: { ...base.round, ...(s.round ?? {}) },
    advance: s.advance ?? "none",
    tricks: s.tricks ?? 0,
  };
}

/** JSON für `POST /admin/lab/tables`. Leere Rundenwerte werden weggelassen. */
export function toScenario(editor) {
  const hands = {};
  for (const [seat, cards] of Object.entries(editor.hands)) if (cards.length) hands[seat] = [...cards];
  const round = {};
  if (editor.round.normalGamesPlayed) round.normalGamesPlayed = editor.round.normalGamesPlayed;
  if (editor.round.bockRemaining) round.bockRemaining = editor.round.bockRemaining;
  if (editor.round.pflichtsoloDone.some(Boolean)) round.pflichtsoloDone = [...editor.round.pflichtsoloDone];
  return {
    title: editor.title,
    settings: { ...editor.settings },
    dealer: editor.dealer,
    hands,
    seats: editor.seats.map((s) => ({ name: s.name, bot: s.bot })),
    round,
    advance: editor.advance,
    tricks: editor.advance === "tricks" ? editor.tricks : 0,
  };
}

/** Test-Tische dieses Browsers: Sitze samt Token (localStorage), damit man mit einem Klick den Platz wechseln kann. */
export function createLabSeats(storage) {
  const read = () => {
    try {
      const data = JSON.parse(storage.getItem(LAB_KEY) || "{}");
      return data && typeof data === "object" ? data : {};
    } catch {
      return {};
    }
  };
  const write = (data) => {
    try {
      storage.setItem(LAB_KEY, JSON.stringify(data));
    } catch {
      /* ohne Speicher: kein Sitzwechsel-Menü */
    }
  };
  return {
    get: (code) => read()[String(code).toUpperCase()] ?? null,
    set(code, seats) {
      write({ ...read(), [String(code).toUpperCase()]: seats });
    },
    remove(code) {
      const data = read();
      delete data[String(code).toUpperCase()];
      write(data);
    },
  };
}

/** Der erste Platz, den der Betreiber selbst spielt (dort sitzt er zu Beginn). */
export const firstHumanSeat = (seats) => seats.find((s) => !s.isBot && s.token) ?? null;

export function readAdminToken(storage) {
  try {
    return storage.getItem(ADMIN_TOKEN_KEY) || "";
  } catch {
    return "";
  }
}
