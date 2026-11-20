<script>
  import { presence } from "../../lib/presence.svelte.js";

  // Knopf zum Öffnen des Dialogs. Gestaltung kommt vom Aufrufer (class), damit er in jede Kopfzeile passt.
  let { class: cls = "nx-btn nx-btn-sm" } = $props();
  const online = $derived(presence.enabled && presence.connected);
  const count = $derived(presence.friends.filter((f) => presence.live[f.code]).length);
</script>

{#if presence.available}
  <button type="button" class={cls} onclick={() => presence.open()} aria-label={online ? `Wer ist online? ${count} Freunde online` : "Wer ist online?"}>
    <span class="dot" class:on={online} aria-hidden="true"></span> ONLINE{#if online && count}&nbsp;({count}){/if}
  </button>
{/if}

<style>
  .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; border: 2px solid #000; background: #fff; margin-right: 4px; vertical-align: -1px; }
  .dot.on { background: #1fa34a; }
</style>
