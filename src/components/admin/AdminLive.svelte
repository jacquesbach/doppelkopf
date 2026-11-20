<script>
  import { onMount } from "svelte";
  import { formatDuration } from "../../lib/format.js";
  import { navigate } from "../../lib/nav.svelte.js";
  import { api, sessions } from "../../lib/services.js";

  let { token, onAuthLost } = $props();

  let data = $state(null);
  let error = $state("");
  let notice = $state("");
  let pending = $state(null); // { code, mode: "message" | "close" }
  let text = $state("");
  let busy = $state(false);
  let paused = $state(false);

  async function load() {
    if (paused) return;
    try {
      data = await api.adminLive(token);
      error = "";
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    }
  }

  onMount(() => {
    load();
    const timer = setInterval(load, 3000); // „Echtzeit“: alle 3 Sekunden
    return () => clearInterval(timer);
  });

  const STATE = { running: ["LÄUFT", "run"], waiting: ["LOBBY", "wait"], finished: ["ENDE", "idle"], idle: ["RUHT", "idle"] };

  function open(code, mode) {
    pending = { code, mode };
    text = "";
    notice = "";
    error = "";
    paused = true; // Eingabe nicht durch Neuladen stören
  }
  function cancel() {
    pending = null;
    paused = false;
  }

  async function submit(event) {
    event.preventDefault();
    if (!pending) return;
    busy = true;
    error = "";
    try {
      if (pending.mode === "message") {
        await api.adminLiveMessage(token, pending.code, text);
        notice = `Nachricht an Tisch ${pending.code} gesendet.`;
      } else {
        await api.adminLiveClose(token, pending.code, text);
        notice = `Tisch ${pending.code} wurde beendet.`;
      }
      pending = null;
      paused = false;
      await load();
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.status === 404 ? "Diesen Tisch gibt es nicht mehr." : e.message;
    } finally {
      busy = false;
    }
  }

  async function spectate(code) {
    error = "";
    try {
      const { memberId, token: seat } = await api.adminLiveSpectate(token, code);
      sessions.set(code, { token: seat, memberId });
      navigate(`/tisch/${code}`);
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.status === 404 ? "Diesen Tisch gibt es nicht mehr." : e.message;
    }
  }
</script>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}
{#if notice}<p class="nx-success" role="status">{notice}</p>{/if}

{#if data}
  <div class="sums" aria-live="polite">
    <div class="sum nx-bg-green"><b>{data.running}</b><span>laufende Spiele</span></div>
    <div class="sum nx-bg-white"><b>{data.waiting}</b><span>Tische in der Lobby</span></div>
    <div class="sum nx-bg-yellow"><b>{data.humansOnline}</b><span>Spieler online</span></div>
    <div class="sum nx-bg-blue"><b>{data.playingNow}</b><span>davon im Spiel</span></div>
    <div class="sum nx-bg-lavender"><b>{data.botOnlyTables}</b><span>Spiele nur gegen Bots</span></div>
    <div class="sum nx-bg-white"><b>{data.idle}</b><span>ruhende Tische</span></div>
  </div>
  <p class="nx-hint live"><i class="dot" aria-hidden="true"></i> Live – aktualisiert sich alle 3 Sekunden{#if paused} (angehalten, solange du eine Nachricht schreibst){/if}.</p>

  {#if !data.tables.length}
    <p>Im Moment ist kein Tisch offen.</p>
  {:else}
    <ul class="tables">
      {#each data.tables as t (t.code)}
        {@const [label, cls] = STATE[t.state] ?? ["?", "idle"]}
        <li class="t nx-box">
          <div class="head">
            <span class="code">{t.code}</span>
            <span class="state {cls}">{label}</span>
            {#if t.isLab}<span class="tag lab">Test</span>{/if}
            {#if t.isPublic}<span class="tag">öffentlich</span>{/if}
            {#if t.hasPassword}<span class="tag">Passwort</span>{/if}
          </div>
          <p class="meta">
            {t.humans} {t.humans === 1 ? "Mensch" : "Menschen"}{#if t.connectedHumans !== t.humans} ({t.connectedHumans} verbunden){/if}
            · {t.bots} {t.bots === 1 ? "Bot" : "Bots"}{#if t.spectators} · {t.spectators} Zuschauer{/if}
            · {#if t.game}Spiel {t.game.number ?? "–"}{#if t.game.tricks != null}, Stich {t.game.tricks}{/if}{:else}kein Spiel{/if}
            · {t.state === "running" ? "gerade aktiv" : `still seit ${formatDuration(t.idleSeconds)}`}
          </p>
          <ul class="seats">
            {#each t.players as p, i (i)}
              <li class:off={!p.isBot && !p.connected}>{p.name}{#if p.isHost} ★{/if}{#if p.isBot} (Bot){:else if !p.connected} (getrennt){/if}</li>
            {/each}
          </ul>
          <div class="actions">
            <button type="button" class="nx-btn nx-btn-sm" onclick={() => spectate(t.code)}>ZUSCHAUEN</button>
            <button type="button" class="nx-btn nx-btn-sm" onclick={() => open(t.code, "message")}>NACHRICHT</button>
            <button type="button" class="nx-btn nx-btn-sm nx-bg-coral" onclick={() => open(t.code, "close")}>BEENDEN</button>
          </div>

          {#if pending?.code === t.code}
            <form class="ask" onsubmit={submit}>
              <label class="nx-label" for="live-msg">
                {pending.mode === "message" ? "Nachricht an alle am Tisch" : "Tisch beenden – Nachricht an alle (optional)"}
              </label>
              <input
                id="live-msg"
                class="nx-input"
                maxlength="300"
                bind:value={text}
                placeholder={pending.mode === "message" ? "z. B. In 5 Minuten gibt es einen Neustart." : "z. B. Wartungsarbeiten – bitte später wieder vorbeikommen."}
              />
              {#if pending.mode === "close"}
                <p class="nx-hint">Alle am Tisch sehen die Nachricht und werden zur Startseite geleitet. Der Tisch und sein Spielstand werden gelöscht.</p>
              {/if}
              <div class="row">
                <button type="submit" class="nx-btn nx-btn-sm {pending.mode === 'close' ? 'nx-bg-coral' : 'nx-bg-yellow'}" disabled={busy || (pending.mode === "message" && !text.trim())}>
                  {busy ? "SENDE …" : pending.mode === "message" ? "SENDEN" : "ENDGÜLTIG BEENDEN"}
                </button>
                <button type="button" class="nx-btn nx-btn-sm" onclick={cancel}>ABBRECHEN</button>
              </div>
            </form>
          {/if}
        </li>
      {/each}
    </ul>
    <p class="nx-hint">Beim Zuschauen siehst du nur die öffentlichen Informationen, keine Handkarten. Die Spieler sehen dich in der Zuschauerliste als „Betreiber“. „Test“-Tische (Test-Tisch-Reiter) zählen nicht in die Summen.</p>
  {/if}
{:else if !error}
  <p>Lade …</p>
{/if}

<style>
  .sums { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 10px; }
  .sum { border: 3px solid #000; box-shadow: var(--nb-shadow-sm); padding: 10px 12px; display: flex; flex-direction: column; }
  .sum b { font-family: var(--font-heading); font-size: 1.8rem; line-height: 1.1; }
  .sum span { font-size: 0.85rem; }
  .live { display: flex; align-items: center; gap: 6px; margin: 0 0 14px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: #1fa34a; border: 2px solid #000; animation: pulse 1.6s ease-in-out infinite; }
  @keyframes pulse { 50% { opacity: 0.35; } }
  @media (prefers-reduced-motion: reduce) { .dot { animation: none; } }
  .tables { list-style: none; margin: 0 0 10px; padding: 0; display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
  .t { padding: 12px; margin: 0; }
  .head { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .code { font-family: var(--font-mono); font-weight: 700; font-size: 1.15rem; }
  .state { border: 2px solid #000; padding: 0 6px; font-weight: 700; font-size: 0.75rem; }
  .state.run { background: var(--nb-green); }
  .state.wait { background: var(--nb-yellow); }
  .state.idle { background: var(--nb-orange); }
  .tag { font-size: 0.72rem; border: 2px solid #000; padding: 0 4px; background: var(--nb-paper); }
  .tag.lab { background: var(--nb-lavender); font-weight: 700; }
  .meta { margin: 6px 0; font-size: 0.85rem; }
  .seats { list-style: none; margin: 0 0 8px; padding: 0; display: flex; flex-wrap: wrap; gap: 4px; }
  .seats li { border: 2px solid #000; background: #fff; padding: 0 6px; font-size: 0.8rem; }
  .seats li.off { background: var(--nb-paper); color: #555; border-style: dashed; }
  .actions, .row { display: flex; flex-wrap: wrap; gap: 8px; }
  .ask { margin-top: 10px; padding-top: 10px; border-top: 3px solid #000; display: grid; gap: 8px; }
</style>
