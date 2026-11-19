<script>
  // Klassischer Kartenrücken (Vektor): blaues Rautenmuster im weißen Rand.
  let { tilt = 0 } = $props();
</script>

<div class="back" style="--tilt:{tilt}deg" aria-hidden="true">
  <svg viewBox="0 0 100 140" class="face" focusable="false">
    <defs>
      <pattern id="doko-lattice" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="12" height="12" fill="#2f4c9a" />
        <path d="M0 0H12M0 0V12" stroke="#9db4ee" stroke-width="1.4" />
      </pattern>
    </defs>
    <rect x="1" y="1" width="98" height="138" rx="8" fill="#ffffff" stroke="#2b2b33" stroke-width="2" />
    <rect x="8" y="8" width="84" height="124" rx="3" fill="url(#doko-lattice)" stroke="#1d2f66" stroke-width="1.5" />
    <rect x="30" y="50" width="40" height="40" fill="#ffffff" transform="rotate(45 50 70)" opacity="0.92" />
    <rect x="37" y="57" width="26" height="26" fill="#2f4c9a" transform="rotate(45 50 70)" />
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
</style>
