<script>
  import CardBack from "../cards/CardBack.svelte";

  // Armut: Der Arme gibt 3 Karten ab, wer sie übernimmt gibt 3 zurück. Die Karten werden in der Hand markiert;
  // hier steht die Anleitung und der Bestätigen-Knopf. Der Server prüft alles (legalActions), hier wird nichts nachgerechnet.
  let { kind, count = 3, picked = 0, busy = false, onconfirm } = $props();

  const passing = $derived(kind === "poverty_pass");
  const ready = $derived(picked === count);
</script>

<section class="panel" aria-live="polite">
  <h2 class="nx-h2">{passing ? "Armut: Karten abgeben" : "Armut: Karten zurückgeben"}</h2>
  <p class="hint">
    {#if passing}
      Wähle <strong>genau {count} Karten</strong>, die du verdeckt weitergibst – auch wenn du weniger Trümpfe hast. So wissen die anderen
      nicht, wie viele Trümpfe dabei sind.
    {:else}
      Du hast die Armut übernommen und {count} Karten bekommen (in der Hand mit „NEU“ markiert). Wähle
      <strong>{count} beliebige Karten</strong>, die du zurückgibst. Ihr beide spielt zusammen als <strong>Re</strong>.
    {/if}
  </p>
  <div class="stack" aria-hidden="true">
    {#each Array(count) as _, i (i)}
      <span class="c" class:on={i < picked}><CardBack /></span>
    {/each}
  </div>
  <p class="count" aria-live="polite">{picked} von {count} Karten gewählt</p>
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
  .stack {
    --back-w: 38px;
    display: flex;
    justify-content: center;
    margin-bottom: 8px;
  }
  .c {
    display: block;
    opacity: 0.35;
    transform: translateY(0);
    transition: opacity 0.15s, transform 0.15s;
  }
  .c + .c {
    margin-left: -10px;
  }
  .c.on {
    opacity: 1;
    transform: translateY(-4px);
  }
  .count {
    margin: 0 0 12px;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.8rem;
  }
  @media (prefers-reduced-motion: reduce) {
    .c {
      transition: none;
    }
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
