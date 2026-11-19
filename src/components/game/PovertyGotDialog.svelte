<script>
  import { cardId } from "../../lib/cards.js";
  import Dialog from "../ui/Dialog.svelte";
  import PlayingCard from "../cards/PlayingCard.svelte";

  // Armut: Der Arme sieht, welche Karten ihm der Käufer zurückgegeben hat (die Karten liegen schon in seiner Hand).
  let { cards, buyerName, onClose } = $props();
</script>

<Dialog title="Deine neuen Karten" {onClose}>
  <p class="text">
    <strong>{buyerName}</strong> hat deine Armut übernommen und dir diese {cards.length} Karten zurückgegeben. Sie liegen jetzt in
    deiner Hand. Ihr beide spielt zusammen als <strong>Re</strong>.
  </p>
  <ul class="cards" aria-label="Neue Karten">
    {#each cards as card (cardId(card))}
      <li><PlayingCard {card} /></li>
    {/each}
  </ul>
  <button type="button" class="nx-btn nx-bg-yellow nx-btn-block" onclick={onClose}>VERSTANDEN</button>
</Dialog>

<style>
  .text {
    margin: 0 0 14px;
  }
  .cards {
    --card-w: min(84px, 24vw);
    list-style: none;
    margin: 0 0 16px;
    padding: 0;
    display: flex;
    justify-content: center;
    gap: 12px;
  }
</style>
