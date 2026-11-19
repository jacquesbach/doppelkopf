<script>
  import { SOLO_LABELS, SOLO_ORDER, SOLO_SUIT } from "../../lib/labels.js";
  import SuitIcon from "../cards/SuitIcon.svelte";

  // Vorbehaltsabfrage, Pflicht-/Lustsolo-Entscheidung und Taufe. Der Server gibt vor, was erlaubt ist.
  let { dialog, baptismKind = null, busy = false, act } = $props();

  const type = $derived(dialog.type);
  const stage = $derived(dialog.action.stage);
  const choices = $derived(dialog.action.choices ?? []);

  const baptismText = $derived(
    baptismKind === "pflichtsolo_forced"
      ? "Du musst dein Pflichtsolo vorführen. Welches Solo spielst du?"
      : baptismKind === "pflichtsolo"
        ? "Dein Pflichtsolo: Welches Solo spielst du?"
        : baptismKind === "lustsolo"
          ? "Dein Lustsolo: Welches Solo spielst du?"
          : "Du hast als Einziger einen Vorbehalt: Hochzeit oder Solo?",
  );
</script>

<section class="panel" aria-live="polite">
  {#if type === "declare"}
    <h2 class="nx-h2">Gesund oder Vorbehalt?</h2>
    <p class="hint">Schau dir deine Karten an. Mit Vorbehalt kannst du später Hochzeit, Armut oder Solo anmelden.</p>
    <div class="nx-btn-row">
      <button type="button" class="nx-btn nx-bg-green" disabled={busy} onclick={() => act({ type: "declare", reservation: false })}>
        GESUND
      </button>
      <button type="button" class="nx-btn nx-bg-coral" disabled={busy} onclick={() => act({ type: "declare", reservation: true })}>
        VORBEHALT
      </button>
    </div>
  {:else if type === "resolve"}
    <h2 class="nx-h2">{stage === "pflichtsolo" ? "Pflichtsolo spielen?" : "Lustsolo spielen?"}</h2>
    <p class="hint">
      {stage === "pflichtsolo"
        ? "Du hast noch kein Pflichtsolo gespielt. Möchtest du es mit diesem Blatt jetzt spielen?"
        : "Möchtest du ein freiwilliges Solo (Lustsolo) spielen?"}
    </p>
    <div class="nx-btn-row">
      <button type="button" class="nx-btn nx-bg-coral" disabled={busy} onclick={() => act({ type: "resolve", accept: true })}>
        JA, SOLO SPIELEN
      </button>
      <button type="button" class="nx-btn nx-bg-white" disabled={busy} onclick={() => act({ type: "resolve", accept: false })}>
        NEIN
      </button>
    </div>
  {:else if type === "baptize"}
    <h2 class="nx-h2">Spielart wählen</h2>
    <p class="hint">{baptismText}</p>
    <div class="grid">
      {#if choices.includes("wedding")}
        <button type="button" class="nx-btn nx-bg-lavender wide" disabled={busy} onclick={() => act({ type: "baptize", choice: "wedding" })}>
          HOCHZEIT
        </button>
      {/if}
      {#each SOLO_ORDER.filter((s) => choices.includes(s)) as solo (solo)}
        <button type="button" class="nx-btn nx-btn-sm solo" disabled={busy} onclick={() => act({ type: "baptize", choice: solo })}>
          {#if SOLO_SUIT[solo]}<SuitIcon suit={SOLO_SUIT[solo]} size="1.2em" />{/if}
          {SOLO_LABELS[solo]}
        </button>
      {/each}
    </div>
  {/if}
</section>

<style>
  .panel {
    border: 3px solid #000;
    background: var(--nb-bg);
    box-shadow: var(--nb-shadow-lg);
    padding: 20px;
    max-width: 460px;
    margin: 0 auto;
  }
  .hint {
    margin: 0 0 16px;
    font-size: 0.92rem;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }
  .wide {
    grid-column: 1 / -1;
  }
  .solo {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 8px;
  }
</style>
