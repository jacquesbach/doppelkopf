<script>
  import { seatBadges, seatName } from "../../lib/view.js";
  import CardBack from "../cards/CardBack.svelte";

  // Namensschild eines Sitzes mit Marken, Ansage, Stichzahl und (bei Gegnern) Kartenrücken.
  let { view, seat, acting = false, announcement = null, showBacks = true } = $props();

  const badges = $derived(seatBadges(view, seat));
  const count = $derived(view.game.handCounts?.[seat] ?? 0);
  const tricks = $derived(view.game.tricksWon?.[seat] ?? 0);
  const bot = $derived(view.table.seats[seat]?.isBot);
</script>

<div class="plate" class:acting aria-label={`Platz ${seat + 1}: ${seatName(view, seat)}`}>
  <div class="name">
    <span class="n">{seatName(view, seat)}</span>
    {#if bot}<span class="tag">BOT</span>{/if}
  </div>
  <div class="tags">
    {#each badges as b (b)}<span class="tag">{b}</span>{/each}
    {#if announcement}<span class="tag say">{announcement}</span>{/if}
  </div>
  <!-- Breit: ausgeschrieben („12 Karten“). Schmal (Mobil, seitliche Plätze): Symbol + Zahl, damit nichts aus dem Kasten ragt. -->
  <div class="meta">
    <span class="stat" title="{count} Karten">
      <span class="full">{count} Karten</span>
      <span class="short" aria-hidden="true">
        <svg viewBox="0 0 14 14" width="14" height="14" focusable="false"><rect x="3" y="1.5" width="8" height="11" fill="#fff" stroke="#000" stroke-width="1.6" /></svg>
        {count}
      </span>
      <span class="sr">{count} Karten</span>
    </span>
    <span class="stat" title="{tricks} {tricks === 1 ? 'Stich' : 'Stiche'}">
      <span class="full">{tricks} {tricks === 1 ? "Stich" : "Stiche"}</span>
      <span class="short" aria-hidden="true">
        <svg viewBox="0 0 14 14" width="14" height="14" focusable="false">
          <rect x="1.5" y="3.5" width="8" height="9" fill="#fff" stroke="#000" stroke-width="1.6" />
          <rect x="4.5" y="1.5" width="8" height="9" fill="#FFD43B" stroke="#000" stroke-width="1.6" />
        </svg>
        {tricks}
      </span>
      <span class="sr">{tricks} {tricks === 1 ? "Stich" : "Stiche"}</span>
    </span>
  </div>
  {#if showBacks && count > 0}
    <div class="backs" aria-hidden="true">
      {#each Array(Math.min(count, 5)) as _, i (i)}<CardBack />{/each}
    </div>
  {/if}
</div>

<style>
  .plate {
    container: plate / inline-size;
    border: 3px solid #000;
    background: var(--nb-bg);
    box-shadow: var(--nb-shadow-sm);
    padding: 8px 10px;
    min-width: 0;
    transition: background 0.15s, box-shadow 0.15s;
  }
  .plate.acting {
    background: var(--nb-yellow);
    box-shadow: var(--nb-shadow-md);
  }
  .name {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: var(--font-heading);
    font-weight: 700;
  }
  .n {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin: 4px 0;
    min-height: 1.4em;
  }
  .tag {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.68rem;
    text-transform: uppercase;
    padding: 0 5px;
    border: 2px solid #000;
    background: var(--nb-bg);
  }
  .tag.say {
    background: var(--nb-coral);
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 2px 8px;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    min-width: 0;
  }
  .stat {
    white-space: nowrap;
  }
  .short {
    display: none;
    align-items: center;
    gap: 4px;
    font-weight: 700;
    font-size: 0.85rem;
  }
  .sr {
    display: none;
  }
  .short svg {
    display: block;
    flex-shrink: 0;
  }
  .backs {
    --back-w: 26px;
    display: flex;
    margin-top: 8px;
  }
  .backs > :global(* + *) {
    margin-left: -14px;
  }
  @media (max-width: 640px) {
    .backs {
      display: none;
    }
    .plate {
      padding: 6px 7px;
    }
  }
  /* Schmaler Kasten (seitliche Plätze auf dem Handy): Symbol + Zahl untereinander statt ausgeschriebenem Text */
  @container plate (max-width: 150px) {
    .name {
      flex-wrap: wrap;
      gap: 2px 6px;
    }
    .n {
      max-width: 100%;
    }
    .full {
      display: none;
    }
    .short {
      display: inline-flex;
    }
    .sr {
      display: block;
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      white-space: nowrap;
    }
    .stat {
      position: relative;
    }
    .meta {
      flex-direction: column;
      align-items: flex-start;
      gap: 3px;
    }
  }
</style>
