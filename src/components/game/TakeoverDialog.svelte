<script>
  import { useCountdown } from "../../lib/countdown.svelte.js";
  import Dialog from "../ui/Dialog.svelte";

  // Erscheint bei dem Spieler, der am Zug ist und nicht reagiert: Läuft der Countdown ab, übernimmt ein Bot den Platz.
  // „Weiterspielen“ stoppt ihn; mit dem Haken wird die Entscheidung gemerkt (dann übernimmt nie ein Bot für diesen Spieler).
  let { store } = $props();

  const warn = $derived(store.view.table.takeoverWarning);
  const total = 30;
  const clock = useCountdown(() => (warn ? { remaining: warn.remaining, at: store.viewAt } : null));
  const seconds = $derived(Math.ceil(clock.left));
  let remember = $state(false);
</script>

<Dialog title="Bist du noch da?">
  <p class="lead">
    Du bist am Zug, aber es tut sich nichts.
    {#if seconds > 0}
      In <strong class="secs">{seconds} {seconds === 1 ? "Sekunde" : "Sekunden"}</strong> übernimmt ein Bot deinen Platz.
    {:else}
      Ein Bot übernimmt deinen Platz …
    {/if}
  </p>
  <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax={total} aria-valuenow={seconds} aria-label="Countdown bis zur Bot-Übernahme">
    <div class="fill" style="width:{Math.min(100, (clock.left / total) * 100)}%"></div>
  </div>

  <label class="check">
    <input type="checkbox" bind:checked={remember} />
    <span>Entscheidung merken: Bei Inaktivität nie durch einen Bot ersetzen</span>
  </label>

  <div class="nx-btn-row" style="margin-top:18px;">
    <button type="button" class="nx-btn nx-btn-lg" disabled={store.busy} onclick={() => store.stay(remember ? true : undefined)}>
      WEITERSPIELEN
    </button>
    <button type="button" class="nx-btn nx-bg-white" disabled={store.busy} onclick={() => store.leaveGame()}>
      BOT JETZT ÜBERNEHMEN LASSEN
    </button>
  </div>
</Dialog>

<style>
  .lead {
    margin: 0 0 14px;
    line-height: 1.45;
  }
  .secs {
    font-family: var(--font-mono);
    font-size: 1.15em;
  }
  .bar {
    height: 16px;
    border: 3px solid #000;
    background: #fff;
    margin-bottom: 16px;
  }
  .fill {
    height: 100%;
    background: var(--nb-coral);
    transition: width 0.25s linear;
  }
  .check {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    font-weight: 600;
    cursor: pointer;
  }
  .check input {
    width: 20px;
    height: 20px;
    margin-top: 1px;
    accent-color: #000;
    flex-shrink: 0;
  }
  @media (prefers-reduced-motion: reduce) {
    .fill {
      transition: none;
    }
  }
</style>
