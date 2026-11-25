<script>
  import PlayingCard from "../cards/PlayingCard.svelte";
  import { cardEntry } from "../../content/rules.js";

  // Zeigt einen `cards`-Block aus src/content/rules.js: gezeichnete Spielkarten in beschrifteten Gruppen.
  // Karten mit `win` sind die Stichgewinner in den Beispielen und werden hervorgehoben.
  let { block } = $props();

  const groups = $derived(
    block.groups.map((group) => ({ label: group.label ?? "", items: group.items.map(cardEntry) })),
  );
</script>

<figure class="cards">
  {#if block.title}<figcaption class="title">{block.title}</figcaption>{/if}
  <div class="groups">
    {#each groups as group, g (g)}
      <div class="group">
        {#if group.label}<p class="label">{group.label}</p>{/if}
        <div class="row">
          {#each group.items as item, i (i)}
            <div class="item" class:win={item.win}>
              <PlayingCard card={item.card} />
              {#if item.cap}<span class="cap">{item.cap}</span>{/if}
              {#if item.win}<span class="tag">Stich</span>{/if}
            </div>
          {/each}
        </div>
      </div>
    {/each}
  </div>
  {#if block.note}<p class="remark">{block.note}</p>{/if}
</figure>

<style>
  .cards {
    --card-w: 72px;
    margin: 18px 0 22px;
    padding: 14px 16px 16px;
    border: var(--nb-border);
    background: #e9f4ea;
    box-shadow: var(--nb-shadow-sm);
  }
  .title {
    margin: 0 0 10px;
    font-family: var(--font-heading);
    font-weight: 700;
    font-size: 0.95rem;
    text-transform: uppercase;
  }
  .groups {
    display: flex;
    flex-wrap: wrap;
    gap: 14px 26px;
  }
  .cards .label {
    margin: 0 0 6px;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: flex-start;
  }
  .item {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    width: calc(var(--card-w) + 14px);
    padding: 6px 4px 6px;
    border: 3px solid transparent;
  }
  .item.win {
    border-color: var(--nb-ink);
    background: var(--nb-yellow);
    box-shadow: var(--nb-shadow-sm);
  }
  .cap {
    font-size: 0.74rem;
    line-height: 1.2;
    text-align: center;
    font-weight: 600;
  }
  .tag {
    font-family: var(--font-mono);
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    padding: 1px 6px;
    background: var(--nb-ink);
    color: var(--nb-bg);
  }
  .cards .remark {
    margin: 12px 0 0;
    font-size: 0.9rem;
  }
  /* Handy: vier Karten pro Zeile (Breite = Bildschirm minus Seitenränder, Rahmen und Innenabstände) */
  @media (max-width: 560px) {
    .cards {
      --card-w: clamp(44px, calc((100vw - 180px) / 4), 64px);
      padding: 12px;
    }
    .groups {
      gap: 12px 14px;
    }
    .row {
      gap: 4px;
    }
    .item {
      width: calc(var(--card-w) + 10px);
      padding: 4px 2px;
    }
    .cap {
      font-size: 0.68rem;
    }
  }
</style>
