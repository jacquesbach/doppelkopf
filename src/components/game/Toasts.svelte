<script>
  // Kurze Hinweise („Anna sagt Re an“, „Fuchs gefangen“, neue Chatnachricht …); schließen sich selbst, per Klick auch früher.
  // Ein Hinweis kann eine Schaltfläche tragen (`action`), z. B. „Antworten“ im Chat-Hinweis.
  let { toasts, ondismiss, onaction = () => {} } = $props();
  const BG = { yellow: "nx-bg-yellow", coral: "nx-bg-coral", blue: "nx-bg-blue", green: "nx-bg-green", lavender: "nx-bg-lavender" };
</script>

<div class="toasts" role="status" aria-live="polite">
  {#each toasts as t (t.key)}
    <div class="toast {BG[t.tone] ?? 'nx-bg-yellow'}" class:with-action={!!t.action}>
      <button type="button" class="body" onclick={() => ondismiss(t.key)} aria-label="Hinweis schließen: {t.title}">
        <span class="title">{t.title}</span>
        <span class="text">{t.text}</span>
      </button>
      {#if t.action}
        <button
          type="button"
          class="nx-btn nx-btn-sm act"
          onclick={() => {
            ondismiss(t.key);
            onaction(t);
          }}
        >
          {t.action.label.toUpperCase()}
        </button>
      {/if}
    </div>
  {/each}
</div>

<style>
  .toasts {
    position: fixed;
    top: 72px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 60;
    display: grid;
    gap: 10px;
    width: min(92vw, 380px);
    pointer-events: none;
  }
  .toast {
    pointer-events: auto;
    display: flex;
    align-items: center;
    gap: 10px;
    border: var(--nb-border);
    box-shadow: var(--nb-shadow-sm);
    color: #000;
    animation: toast-in 0.25s ease-out both;
  }
  .body {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 2px;
    text-align: left;
    padding: 10px 14px;
    background: none;
    border: 0;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }
  .with-action .body {
    padding-right: 0;
  }
  .act {
    flex-shrink: 0;
    margin-right: 10px;
  }
  .title {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .text {
    font-weight: 600;
    line-height: 1.3;
    overflow-wrap: anywhere;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  @keyframes toast-in {
    from { transform: translateY(-14px); opacity: 0; }
    to { transform: none; opacity: 1; }
  }
  @media (prefers-reduced-motion: reduce) {
    .toast { animation: none; }
  }
</style>
