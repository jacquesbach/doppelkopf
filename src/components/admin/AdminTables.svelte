<script>
  import { onMount } from "svelte";
  import { formatDuration, formatDateTime } from "../../lib/format.js";
  import { api } from "../../lib/services.js";

  let { token, onAuthLost } = $props();

  let data = $state(null);
  let error = $state("");
  let now = $state(Date.now() / 1000);

  async function load() {
    try {
      data = await api.adminTables(token);
      now = Date.now() / 1000;
      error = "";
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    }
  }

  onMount(() => {
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  });

  const STATUS = { waiting: "Lobby", playing: "Läuft", finished: "Beendet" };
</script>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}

{#if data}
  <div class="sums">
    <div class="sum nx-bg-white"><b>{data.count}</b><span>offene Tische</span></div>
    <div class="sum nx-bg-green"><b>{data.activeCount}</b><span>aktiv (letzte 5 Min.)</span></div>
    <div class="sum nx-bg-blue"><b>{data.humansTotal}</b><span>echte Menschen</span></div>
    <div class="sum nx-bg-yellow"><b>{data.connectedTotal}</b><span>gerade verbunden</span></div>
  </div>

  {#if !data.tables.length}
    <p>Im Moment ist kein Tisch offen.</p>
  {:else}
    <div class="scroll">
      <table class="nx-table">
        <thead>
          <tr>
            <th>Tisch</th><th>Zustand</th><th class="num">Menschen</th><th class="num">Bots</th>
            <th>Aktiv seit</th><th>Letzte Aktion</th><th>Spiel</th>
          </tr>
        </thead>
        <tbody>
          {#each data.tables as t (t.code)}
            <tr>
              <td class="mono">{t.code}
                {#if t.isLab}<span class="tag lab">Test</span>{/if}
                {#if t.isPublic}<span class="tag">öffentlich</span>{/if}
                {#if t.hasPassword}<span class="tag">Passwort</span>{/if}
              </td>
              <td>
                <span class="state {t.state}">{t.state === "active" ? "AKTIV" : "INAKTIV"}</span>
                <small>{STATUS[t.status] ?? t.status}</small>
              </td>
              <td class="num">{t.humans}{#if t.connectedHumans !== t.humans} <small>({t.connectedHumans} da)</small>{/if}
                {#if t.againstBotsOnly}<small class="solo">solo</small>{/if}</td>
              <td class="num">{t.bots}</td>
              <td>{formatDuration(now - t.activeSince)} <small>(seit {formatDateTime(t.activeSince)})</small></td>
              <td>{t.state === "active" ? "gerade eben" : `vor ${formatDuration(t.idleSeconds)}`}</td>
              <td>{#if t.game}Spiel {t.game.number ?? "–"}{:else}–{/if}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="nx-hint">„Aktiv seit“ zählt ab dem ersten Spielstart (in der Lobby: seit dem Anlegen). „Inaktiv“ heißt: seit mehr als 5 Minuten keine Aktion. Leere Tische räumt das System nach 12 Stunden ab.</p>
  {/if}
{:else if !error}
  <p>Lade …</p>
{/if}

<style>
  .sums { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 18px; }
  .sum { border: 3px solid #000; box-shadow: var(--nb-shadow-sm); padding: 10px 12px; display: flex; flex-direction: column; }
  .sum b { font-family: var(--font-heading); font-size: 1.8rem; line-height: 1.1; }
  .sum span { font-size: 0.85rem; }
  .scroll { overflow-x: auto; margin-bottom: 8px; }
  .mono { font-family: var(--font-mono); font-weight: 700; white-space: nowrap; }
  .tag { font-family: var(--font-body); font-weight: 400; font-size: 0.72rem; border: 2px solid #000; padding: 0 4px; margin-left: 4px; background: var(--nb-paper); }
  .tag.lab { background: var(--nb-lavender); font-weight: 700; }
  small { color: #444; }
  .state { display: inline-block; border: 2px solid #000; padding: 0 6px; font-weight: 700; font-size: 0.78rem; margin-right: 4px; }
  .state.active { background: var(--nb-green); }
  .state.idle { background: var(--nb-orange); }
  .solo { margin-left: 4px; }
</style>
