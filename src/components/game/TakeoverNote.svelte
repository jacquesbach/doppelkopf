<script>
  import { useCountdown } from "../../lib/countdown.svelte.js";
  import { seatName } from "../../lib/view.js";

  // Hinweis für die anderen Mitspieler: Auf wen gewartet wird und wann ein Bot einspringt.
  let { store } = $props();

  const warn = $derived(store.view.table.takeoverWarning);
  const clock = useCountdown(() => (warn ? { remaining: warn.remaining, at: store.viewAt } : null));
  const seconds = $derived(Math.ceil(clock.left));
</script>

{#if warn}
  <p class="note" role="status">
    {seatName(store.view, warn.seat)} reagiert nicht –
    {#if seconds > 0}ein Bot übernimmt in {seconds} s.{:else}ein Bot übernimmt gleich.{/if}
  </p>
{/if}

<style>
  .note {
    margin: 0 auto 12px;
    width: fit-content;
    max-width: 100%;
    padding: 6px 12px;
    border: 3px solid #000;
    background: var(--nb-coral);
    box-shadow: var(--nb-shadow-sm);
    font-weight: 700;
    text-align: center;
  }
</style>
