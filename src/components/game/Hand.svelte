<script>
  import { cardId } from "../../lib/cards.js";
  import PlayingCard from "../cards/PlayingCard.svelte";

  // `playable`: Set erlaubter Karten-IDs (vom Server) oder null, wenn gerade nichts gespielt werden darf.
  let { hand, playable = null, onplay } = $props();
</script>

<ul class="hand" aria-label="Deine Hand">
  {#each hand as card (cardId(card))}
    {@const id = cardId(card)}
    {@const ok = playable?.has(id) ?? false}
    <li>
      <PlayingCard {card} onclick={() => onplay(id)} enabled={ok} />
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
  li:hover {
    z-index: 4;
  }
</style>
