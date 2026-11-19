// Betreiberangaben für Impressum und Datenschutzerklärung.
//
// Sie stehen NICHT im Code (das Repository ist öffentlich kopierbar und soll nicht jedem dasselbe Impressum geben),
// sondern in der Datei /legal/legal.json auf dem Server. Beim Deploy erzeugt GitHub Actions sie aus den Variablen
// LEGAL_NAME, LEGAL_STREET, … (siehe docs/DEPLOYMENT.md). Fehlt die Datei, zeigt die Seite deutlich markierte TESTDATEN.

export const LEGAL_URL = "/legal/legal.json";

export const DEMO_LEGAL = Object.freeze({
  demo: true,
  name: "Max Mustermann",
  street: "Musterstraße 1",
  city: "12345 Musterstadt",
  country: "Deutschland",
  email: "kontakt@example.com",
  phone: "+49 123 4567890",
  vatId: "",
  hostingProvider: "Musterprovider",
  hostingRegion: "Musterstadt",
  registrar: "Musterregistrar",
});

const MAX = 200;
const REQUIRED = ["name", "street", "city", "email"];
const OPTIONAL = ["phone", "vatId", "hostingProvider", "hostingRegion", "registrar"];

function clean(value) {
  // Steuerzeichen und Zeilenumbrüche entfernen, Länge begrenzen. Die Seite setzt alles als Text ein (nie als HTML).
  return typeof value === "string" ? value.replace(/[\u0000-\u001f\u007f]+/g, " ").trim().slice(0, MAX) : "";
}

/**
 * Prüft die geladene Datei. Fehlt eines der Pflichtfelder (Name, Straße, Ort, E-Mail) oder ist sie kein Objekt,
 * gelten die Testdaten – lieber sichtbar falsch als still unvollständig.
 */
export function normalizeLegal(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return { ...DEMO_LEGAL };
  const out = { demo: false, country: clean(raw.country) || "Deutschland" };
  for (const key of REQUIRED) {
    out[key] = clean(raw[key]);
    if (!out[key]) return { ...DEMO_LEGAL };
  }
  for (const key of OPTIONAL) out[key] = clean(raw[key]);
  return out;
}

/** Lädt /legal/legal.json. Jeder Fehler (Datei fehlt, kein JSON, Netzwerk) ergibt die Testdaten. */
export async function loadLegal(fetchImpl = globalThis.fetch) {
  try {
    const res = await fetchImpl(LEGAL_URL, { headers: { Accept: "application/json" }, cache: "no-cache" });
    const type = res.headers?.get?.("content-type") ?? "";
    if (!res.ok || !/json/i.test(type)) return { ...DEMO_LEGAL };
    return normalizeLegal(await res.json());
  } catch {
    return { ...DEMO_LEGAL };
  }
}

/** Nur echte E-Mail-Adressen werden zum mailto-Link, alles andere bleibt Text. */
export function mailHref(email) {
  return /^[^\s@<>"']+@[^\s@<>"']+\.[^\s@<>"']+$/.test(email) ? `mailto:${email}` : null;
}

/** Anschrift in Zeilen: Name, Straße, Ort, Land. */
export function addressLines(legal) {
  return [legal.name, legal.street, legal.city, legal.country].filter(Boolean);
}
