<script>
  import { onMount } from "svelte";
  import { api } from "../../lib/services.js";
  import { rankSuggestions, TITLE_MAX, DESC_MAX } from "../../lib/suggestions.js";
  import { formatDateTime } from "../../lib/format.js";

  let { token, onAuthLost } = $props();

  let items = $state(null);
  let error = $state("");
  let busy = $state(false);
  let editId = $state(null);
  let editTitle = $state("");
  let editDesc = $state("");
  let filter = $state("all"); // all | visible | hidden

  async function run(job) {
    busy = true;
    error = "";
    try {
      await job();
      return true;
    } catch (e) {
      if (e.status === 401) onAuthLost();
      else error = e.message;
      return false;
    } finally {
      busy = false;
    }
  }

  const reload = async () => (items = rankSuggestions((await api.adminSuggestions(token)).suggestions));
  const load = () => run(reload);

  const toggle = (item) =>
    run(async () => {
      await api.adminSuggestionStatus(token, item.id, item.status === "visible" ? "hidden" : "visible");
      await reload();
    });

  async function remove(item) {
    if (!confirm(`Vorschlag endgültig löschen (samt Daumen)?\n\n„${item.title}“`)) return;
    await run(async () => {
      await api.adminDeleteSuggestion(token, item.id);
      items = items.filter((x) => x.id !== item.id);
    });
  }

  function startEdit(item) {
    editId = item.id;
    editTitle = item.title;
    editDesc = item.description;
  }

  async function saveEdit(event) {
    event.preventDefault();
    const ok = await run(async () => {
      await api.adminEditSuggestion(token, editId, editTitle, editDesc);
      await reload();
    });
    if (ok) editId = null;
  }

  const shown = $derived(items ? items.filter((i) => filter === "all" || i.status === filter) : []);
  const hiddenCount = $derived(items ? items.filter((i) => i.status === "hidden").length : 0);

  onMount(load);
</script>

<p class="nx-hint">
  „Ausblenden“ nimmt einen Vorschlag sofort für alle aus der Liste (Daumen bleiben erhalten, Wiedereinblenden geht jederzeit).
  „Löschen“ entfernt ihn endgültig.
</p>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}

<div class="filters" role="group" aria-label="Filter">
  {#each [["all", "ALLE"], ["visible", "SICHTBAR"], ["hidden", `AUSGEBLENDET (${hiddenCount})`]] as [value, label] (value)}
    <button type="button" class="nx-btn nx-btn-sm" class:on={filter === value} aria-pressed={filter === value} onclick={() => (filter = value)}>{label}</button>
  {/each}
</div>

{#if items === null}
  <p>Lade …</p>
{:else if !shown.length}
  <p>Keine Vorschläge{filter === "all" ? "" : " in dieser Ansicht"}.</p>
{:else}
  <ul class="list">
    {#each shown as item (item.id)}
      <li class="item" class:hidden={item.status === "hidden"}>
        {#if editId === item.id}
          <form class="edit" onsubmit={saveEdit}>
            <label class="nx-label" for="se-t">Titel</label>
            <input id="se-t" class="nx-input" bind:value={editTitle} maxlength={TITLE_MAX} />
            <label class="nx-label" for="se-d">Beschreibung</label>
            <textarea id="se-d" class="nx-input" rows="4" bind:value={editDesc} maxlength={DESC_MAX}></textarea>
            <div class="nx-btn-row">
              <button type="submit" class="nx-btn nx-btn-sm nx-bg-green" disabled={busy}>SPEICHERN</button>
              <button type="button" class="nx-btn nx-btn-sm" onclick={() => (editId = null)}>ABBRECHEN</button>
            </div>
          </form>
        {:else}
          <div class="meta">
            <span class="votes">👍 {item.votes}</span>
            <span class="nx-hint">{formatDateTime(item.createdAt)}</span>
            {#if item.status === "hidden"}<span class="badge">AUSGEBLENDET</span>{/if}
          </div>
          <h4>{item.title}</h4>
          <p>{item.description}</p>
          <div class="tools">
            <button type="button" class="nx-btn nx-btn-sm nx-bg-yellow" disabled={busy} onclick={() => toggle(item)}>
              {item.status === "visible" ? "AUSBLENDEN" : "WIEDER EINBLENDEN"}
            </button>
            <button type="button" class="nx-btn nx-btn-sm" disabled={busy} onclick={() => startEdit(item)}>BEARBEITEN</button>
            <button type="button" class="nx-btn nx-btn-sm nx-bg-coral" disabled={busy} onclick={() => remove(item)}>LÖSCHEN</button>
          </div>
        {/if}
      </li>
    {/each}
  </ul>
{/if}

<style>
  .filters { display: flex; gap: 8px; flex-wrap: wrap; margin: 10px 0 16px; }
  .filters .on { background: var(--nb-yellow); }
  .list { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
  .item { border: 3px solid #000; background: #fff; box-shadow: var(--nb-shadow-sm); padding: 10px 12px; }
  .item.hidden { background: repeating-linear-gradient(45deg, #fff, #fff 10px, var(--nb-paper) 10px, var(--nb-paper) 20px); }
  .meta { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .votes { font-family: var(--font-mono); font-weight: 700; }
  .badge { background: var(--nb-orange); border: 2px solid #000; padding: 0 6px; font-weight: 700; font-size: 0.75rem; }
  h4 { margin: 6px 0 4px; font-family: var(--font-heading); overflow-wrap: anywhere; }
  p { margin: 0 0 10px; white-space: pre-line; overflow-wrap: anywhere; }
  .tools { display: flex; gap: 8px; flex-wrap: wrap; }
  .edit { display: grid; gap: 8px; }
  textarea { resize: vertical; }
</style>
