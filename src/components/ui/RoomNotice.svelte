<script>
  import Dialog from "./Dialog.svelte";
  import { navigate } from "../../lib/nav.svelte.js";

  // Nachricht des Betreibers an alle am Tisch. Bei „beendet“ geht es danach zur Startseite.
  let { store } = $props();
  const notice = $derived(store.notice);

  function ok() {
    const closed = notice?.closed;
    store.dismissNotice();
    if (closed) navigate("/");
  }
</script>

{#if notice}
  <Dialog title={notice.closed ? "Tisch beendet" : "Nachricht vom Betreiber"} onClose={notice.closed ? null : ok}>
    <p class="msg">{notice.message}</p>
    {#if notice.closed}<p class="nx-hint">Dieser Tisch wurde vom Betreiber beendet.</p>{/if}
    <button type="button" class="nx-btn nx-btn-block" onclick={ok}>{notice.closed ? "ZUR STARTSEITE" : "OK"}</button>
  </Dialog>
{/if}

<style>
  .msg { font-weight: 600; font-size: 1.05rem; overflow-wrap: anywhere; white-space: pre-line; }
</style>
