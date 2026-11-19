<script>
  import SuitGlyph from "../cards/SuitGlyph.svelte";

  // Logo: Kartenfächer mit den vier Kartenfarben. `size` = Höhe in px (die Breite folgt dem Seitenverhältnis).
  // Beim Überfahren (oder Fokussieren des umgebenden Links) ziehen sich die Karten zu einem Stapel zusammen; zuletzt liegt
  // nur noch das Karo oben. Beim Verlassen fächern sie sich wieder auf.
  let { size = 40 } = $props();
  const VB = { x: -7.6, y: 5.1, w: 59.3, h: 38.3 };
  const CARDS = [
    { suit: "♣", angle: -36 },
    { suit: "♠", angle: -12 },
    { suit: "♥", angle: 12 },
    { suit: "♦", angle: 36 },
  ];
  const W = 16, H = 27, X0 = 14, Y0 = 8, SUIT = 9.5;
</script>

<svg
  class="logo"
  width={(size * VB.w) / VB.h}
  height={size}
  viewBox="{VB.x} {VB.y} {VB.w} {VB.h}"
  fill="none"
  xmlns="http://www.w3.org/2000/svg"
  aria-hidden="true"
>
  {#each CARDS as c, i (c.suit)}
    <g class="card" style="--a:{c.angle}deg; --i:{i}">
      <rect x={X0} y={Y0} width={W} height={H} fill="#FFFDF5" stroke="#000000" stroke-width="2.5" />
      <g transform="translate({X0 + 2.5} {Y0 + 3}) scale({SUIT / 24})">
        <SuitGlyph suit={c.suit} black="#000000" red="#FF6B6B" />
      </g>
    </g>
  {/each}
</svg>

<style>
  /* Drehpunkt = Fächermitte unterhalb der Karten, in Koordinaten der viewBox */
  .card {
    transform-box: view-box;
    transform-origin: 22px 44px;
    transform: rotate(var(--a));
    transition: transform 0.55s cubic-bezier(0.3, 1.3, 0.5, 1);
  }

  /* Hover/Fokus: alle Karten drehen sich in die Senkrechte und liegen deckungsgleich übereinander (oben: Karo) */
  :global(.nx-logo:hover) .card,
  :global(.nx-logo:focus-visible) .card,
  .logo:hover .card {
    transform: rotate(0deg);
    transition: transform 0.5s cubic-bezier(0.55, 0, 0.25, 1);
  }

  @media (prefers-reduced-motion: reduce) {
    .card {
      transition-duration: 0s !important;
    }
  }
</style>
