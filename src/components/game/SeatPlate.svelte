<script>
  import { seatBadges, seatName } from "../../lib/view.js";
  import CardBack from "../cards/CardBack.svelte";

  // Ein Sitz am Tisch: Kartenstapel des Mitspielers am Rand und daneben – ohne Kasten – Name, Marken,
  // Kartenzahl und Stiche. Links und rechts steht die Beschriftung gekippt (wie bei den bekannten Online-Tischen).
  // `place`: Lage am Tisch (top | left | right | bottom). Größe und Überlappung der Stapel kommen von GameTable
  // (CSS-Variablen --back-w, --step, --crop).
  let { view, seat, acting = false, announcement = null, showBacks = true, place = "bottom" } = $props();

  const badges = $derived(seatBadges(view, seat));
  const count = $derived(view.game.handCounts?.[seat] ?? 0);
  const tricks = $derived(view.game.tricksWon?.[seat] ?? 0);
  const bot = $derived(view.table.seats[seat]?.isBot);
  const shownCount = $derived(Math.min(count, 12));
  const vertical = $derived(place === "left" || place === "right");
</script>

<div
  class="seat s-{place}"
  class:acting
  class:vertical
  aria-label={`Platz ${seat + 1}: ${seatName(view, seat)}, ${count} Karten, ${tricks} ${tricks === 1 ? "Stich" : "Stiche"}`}
>
  {#if showBacks && count > 0}
    <div class="deck" style="--n:{shownCount}" aria-hidden="true">
      {#each Array(shownCount) as _, i (i)}
        <span class="b" style="--i:{i}"><CardBack /></span>
      {/each}
    </div>
  {/if}

  <div class="info">
    <span class="n">{seatName(view, seat)}</span>
    {#if bot}<span class="tag">BOT</span>{/if}
    {#each badges as b (b)}<span class="tag">{b}</span>{/each}
    {#if announcement}<span class="tag say">{announcement}</span>{/if}
    <span class="stat" title="{count} Karten">
      <svg viewBox="0 0 14 14" width="14" height="14" aria-hidden="true" focusable="false">
        <rect x="3" y="1.5" width="8" height="11" fill="#fff" stroke="#000" stroke-width="1.6" />
      </svg>
      <span aria-hidden="true">{count}</span>
    </span>
    <span class="stat" title="{tricks} {tricks === 1 ? 'Stich' : 'Stiche'}">
      <svg viewBox="0 0 14 14" width="14" height="14" aria-hidden="true" focusable="false">
        <rect x="1.5" y="3.5" width="8" height="9" fill="#fff" stroke="#000" stroke-width="1.6" />
        <rect x="4.5" y="1.5" width="8" height="9" fill="#FFD43B" stroke="#000" stroke-width="1.6" />
      </svg>
      <span aria-hidden="true">{tricks}</span>
    </span>
  </div>
</div>

<style>
  .seat {
    --bw: var(--back-w, 40px);
    --st: var(--step, 0.34);
    display: flex;
    min-width: 0;
  }

  /* ---------- Beschriftung (ohne Kasten) ---------- */
  .info {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 3px 8px;
    font-family: var(--font-mono);
    font-size: 0.82rem;
    font-weight: 700;
  }
  .n {
    max-inline-size: 11em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--font-heading);
    font-size: 1rem;
    line-height: 1.25;
  }
  /* Wer am Zug ist, trägt den Namen auf gelbem Grund */
  .acting .n {
    padding-block: 0;
    padding-inline: 6px;
    background: var(--nb-yellow);
    border: 2px solid #000;
  }
  .tag {
    font-size: 0.68rem;
    line-height: 1.3;
    text-transform: uppercase;
    padding-block: 0;
    padding-inline: 5px;
    border: 2px solid #000;
    background: var(--nb-bg);
  }
  .tag.say {
    background: var(--nb-coral);
  }
  .stat {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
  }
  .stat svg {
    display: block;
    flex-shrink: 0;
  }

  /* ---------- Kartenstapel: 12 Rücken, die sich überlappen ---------- */
  .deck {
    position: relative;
    flex-shrink: 0;
  }
  .b {
    position: absolute;
    display: block;
  }

  /* Oben und unten (Zuschauer): waagerecht */
  .s-top,
  .s-bottom {
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .s-bottom {
    flex-direction: column-reverse;
  }
  .s-top .deck,
  .s-bottom .deck {
    width: calc(var(--bw) * (1 + (var(--n) - 1) * var(--st)));
    height: calc(var(--bw) * 1.4 * var(--keep, 1));
    overflow: hidden;
  }
  .s-top .b,
  .s-bottom .b {
    left: calc(var(--i) * var(--bw) * var(--st));
    top: calc(var(--bw) * 1.4 * (var(--keep, 1) - 1));
  }

  /* Links und rechts: Karten quer gelegt, untereinander; Beschriftung gekippt */
  .s-left,
  .s-right {
    align-items: center;
    gap: 4px;
  }
  .s-right {
    flex-direction: row-reverse;
  }
  .s-left .deck,
  .s-right .deck {
    width: calc(var(--bw) * 1.4 * var(--keep, 1));
    height: calc(var(--bw) * (1 + (var(--n) - 1) * var(--st)));
    overflow: hidden;
  }
  .s-left .b,
  .s-right .b {
    width: calc(var(--bw) * 1.4);
    height: var(--bw);
    top: calc(var(--i) * var(--bw) * var(--st));
  }
  .s-left .b {
    left: calc(var(--bw) * 1.4 * (var(--keep, 1) - 1));
  }
  .s-right .b {
    left: 0;
  }
  .s-left .b :global(.back),
  .s-right .b :global(.back) {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%) rotate(90deg);
  }

  .vertical .info {
    writing-mode: vertical-rl;
    flex-wrap: wrap;
    align-content: center;
    gap: 8px 3px;
    max-height: calc(var(--bw) * (1 + 11 * var(--st)) + 20px);
  }
  .s-left .info {
    transform: rotate(180deg);
  }
  .vertical .stat svg {
    transform: rotate(90deg);
  }

  @media (max-width: 640px) {
    .info {
      gap: 2px 6px;
      font-size: 0.74rem;
    }
    .n {
      font-size: 0.86rem;
      max-inline-size: 7.5em;
    }
    .tag {
      font-size: 0.6rem;
      padding-inline: 3px;
      border-width: 1.5px;
    }
    .acting .n {
      padding-inline: 4px;
      border-width: 1.5px;
    }
    .vertical .info {
      gap: 6px 2px;
    }
  }
</style>
