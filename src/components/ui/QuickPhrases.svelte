<script>
  import { onMount } from "svelte";
  import { SPRUECHE } from "../../lib/sprueche.js";
  import { api } from "../../lib/services.js";

  // Auswahl klassischer Doppelkopf-Sprüche für den Chat: Spruch wählen, „SPRUCH SENDEN“ drücken.
  // `onsend(text)` gibt true zurück, wenn die Nachricht gesendet wurde (dann springt die Auswahl zurück).
  let { onsend, busy = false } = $props();

  // Die Liste pflegt der Betreiber; solange sie nicht geladen ist (oder der Server nicht antwortet), gilt die eingebaute.
  let phrases = $state(SPRUECHE);
  let chosen = $state("");

  onMount(async () => {
    try {
      const list = (await api.phrases()).phrases.map((p) => p.text);
      if (list.length) phrases = list;
    } catch {
      /* eingebaute Liste behalten */
    }
  });
  const id = `spruch-${Math.random().toString(36).slice(2, 7)}`;

  async function send(event) {
    event.preventDefault();
    if (chosen && (await onsend(chosen))) chosen = "";
  }
</script>

<form class="phrases" onsubmit={send}>
  <label class="nx-sr" for={id}>Doppelkopf-Spruch auswählen</label>
  <select {id} class="pick" bind:value={chosen}>
    <option value="">Klassiker-Spruch wählen …</option>
    {#each phrases as s (s)}
      <option value={s}>{s}</option>
    {/each}
  </select>
  <button type="submit" class="go" disabled={!chosen || busy}>SPRUCH SENDEN</button>
</form>

<style>
  .phrases {
    display: flex;
    gap: 8px;
    margin-top: 8px;
    min-width: 0;
  }
  .pick {
    flex: 1;
    min-width: 0;
    padding: 8px 10px;
    border: 3px solid #000;
    background: #fff;
    font: inherit;
    font-weight: 600;
    color: #000;
    border-radius: 0;
  }
  .go {
    flex-shrink: 0;
    padding: 6px 12px;
    border: 3px solid #000;
    background: var(--nb-lavender);
    box-shadow: var(--nb-shadow-sm);
    font-family: var(--font-heading);
    font-weight: 700;
    font-size: 0.85rem;
    cursor: pointer;
    color: #000;
  }
  .go:disabled {
    cursor: not-allowed;
    box-shadow: none;
  }
  .go:not(:disabled):active {
    transform: translate(2px, 2px);
    box-shadow: none;
  }
  @media (max-width: 480px) {
    .phrases {
      flex-direction: column;
    }
  }
</style>
