<script>
  import { onMount } from "svelte";
  import { formatMinutes, formatNumber, percent } from "../../lib/format.js";
  import { api } from "../../lib/services.js";

  let { token, onAuthLost } = $props();

  let s = $state(null);
  let error = $state("");

  onMount(async () => {
    try {
      s = await api.adminStats(token);
    } catch (e) {
      if (e.status === 401) return onAuthLost();
      error = e.message;
    }
  });

  const maxDay = $derived(s ? Math.max(1, ...s.perDay.map((d) => d.tables)) : 1);
  const maxBucket = $derived(s ? Math.max(1, ...s.gamesBuckets.map((b) => b.tables)) : 1);
  const maxHumans = $derived(s ? Math.max(1, ...Object.values(s.byHumans)) : 1);
  const groups = $derived(
    s ? [["Nur gegen Bots (1 Mensch)", s.againstBotsOnly, "nx-bg-coral"], ["Mit mehreren Menschen", s.withHumans, "nx-bg-green"]] : [],
  );
</script>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}

{#if s}
  <div class="sums">
    <div class="sum nx-bg-yellow"><b>{formatNumber(s.tablesTotal)}</b><span>Tische insgesamt</span></div>
    <div class="sum nx-bg-white"><b>{formatNumber(s.last24h)}</b><span>letzte 24 Std.</span></div>
    <div class="sum nx-bg-white"><b>{formatNumber(s.last7d)}</b><span>letzte 7 Tage</span></div>
    <div class="sum nx-bg-white"><b>{formatNumber(s.last30d)}</b><span>letzte 30 Tage</span></div>
    <div class="sum nx-bg-blue"><b>{formatNumber(s.gamesTotal)}</b><span>Spiele gespielt</span></div>
    <div class="sum nx-bg-lavender"><b>{formatNumber(s.tablesNeverStarted)}</b><span>nie gestartet</span></div>
  </div>

  <h3 class="nx-h3">Gegen Bots oder mit Menschen?</h3>
  <p class="nx-hint">Gezählt werden gestartete Tische. „Nur gegen Bots“ heißt: ein einziger Mensch am Tisch.</p>
  <div class="split" role="img" aria-label="Anteil der Tische nur gegen Bots und mit mehreren Menschen">
    {#each groups as [label, g, cls] (label)}
      {#if g.tables}
        <div class="seg {cls}" style="flex-grow: {g.tables}">{g.tables} · {percent(g.tables, s.tablesStarted)}</div>
      {/if}
    {/each}
    {#if !s.tablesStarted}<div class="seg nx-bg-white" style="flex-grow: 1">noch keine Daten</div>{/if}
  </div>

  <div class="scroll">
    <table class="nx-table">
      <thead>
        <tr><th>Gruppe</th><th class="num">Tische</th><th class="num">Ø Min.</th><th class="num">Median Min.</th><th class="num">Längster Tisch (Min.)</th><th class="num">Ø Spiele</th><th class="num">Median Spiele</th></tr>
      </thead>
      <tbody>
        {#each groups as [label, g] (label)}
          <tr>
            <td>{label}</td><td class="num">{g.tables}</td>
            <td class="num">{formatMinutes(g.minutes.avg)}</td><td class="num">{formatMinutes(g.minutes.median)}</td><td class="num">{formatMinutes(g.minutes.max)}</td>
            <td class="num">{formatMinutes(g.games.avg)}</td><td class="num">{formatMinutes(g.games.median)}</td>
          </tr>
        {/each}
        <tr class="total">
          <td>Alle</td><td class="num">{s.tablesStarted}</td>
          <td class="num">{formatMinutes(s.minutes.avg)}</td><td class="num">{formatMinutes(s.minutes.median)}</td><td class="num">{formatMinutes(s.minutes.max)}</td>
          <td class="num">{formatMinutes(s.games.avg)}</td><td class="num">{formatMinutes(s.games.median)}</td>
        </tr>
      </tbody>
    </table>
  </div>
  <p class="nx-hint">Spielzeit = vom ersten Spielstart bis zur letzten Aktion am Tisch.</p>

  <h3 class="nx-h3">Wie viele Menschen sitzen am Tisch?</h3>
  <ul class="bars">
    {#each Object.entries(s.byHumans) as [n, count] (n)}
      <li>
        <span class="lab">{n} {n === "1" ? "Mensch" : "Menschen"}</span>
        <span class="bar"><i style="width: {(count / maxHumans) * 100}%"></i></span>
        <span class="val">{count}</span>
      </li>
    {/each}
  </ul>

  <h3 class="nx-h3">Wie viele Spiele je Tisch?</h3>
  <ul class="bars">
    {#each s.gamesBuckets as b (b.label)}
      <li>
        <span class="lab">{b.label}</span>
        <span class="bar"><i style="width: {(b.tables / maxBucket) * 100}%"></i></span>
        <span class="val">{b.tables}</span>
      </li>
    {/each}
  </ul>

  <h3 class="nx-h3">Neue Tische pro Tag (14 Tage)</h3>
  <div class="days" role="img" aria-label="Neue Tische pro Tag in den letzten 14 Tagen">
    {#each s.perDay as d (d.date)}
      <div class="day" title="{d.date}: {d.tables}">
        <span class="v">{d.tables}</span>
        <span class="col"><i style="height: {(d.tables / maxDay) * 100}%"></i></span>
        <span class="d">{d.date.slice(8)}.{d.date.slice(5, 7)}.</span>
      </div>
    {/each}
  </div>
{:else if !error}
  <p>Lade …</p>
{/if}

<style>
  .sums { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 18px; }
  .sum { border: 3px solid #000; box-shadow: var(--nb-shadow-sm); padding: 10px 12px; display: flex; flex-direction: column; }
  .sum b { font-family: var(--font-heading); font-size: 1.8rem; line-height: 1.1; }
  .sum span { font-size: 0.85rem; }
  h3 { margin: 22px 0 6px; }
  .split { display: flex; border: 3px solid #000; margin: 8px 0 14px; min-height: 42px; }
  .seg { display: flex; align-items: center; justify-content: center; padding: 6px 10px; font-weight: 700; font-size: 0.9rem; text-align: center; }
  .seg + .seg { border-left: 3px solid #000; }
  .scroll { overflow-x: auto; }
  .total td { font-weight: 700; background: var(--nb-paper); }
  .bars { list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 6px; }
  .bars li { display: grid; grid-template-columns: 110px 1fr 40px; gap: 10px; align-items: center; }
  .lab { font-weight: 600; }
  .bar { border: 3px solid #000; background: #fff; height: 22px; display: block; }
  .bar i { display: block; height: 100%; background: var(--nb-blue); border-right: 3px solid #000; min-width: 0; }
  .bar i[style*="width: 0%"] { border-right: 0; }
  .val { font-family: var(--font-mono); font-weight: 700; text-align: right; }
  .days { display: grid; grid-template-columns: repeat(14, minmax(0, 1fr)); gap: 4px; align-items: end; margin: 10px 0; }
  .day { display: flex; flex-direction: column; align-items: center; gap: 2px; font-size: 0.7rem; }
  .col { display: flex; align-items: flex-end; width: 100%; height: 90px; border-bottom: 3px solid #000; }
  .col i { display: block; width: 100%; background: var(--nb-yellow); border: 2px solid #000; border-bottom: 0; }
  .col i[style*="height: 0%"] { border: 0; }
  .v { font-family: var(--font-mono); font-weight: 700; }
  .d { font-family: var(--font-mono); font-size: 0.62rem; }
  @media (max-width: 520px) {
    .bars li { grid-template-columns: 84px 1fr 32px; }
    .d { display: none; }
  }
</style>
