<script>
  import { onMount } from "svelte";
  import { api } from "../../lib/services.js";
  import { link } from "../../lib/nav.svelte.js";
  import { activeRuleLabels } from "../../lib/view.js";

  // Öffentliche Tische, die Mitspieler suchen (mit ihren Regeln). Aktualisiert sich selbst.
  let { compact = false } = $props();

  let rooms = $state(null); // null = lädt
  let failed = $state(false);

  async function load() {
    try {
      rooms = (await api.publicRooms()).rooms;
      failed = false;
    } catch {
      failed = true;
      rooms ??= [];
    }
  }

  onMount(() => {
    load();
    const timer = setInterval(load, 8000);
    return () => clearInterval(timer);
  });
</script>

<div class="list" class:compact aria-live="polite">
  {#if rooms === null}
    <p class="empty">Lade Tische …</p>
  {:else if failed && !rooms.length}
    <p class="empty">Die Tischliste ist gerade nicht erreichbar.</p>
  {:else if !rooms.length}
    <p class="empty">Gerade sucht kein Tisch Mitspieler. Eröffne doch selbst einen und stelle ihn auf „öffentlich“.</p>
  {:else}
    {#each rooms as r (r.code)}
      {@const free = 4 - r.playerCount}
      <article class="table">
        <div class="top">
          <strong class="host">{r.host}s Tisch</strong>
          <span class="seats">{r.playerCount} / 4 {r.hasPassword ? "· 🔒" : ""}</span>
        </div>
        <p class="who">Am Tisch: {r.players.join(", ")} · {free === 1 ? "1 Platz frei" : `${free} Plätze frei`}</p>
        <div class="tags">
          {#each activeRuleLabels(r.settings) as tag (tag)}<span class="tag">{tag}</span>{/each}
        </div>
        <a class="join" href={`/beitreten/${r.code}`} use:link>{r.hasPassword ? "MIT PASSWORT BEITRETEN" : "BEITRETEN"} &rarr;</a>
      </article>
    {/each}
  {/if}
</div>

<style>
  .list {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr));
  }
  .empty {
    grid-column: 1 / -1;
    margin: 0;
    padding: 18px;
    border: 3px dashed #000;
    background: #fffdf5;
    font-weight: 600;
  }
  .table {
    display: grid;
    gap: 10px;
    align-content: start;
    padding: 16px;
    border: 3px solid #000;
    background: #ffffff;
    box-shadow: 5px 5px 0 0 #000;
    color: #000;
  }
  .top {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: baseline;
  }
  .host {
    font-family: var(--font-display, inherit);
    font-size: 1.05rem;
    overflow-wrap: anywhere;
  }
  .seats {
    font-family: var(--font-mono, monospace);
    font-weight: 700;
    white-space: nowrap;
  }
  .who {
    margin: 0;
    font-size: 0.9rem;
  }
  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .tag {
    padding: 2px 8px;
    border: 2px solid #000;
    background: #b8a9fa;
    font-family: var(--font-mono, monospace);
    font-size: 0.72rem;
    font-weight: 700;
  }
  .join {
    justify-self: start;
    padding: 8px 14px;
    border: 3px solid #000;
    background: #ffd23f;
    box-shadow: 3px 3px 0 0 #000;
    color: #000;
    font-family: var(--font-mono, monospace);
    font-weight: 700;
    font-size: 0.85rem;
    text-decoration: none;
  }
  .join:hover {
    transform: translate(-1px, -1px);
    box-shadow: 4px 4px 0 0 #000;
  }
  .compact .table {
    box-shadow: 3px 3px 0 0 #000;
    padding: 12px;
  }
</style>
