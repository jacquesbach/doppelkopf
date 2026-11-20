<script>
  import { onMount } from "svelte";
  import {
    COLOR_KEYS, COLOR_LABELS, DEFAULT_COLORS, TONES, applyColors, colorWarnings, isHex, normalizeSettings,
  } from "../../lib/siteSettings.js";
  import { siteSettings } from "../../lib/siteSettings.svelte.js";
  import { api } from "../../lib/services.js";

  let { token, onAuthLost } = $props();

  let form = $state(null);
  let error = $state("");
  let notice = $state("");
  let busy = $state(false);

  onMount(async () => {
    try {
      form = normalizeSettings(await api.adminSiteSettings(token));
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    }
  });

  const warnings = $derived(form ? colorWarnings(form.colors) : []);
  const valid = $derived(form ? COLOR_KEYS.every((k) => isHex(form.colors[k])) && (!form.banner.enabled || form.banner.text.trim()) : false);

  function preview() {
    // Vorschau auf der ganzen Seite, noch ohne Speichern (Neuladen verwirft sie)
    if (form) applyColors(document.documentElement.style, form.colors);
  }

  async function save(event) {
    event.preventDefault();
    busy = true;
    error = notice = "";
    try {
      const saved = await api.adminSaveSiteSettings(token, form);
      siteSettings.apply(saved);
      form = normalizeSettings(saved);
      notice = "Gespeichert. Die Einstellungen gelten sofort für alle neu geladenen Seiten.";
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    } finally {
      busy = false;
    }
  }

  async function reset() {
    busy = true;
    error = notice = "";
    try {
      const saved = await api.adminResetSiteSettings(token);
      siteSettings.apply(saved);
      form = normalizeSettings(saved);
      notice = "Alles auf die Standardwerte zurückgesetzt.";
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    } finally {
      busy = false;
    }
  }

  function setColor(key, value) {
    form.colors[key] = value;
    preview();
  }
</script>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}
{#if notice}<p class="nx-success" role="status">{notice}</p>{/if}

{#if form}
  <form onsubmit={save}>
    <h3 class="nx-h3">Banner (z. B. Wartungshinweis)</h3>
    <p class="nx-hint">Erscheint ganz oben auf jeder Seite. Reiner Text, höchstens 280 Zeichen.</p>
    <label class="check"><input type="checkbox" bind:checked={form.banner.enabled} /> Banner anzeigen</label>
    <div class="nx-field">
      <label class="nx-label" for="bn-text">Text</label>
      <input id="bn-text" class="nx-input" maxlength="280" bind:value={form.banner.text} placeholder="z. B. Heute 22 Uhr: kurze Wartungsarbeiten, laufende Spiele können unterbrochen werden." />
    </div>
    <div class="nx-field">
      <label class="nx-label" for="bn-tone">Art</label>
      <select id="bn-tone" class="nx-input" bind:value={form.banner.tone}>
        {#each TONES as [id, label] (id)}<option value={id}>{label}</option>{/each}
      </select>
    </div>
    <label class="check"><input type="checkbox" bind:checked={form.banner.dismissible} /> Besucher dürfen den Banner schließen</label>
    {#if form.banner.text.trim()}
      <div class="prev {form.banner.tone}" aria-hidden="true">{form.banner.text}</div>
    {/if}

    <h3 class="nx-h3">Farben</h3>
    <p class="nx-hint">Wirkt auf die ganze Seite (Knöpfe, Karten, Flächen). Die Vorschau ist sofort sichtbar, gespeichert wird erst mit „Speichern“.</p>
    <div class="colors">
      {#each COLOR_KEYS as key (key)}
        <div class="color">
          <input type="color" id="c-{key}" value={form.colors[key]} oninput={(e) => setColor(key, e.currentTarget.value)} />
          <label for="c-{key}">{COLOR_LABELS[key]}<small>{form.colors[key]}{form.colors[key] === DEFAULT_COLORS[key] ? " (Standard)" : ""}</small></label>
        </div>
      {/each}
    </div>
    {#each warnings as w (w)}<p class="warn">⚠ {w}</p>{/each}

    <h3 class="nx-h3">Spieltisch</h3>
    <div class="nx-field">
      <label class="nx-label" for="tb-theme">Vorgabe: Hell oder Dunkel</label>
      <select id="tb-theme" class="nx-input" bind:value={form.tableTheme}>
        <option value="light">Hell</option>
        <option value="dark">Dunkel</option>
      </select>
      <p class="nx-hint">Gilt nur für Spieler, die am Tisch noch nichts selbst gewählt haben. Der Dark Mode betrifft nur die Tischansicht.</p>
    </div>

    <h3 class="nx-h3">Funktionen</h3>
    <label class="check"><input type="checkbox" bind:checked={form.friendsEnabled} /> „Wer ist online“ / Freunde (freiwillig, ohne Konto) anbieten</label>
    <p class="nx-hint">Abgeschaltet verschwindet die Funktion für alle und es wird nichts mehr dazu verarbeitet.</p>

    <div class="row">
      <button type="submit" class="nx-btn nx-bg-yellow" disabled={busy || !valid}>{busy ? "SPEICHERE …" : "SPEICHERN"}</button>
      <button type="button" class="nx-btn" disabled={busy} onclick={reset}>AUF STANDARD ZURÜCKSETZEN</button>
    </div>
  </form>
{:else if !error}
  <p>Lade …</p>
{/if}

<style>
  form { max-width: 640px; }
  h3 { margin: 22px 0 6px; }
  h3:first-child { margin-top: 0; }
  .check { display: flex; gap: 8px; align-items: center; margin: 8px 0; font-weight: 600; }
  .check input { width: 20px; height: 20px; accent-color: #000; }
  .prev { border: 3px solid #000; padding: 8px 12px; font-family: var(--font-heading); font-weight: 700; text-align: center; margin: 8px 0 0; color: #000; }
  .prev.info { background: var(--nb-blue); }
  .prev.warn { background: var(--nb-orange); }
  .prev.alert { background: var(--nb-coral); }
  .colors { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; margin: 10px 0; }
  .color { display: flex; align-items: center; gap: 10px; border: 3px solid #000; padding: 6px 8px; background: #fff; }
  .color input { width: 44px; height: 36px; border: 3px solid #000; padding: 0; background: none; cursor: pointer; flex: none; }
  .color label { display: flex; flex-direction: column; font-weight: 600; font-size: 0.85rem; line-height: 1.25; }
  .color small { font-family: var(--font-mono); font-weight: 400; color: #444; }
  p.warn { background: var(--nb-orange); border: 2px solid #000; padding: 4px 8px; margin: 6px 0; font-size: 0.85rem; }
  .row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 22px; }
</style>
