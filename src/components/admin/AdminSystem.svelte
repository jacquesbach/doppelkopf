<script>
  import { onMount } from "svelte";
  import { formatDateTime, formatDuration, formatNumber } from "../../lib/format.js";
  import { api } from "../../lib/services.js";

  let { token, onAuthLost } = $props();

  let sys = $state(null);
  let errors = $state([]);
  let error = $state("");
  let open = $state(null);
  let busy = $state(false);

  async function load() {
    try {
      const [s, e] = await Promise.all([api.adminSystem(token), api.adminErrors(token)]);
      sys = s;
      errors = e.errors;
      error = "";
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    }
  }
  onMount(load);

  async function remove(id) {
    try {
      await api.adminDeleteError(token, id);
      errors = errors.filter((x) => x.id !== id);
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      if (e.status !== 404) error = e.message;
      await load();
    }
  }
  async function clearAll() {
    busy = true;
    try {
      await api.adminClearErrors(token);
      await load();
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    } finally {
      busy = false;
    }
  }

  function bytes(n) {
    if (n == null) return "unbekannt";
    if (n < 1024) return `${n} B`;
    if (n < 1024 ** 2) return `${(n / 1024).toFixed(1).replace(".", ",")} KB`;
    if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1).replace(".", ",")} MB`;
    return `${(n / 1024 ** 3).toFixed(2).replace(".", ",")} GB`;
  }
  function stamp(iso) {
    if (!iso) return "unbekannt";
    const d = new Date(iso);
    return Number.isNaN(d.getTime())
      ? iso
      : d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  const ROWS = {
    tables: "Tische", games: "Spielverlauf-Einträge", tableLogs: "Tisch-Statistik", gameEvents: "Spiel-Ereignisse (anonym)",
    suggestions: "Vorschläge", phrases: "Sprüche", errors: "Fehler-Einträge",
  };
  const health = $derived(!sys ? "" : sys.runtime.errors24h === 0 ? "ok" : sys.runtime.errors24h < 10 ? "warn" : "bad");
</script>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}

{#if sys}
  <div class="sums">
    <div class="sum nx-bg-green"><b>{sys.version}</b><span>Version (Commit)</span></div>
    <div class="sum nx-bg-white"><b>{stamp(sys.deployedAt)}</b><span>Letzter Deploy</span></div>
    <div class="sum nx-bg-blue"><b>{formatDuration(sys.uptimeSeconds)}</b><span>Läuft seit dem Neustart</span></div>
    <div class="sum nx-bg-yellow"><b>{bytes(sys.db.bytes)}</b><span>Datenbank ({sys.db.kind})</span></div>
    <div class="sum {health === 'ok' ? 'nx-bg-green' : health === 'warn' ? 'nx-bg-orange' : 'nx-bg-coral'}">
      <b>{sys.runtime.errors24h}</b><span>Fehler in 24 Std.</span>
    </div>
  </div>

  <h3 class="nx-h3">Systemstatus</h3>
  <div class="scroll">
    <table class="nx-table">
      <tbody>
        <tr><td>Server gestartet</td><td>{formatDateTime(sys.startedAt)}</td></tr>
        <tr><td>Python</td><td>{sys.python}</td></tr>
        <tr><td>Laufende Bot-Schleifen</td><td>{sys.runtime.botLoops}</td></tr>
        <tr><td>Offene Socket-Verbindungen</td><td>{sys.runtime.socketConnections}</td></tr>
        <tr><td>Online-Status aktiv (freiwillig)</td><td>{sys.runtime.presenceOnline}</td></tr>
        {#if sys.runtime.disk}
          <tr><td>Freier Speicher</td><td>{bytes(sys.runtime.disk.free)} von {bytes(sys.runtime.disk.total)}</td></tr>
        {/if}
        {#each Object.entries(sys.db.rows) as [key, n] (key)}
          <tr><td>{ROWS[key] ?? key}</td><td>{formatNumber(n)}</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
  <p class="nx-hint">Version und Deploy-Zeitpunkt schreibt die GitHub-Action beim Deploy in die Server-Datei <code>.env</code>. Läuft der Server ohne Deploy (lokal), steht dort „unbekannt“.</p>

  <div class="head">
    <h3 class="nx-h3">Fehler-Log</h3>
    <div class="btns">
      <button type="button" class="nx-btn nx-btn-sm" onclick={load}>AKTUALISIEREN</button>
      {#if errors.length}<button type="button" class="nx-btn nx-btn-sm nx-bg-coral" disabled={busy} onclick={clearAll}>ALLE LÖSCHEN</button>{/if}
    </div>
  </div>
  {#if !errors.length}
    <p>Keine Fehler erfasst. 🎉</p>
  {:else}
    <ul class="errs">
      {#each errors as e (e.id)}
        <li class="nx-box">
          <button type="button" class="top" aria-expanded={open === e.id} onclick={() => (open = open === e.id ? null : e.id)}>
            <span class="kind">{e.kind}</span>
            <span class="msg">{e.message || "(ohne Text)"}</span>
            <span class="cnt">{e.count}×</span>
          </button>
          <p class="meta">{e.source === "http" ? "Anfrage" : "Hintergrund"} · {e.where} · zuletzt {formatDateTime(e.lastAt)} · erstmals {formatDateTime(e.firstAt)}</p>
          {#if open === e.id}
            <pre>{e.trace || "Kein Stacktrace."}</pre>
            <button type="button" class="nx-btn nx-btn-sm" onclick={() => remove(e.id)}>EINTRAG LÖSCHEN</button>
          {/if}
        </li>
      {/each}
    </ul>
    <p class="nx-hint">Gleiche Fehler werden gezählt statt wiederholt. Es werden höchstens 300 Einträge gehalten und Einträge nach 30 Tagen automatisch gelöscht. Der Text kann Fehlerdetails des Servers enthalten, aber keine Namen, Karten oder Chatnachrichten.</p>
  {/if}
{:else if !error}
  <p>Lade …</p>
{/if}

<style>
  .sums { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 10px; }
  .sum { border: 3px solid #000; box-shadow: var(--nb-shadow-sm); padding: 10px 12px; display: flex; flex-direction: column; }
  .sum b { font-family: var(--font-heading); font-size: 1.3rem; line-height: 1.2; overflow-wrap: anywhere; }
  .sum span { font-size: 0.85rem; }
  h3 { margin: 22px 0 6px; }
  .scroll { overflow-x: auto; }
  .head { display: flex; justify-content: space-between; align-items: end; gap: 10px; flex-wrap: wrap; }
  .btns { display: flex; gap: 8px; }
  .errs { list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 10px; }
  .errs li { padding: 8px 10px; margin: 0; }
  .top { all: unset; display: flex; gap: 8px; align-items: baseline; width: 100%; cursor: pointer; box-sizing: border-box; }
  .top:focus-visible { outline: 3px solid #000; outline-offset: 2px; }
  .kind { font-family: var(--font-mono); font-weight: 700; background: var(--nb-coral); border: 2px solid #000; padding: 0 5px; font-size: 0.8rem; }
  .msg { flex: 1; min-width: 0; overflow-wrap: anywhere; font-weight: 600; }
  .cnt { font-family: var(--font-mono); font-weight: 700; }
  .meta { margin: 4px 0 0; font-size: 0.78rem; color: #444; overflow-wrap: anywhere; }
  pre { margin: 8px 0; padding: 8px; background: #fff; border: 2px solid #000; overflow-x: auto; font-size: 0.74rem; max-height: 280px; }
</style>
