<script>
  import PageShell from "../components/ui/PageShell.svelte";
  import CardGroups from "../components/rules/CardGroups.svelte";
  import { link } from "../lib/nav.svelte.js";
  import { RULES, RULES_LEAD, RULES_TITLE, RULES_TOC } from "../content/rules.js";

  // Der Text kommt aus src/content/rules.js (derselbe Inhalt steht beim Build auch als statisches HTML in /regeln).
  // Inhaltsverzeichnis: am Rand (breite Fenster, klebt beim Scrollen) oder als Leiste unter der Kopfzeile (schmale Fenster).
  let active = $state(RULES_TOC[0].id);

  // Der Abschnitt, dessen Überschrift zuletzt oben aus dem Bild gelaufen ist, gilt als aktuell.
  function updateActive() {
    let current = RULES_TOC[0].id;
    for (const entry of RULES_TOC) {
      const el = document.getElementById(entry.id);
      if (el && el.getBoundingClientRect().top <= 150) current = entry.id;
    }
    active = current;
  }

  $effect(() => {
    let frame = 0;
    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        updateActive();
      });
    };
    updateActive();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  });

  // Direktlink wie /regeln#trumpf: Die Seite wird erst per JavaScript aufgebaut, daher springen wir selbst.
  $effect(() => {
    const id = decodeURIComponent(window.location.hash.slice(1));
    if (id) document.getElementById(id)?.scrollIntoView();
  });

  function jump(event, id) {
    const el = document.getElementById(id);
    if (!el) return;
    event.preventDefault();
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    window.history.replaceState(window.history.state, "", `#${id}`);
    active = id;
  }
</script>

<PageShell>
  <span class="nx-badge nx-bg-yellow">SPIELREGELN</span>
  <h1 class="nx-title">{RULES_TITLE}</h1>

  <div class="layout">
    <nav class="toc" aria-label="Inhaltsverzeichnis">
      <p class="toc-title">Inhalt</p>
      <ol>
        {#each RULES_TOC as entry (entry.id)}
          <li>
            <a
              href={`#${entry.id}`}
              class:active={active === entry.id}
              aria-current={active === entry.id ? "location" : undefined}
              onclick={(event) => jump(event, entry.id)}>{entry.label}</a
            >
          </li>
        {/each}
      </ol>
    </nav>

    <article class="nx-box nx-prose rules">
      <p class="rules-lead">{RULES_LEAD}</p>
      {#each RULES as block}
        {#if block.type === "h2"}
          <h2 class="nx-h2" id={block.id}>{block.text}</h2>
        {:else if block.type === "h3"}
          <h3 class="nx-h3">{block.text}</h3>
        {:else if block.type === "p"}
          <p>{block.text}</p>
        {:else if block.type === "ul"}
          <ul>{#each block.items as item}<li>{item}</li>{/each}</ul>
        {:else if block.type === "ol"}
          <ol>{#each block.items as item}<li>{item}</li>{/each}</ol>
        {:else if block.type === "note"}
          <aside class="note"><strong>{block.title}</strong><p>{block.text}</p></aside>
        {:else if block.type === "table"}
          <div class="table-wrap">
            <table class="nx-table">
              <thead><tr>{#each block.head as cell}<th>{cell}</th>{/each}</tr></thead>
              <tbody>
                {#each block.rows as row}
                  <tr>{#each row as cell}<td>{cell}</td>{/each}</tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else if block.type === "cards"}
          <CardGroups {block} />
        {/if}
      {/each}
      <div class="nx-btn-row cta">
        <a href="/neu" use:link class="nx-btn">TISCH ERÖFFNEN</a>
        <a href="/neu?ki=1" use:link class="nx-btn nx-bg-white">GEGEN BOTS SPIELEN</a>
      </div>
    </article>
  </div>
</PageShell>

<style>
  .layout {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: 32px;
    align-items: start;
  }

  /* --- Inhaltsverzeichnis: breit = Spalte links, klebt unter der Kopfzeile --- */
  .toc {
    position: sticky;
    top: 96px;
    max-height: calc(100vh - 120px);
    overflow-y: auto;
    padding: 14px 12px;
    border: var(--nb-border);
    background: var(--nb-bg);
    box-shadow: var(--nb-shadow-sm);
  }
  .toc-title {
    margin: 0 0 8px;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
  }
  .toc ol {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .toc a {
    display: block;
    padding: 5px 8px;
    border-left: 4px solid transparent;
    font-family: var(--font-heading);
    font-weight: 700;
    font-size: 0.9rem;
    line-height: 1.25;
    color: var(--nb-ink);
    text-decoration: none;
  }
  .toc a:hover {
    background: var(--nb-yellow);
  }
  .toc a.active {
    border-left-color: var(--nb-ink);
    background: var(--nb-yellow);
  }

  /* --- Text --- */
  .rules-lead {
    font-size: 1.1rem;
  }
  .rules :global(h2) {
    margin-top: 34px;
    scroll-margin-top: 100px;
  }
  .rules :global(h3) {
    margin-top: 22px;
  }
  .rules :global(ul),
  .rules :global(ol) {
    margin: 0 0 14px;
    padding-left: 1.4rem;
  }
  .rules :global(li) {
    margin-bottom: 6px;
  }
  .table-wrap {
    margin: 4px 0 18px;
    overflow-x: auto;
  }
  .table-wrap :global(td) {
    vertical-align: top;
  }
  .note {
    margin: 16px 0 18px;
    padding: 10px 14px;
    border: var(--nb-border);
    background: #fff3c4;
  }
  .note strong {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    text-transform: uppercase;
  }
  .note p {
    margin: 4px 0 0;
  }
  .cta {
    margin-top: 28px;
  }

  /* --- Schmal: Inhaltsverzeichnis als waagerechte Leiste unter der Kopfzeile --- */
  @media (max-width: 900px) {
    .layout {
      grid-template-columns: minmax(0, 1fr);
      gap: 16px;
    }
    .toc {
      top: 72px;
      z-index: 10;
      max-height: none;
      overflow-y: visible;
      padding: 8px;
    }
    .toc-title {
      display: none;
    }
    .toc ol {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 2px;
      scrollbar-width: thin;
    }
    .toc li {
      flex: none;
    }
    .toc a {
      border: 2px solid var(--nb-ink);
      padding: 6px 10px;
      white-space: nowrap;
    }
    .toc a.active {
      background: var(--nb-yellow);
    }
    .rules :global(h2) {
      scroll-margin-top: 140px;
    }
  }
</style>
