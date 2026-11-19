<script>
  import { cardId } from "../../lib/cards.js";
  import { receive, send } from "../../lib/fly.js";
  import PlayingCard from "../cards/PlayingCard.svelte";

  // Armut: Der Arme gibt 3 Karten ab, wer sie übernimmt gibt 3 zurück. Gewählte Karten fliegen aus der Hand hierher
  // (`cards`) und lassen sich mit ✕ zurück auf die Hand nehmen (`onremove`). Der Käufer sieht die übernommenen Karten
  // (`received`) klein als Erinnerung. Der Server prüft alles (legalActions), hier wird nichts nachgerechnet.
  let { kind, count = 3, cards = [], received = [], busy = false, onconfirm, onremove } = $props();

  const passing = $derived(kind === "poverty_pass");
  const ready = $derived(cards.length === count);
  const pickedIds = $derived(new Set(cards.map(cardId)));
  const slots = $derived([
    ...cards.map((card) => ({ key: cardId(card), card })),
    ...Array.from({ length: Math.max(0, count - cards.length) }, (_, i) => ({ key: `leer-${i}`, card: null })),
  ]);
</script>

<section class="panel" aria-live="polite">
  <h2 class="nx-h2">{passing ? "Armut: Karten abgeben" : "Armut: Karten zurückgeben"}</h2>
  <p class="hint">
    {#if passing}
      Tippe in deiner Hand <strong>genau {count} Karten</strong> an, die du verdeckt weitergibst – auch wenn du weniger Trümpfe
      hast. Mit ✕ nimmst du eine Karte zurück auf die Hand.
    {:else}
      Du hast die Armut übernommen. Tippe <strong>{count} beliebige Karten</strong> an, die du zurückgibst. Ihr beide spielt
      zusammen als <strong>Re</strong>.
    {/if}
  </p>

  {#if !passing && received.length}
    <div class="recv">
      <span class="lbl">Übernommen</span>
      <ul class="mini" aria-label="Übernommene Karten">
        {#each received as card (cardId(card))}
          <li class:gone={pickedIds.has(cardId(card))}><PlayingCard {card} /></li>
        {/each}
      </ul>
    </div>
  {/if}

  <ul class="slots" aria-label={passing ? "Karten zum Abgeben" : "Karten zum Zurückgeben"}>
    {#each slots as slot (slot.key)}
      {#if slot.card}
        <li class="slot full" in:receive={{ key: slot.key }} out:send={{ key: slot.key }}>
          <PlayingCard card={slot.card} />
          <button type="button" class="x" aria-label="Karte zurück auf die Hand" title="Zurück auf die Hand" onclick={() => onremove(slot.key)}>
            <svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 2L12 12M12 2L2 12" stroke="#000" stroke-width="3" /></svg>
          </button>
        </li>
      {:else}
        <li class="slot empty" aria-hidden="true"></li>
      {/if}
    {/each}
  </ul>
  <p class="count">{cards.length} von {count} Karten gewählt</p>
  <button type="button" class="nx-btn nx-bg-coral" disabled={busy || !ready} onclick={onconfirm}>
    {passing ? `${count} KARTEN ABGEBEN` : `${count} KARTEN ZURÜCKGEBEN`}
  </button>
</section>

<style>
  .panel {
    border: 3px solid #000;
    background: var(--nb-bg);
    box-shadow: var(--nb-shadow-lg);
    padding: 16px;
    max-width: 460px;
    margin: 0 auto;
    text-align: center;
  }
  .hint {
    margin: 0 0 12px;
    font-size: 0.9rem;
  }
  ul {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .recv {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin-bottom: 12px;
    padding: 6px 8px;
    background: var(--nb-paper);
    border: 2px solid #000;
  }
  .lbl {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.7rem;
    text-transform: uppercase;
  }
  .mini {
    --card-w: 34px;
    display: flex;
    gap: 5px;
  }
  .mini li {
    transition: opacity 0.2s;
  }
  .mini li.gone {
    opacity: 0.3;
  }
  .slots {
    --card-w: min(64px, 20vw);
    display: flex;
    justify-content: center;
    gap: 10px;
    margin-bottom: 10px;
  }
  .slot {
    position: relative;
    width: var(--card-w);
    height: calc(var(--card-w) * 1.4);
  }
  .slot.empty {
    border: 3px dashed #000;
    border-radius: 6px;
    opacity: 0.35;
  }
  .x {
    position: absolute;
    top: -9px;
    right: -9px;
    width: 24px;
    height: 24px;
    display: grid;
    place-items: center;
    padding: 0;
    background: var(--nb-yellow);
    border: 2px solid #000;
    border-radius: 50%;
    cursor: pointer;
    z-index: 2;
  }
  .x:hover {
    background: var(--nb-coral);
  }
  .count {
    margin: 0 0 12px;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.8rem;
  }
  @media (max-width: 640px) {
    .panel {
      padding: 10px;
    }
    .hint {
      font-size: 0.8rem;
      margin-bottom: 8px;
    }
  }
</style>
