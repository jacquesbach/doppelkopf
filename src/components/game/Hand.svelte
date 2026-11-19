<script>
  import { cardId } from "../../lib/cards.js";
  import { isTouchPrimary, keepSelection, tapCard } from "../../lib/selection.js";
  import PlayingCard from "../cards/PlayingCard.svelte";

  // `playable`: Set erlaubter Karten-IDs (vom Server) oder null, wenn gerade nichts gespielt werden darf.
  // `twoStep`: true = erst auswählen, dann ausspielen (Handy); false = sofort spielen; null = automatisch (Touch-Gerät).
  let { hand, playable = null, onplay, twoStep = null } = $props();

  let touch = $state(isTouchPrimary());
  $effect(() => {
    const mq = window.matchMedia?.("(hover: none) and (pointer: coarse)");
    if (!mq) return;
    const update = () => (touch = mq.matches);
    update();
    mq.addEventListener?.("change", update);
    return () => mq.removeEventListener?.("change", update);
  });
  const two = $derived(twoStep ?? touch);

  let selected = $state(null);
  // Zug vorbei oder Karte nicht mehr spielbar → Auswahl verwerfen.
  $effect(() => {
    if (selected && !keepSelection(selected, playable)) selected = null;
  });

  function tap(id) {
    const r = tapCard(selected, id, two);
    selected = r.selected;
    if (r.play) onplay(r.play);
  }

  // Tipp neben die Hand hebt die Auswahl wieder auf.
  function outside(e) {
    if (selected && !e.target?.closest?.(".hand")) selected = null;
  }
</script>

<svelte:window onpointerdown={outside} />

{#if two}
  <p class="hint" aria-live="polite">
    {#if playable}{selected ? "Nochmal antippen zum Ausspielen" : "Karte antippen zum Auswählen"}{/if}
  </p>
{/if}
<ul class="hand" aria-label="Deine Hand">
  {#each hand as card (cardId(card))}
    {@const id = cardId(card)}
    {@const ok = playable?.has(id) ?? false}
    <li class:sel={selected === id}>
      <PlayingCard {card} onclick={() => tap(id)} enabled={ok} selected={selected === id} />
    </li>
  {/each}
</ul>

<style>
  .hand {
    list-style: none;
    margin: 0;
    padding: 14px 8px 6px;
    display: flex;
    justify-content: center;
    min-height: calc(var(--card-w, 72px) * 1.4 + 20px);
  }
  li + li {
    margin-left: calc(var(--card-w, 72px) * -0.42);
  }
  li:hover,
  li.sel {
    z-index: 4;
  }
  li.sel {
    z-index: 6;
  }
  .hint {
    margin: 0;
    min-height: 1.3em;
    text-align: center;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.72rem;
  }
  /* Handy: stärker überlappender Fächer; oben Platz für die herausragende, ausgewählte Karte. */
  @media (max-width: 640px) {
    .hand {
      padding: 30px 4px 8px;
      min-height: calc(var(--card-w, 72px) * 1.4 + 40px);
    }
    li + li {
      margin-left: calc(var(--card-w, 72px) * -0.54);
    }
  }
</style>
