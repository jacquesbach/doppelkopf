<script>
  import SuitGlyph from "./SuitGlyph.svelte";

  // Farbsymbol als eigenständiges Inline-SVG. `size` ist eine CSS-Länge.
  let { suit, size = "1em" } = $props();
</script>

<svg class="suit" style="width:{size};height:{size}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
  <SuitGlyph {suit} />
</svg>

<style>
  .suit {
    display: block;
    flex-shrink: 0;
  }
</style>
