<script>
  import { announceOptions, legalAction } from "../../lib/view.js";

  // Ansagen und Schweinchen: Welche Stufen erlaubt sind, entscheidet der Server (legalActions).
  let { view, busy = false, act } = $props();

  const options = $derived(announceOptions(view));
  const schweinchen = $derived(!!legalAction(view, "schweinchen"));
  const mandatory = $derived(view.game.mandatoryAnnouncementSeat === view.table.mySeat);
</script>

{#if options.length || schweinchen}
  <div class="bar" role="group" aria-label="Ansagen">
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
        onclick={() => act({ type: "announce", level: o.level })}
      >
        {o.label}
      </button>
    {/each}
    {#if schweinchen}
      <button type="button" class="nx-btn nx-btn-sm nx-bg-lavender" disabled={busy} onclick={() => act({ type: "schweinchen" })}>
        SCHWEINCHEN
      </button>
    {/if}
  </div>
{/if}

<style>
  .bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 8px 0;
  }
  .note {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.8rem;
  }
</style>
