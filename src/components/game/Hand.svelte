<script>
  import { cardId } from "../../lib/cards.js";
  import { isTouchPrimary, keepSelection, tapCard } from "../../lib/selection.js";
  import { receive, send } from "../../lib/fly.js";
  import PlayingCard from "../cards/PlayingCard.svelte";

  // `playable`: Set erlaubter Karten-IDs (vom Server) oder null, wenn gerade nichts gespielt werden darf.
  // `twoStep`: true = erst auswählen, dann ausspielen (Handy); false = sofort spielen; null = automatisch (Touch-Gerät).
  // `pick`: Armut – statt zu spielen werden mehrere Karten markiert: { selected: [ids], allowed: Set, received: [ids],
  // hint: Text, onToggle(id) }. `received` sind die Karten, die man gerade übernommen hat (Markierung „NEU“).
  // Gewählte Karten (`selected`) verlassen die Hand: Sie liegen im Armuts-Fenster und fliegen dorthin (bzw. zurück).
  let { hand, playable = null, onplay, twoStep = null, pick = null } = $props();

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
  const shown = $derived(pick ? hand.filter((c) => !pick.selected.includes(cardId(c))) : hand);
  // Flugeffekt nur beim Armut-Wählen; sonst (z. B. Karte ausspielen) kein Effekt.
  const flyIn = (node, params) => (pick ? receive(node, params) : { duration: 0 });
  const flyOut = (node, params) => (pick ? send(node, params) : { duration: 0 });

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

{#if pick}
  <p class="hint" aria-live="polite">{pick.hint}</p>
{:else if two}
  <p class="hint" aria-live="polite">
    {#if playable}{selected ? "Nochmal antippen zum Ausspielen" : "Karte antippen zum Auswählen"}{/if}
  </p>
{/if}
<ul class="hand" style="--n:{shown.length}" aria-label="Deine Hand">
  {#each shown as card, i (cardId(card))}
    {@const id = cardId(card)}
    {@const ok = pick ? (pick.allowed?.has(id) ?? true) : (playable?.has(id) ?? false)}
    {@const chosen = !pick && selected === id}
    <li
      class:sel={chosen}
      class:fresh={!!pick?.received?.includes(id)}
      style="--d:{i - (shown.length - 1) / 2}"
      in:flyIn={{ key: id }}
      out:flyOut={{ key: id }}
    >
      <div class="tilt">
        <PlayingCard {card} onclick={() => (pick ? pick.onToggle(id) : tap(id))} enabled={ok} selected={chosen} />
      </div>
    </li>
  {/each}
</ul>

<style>
  /* Aufgefächert: Jede Karte ist um ihren Abstand zur Mitte (--d) gekippt und etwas abgesenkt – ein sanfter Bogen */
  .hand {
    --step: 2deg;
    --sag: 0.55px;
    list-style: none;
    margin: 0;
    padding: 14px 8px calc(var(--sag) * var(--n, 12) * var(--n, 12) / 4 + 6px);
    display: flex;
    justify-content: center;
    min-height: calc(var(--card-w, 72px) * 1.4 + 20px);
  }
  li {
    position: relative;
  }
  li + li {
    margin-left: calc(var(--card-w, 72px) * -0.42);
  }
  .tilt {
    transform: translateY(calc(var(--d, 0) * var(--d, 0) * var(--sag))) rotate(calc(var(--d, 0) * var(--step)));
    transform-origin: 50% 100%;
  }
  /* Armut: soeben übernommene Karten tragen ein kleines „NEU“ */
  /* Das Etikett hängt an der Karte selbst (im gekippten Rahmen) und dreht sich mit ihr; die Karte bleibt eingereiht. */
  li.fresh .tilt::after {
    content: "NEU";
    position: absolute;
    top: -9px;
    left: -1px;
    padding: 0 3px;
    background: var(--nb-yellow, #ffd23f);
    border: 2px solid #000;
    font-family: var(--font-mono);
    font-weight: 800;
    font-size: 0.56rem;
    line-height: 1.3;
    transform: rotate(-7deg);
    transform-origin: 0 100%;
    pointer-events: none;
    z-index: 7;
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
    color: var(--table-ink, #000);
  }
  /* Handy: stärker überlappender Fächer; oben Platz für die herausragende, ausgewählte Karte. */
  @media (max-width: 640px) {
    /* Die Hand beginnt direkt am unteren Bildschirmrand: Karten etwas länger gezogen, unten angeschnitten */
    .hand {
      --step: 2.1deg;
      --sag: 0.8px;
      align-self: stretch;
      padding: 30px 4px 0;
      min-height: 0;
      height: calc(30px + var(--card-w, 72px) * 1.6 * 0.8);
      overflow: hidden;
    }
    .tilt :global(.card) {
      aspect-ratio: 5 / 8;
    }
    li + li {
      margin-left: calc(var(--card-w, 72px) * -0.54);
    }
  }
</style>
