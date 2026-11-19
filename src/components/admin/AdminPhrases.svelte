<script>
  import { onMount } from "svelte";
  import { api } from "../../lib/services.js";

  let { token, onAuthLost } = $props();

  const MAX = 200;
  let phrases = $state(null);
  let error = $state("");
  let fresh = $state("");
  let editId = $state(null);
  let editText = $state("");
  let busy = $state(false);

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

  const load = () => run(async () => (phrases = (await api.adminPhrases(token)).phrases));

  async function add(event) {
    event.preventDefault();
    if (!fresh.trim()) return;
    const ok = await run(async () => {
      await api.adminAddPhrase(token, fresh);
      phrases = (await api.adminPhrases(token)).phrases;
    });
    if (ok) fresh = "";
  }

  function startEdit(p) {
    editId = p.id;
    editText = p.text;
  }

  async function saveEdit(event) {
    event.preventDefault();
    const ok = await run(async () => {
      await api.adminEditPhrase(token, editId, editText);
      phrases = (await api.adminPhrases(token)).phrases;
    });
    if (ok) editId = null;
  }

  async function remove(p) {
    if (!confirm(`Spruch löschen?\n\n„${p.text}“`)) return;
    await run(async () => {
      await api.adminDeletePhrase(token, p.id);
      phrases = phrases.filter((x) => x.id !== p.id);
    });
  }

  const move = (p, direction) =>
    run(async () => (phrases = (await api.adminMovePhrase(token, p.id, direction)).phrases));

  onMount(load);
</script>

<p class="nx-hint">Diese Sprüche erscheinen allen Spielern in der Auswahl im Chat – in genau dieser Reihenfolge.</p>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}

<form class="add" onsubmit={add}>
  <label class="nx-sr" for="ph-new">Neuer Spruch</label>
  <input id="ph-new" class="nx-input" bind:value={fresh} maxlength={MAX} placeholder="Neuen Spruch hinzufügen …" autocomplete="off" />
  <button type="submit" class="nx-btn nx-bg-green" disabled={busy || !fresh.trim()}>HINZUFÜGEN</button>
</form>

{#if phrases === null}
  <p>Lade …</p>
{:else if !phrases.length}
  <p>Noch keine Sprüche. Im Chat greift dann die eingebaute Liste nicht mehr – füge mindestens einen hinzu.</p>
{:else}
  <ol class="list">
    {#each phrases as p, i (p.id)}
      <li class="row">
        {#if editId === p.id}
          <form class="edit" onsubmit={saveEdit}>
            <label class="nx-sr" for="ph-edit">Spruch bearbeiten</label>
            <input id="ph-edit" class="nx-input" bind:value={editText} maxlength={MAX} />
            <button type="submit" class="nx-btn nx-btn-sm nx-bg-green" disabled={busy || !editText.trim()}>SPEICHERN</button>
            <button type="button" class="nx-btn nx-btn-sm" onclick={() => (editId = null)}>ABBRECHEN</button>
          </form>
        {:else}
          <span class="text">{p.text}</span>
          <span class="tools">
            <button type="button" class="nx-btn nx-btn-sm" disabled={busy || i === 0} onclick={() => move(p, "up")} aria-label="Nach oben">↑</button>
            <button type="button" class="nx-btn nx-btn-sm" disabled={busy || i === phrases.length - 1} onclick={() => move(p, "down")} aria-label="Nach unten">↓</button>
            <button type="button" class="nx-btn nx-btn-sm nx-bg-yellow" disabled={busy} onclick={() => startEdit(p)}>BEARBEITEN</button>
            <button type="button" class="nx-btn nx-btn-sm nx-bg-coral" disabled={busy} onclick={() => remove(p)}>LÖSCHEN</button>
          </span>
        {/if}
      </li>
    {/each}
  </ol>
{/if}

<style>
  .add { display: flex; gap: 10px; margin: 12px 0 18px; flex-wrap: wrap; }
  .add .nx-input { flex: 1; min-width: 200px; }
  .list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
  .row { display: flex; gap: 10px; align-items: center; justify-content: space-between; flex-wrap: wrap; border: 3px solid #000; background: #fff; padding: 8px 10px; }
  .text { flex: 1; min-width: 160px; overflow-wrap: anywhere; font-weight: 600; }
  .tools { display: flex; gap: 6px; flex-wrap: wrap; }
  .edit { display: flex; gap: 8px; width: 100%; flex-wrap: wrap; }
  .edit .nx-input { flex: 1; min-width: 180px; }
</style>
