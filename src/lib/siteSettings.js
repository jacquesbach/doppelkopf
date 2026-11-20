// Design-Einstellungen und Banner des Betreibers (siehe backend/app/ops/settings.py). Reine Funktionen, ohne Browser testbar.

export const COLOR_KEYS = ["bg", "paper", "yellow", "coral", "blue", "green", "lavender", "orange"];
export const COLOR_LABELS = {
  bg: "Seiten- und Fensterhintergrund",
  paper: "Helle Flächen (Tabellen, Chips)",
  yellow: "Gelb (Hauptfarbe, Knöpfe)",
  coral: "Koralle (Warnungen, Ansagen)",
  blue: "Blau",
  green: "Grün",
  lavender: "Lavendel",
  orange: "Orange",
};
export const DEFAULT_COLORS = {
  bg: "#fffdf5",
  paper: "#f4f1e6",
  yellow: "#ffd23f",
  coral: "#ff6b6b",
  blue: "#74b9ff",
  green: "#88d498",
  lavender: "#b8a9fa",
  orange: "#ffa552",
};
export const DEFAULT_SETTINGS = Object.freeze({
  colors: DEFAULT_COLORS,
  banner: { enabled: false, text: "", tone: "info", dismissible: true },
  tableTheme: "light",
  friendsEnabled: true,
});
export const TONES = [
  ["info", "Hinweis (blau)"],
  ["warn", "Warnung (orange)"],
  ["alert", "Wichtig (rot)"],
];
const HEX = /^#[0-9a-fA-F]{6}$/;

export const isHex = (value) => typeof value === "string" && HEX.test(value);

/** Server-Antwort (oder nichts) -> vollständige, sichere Einstellungen. Unbrauchbares wird durch Standardwerte ersetzt. */
export function normalizeSettings(raw) {
  const data = raw && typeof raw === "object" ? raw : {};
  const colors = { ...DEFAULT_COLORS };
  for (const key of COLOR_KEYS) if (isHex(data.colors?.[key])) colors[key] = data.colors[key].toLowerCase();
  const banner = data.banner && typeof data.banner === "object" ? data.banner : {};
  const text = typeof banner.text === "string" ? banner.text.replace(/\s+/g, " ").trim().slice(0, 280) : "";
  return {
    colors,
    banner: {
      enabled: !!banner.enabled && text !== "",
      text,
      tone: ["info", "warn", "alert"].includes(banner.tone) ? banner.tone : "info",
      dismissible: banner.dismissible !== false,
    },
    tableTheme: data.tableTheme === "dark" ? "dark" : "light",
    friendsEnabled: data.friendsEnabled !== false,
  };
}

/** Farben als CSS-Variablen auf ein Element setzen (nur gültige Hex-Werte; Standardfarben werden nicht gesetzt). */
export function applyColors(style, colors) {
  for (const key of COLOR_KEYS) {
    const value = colors?.[key];
    const name = `--nb-${key}`;
    if (isHex(value) && value.toLowerCase() !== DEFAULT_COLORS[key]) style.setProperty(name, value);
    else style.removeProperty(name);
  }
}

/** Kurzer Schlüssel des Bannertextes: Wer ihn weggeklickt hat, sieht ihn erst bei geändertem Text wieder. */
export function bannerKey(banner) {
  let hash = 5381;
  for (const ch of `${banner?.tone}|${banner?.text}`) hash = ((hash << 5) + hash + ch.codePointAt(0)) >>> 0;
  return `b${hash.toString(36)}`;
}

/** Relative Helligkeit (0–1) einer Hex-Farbe nach WCAG. */
export function luminance(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Kontrastverhältnis von schwarzem Text auf dieser Farbe (WCAG: ab 4,5 gut lesbar). */
export function contrastOnBlack(hex) {
  return (luminance(hex) + 0.05) / 0.05;
}

/** Hinweise zu den gewählten Farben (nur Warnungen, kein Zwang). */
export function colorWarnings(colors) {
  const out = [];
  for (const key of COLOR_KEYS) {
    if (isHex(colors?.[key]) && contrastOnBlack(colors[key]) < 4.5)
      out.push(`„${COLOR_LABELS[key]}“ ist sehr dunkel: Schwarzer Text darauf ist schwer lesbar.`);
  }
  return out;
}
