// Hell/Dunkel am Tisch (nur die Tischansicht, nicht die ganze Seite). Die Wahl bleibt im Browser (localStorage).
// Ohne eigene Wahl gilt die Vorgabe des Betreibers (siehe Design-Einstellungen).
export const THEME_KEY = "doko.theme.v1";

export function readTheme(storage) {
  try {
    const value = storage.getItem(THEME_KEY);
    return value === "dark" || value === "light" ? value : null;
  } catch {
    return null;
  }
}

export function writeTheme(storage, theme) {
  try {
    storage.setItem(THEME_KEY, theme);
  } catch {
    /* gesperrter Speicher: gilt bis zum Neuladen */
  }
}

/** Wahl des Besuchers, sonst Vorgabe des Betreibers, sonst hell. */
export function effectiveTheme(choice, fallback) {
  if (choice === "dark" || choice === "light") return choice;
  return fallback === "dark" ? "dark" : "light";
}

export const toggled = (theme) => (theme === "dark" ? "light" : "dark");
