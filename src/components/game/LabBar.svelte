<script>
  import { api, labSeats, sessions } from "../../lib/services.js";
  import { navigate } from "../../lib/nav.svelte.js";
  import { readAdminToken } from "../../lib/lab.js";

  // Leiste für Test-Tische (nur sichtbar, wenn dieser Browser den Tisch über den Admin-Bereich angelegt/geöffnet hat):
  // Platz wechseln und das Szenario neu starten. Der Wechsel tauscht das Sitzungs-Token und lädt die Seite neu.
  let { code, mySeat } = $props();

  const seats = $derived(labSeats.get(code));
  let open = $state(false);
  let error = $state("");
  let busy = $state(false);

  function switchTo(seat) {
    const current = sessions.get(code) ?? {};
    sessions.set(code, { ...current, token: seat.token, memberId: seat.memberId });
    window.location.reload();
  }

  async function restart() {
    const admin = readAdminToken(window.sessionStorage);
    if (!admin) {
      error = "Zum Neustarten im Betreiber-Bereich anmelden (Tab „Test-Tisch“).";
      return;
    }
    busy = true;
    error = "";
    try {
      await api.adminLabReset(admin, code);
      window.location.reload();
    } catch (e) {
      busy = false;
      error = e.status === 401 ? "Anmeldung abgelaufen – bitte im Betreiber-Bereich neu anmelden." : e.message;
    }
  }
</script>

{#if seats}
  <aside class="lab" class:open aria-label="Test-Tisch">
    <button type="button" class="tab" onclick={() => (open = !open)} aria-expanded={open}>
      TEST {open ? "▼" : "▲"}
    </button>
    {#if open}
      <div class="panel nx-box">
        <p class="t">Du spielst: <b>Platz {(mySeat ?? 0) + 1}</b></p>
        <div class="row" role="group" aria-label="Platz wechseln">
          {#each seats as s (s.seat)}
            {#if s.isBot}
              <span class="seat bot" title="Bot">{s.seat + 1} Bot</span>
            {:else}
              <button type="button" class="seat" class:on={s.seat === mySeat} disabled={s.seat === mySeat} onclick={() => switchTo(s)}>
                {s.seat + 1} {s.name}
              </button>
            {/if}
          {/each}
        </div>
        <div class="row">
          <button type="button" class="nx-btn nx-btn-sm nx-bg-yellow" disabled={busy} onclick={restart}>SZENARIO NEU STARTEN</button>
          <button type="button" class="nx-btn nx-btn-sm" onclick={() => navigate("/admin")}>ZUM ADMIN</button>
        </div>
        {#if error}<p class="nx-error" role="alert">{error}</p>{/if}
      </div>
    {/if}
  </aside>
{/if}

<style>
  .lab { position: fixed; left: 8px; bottom: 8px; z-index: 60; display: flex; flex-direction: column; align-items: flex-start; gap: 6px; max-width: calc(100vw - 16px); }
  .tab { font-family: var(--font-heading); font-weight: 700; font-size: 0.78rem; background: var(--nb-lavender); border: 3px solid #000; box-shadow: var(--nb-shadow-sm); padding: 4px 10px; cursor: pointer; }
  .panel { margin: 0; padding: 10px; background: #fff; }
  .t { margin: 0 0 8px; font-size: 0.9rem; }
  .row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
  .seat { font: inherit; font-weight: 700; font-size: 0.82rem; background: #fff; border: 2px solid #000; padding: 4px 8px; cursor: pointer; }
  .seat.on { background: var(--nb-yellow); cursor: default; }
  .seat.bot { background: var(--nb-paper); color: #555; font-weight: 400; cursor: default; }
</style>
