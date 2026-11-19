<script>
  import { link } from "../lib/nav.svelte.js";
  import PageShell from "../components/ui/PageShell.svelte";
</script>

<PageShell narrow>
  <span class="nx-badge nx-bg-coral">404</span>
  <h1 class="nx-title">Diese Seite gibt es nicht</h1>
  <a href="/" use:link class="nx-btn">ZUR STARTSEITE</a>
</PageShell>
