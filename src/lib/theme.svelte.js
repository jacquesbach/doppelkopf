import { effectiveTheme, readTheme, toggled, writeTheme } from "./theme.js";
import { siteSettings } from "./siteSettings.svelte.js";

class ThemeStore {
  choice = $state(null);
  #storage = null;

  init(storage) {
    this.#storage = storage;
    this.choice = readTheme(storage);
  }

  get theme() {
    return effectiveTheme(this.choice, siteSettings.value.tableTheme);
  }

  get dark() {
    return this.theme === "dark";
  }

  toggle() {
    this.choice = toggled(this.theme);
    if (this.#storage) writeTheme(this.#storage, this.choice);
  }
}

export const tableTheme = new ThemeStore();
