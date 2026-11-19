// Feste Eckdaten der Website. Die Domain steht NICHT im Code, sondern kommt aus SITE_URL (siehe .env.example / docs/DEPLOYMENT.md).
export const SITE_NAME = "DOPPELKOPF.CC";
export const DEFAULT_SITE_URL = "https://doppelkopf.cc";
export const GITHUB_URL = "https://github.com/jacquesbach/doppelkopf";
export const DDV_URL = "https://www.doko-verband.de/";

/** Entfernt Leerraum und abschließende Schrägstriche: "https://doppelkopf.cc/" → "https://doppelkopf.cc". */
export function cleanSiteUrl(value) {
  const text = String(value ?? "").trim().replace(/\/+$/, "");
  return /^https?:\/\/[^\s/]+$/i.test(text) ? text : DEFAULT_SITE_URL;
}

// Beim Build setzt Vite den Wert aus SITE_URL ein (siehe vite.config.js). Unter Node (Tests, Build-Skript) gibt es
// kein import.meta.env: der Zugriff wirft dort und es gilt der Standardwert.
let fromBuild;
try {
  fromBuild = import.meta.env.VITE_SITE_URL;
} catch {
  fromBuild = undefined;
}
export const SITE_URL = cleanSiteUrl(fromBuild);
