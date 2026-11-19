<script>
  import { onMount } from "svelte";

  // onClose = null: Dialog lässt sich nicht wegklicken (z. B. wenn eine Entscheidung nötig ist).
  let { title, onClose = null, wide = false, children } = $props();
  let dialogEl = $state(null);
  const titleId = `dlg-${Math.random().toString(36).slice(2, 8)}`;

  onMount(() => {
    const previous = document.activeElement;
    dialogEl?.focus();
    return () => previous?.focus?.();
  });

  function onKey(event) {
    if (event.key === "Escape" && onClose) onClose();
  }
</script>

<svelte:window onkeydown={onKey} />

<div
  class="nx-backdrop"
  role="presentation"
  onmousedown={(event) => {
    if (event.target === event.currentTarget && onClose) onClose();
  }}
>
  <div
    class="nx-dialog"
    class:nx-dialog-wide={wide}
    role="dialog"
    aria-modal="true"
    aria-labelledby={titleId}
    tabindex="-1"
    bind:this={dialogEl}
  >
    <div class="nx-dialog-head">
      <h2 class="nx-dialog-title" id={titleId}>{title}</h2>
      {#if onClose}
        <button type="button" class="nx-btn nx-btn-sm" onclick={onClose} aria-label="Schließen">
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
            <path d="M2 2L12 12M12 2L2 12" stroke="#000" stroke-width="3" />
          </svg>
        </button>
      {/if}
    </div>
    {@render children()}
  </div>
</div>
