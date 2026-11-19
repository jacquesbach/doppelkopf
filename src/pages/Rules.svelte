<script>
  import PageShell from "../components/ui/PageShell.svelte";
  import { link } from "../lib/nav.svelte.js";
  import { RULES, RULES_LEAD, RULES_TITLE } from "../content/rules.js";
</script>

<!-- Regeln-Seite: Text aus src/content/rules.js (derselbe Inhalt steht beim Build auch als statisches HTML in /regeln) -->
<PageShell narrow>
  <span class="nx-badge nx-bg-yellow">SPIELREGELN</span>
  <h1 class="nx-title">{RULES_TITLE}</h1>
  <article class="nx-box nx-prose rules">
    <p class="rules-lead">{RULES_LEAD}</p>
    {#each RULES as block}
      {#if block.type === "h2"}
        <h2 class="nx-h2">{block.text}</h2>
      {:else if block.type === "h3"}
        <h3 class="nx-h3">{block.text}</h3>
      {:else if block.type === "p"}
        <p>{block.text}</p>
      {:else if block.type === "ul"}
        <ul>{#each block.items as item}<li>{item}</li>{/each}</ul>
      {:else if block.type === "ol"}
        <ol>{#each block.items as item}<li>{item}</li>{/each}</ol>
      {/if}
    {/each}
    <div class="nx-btn-row cta">
      <a href="/neu" use:link class="nx-btn">TISCH ERÖFFNEN</a>
      <a href="/neu?ki=1" use:link class="nx-btn nx-bg-white">GEGEN BOTS SPIELEN</a>
    </div>
  </article>
</PageShell>

<style>
  .rules-lead {
    font-size: 1.1rem;
  }
  .rules :global(h2) {
    margin-top: 28px;
  }
  .rules :global(ul),
  .rules :global(ol) {
    margin: 0 0 14px;
    padding-left: 1.4rem;
  }
  .rules :global(li) {
    margin-bottom: 6px;
  }
  .cta {
    margin-top: 28px;
  }
</style>
