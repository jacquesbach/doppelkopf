<script>
  import { bannerKey } from "../../lib/siteSettings.js";
  import { siteSettings } from "../../lib/siteSettings.svelte.js";

  // Hinweisleiste des Betreibers (z. B. Wartungsarbeiten). Reiner Text; wer sie schließt, sieht sie in diesem Tab nicht
  // wieder, bis sich der Text ändert. Gespeichert wird das nur im Tab-Speicher (sessionStorage).
  const banner = $derived(siteSettings.value.banner);
  const key = $derived(bannerKey(banner));
  let closed = $state(readClosed());

  function readClosed() {
    try {
      return window.sessionStorage.getItem("doko.banner.closed") || "";
    } catch {
      return "";
    }
  }
  const visible = $derived(banner.enabled && closed !== key);

  function close() {
    closed = key;
    try {
      window.sessionStorage.setItem("doko.banner.closed", key);
    } catch {
      /* ohne Speicher: gilt bis zum Neuladen */
    }
  }
</script>

{#if visible}
  <div class="banner {banner.tone}" role={banner.tone === "alert" ? "alert" : "status"}>
    <p>{banner.text}</p>
    {#if banner.dismissible}
      <button type="button" class="x" aria-label="Hinweis schließen" onclick={close}>
        <svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true"><path d="M2 2L12 12M12 2L2 12" stroke="#000" stroke-width="3" /></svg>
      </button>
    {/if}
  </div>
{/if}

<style>
  .banner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 8px 14px;
    border-bottom: 3px solid #000;
    color: #000;
    font-family: var(--font-heading);
    font-weight: 700;
    font-size: 0.92rem;
    text-align: center;
  }
  .banner p {
    margin: 0;
    overflow-wrap: anywhere;
  }
  .info {
    background: var(--nb-blue);
  }
  .warn {
    background: var(--nb-orange);
  }
  .alert {
    background: var(--nb-coral);
  }
  .x {
    flex: none;
    display: inline-flex;
    padding: 6px;
    border: 2px solid #000;
    background: var(--nb-bg);
    cursor: pointer;
  }
  @media (max-width: 640px) {
    .banner {
      font-size: 0.82rem;
      padding: 6px 10px;
    }
  }
</style>
