<script>
  import { SOLO_LABELS, SOLO_ORDER, SOLO_SUIT } from "../../lib/labels.js";
  import SuitIcon from "../cards/SuitIcon.svelte";

  // Vorbehaltsabfrage, Pflicht-/Lustsolo-Entscheidung, Taufe und Armut. Der Server gibt vor, was erlaubt ist.
  // `poverty`: Hausregel Armut ist am Tisch eingeschaltet; `poorName`: wer die Armut angemeldet hat.
  let { dialog, baptismKind = null, busy = false, act, poverty = false, poorName = "" } = $props();

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
          : choices.includes("poverty")
            ? choices.includes("wedding")
              ? "Du hast als Einziger einen Vorbehalt: Hochzeit, Armut oder Solo?"
              : "Du hast als Einziger einen Vorbehalt: Armut oder Solo?"
            : "Du hast als Einziger einen Vorbehalt: Hochzeit oder Solo?",
  );
</script>

<section class="panel" aria-live="polite">
  {#if type === "declare"}
    <h2 class="nx-h2">Gesund oder Vorbehalt?</h2>
    <p class="hint">
      Schau dir deine Karten an. Mit Vorbehalt kannst du später {poverty ? "Hochzeit, Armut oder Solo" : "Hochzeit oder Solo"} anmelden.
    </p>
    <div class="nx-btn-row">
      <button type="button" class="nx-btn nx-bg-green" disabled={busy} onclick={() => act({ type: "declare", reservation: false })}>
        GESUND
      </button>
      <button type="button" class="nx-btn nx-bg-coral" disabled={busy} onclick={() => act({ type: "declare", reservation: true })}>
        VORBEHALT
      </button>
    </div>
  {:else if type === "resolve"}
    <h2 class="nx-h2">
      {stage === "pflichtsolo" ? "Pflichtsolo spielen?" : stage === "poverty" ? "Armut anmelden?" : "Lustsolo spielen?"}
    </h2>
    <p class="hint">
      {stage === "pflichtsolo"
        ? "Du hast noch kein Pflichtsolo gespielt. Möchtest du es mit diesem Blatt jetzt spielen?"
        : stage === "poverty"
          ? "Du hast höchstens 3 Trümpfe. Möchtest du eine Armut anmelden und 3 Karten verdeckt weitergeben? Findet sich kein Käufer, wird neu gegeben."
          : "Möchtest du ein freiwilliges Solo (Lustsolo) spielen?"}
    </p>
    <div class="nx-btn-row">
      <button type="button" class="nx-btn nx-bg-coral" disabled={busy} onclick={() => act({ type: "resolve", accept: true })}>
        {stage === "poverty" ? "JA, ARMUT ANMELDEN" : "JA, SOLO SPIELEN"}
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
      {#if choices.includes("poverty")}
        <button type="button" class="nx-btn nx-bg-yellow wide" disabled={busy} onclick={() => act({ type: "baptize", choice: "poverty" })}>
          ARMUT (3 KARTEN WEITERGEBEN)
        </button>
      {/if}
      {#each SOLO_ORDER.filter((s) => choices.includes(s)) as solo (solo)}
        <button type="button" class="nx-btn nx-btn-sm solo" disabled={busy} onclick={() => act({ type: "baptize", choice: solo })}>
          {#if SOLO_SUIT[solo]}<SuitIcon suit={SOLO_SUIT[solo]} size="1.2em" />{/if}
          {SOLO_LABELS[solo]}
        </button>
      {/each}
    </div>
  {:else if type === "poverty_offer"}
    <h2 class="nx-h2">Armut übernehmen?</h2>
    <p class="hint">
      {poorName || "Ein Mitspieler"} hat eine Armut angemeldet und 3 Karten verdeckt abgelegt. Übernimmst du sie, kommen sie in dein
      Blatt – danach gibst du 3 beliebige Karten zurück. Ihr beide spielt dann zusammen als Re gegen die anderen zwei. Übernimmt niemand,
      wird neu gegeben.
    </p>
    <div class="nx-btn-row">
      <button type="button" class="nx-btn nx-bg-coral" disabled={busy} onclick={() => act({ type: "poverty_offer", accept: true })}>
        JA, ÜBERNEHMEN
      </button>
      <button type="button" class="nx-btn nx-bg-white" disabled={busy} onclick={() => act({ type: "poverty_offer", accept: false })}>
        NEIN
      </button>
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
  /* Desktop mit wenig Höhe: Panel kompakter, damit es in die Tischmitte passt (die Hand bleibt sichtbar) */
  @media (min-width: 641px) and (max-height: 800px) {
    .panel {
      padding: 12px 16px;
      max-width: 560px;
    }
    .panel :global(.nx-h2) {
      margin-bottom: 6px;
      font-size: 1.1rem;
    }
    .hint {
      margin-bottom: 8px;
      font-size: 0.85rem;
      line-height: 1.4;
    }
    .grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .panel :global(.nx-btn) {
      padding-block: 6px;
      font-size: 0.88rem;
    }
  }
</style>
