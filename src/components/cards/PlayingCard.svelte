<script>
  import { cardName, rankLabel } from "../../lib/cards.js";
  import { INK, SUIT_SHAPES } from "../../lib/suits.js";
  import SuitGlyph from "./SuitGlyph.svelte";

  // Klassische Spielkarte als Inline-SVG (skaliert verlustfrei). `onclick` gesetzt → Button, sonst Anzeige.
  // Nicht spielbare Karten bleiben unverändert; nur der Mauszeiger (not-allowed) zeigt es an.
  // `selected`: Karte ist vorgewählt (Handy: erster Tipp) – sie ragt aus dem Fächer heraus.
  // Schmale Karten (unter ca. 70 px, also vor allem auf dem Handy) zeigen einen großen Eck-Index
  // und ein einzelnes großes Symbol statt vieler kleiner Punkte; die Auswahl erfolgt per Container-Query.
  let { card, onclick = null, enabled = true, tilt = 0, selected = false } = $props();

  const label = $derived(rankLabel(card.rank));
  const ink = $derived(SUIT_SHAPES[card.suit]?.ink === "red" ? INK.red : INK.black);
  const isCourt = $derived(["K", "Q", "J"].includes(card.rank));

  // Pip-Positionen (Mittelpunkte im 100×140-Raster) für 9 und 10; untere Hälfte steht kopf.
  const SIDE = [30, 52, 88, 110];
  const pips = $derived(
    card.rank === "10"
      ? [...SIDE.flatMap((y) => [[31, y], [69, y]]), [50, 41], [50, 99]]
      : card.rank === "9"
        ? [...SIDE.flatMap((y) => [[31, y], [69, y]]), [50, 70]]
        : [],
  );
</script>

{#snippet face()}
  <svg viewBox="0 0 100 140" class="face" aria-hidden="true" focusable="false">
    <rect x="1" y="1" width="98" height="138" rx="8" fill="#ffffff" stroke="#2b2b33" stroke-width="2" />

    <g class="std">
      {#each [0, 180] as turn (turn)}
        <g transform="rotate({turn} 50 70)">
          <text x="13" y="21" text-anchor="middle" class="idx" font-size={label.length > 1 ? 15 : 18} fill={ink}>{label}</text>
          <g transform="translate(5.5 25) scale(0.6)"><SuitGlyph suit={card.suit} /></g>
        </g>
      {/each}

      {#if card.rank === "A"}
        <g transform="translate(24 44) scale(2.1)"><SuitGlyph suit={card.suit} /></g>
      {:else if isCourt}
        <rect x="24" y="22" width="52" height="96" fill="#faf6ea" stroke={ink} stroke-width="1.6" />
        <g transform="translate(40 27) scale(0.8)"><SuitGlyph suit={card.suit} /></g>
        <text x="50" y="86" text-anchor="middle" class="court" font-size="44" fill={ink}>{label}</text>
        <g transform="rotate(180 50 70)"><g transform="translate(40 27) scale(0.8)"><SuitGlyph suit={card.suit} /></g></g>
      {:else}
        {#each pips as [cx, cy] (`${cx}-${cy}`)}
          <g transform="rotate({cy > 70 ? 180 : 0} {cx} {cy}) translate({cx - 10.5} {cy - 10.5}) scale(0.88)">
            <SuitGlyph suit={card.suit} />
          </g>
        {/each}
      {/if}
    </g>

    <!-- Schmale Karten: Index links oben (im Fächer als einziger Teil sichtbar) möglichst groß, Motiv rechts davon. -->
    <g class="big">
      <text x="19" y="32" text-anchor="middle" class="idx" font-size={label.length > 1 ? 28 : 33} fill={ink}>{label}</text>
      <g transform="translate(7 38)"><SuitGlyph suit={card.suit} /></g>

      {#if isCourt}
        <rect x="40" y="20" width="52" height="100" fill="#faf6ea" stroke={ink} stroke-width="1.6" />
        <g transform="translate(56 25) scale(0.8)"><SuitGlyph suit={card.suit} /></g>
        <text x="66" y="87" text-anchor="middle" class="court" font-size="46" fill={ink}>{label}</text>
        <g transform="rotate(180 66 70)"><g transform="translate(56 25) scale(0.8)"><SuitGlyph suit={card.suit} /></g></g>
      {:else}
        <g transform="translate(39 41) scale(2.4)"><SuitGlyph suit={card.suit} /></g>
      {/if}
    </g>
  </svg>
{/snippet}

{#if onclick}
  <button
    type="button"
    class="card interactive"
    class:selected
    style="--tilt:{tilt}deg"
    disabled={!enabled}
    aria-label={cardName(card)}
    aria-pressed={selected}
    {onclick}
  >
    {@render face()}
  </button>
{:else}
  <div class="card" style="--tilt:{tilt}deg" role="img" aria-label={cardName(card)}>
    {@render face()}
  </div>
{/if}

<style>
  .card {
    display: block;
    flex-shrink: 0;
    width: var(--card-w, 72px);
    aspect-ratio: 5 / 7;
    padding: 0;
    border: 0;
    background: none;
    border-radius: 8%;
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.45));
    transform: rotate(var(--tilt, 0deg));
    transition: transform 0.14s ease, filter 0.14s ease, opacity 0.14s ease;
    container-type: inline-size;
    -webkit-tap-highlight-color: transparent;
  }
  .big {
    display: none;
  }
  @container (max-width: 70px) {
    .std {
      display: none;
    }
    .big {
      display: inline;
    }
  }
  .face {
    display: block;
    width: 100%;
    height: 100%;
  }
  .idx {
    font-family: var(--font-body);
    font-weight: 700;
  }
  .court {
    font-family: var(--font-heading);
    font-weight: 700;
  }
  .interactive {
    cursor: pointer;
  }
  /* Hover nur mit Maus; auf Touch-Geräten bliebe er nach dem Tippen „hängen“. */
  @media (hover: hover) {
    .interactive:hover:enabled {
      transform: translateY(-12px) rotate(var(--tilt, 0deg));
      filter: drop-shadow(0 8px 6px rgba(0, 0, 0, 0.4));
      z-index: 5;
    }
  }
  .interactive:active:enabled {
    transform: translateY(-5px);
  }
  .interactive.selected:enabled,
  .interactive.selected:active:enabled {
    transform: translateY(-24%) scale(1.07) rotate(var(--tilt, 0deg));
    filter: drop-shadow(0 8px 6px rgba(0, 0, 0, 0.45));
    outline: 3px solid var(--nb-yellow);
    outline-offset: 1px;
  }
  .interactive:disabled {
    cursor: not-allowed;
  }
  .interactive:focus-visible {
    outline: 3px solid var(--nb-blue);
    outline-offset: 2px;
  }
</style>
