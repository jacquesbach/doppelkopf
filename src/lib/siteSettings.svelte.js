// Gemeinsame Einstellungen der Seite: einmal laden, Farben anwenden, Banner und Vorgaben bereitstellen.
import { DEFAULT_SETTINGS, applyColors, normalizeSettings } from "./siteSettings.js";

class SiteSettingsStore {
  value = $state(normalizeSettings(DEFAULT_SETTINGS));
  loaded = $state(false);

  async load(api) {
    try {
      this.apply(await api.siteSettings());
    } catch {
      /* ohne Antwort bleiben die Standardwerte */
    } finally {
      this.loaded = true;
    }
  }

  apply(raw) {
    this.value = normalizeSettings(raw);
    if (typeof document !== "undefined") applyColors(document.documentElement.style, this.value.colors);
  }
}

export const siteSettings = new SiteSettingsStore();
