<svelte:options namespace="svg" />

<script>
  import { INK, SUIT_SHAPES } from "../../lib/suits.js";

  // Zeichnet eine Kartenfarbe als <g> im 24×24-Raster. `black`/`red` überschreiben die Tinte (z. B. im Logo).
  let { suit, black = INK.black, red = INK.red } = $props();

  const shape = $derived(SUIT_SHAPES[suit] ?? SUIT_SHAPES["♣"]);
  const fill = $derived(shape.ink === "red" ? red : black);
</script>

<g {fill}>
  {#each shape.parts as part, i (i)}
    {#if part.circle}
      <circle cx={part.circle[0]} cy={part.circle[1]} r={part.circle[2]} />
    {:else}
      <path d={part.path} />
    {/if}
  {/each}
</g>
