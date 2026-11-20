<script>
  import { link } from "../../lib/nav.svelte.js";
  import Logo from "./Logo.svelte";
  import GithubLink from "./GithubLink.svelte";
  import FriendsButton from "../community/FriendsButton.svelte";

  let { children, narrow = false } = $props();
</script>

<div class="nx-page">
  <header class="nx-header">
    <div class="nx-container nx-header-inner">
      <a href="/" use:link class="nx-logo" aria-label="Doppelkopf App Startseite">
        <Logo size={40} />
        <span class="nx-logo-text">DOPPELKOPF.CC</span>
      </a>
      <div class="actions">
        <FriendsButton class="nx-btn nx-btn-sm nx-bg-white" />
        <a href="/beitreten" use:link class="nx-btn nx-btn-sm">Tisch beitreten</a>
      </div>
    </div>
  </header>

  <main class="nx-main">
    <div class="nx-container" class:nx-narrow={narrow}>
      {@render children()}
    </div>
  </main>

  <footer class="nx-footer">
    <div class="nx-container nx-footer-inner">
      <p class="nx-mono">DOPPELKOPF.CC</p>
      <div>
        <a href="/regeln" use:link>Regeln</a>
        <a href="/impressum" use:link>Impressum</a>
        <a href="/datenschutz" use:link>Datenschutz</a>
        <GithubLink />
      </div>
    </div>
  </footer>
</div>

<style>
  .actions { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
</style>
