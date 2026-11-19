// Zufällige Kennung pro Browser: damit zählt ein Daumen nur einmal je Vorschlag. Enthält keine persönlichen Daten.
const KEY = "doko.client.v1";
const VALID = /^[A-Za-z0-9_-]{8,64}$/;

function randomId() {
  const c = globalThis.crypto;
  if (c?.randomUUID) return c.randomUUID().replace(/-/g, "");
  return Array.from({ length: 4 }, () => Math.random().toString(36).slice(2, 10)).join("");
}

export function getClientId(storage) {
  try {
    const known = storage.getItem(KEY);
    if (known && VALID.test(known)) return known;
    const fresh = randomId();
    storage.setItem(KEY, fresh);
    return fresh;
  } catch {
    // Speicher gesperrt: eine Kennung nur für diesen Seitenaufruf (Daumen dann nicht dauerhaft wiedererkennbar)
    memory ??= randomId();
    return memory;
  }
}
let memory = null;
