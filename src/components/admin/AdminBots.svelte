<script>
  import { onMount } from "svelte";
  import { changedKeys, groupedItems, isActive, normalizeBots, problems, updatePayload, valueText } from "../../lib/botTuning.js";
  import { api } from "../../lib/services.js";

  let { token, onAuthLost } = $props();

  let schema = $state(null); // Texte, Grenzen, Standardwerte (vom Server)
  let saved = $state({}); // zuletzt gespeicherter Stand
  let form = $state({}); // Bearbeitung
  let error = $state("");
  let notice = $state("");
  let busy = $state(false);

  const groups = $derived(schema ? groupedItems(schema) : []);
  const changed = $derived(changedKeys(form, saved));
  const issues = $derived(schema ? problems(schema, form) : []);

  function take(raw) {
    const next = normalizeBots(raw);
    schema = next;
    saved = { ...next.values };
    form = { ...next.values };
  }

  onMount(async () => {
    try {
      take(await api.adminBots(token));
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    }
  });

  async function save(event) {
    event.preventDefault();
    busy = true;
    error = notice = "";
    try {
      take(await api.adminSaveBots(token, updatePayload(form, saved)));
      notice = "Gespeichert. Die Bots rechnen ab dem nächsten Zug mit den neuen Einstellungen, an allen Tischen.";
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
      take(await api.adminResetBots(token));
      notice = "Alle Bot-Einstellungen stehen wieder auf den Standardwerten.";
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    } finally {
      busy = false;
    }
  }

  function discard() {
    form = { ...saved };
    error = notice = "";
  }

  const labelOf = (key) => schema?.items.find((i) => i.key === key)?.label ?? key;
</script>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}
{#if notice}<p class="nx-success" role="status">{notice}</p>{/if}

{#if schema}
  <form onsubmit={save}>
    <p class="nx-hint">
      Hier stellst du ein, wie die Bots am Tisch denken. Die Einstellungen gelten sofort für alle Tische und bleiben nach einem Neustart erhalten.
      Die Bots kennen nie fremde Hände; sie rechnen nur mit dem, was am Tisch öffentlich bekannt ist.
      <strong>Standardwerte sind im Selbstspiel gemessen und abgestimmt.</strong> Wer etwas abschaltet, macht die Bots in aller Regel schwächer.
    </p>

    {#each groups as { group, items } (group.id)}
      <h3 class="nx-h3">{group.title}</h3>
      <p class="nx-hint">{group.text}</p>
      {#each items as item (item.key)}
        {@const active = isActive(item, form)}
        <div class="item" class:off={!active}>
          {#if item.kind === "bool"}
            <label class="check">
              <input type="checkbox" bind:checked={form[item.key]} disabled={!active} />
              {item.label}
              {#if form[item.key] !== schema.defaults[item.key]}<span class="tag">geändert (Standard: {valueText(item, schema.defaults[item.key])})</span>{/if}
            </label>
          {:else if item.kind === "choice"}
            <div class="nx-field">
              <label class="nx-label" for="bot-{item.key}">{item.label}</label>
              <select id="bot-{item.key}" class="nx-input" bind:value={form[item.key]} disabled={!active}>
                {#each item.options as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
              </select>
            </div>
          {:else}
            <div class="nx-field">
              <label class="nx-label" for="bot-{item.key}">{item.label}</label>
              <div class="num">
                <input
                  id="bot-{item.key}"
                  class="nx-input"
                  type="number"
                  min={item.min}
                  max={item.max}
                  step={item.step}
                  bind:value={form[item.key]}
                  disabled={!active}
                />
                <span>{item.unit}</span>
                {#if form[item.key] !== schema.defaults[item.key]}<span class="tag">geändert (Standard: {valueText(item, schema.defaults[item.key])})</span>{/if}
              </div>
            </div>
          {/if}
          <p class="nx-hint text">{item.text}</p>
          {#if item.note}<p class="nx-hint note">{item.note}</p>{/if}
          {#if !active}<p class="nx-hint note">Wirkt nur, wenn „{labelOf(item.needs.key)}“ {item.needs.value === true ? "an" : "auf „" + valueText(schema.items.find((i) => i.key === item.needs.key), item.needs.value) + "“ steht"}.</p>{/if}
        </div>
      {/each}
    {/each}

    {#each issues as msg (msg)}<p class="issue" role="alert">⚠ {msg}</p>{/each}

    <div class="row">
      <button type="submit" class="nx-btn nx-bg-yellow" disabled={busy || changed.length === 0 || issues.length > 0}>
        {busy ? "SPEICHERE …" : changed.length ? `SPEICHERN (${changed.length})` : "SPEICHERN"}
      </button>
      <button type="button" class="nx-btn" disabled={busy || changed.length === 0} onclick={discard}>ÄNDERUNGEN VERWERFEN</button>
      <button type="button" class="nx-btn" disabled={busy} onclick={reset}>AUF STANDARD ZURÜCKSETZEN</button>
    </div>
  </form>
{:else if !error}
  <p>Lade …</p>
{/if}

<style>
  form { max-width: 720px; }
  h3 { margin: 26px 0 6px; }
  h3:first-of-type { margin-top: 18px; }
  .item { border-left: 6px solid #000; padding: 4px 0 4px 12px; margin: 14px 0; }
  .item.off { opacity: 0.55; border-left-color: #999; }
  .check { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-weight: 700; }
  .check input { width: 20px; height: 20px; accent-color: #000; }
  .num { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .num input { width: 7.5em; }
  .tag { background: var(--nb-yellow); border: 2px solid #000; padding: 0 6px; font-size: 0.75rem; font-weight: 700; }
  .text { margin: 4px 0 0; }
  .note { margin: 2px 0 0; font-style: italic; }
  .issue { background: var(--nb-orange); border: 2px solid #000; padding: 4px 8px; margin: 8px 0; font-size: 0.85rem; }
  .row { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 22px; }
</style>
