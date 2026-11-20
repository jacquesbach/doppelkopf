<script>
  import { onMount } from "svelte";
  import { formatMinutes, formatNumber, percent } from "../../lib/format.js";
  import { api } from "../../lib/services.js";

  let { token, onAuthLost } = $props();

  let s = $state(null);
  let error = $state("");

  onMount(async () => {
    try {
      s = await api.adminInsights(token);
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    }
  });

  const maxDay = $derived(s ? Math.max(1, ...s.perDay.map((d) => d.games)) : 1);
  const maxHour = $derived(s ? Math.max(1, ...s.byHour) : 1);
  const maxWeekday = $derived(s ? Math.max(1, ...s.byWeekday.map((d) => d.games)) : 1);
  const hourLabel = (h) => `${String(h).padStart(2, "0")}–${String((h + 1) % 24).padStart(2, "0")} Uhr`;
  const rate = (value) => (value == null ? "–" : `${Math.round(value * 100)} %`);
</script>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}

{#if s}
  <div class="sums">
    <div class="sum nx-bg-yellow"><b>{formatNumber(s.gamesInPeriod)}</b><span>Spiele in {s.days} Tagen</span></div>
    <div class="sum nx-bg-white"><b>{formatNumber(s.gamesTotal)}</b><span>Spiele insgesamt (seit Erfassung)</span></div>
    <div class="sum nx-bg-blue"><b>{s.peak.hour == null ? "–" : hourLabel(s.peak.hour)}</b><span>Spitzenzeit</span></div>
    <div class="sum nx-bg-green"><b>{s.duration.count ? `${formatMinutes(s.duration.avg)} Min.` : "–"}</b><span>Ø Spieldauer</span></div>
    <div class="sum nx-bg-coral"><b>{rate(s.abort.neverFinishedRate)}</b><span>Tische ohne ein fertiges Spiel</span></div>
  </div>
  <p class="nx-hint">Alle Zeiten in deutscher Zeit. Erfasst wird pro beendetem Spiel nur: Zeitpunkt, Dauer und Zahl der Menschen – keine Namen, keine Karten.</p>

  <h3 class="nx-h3">Spiele pro Tag ({s.days} Tage)</h3>
  <div class="days" role="img" aria-label="Spiele pro Tag">
    {#each s.perDay as d (d.date)}
      <div class="day" title="{d.date}: {d.games}">
        <span class="col"><i style="height: {(d.games / maxDay) * 100}%"></i></span>
      </div>
    {/each}
  </div>
  <p class="axis"><span>{s.perDay[0].date.slice(8)}.{s.perDay[0].date.slice(5, 7)}.</span><span>Höchstwert {maxDay}</span><span>heute</span></p>

  <h3 class="nx-h3">Spitzenzeiten nach Uhrzeit</h3>
  <div class="hours" role="img" aria-label="Spiele nach Uhrzeit">
    {#each s.byHour as n, h (h)}
      <div class="hr" title="{hourLabel(h)}: {n}">
        <span class="col"><i style="height: {(n / maxHour) * 100}%"></i></span>
        <span class="h">{h % 3 === 0 ? h : ""}</span>
      </div>
    {/each}
  </div>

  <h3 class="nx-h3">Nach Wochentag{#if s.peak.weekday} <small>(am meisten: {s.peak.weekday})</small>{/if}</h3>
  <ul class="bars">
    {#each s.byWeekday as d (d.label)}
      <li>
        <span class="lab">{d.label}</span>
        <span class="bar"><i style="width: {(d.games / maxWeekday) * 100}%"></i></span>
        <span class="val">{d.games}</span>
      </li>
    {/each}
  </ul>

  <h3 class="nx-h3">Spieldauer</h3>
  <div class="scroll">
    <table class="nx-table">
      <thead><tr><th>Gruppe</th><th class="num">Spiele</th><th class="num">Ø Min.</th><th class="num">Median Min.</th><th class="num">90 % unter Min.</th></tr></thead>
      <tbody>
        <tr><td>Alle</td><td class="num">{s.duration.count}</td><td class="num">{formatMinutes(s.duration.avg)}</td><td class="num">{formatMinutes(s.duration.median)}</td><td class="num">{formatMinutes(s.duration.p90)}</td></tr>
        <tr><td>Mit mindestens 2 Menschen</td><td class="num">{s.durationWithHumans.count}</td><td class="num">{formatMinutes(s.durationWithHumans.avg)}</td><td class="num">{formatMinutes(s.durationWithHumans.median)}</td><td class="num">{formatMinutes(s.durationWithHumans.p90)}</td></tr>
      </tbody>
    </table>
  </div>
  <p class="nx-hint">Gezählt wird die Zeit vom Spielstart bis zum Ergebnis. Pausen über 3 Stunden (offen gelassene Tische) bleiben außen vor.</p>

  <h3 class="nx-h3">Abbrüche</h3>
  <div class="scroll">
    <table class="nx-table">
      <tbody>
        <tr><td>Beendete Tische (gestartet, seit &gt; 1 Std. ruhig)</td><td class="num">{formatNumber(s.abort.tablesEnded)}</td></tr>
        <tr><td>… davon ohne ein einziges fertiges Spiel</td><td class="num">{formatNumber(s.abort.neverFinishedAGame)} · {percent(s.abort.neverFinishedAGame, s.abort.tablesEnded)}</td></tr>
        <tr><td>Runden dieser Tische</td><td class="num">{formatNumber(s.abort.rounds)}</td></tr>
        <tr><td>… davon nicht zu Ende gespielt</td><td class="num">{formatNumber(s.abort.roundsAborted)} · {rate(s.abort.roundsAbortedRate)}</td></tr>
      </tbody>
    </table>
  </div>
  <p class="nx-hint">Abbruchquote = Anteil der Runden und Tische, die nie zu Ende gespielt wurden (Fenster zu, Streit, Verbindungsprobleme …).</p>
{:else if !error}
  <p>Lade …</p>
{/if}

<style>
  .sums { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 10px; }
  .sum { border: 3px solid #000; box-shadow: var(--nb-shadow-sm); padding: 10px 12px; display: flex; flex-direction: column; }
  .sum b { font-family: var(--font-heading); font-size: 1.5rem; line-height: 1.15; }
  .sum span { font-size: 0.85rem; }
  h3 { margin: 22px 0 6px; }
  h3 small { font-weight: 400; }
  .scroll { overflow-x: auto; }
  .days { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(0, 1fr); gap: 3px; align-items: end; margin-top: 10px; }
  .hours { display: grid; grid-template-columns: repeat(24, minmax(0, 1fr)); gap: 3px; margin-top: 10px; }
  .col { display: flex; align-items: flex-end; width: 100%; height: 90px; border-bottom: 3px solid #000; }
  .col i { display: block; width: 100%; background: var(--nb-yellow); border: 2px solid #000; border-bottom: 0; }
  .col i[style*="height: 0%"] { border: 0; }
  .hr { display: flex; flex-direction: column; align-items: center; }
  .h { font-family: var(--font-mono); font-size: 0.65rem; min-height: 1em; }
  .axis { display: flex; justify-content: space-between; font-family: var(--font-mono); font-size: 0.68rem; margin: 2px 0 0; }
  .bars { list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 6px; }
  .bars li { display: grid; grid-template-columns: 110px 1fr 40px; gap: 10px; align-items: center; }
  .lab { font-weight: 600; }
  .bar { border: 3px solid #000; background: #fff; height: 22px; display: block; }
  .bar i { display: block; height: 100%; background: var(--nb-blue); border-right: 3px solid #000; }
  .bar i[style*="width: 0%"] { border-right: 0; }
  .val { font-family: var(--font-mono); font-weight: 700; text-align: right; }
  @media (max-width: 520px) { .bars li { grid-template-columns: 90px 1fr 32px; } }
</style>
