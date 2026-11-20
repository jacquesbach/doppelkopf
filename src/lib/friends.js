// Freiwilliger Online-Status OHNE Konto. Alles liegt nur im eigenen Browser (localStorage, Schlüssel doko.friends.v1):
// ein zufälliger Freundescode, ein selbst gewählter Anzeigename und die Liste der Codes, die man selbst eingetragen hat.
// Der Server kennt den Code nur, solange man online sichtbar ist (nur Arbeitsspeicher). Reine Funktionen, ohne Browser testbar.
export const FRIENDS_KEY = "doko.friends.v1";
export const CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
export const CODE_LENGTH = 10;
export const NAME_MAX = 24;
export const MAX_FRIENDS = 50;
const CODE_RE = /^[A-HJ-NP-Z2-9]{10}$/;

/** Zufälliger Code aus 32 Zeichen: 32^10 Möglichkeiten, nicht erratbar. `random(n)` liefert eine Zahl 0..n-1. */
export function generateCode(random = cryptoRandom) {
  let out = "";
  for (let i = 0; i < CODE_LENGTH; i += 1) out += CODE_ALPHABET[random(CODE_ALPHABET.length)];
  return out;
}

function cryptoRandom(n) {
  const c = globalThis.crypto;
  if (c?.getRandomValues) {
    const limit = 256 - (256 % n); // gleichmäßig: Werte oberhalb verwerfen
    const buf = new Uint8Array(1);
    for (;;) {
      c.getRandomValues(buf);
      if (buf[0] < limit) return buf[0] % n;
    }
  }
  return Math.floor(Math.random() * n);
}

/** Eingabe (auch mit Bindestrich/Leerzeichen/Kleinbuchstaben) -> 10-stelliger Code oder null. */
export function parseCode(value) {
  const text = String(value ?? "").trim().toUpperCase().replace(/[\s-]+/g, "");
  return CODE_RE.test(text) ? text : null;
}

/** Anzeige in zwei Hälften: ABCDE-FGHJK. */
export const formatCode = (code) => (code && code.length === CODE_LENGTH ? `${code.slice(0, 5)}-${code.slice(5)}` : code ?? "");

export function cleanName(value) {
  return String(value ?? "").replace(/[\u0000-\u001f\u007f]+/g, " ").replace(/\s+/g, " ").trim().slice(0, NAME_MAX);
}

export const EMPTY = Object.freeze({ enabled: false, code: "", name: "", friends: [] });

/** Gespeicherten Text -> sichere Struktur. Kaputtes wird ignoriert. */
export function normalizeFriends(raw) {
  let data = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      data = null;
    }
  }
  if (!data || typeof data !== "object") return { ...EMPTY, friends: [] };
  const seen = new Set();
  const friends = [];
  for (const f of Array.isArray(data.friends) ? data.friends : []) {
    const code = parseCode(f?.code);
    if (!code || seen.has(code) || friends.length >= MAX_FRIENDS) continue;
    seen.add(code);
    friends.push({ code, name: cleanName(f?.name) });
  }
  const code = parseCode(data.code) ?? "";
  return { enabled: !!data.enabled && !!code && cleanName(data.name) !== "", code, name: cleanName(data.name), friends };
}

export function loadFriends(storage) {
  try {
    return normalizeFriends(storage.getItem(FRIENDS_KEY));
  } catch {
    return { ...EMPTY, friends: [] };
  }
}

export function saveFriends(storage, state) {
  try {
    if (!state.code && !state.friends.length && !state.name) storage.removeItem(FRIENDS_KEY);
    else storage.setItem(FRIENDS_KEY, JSON.stringify({ enabled: state.enabled, code: state.code, name: state.name, friends: state.friends }));
  } catch {
    /* gesperrter Speicher: gilt bis zum Neuladen */
  }
}

/** Freund eintragen. Gibt { friends } oder { error } zurück. Der eigene Code ist nicht erlaubt. */
export function addFriend(friends, ownCode, rawCode, rawName) {
  const code = parseCode(rawCode);
  if (!code) return { error: "Der Code muss aus 10 Zeichen bestehen (Buchstaben und Ziffern, ohne 0, 1, I, O)." };
  if (code === ownCode) return { error: "Das ist dein eigener Code." };
  if (friends.some((f) => f.code === code)) return { error: "Diesen Code hast du schon eingetragen." };
  if (friends.length >= MAX_FRIENDS) return { error: `Du kannst höchstens ${MAX_FRIENDS} Freunde eintragen.` };
  return { friends: [...friends, { code, name: cleanName(rawName) }] };
}

export const removeFriend = (friends, code) => friends.filter((f) => f.code !== code);

/** Angezeigter Name: selbst vergebene Bezeichnung, sonst der Name, den der Freund online nutzt, sonst ein Platzhalter. */
export function friendLabel(friend, live) {
  return friend.name || live?.name || "Freund";
}

/** Server-Antwort `presence:state` / `presence:update` -> Tabelle code -> { name }. */
export function applyPresence(current, event) {
  const next = { ...current };
  if (event?.friends && typeof event.friends === "object") {
    for (const key of Object.keys(next)) delete next[key];
    for (const [code, info] of Object.entries(event.friends)) if (info?.online) next[code] = { name: cleanName(info.name) };
  } else if (event?.code) {
    if (event.online) next[event.code] = { name: cleanName(event.name) };
    else delete next[event.code];
  }
  return next;
}
