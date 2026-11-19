<script>
  import { announceOptions, legalAction } from "../../lib/view.js";

  // Ansagen und Schweinchen: Welche Stufen erlaubt sind, entscheidet der Server (legalActions).
  // Am Handy sind die Knöpfe hinter einem Schalter „ANSAGEN“ eingeklappt, damit die Hand Platz hat;
  // bei Pflichtansage klappt die Leiste von selbst auf.
  let { view, busy = false, act } = $props();

  const options = $derived(announceOptions(view));
  const schweinchen = $derived(!!legalAction(view, "schweinchen"));
  const mandatory = $derived(view.game.mandatoryAnnouncementSeat === view.table.mySeat);

  let open = $state(false);
  const shown = $derived(open || mandatory);
  const toggleLabel = $derived(!options.length && schweinchen ? "SCHWEINCHEN" : "ANSAGEN");

  function run(action) {
    open = false;
    act(action);
  }
</script>

{#if options.length || schweinchen}
  <div class="bar" class:open={shown} role="group" aria-label="Ansagen">
    <button
      type="button"
      class="nx-btn nx-btn-sm nx-bg-white toggle"
      aria-expanded={shown}
      aria-controls="announce-options"
      onclick={() => (open = !open)}
    >
      {toggleLabel} <span aria-hidden="true">{shown ? "▾" : "▴"}</span>
    </button>
    <div class="opts" id="announce-options">
      {#if mandatory}
        <span class="note">Pflichtansage: Du musst jetzt Re oder Kontra ansagen.</span>
      {:else if options.length}
        <span class="note">Ansagen:</span>
      {/if}
      {#each options as o (o.level)}
        <button
          type="button"
          class="nx-btn nx-btn-sm {o.level === 0 ? 'nx-bg-coral' : 'nx-bg-blue'}"
          disabled={busy}
          onclick={() => run({ type: "announce", level: o.level })}
        >
          {o.label}
        </button>
      {/each}
      {#if schweinchen}
        <button type="button" class="nx-btn nx-btn-sm nx-bg-lavender" disabled={busy} onclick={() => run({ type: "schweinchen" })}>
          SCHWEINCHEN
        </button>
      {/if}
    </div>
  </div>
{/if}

<style>
  .bar {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 0;
  }
  .opts {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }
  .toggle {
    display: none;
  }
  .note {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.8rem;
  }
  @media (max-width: 640px) {
    .bar {
      padding: 4px 0;
      gap: 8px;
    }
    .toggle {
      display: inline-block;
    }
    .opts {
      display: none;
      gap: 6px;
    }
    .opts :global(.nx-btn) {
      padding: 6px 8px;
      font-size: 0.72rem;
    }
    .bar.open .opts {
      display: flex;
    }
    .note {
      flex-basis: 100%;
      text-align: center;
      font-size: 0.74rem;
    }
  }
</style>
