<script module>
  // Jede Instanz bekommt ein eigenes Muster: Eine gemeinsame ID würde ins Leere zeigen,
  // sobald die erste Instanz in einem ausgeblendeten Bereich (display: none) steht – dann blieben alle Rücken weiß.
  let counter = 0;
</script>

<script>
  // Kartenrücken (Vektor) im Neubrutalism-Stil: Gelb mit Korallen-Streifen, schwarze Konturen, Raute in der Mitte.
  // Die Farben kommen aus den Design-Variablen (Fallback: dieselben Werte), damit der Rücken zur Seite passt.
  let { tilt = 0 } = $props();
  const patternId = `doko-back-${counter++}`;
</script>

<div class="back" style="--tilt:{tilt}deg" aria-hidden="true">
  <svg viewBox="0 0 100 140" class="face" focusable="false">
    <defs>
      <pattern id={patternId} width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="14" height="14" class="yellow" />
        <rect width="14" height="5" class="coral" />
      </pattern>
    </defs>
    <rect x="1.5" y="1.5" width="97" height="137" rx="8" class="paper ink" stroke-width="3" />
    <rect x="9" y="9" width="82" height="122" rx="3" fill="url(#{patternId})" class="ink" stroke-width="3" />
    <!-- Raute mit hartem Schatten, wie die Knöpfe der Seite -->
    <rect x="35" y="55" width="30" height="30" transform="translate(3.5 3.5) rotate(45 50 70)" class="shadow" />
    <rect x="35" y="55" width="30" height="30" transform="rotate(45 50 70)" class="paper ink" stroke-width="3" />
    <rect x="43.5" y="63.5" width="13" height="13" transform="rotate(45 50 70)" class="blue ink" stroke-width="2.5" />
  </svg>
</div>

<style>
  .back {
    flex-shrink: 0;
    width: var(--back-w, 40px);
    aspect-ratio: 5 / 7;
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.45));
    transform: rotate(var(--tilt, 0deg));
  }
  .face {
    display: block;
    width: 100%;
    height: 100%;
  }
  .ink {
    stroke: var(--nb-ink, #000);
  }
  .shadow {
    fill: var(--nb-ink, #000);
  }
  .paper {
    fill: var(--nb-bg, #fffdf5);
  }
  .yellow {
    fill: var(--nb-yellow, #ffd23f);
  }
  .coral {
    fill: var(--nb-coral, #ff6b6b);
  }
  .blue {
    fill: var(--nb-blue, #74b9ff);
  }
</style>
