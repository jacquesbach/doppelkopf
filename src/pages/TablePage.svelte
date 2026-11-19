<script>
  import { onDestroy, onMount } from "svelte";
  import { api, realtime, sessions } from "../lib/services.js";
  import { navigate } from "../lib/nav.svelte.js";
  import { TableStore } from "../lib/table.svelte.js";
  import PageShell from "../components/ui/PageShell.svelte";
  import Lobby from "./Lobby.svelte";
  import GameTable from "../components/game/GameTable.svelte";

  let { code } = $props();

  const store = new TableStore(code, { api, sessions, realtime });

  onMount(async () => {
    await store.init();
    if (store.status === "needs_join") navigate(`/beitreten/${code}`, { replace: true });
  });
  onDestroy(() => store.destroy());
</script>

{#if store.status === "loading"}
  <PageShell narrow><p class="nx-mono" role="status">LADE TISCH …</p></PageShell>
{:else if store.status === "not_found"}
  <PageShell narrow>
    <span class="nx-badge nx-bg-coral">404</span>
    <h1 class="nx-title">Tisch nicht gefunden</h1>
    <p>Der Tisch <strong>{code}</strong> existiert nicht (mehr).</p>
    <button class="nx-btn" onclick={() => navigate("/")}>ZUR STARTSEITE</button>
  </PageShell>
{:else if store.status === "error"}
  <PageShell narrow>
    <span class="nx-badge nx-bg-coral">FEHLER</span>
    <h1 class="nx-title">Keine Verbindung</h1>
    <p>{store.error}</p>
    <button class="nx-btn" onclick={() => window.location.reload()}>NEU LADEN</button>
  </PageShell>
{:else if store.status === "ready" && store.room}
  {#if store.room.status === "waiting" || !store.view}
    <Lobby {store} />
  {:else}
    <GameTable {store} />
  {/if}
{/if}

{#if store.error && store.status === "ready"}
  <div class="nx-toast" role="alert">
    <span>{store.error}</span>
    <button class="nx-btn nx-btn-sm" onclick={() => store.clearError()} aria-label="Meldung schließen">OK</button>
  </div>
{/if}
