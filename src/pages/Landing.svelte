<script>
  import { presence } from "../lib/presence.svelte.js";
  import Logo from "../components/ui/Logo.svelte";
  import PublicTables from "../components/ui/PublicTables.svelte";
  import SuggestionsModal from "../components/community/SuggestionsModal.svelte";
  import GithubLink from "../components/ui/GithubLink.svelte";
  import { FAQ, FAQ_TITLE } from "../content/home.js";
  import { link } from "../lib/nav.svelte.js";

  let suggestionsOpen = $state(false);
</script>

<div class="nb-page">
  <!-- Top-Navigation mit Inline-SVG Logo -->
  <header class="nb-header">
    <div class="nb-container nb-header-inner">
      <a href="/" use:link class="nb-logo" aria-label="Doppelkopf App Startseite">
        <Logo size={44} />
        <span class="nb-logo-text">DOPPELKOPF.CC</span>
      </a>

      <nav class="nb-nav" aria-label="Hauptnavigation">
        <a href="#modes" class="nb-nav-link">Modi</a>
        <a href="/regeln" use:link class="nb-nav-link">Regeln</a>
      <a href="/beitreten" use:link class="nb-nav-link">Beitreten</a>
        {#if presence.available}
          <button type="button" class="nb-nav-link nb-nav-btn" onclick={() => presence.open()}>
            <span class="nb-dot" class:on={presence.enabled && presence.connected} aria-hidden="true"></span>Online
          </button>
        {/if}
        <a href="/neu" use:link class="nb-btn nb-btn-sm nb-bg-yellow">Jetzt spielen</a>
      </nav>
    </div>
  </header>

  <main>
    <!-- Hero-Sektion: Asymmetrisches 2-Spalten-Grid ("Broken but not random") -->
    <section class="nb-hero">
      <div class="nb-container nb-hero-grid">
        <div class="nb-hero-copy">
          <div class="nb-badge nb-bg-lavender">VERSION 1.0-BETA</div>
          <h1 class="nb-display">
            <span class="nb-highlight">DOPPELKOPF.</span><br />
            OHNE SCHNICK&shy;SCHNACK.
          </h1>
          <p class="nb-lead">
            Ehrliches Kartenspiel für den Browser und unterwegs. Blitzschnelle Runden,
            turnierfeste Regelwerke und klare Kante statt überladener Casino-Optik.
          </p>
          <div class="nb-cta-group" id="start">
            <a href="#modes" class="nb-btn nb-btn-lg nb-bg-coral">SOFORT LOSLEGEN &rarr;</a>
            <!--<a href="#features" class="nb-btn nb-btn-lg nb-bg-white">REGELWERK PRÜFEN</a>-->
          </div>
        </div>

        <!-- Visuelles Hero-Modul: Gestapelte Spielkarten als Inline-Vektorgrafik -->
        <div class="nb-hero-stage" aria-label="Illustration zweier Doppelkopf-Karten">
          <div class="nb-card-stack">
            <!-- Karte 1: Kreuz Dame -->
            <article class="nb-playing-card nb-card-back nb-bg-blue">
              <header class="nb-card-corner">
                <span>D</span>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="#000000" aria-hidden="true">
                  <circle cx="12" cy="7" r="4.5" />
                  <circle cx="7.5" cy="14" r="4.5" />
                  <circle cx="16.5" cy="14" r="4.5" />
                  <rect x="10.5" y="14" width="3" height="7" />
                </svg>
              </header>
              <div class="nb-card-center">
                <svg width="76" height="76" viewBox="0 0 64 64" fill="none" aria-hidden="true">
                  <circle cx="32" cy="20" r="11" fill="#FFD23F" stroke="#000000" stroke-width="3" />
                  <circle cx="21" cy="36" r="11" fill="#FFD23F" stroke="#000000" stroke-width="3" />
                  <circle cx="43" cy="36" r="11" fill="#FFD23F" stroke="#000000" stroke-width="3" />
                  <path d="M28 38H36L39 54H25L28 38Z" fill="#000000" />
                </svg>
              </div>
            </article>

            <!-- Karte 2: Herz Zehn -->
            <article class="nb-playing-card nb-card-front nb-bg-yellow">
              <header class="nb-card-corner">
                <span>10</span>
                <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M12 21L3.5 12.2C1.2 9.8 1.2 6 3.5 3.6C5.8 1.2 9.5 1.2 11.8 3.6L12 3.8L12.2 3.6C14.5 1.2 18.2 1.2 20.5 3.6C22.8 6 22.8 9.8 20.5 12.2L12 21Z"
                    fill="#FF6B6B"
                    stroke="#000000"
                    stroke-width="2.5"
                  />
                </svg>
              </header>
              <div class="nb-card-center">
                <svg width="80" height="80" viewBox="0 0 64 64" fill="none" aria-hidden="true">
                  <path
                    d="M32 54L10 31.5C4.5 25.8 4.5 16.5 10 10.8C15.5 5.1 24.5 5.1 30 10.8L32 12.9L34 10.8C39.5 5.1 48.5 5.1 54 10.8C59.5 16.5 59.5 25.8 54 31.5L32 54Z"
                    fill="#FF6B6B"
                    stroke="#000000"
                    stroke-width="3.5"
                  />
                </svg>
              </div>
            </article>
          </div>
        </div>
      </div>
    </section>

    <!-- Fakten-Leiste mit 4 Spiel-Farben als Vektorgrafiken -->
    <section class="nb-strip">
      <div class="nb-container nb-strip-grid">
        <div class="nb-strip-item">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="#000000" aria-hidden="true">
            <circle cx="12" cy="7" r="4.5" />
            <circle cx="7.5" cy="14" r="4.5" />
            <circle cx="16.5" cy="14" r="4.5" />
            <rect x="10.5" y="14" width="3" height="7" />
          </svg>
          <span>DDV-TURNIERREGELN</span>
        </div>
        <div class="nb-strip-item">
          <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 2L21 13C21 16.5 18.2 18.5 15.5 18.5C14 18.5 13 17.8 12 16.8C11 17.8 10 18.5 8.5 18.5C5.8 18.5 3 16.5 3 13L12 2Z"
              fill="#74B9FF"
              stroke="#000000"
              stroke-width="2"
            />
            <rect x="10.5" y="16" width="3" height="6" fill="#000000" />
          </svg>
          <span>MIT / OHNE NEUNER</span>
        </div>
        <div class="nb-strip-item">
          <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M12 21L3.5 12.2C1.2 9.8 1.2 6 3.5 3.6C5.8 1.2 9.5 1.2 11.8 3.6L12 3.8L12.2 3.6C14.5 1.2 18.2 1.2 20.5 3.6C22.8 6 22.8 9.8 20.5 12.2L12 21Z"
              fill="#FF6B6B"
              stroke="#000000"
              stroke-width="2"
            />
          </svg>
          <span>SCHWEINCHEN &amp; ARMUT</span>
        </div>
        <div class="nb-strip-item">
          <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true">
            <polygon
              points="12,2 21,12 12,22 3,12"
              fill="#FFD23F"
              stroke="#000000"
              stroke-width="2"
            />
          </svg>
          <span>SOLO-VARIATIONEN</span>
        </div>
      </div>
    </section>

    <!-- Feature-Grid -->
    <section class="nb-section" id="features">
      <div class="nb-container">
        <div class="nb-section-head">
          <span class="nb-badge nb-bg-green">FUNKTIONEN</span>
          <h2 class="nb-h2">GEBAUT FÜR ECHTE KARTENSPIELER</h2>
        </div>

        <div class="nb-grid-3">
          <article class="nb-box nb-bg-white">
            <div class="nb-icon-box nb-bg-yellow">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="3" y="4" width="18" height="16" stroke="#000000" stroke-width="2.5" />
                <line x1="3" y1="10" x2="21" y2="10" stroke="#000000" stroke-width="2.5" />
                <line x1="9" y1="10" x2="9" y2="20" stroke="#000000" stroke-width="2.5" />
              </svg>
            </div>
            <h3 class="nb-h3">Sonderregeln nach Maß</h3>
            <p class="nb-body">
              Ob mit oder ohne Neuner, zweite Dulle sticht, Karlchen-Sonderpunkt, Schweinchen oder Armut:
              Jeder Tisch konfiguriert seine Hausregeln vor dem ersten Stich.
            </p>
          </article>

          <article class="nb-box nb-bg-white">
            <div class="nb-icon-box nb-bg-blue">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <polygon
                  points="13,2 4,14 11,14 10,22 20,10 13,10"
                  fill="#FFFDF5"
                  stroke="#000000"
                  stroke-width="2.5"
                />
              </svg>
            </div>
            <h3 class="nb-h3">Null Wartezeit</h3>
            <p class="nb-body">
              Kein Account-Zwang für schnelle Runden. Tisch-Link teilen, sofort zu viert einsteigen
              oder gegen regelstarke Bots trainieren.
            </p>
          </article>

          <article class="nb-box nb-bg-white">
            <div class="nb-icon-box nb-bg-coral">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="4" y="12" width="4" height="8" fill="#FFFDF5" stroke="#000000" stroke-width="2.5" />
                <rect x="10" y="8" width="4" height="12" fill="#FFFDF5" stroke="#000000" stroke-width="2.5" />
                <rect x="16" y="4" width="4" height="16" fill="#FFFDF5" stroke="#000000" stroke-width="2.5" />
              </svg>
            </div>
            <h3 class="nb-h3">Lückenloses Stich-Protokoll</h3>
            <p class="nb-body">
              Jeder Stich, jede Ansage und die komplette Abrechnung nach Punkten sind nach dem Spiel
              transparent einsehbar – ideal für die Analyse danach.
            </p>
          </article>
        </div>
      </div>
    </section>

    <!-- Spielmodi-Sektion -->
    <section class="nb-section nb-section-alt" id="modes">
      <div class="nb-container">
        <div class="nb-section-head">
          <span class="nb-badge nb-bg-yellow">SPIELMODI</span>
          <h2 class="nb-h2">WÄHLE DEINEN TISCH</h2>
        </div>

        <div class="nb-grid-2">
          <article class="nb-box nb-box-lg nb-bg-white">
            <div class="nb-box-top">
              <span class="nb-mono-tag">MODUS 01</span>
              <span class="nb-badge nb-bg-blue">MULTIPLAYER</span>
            </div>
            <h3 class="nb-h3">Privater Stammtisch</h3>
            <p class="nb-body">
              Erstelle einen geschlossenen Raum mit eigenem Regelwerk und lade drei Mitspieler
              per Direktlink ein. Inklusive Runden-Zähler und Bockrunden-Automatik.
            </p>
            <a href="/neu" use:link class="nb-btn nb-btn-md nb-bg-yellow">TISCH ERÖFFNEN</a>
          </article>

          <article class="nb-box nb-box-lg nb-bg-lavender">
            <div class="nb-box-top">
              <span class="nb-mono-tag">MODUS 02</span>
              <span class="nb-badge nb-bg-coral">TRAINING</span>
            </div>
            <h3 class="nb-h3">Sofort-Partie gegen KI</h3>
            <p class="nb-body">
              Perfekt für unterwegs oder zum Testen von Solo-Strategien. Keine Wartezeit,
              sofortige Kartenausgabe und Mitspieler, die sich an die Regeln halten.
            </p>
            <a href="/neu?ki=1" use:link class="nb-btn nb-btn-md nb-bg-white">PARTIE STARTEN</a>
          </article>
        </div>
      </div>
    </section>

    <!-- Offene Tische -->
    <section class="nb-section" id="tische">
      <div class="nb-container">
        <div class="nb-section-head">
          <span class="nb-badge nb-bg-green">LIVE</span>
          <h2 class="nb-h2">DIESE TISCHE SUCHEN MITSPIELER</h2>
        </div>
        <PublicTables />
      </div>
    </section>

    <!-- Verbesserungsvorschläge -->
    <section class="nb-section" id="ideen">
      <div class="nb-container">
        <div class="nb-box idea-box">
          <div>
            <span class="nb-mono-tag">DU BESTIMMST MIT</span>
            <h2 class="nb-h3">Was fehlt dir im Spiel?</h2>
            <p class="nb-body">
              Schlage neue Werkzeuge und Verbesserungen vor oder gib den Ideen anderer einen Daumen hoch.
            </p>
          </div>
          <button type="button" class="nb-btn nb-btn-md nb-bg-yellow" onclick={() => (suggestionsOpen = true)}>
            VORSCHLÄGE ANSEHEN &amp; EINREICHEN
          </button>
        </div>
      </div>
    </section>
    <!-- Häufige Fragen (Text aus src/content/home.js, steht beim Build auch im statischen HTML) -->
    <section class="nb-section nb-section-alt" id="faq">
      <div class="nb-container">
        <div class="nb-section-head">
          <span class="nb-badge nb-bg-lavender">FAQ</span>
          <h2 class="nb-h2">{FAQ_TITLE}</h2>
        </div>
        <div class="nb-faq">
          {#each FAQ as item}
            <details class="nb-faq-item">
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          {/each}
        </div>
        <p class="nb-faq-more">
          Alle Regeln im Überblick: <a href="/regeln" use:link>Doppelkopf-Regeln einfach erklärt</a>
        </p>
      </div>
    </section>
  </main>

  {#if suggestionsOpen}
    <SuggestionsModal onClose={() => (suggestionsOpen = false)} />
  {/if}

  <!-- Footer -->
  <footer class="nb-footer">
    <div class="nb-container nb-footer-inner">
      <p class="nb-mono-tag">DOPPELKOPF.CC</p>
      <div class="nb-footer-links">
        <a href="/regeln" use:link>Spielregeln</a>
        <a href="/impressum" use:link>Impressum</a>
        <a href="/datenschutz" use:link>Datenschutz</a>
        <a href="https://www.doko-verband.de/" target="_blank" rel="noopener noreferrer">Turnierregeln</a>
        <GithubLink />
      </div>
    </div>
  </footer>
</div>

<style>
/* Schriften: lokal gebündelt über @fontsource (siehe src/main.js) */

/* 1. Design Tokens (Canonical Palette, Borders & 3-Tier Shadow System) */
.nb-page {
  --nb-ink: #000000;

  --nb-border: 3px solid var(--nb-ink);
  --nb-shadow-sm: 3px 3px 0 0 var(--nb-ink);
  --nb-shadow-md: 5px 5px 0 0 var(--nb-ink);
  --nb-shadow-lg: 8px 8px 0 0 var(--nb-ink);

  --font-display: 'Space Grotesk', sans-serif;
  --font-heading: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'Space Mono', monospace;

  background-color: var(--nb-bg);
  color: var(--nb-ink);
  font-family: var(--font-body);
  line-height: 1.6;
  min-height: 100vh;
}

.nb-page *,
.nb-page *::before,
.nb-page *::after {
  box-sizing: border-box;
  border-radius: 0; /* Strikte eckige Kanten */
}

/* Hilfsklassen für flache Farbflächen */
.nb-bg-white { background-color: var(--nb-bg); }
.nb-bg-yellow { background-color: var(--nb-yellow); }
.nb-bg-coral { background-color: var(--nb-coral); }
.nb-bg-blue { background-color: var(--nb-blue); }
.nb-bg-green { background-color: var(--nb-green); }
.nb-bg-lavender { background-color: var(--nb-lavender); }

/* Layout-Container */
.nb-container {
  max-width: 1160px;
  margin: 0 auto;
  padding: 0 24px;
}

/* 2. Header & Navigation */
.nb-header {
  border-bottom: var(--nb-border);
  background-color: var(--nb-bg);
  position: sticky;
  top: 0;
  z-index: 20;
}

.nb-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 80px;
  gap: 16px;
}

.nb-logo {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  text-decoration: none;
  color: var(--nb-ink);
}

.nb-logo-mark {
  display: block;
  flex-shrink: 0;
}

.nb-logo-text {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.5rem;
  letter-spacing: -0.03em;
}

.nb-nav {
  display: flex;
  align-items: center;
  gap: 24px;
}

.nb-nav-btn {
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
}
.nb-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #000;
  background: #fff;
  margin-right: 6px;
}
.nb-dot.on {
  background: #1fa34a;
}

.nb-nav-link {
  font-family: var(--font-heading);
  font-weight: 700;
  color: var(--nb-ink);
  text-decoration: none;
  text-transform: uppercase;
  font-size: 0.95rem;
}

.nb-nav-link:hover {
  text-decoration: underline;
  text-decoration-thickness: 3px;
  text-underline-offset: 4px;
}

/* 3. Buttons & Badges (Taktiles Press-Verhalten per reinem CSS) */
.nb-btn {
  display: inline-block;
  font-family: var(--font-heading);
  font-weight: 700;
  text-transform: uppercase;
  text-decoration: none;
  color: var(--nb-ink);
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-md);
  transition: transform 0.1s ease, box-shadow 0.1s ease;
  cursor: pointer;
}

.nb-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 7px 7px 0 0 var(--nb-ink);
}

.nb-btn:active {
  transform: translate(4px, 4px);
  box-shadow: 1px 1px 0 0 var(--nb-ink);
}

.nb-btn-sm {
  padding: 8px 16px;
  font-size: 0.875rem;
  box-shadow: var(--nb-shadow-sm);
}

.nb-btn-md {
  padding: 12px 22px;
  font-size: 1rem;
}

.nb-btn-lg {
  padding: 16px 28px;
  font-size: 1.05rem;
}

.nb-badge {
  display: inline-block;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.78rem;
  text-transform: uppercase;
  padding: 4px 10px;
  border: 2px solid var(--nb-ink);
  box-shadow: var(--nb-shadow-sm);
}

/* 4. Hero-Sektion */
.nb-hero {
  padding: 72px 0 84px;
  border-bottom: var(--nb-border);
}

.nb-hero-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 48px;
  align-items: center;
}

.nb-display {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(2.5rem, 5vw, 4.1rem);
  line-height: 1.02;
  letter-spacing: -0.03em;
  margin: 20px 0 24px;
  text-transform: uppercase;
}

.nb-highlight {
  display: inline-block;
  background-color: var(--nb-yellow);
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-md);
  padding: 2px 12px;
  margin-bottom: 8px;
}

.nb-lead {
  font-size: 1.15rem;
  max-width: 54ch;
  margin: 0 0 32px;
}

.nb-cta-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

/* Hero-Kartenstapel (Asymmetrischer Akzent) */
.nb-hero-stage {
  display: flex;
  justify-content: center;
}

.nb-card-stack {
  position: relative;
  width: 310px;
  height: 360px;
}

.nb-playing-card {
  position: absolute;
  width: 220px;
  height: 300px;
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-lg);
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.nb-card-back {
  top: 0;
  left: 0;
  transform: rotate(-5deg);
}

.nb-card-front {
  bottom: 0;
  right: 0;
  transform: rotate(3deg);
}

.nb-card-corner {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.5rem;
  line-height: 1;
  gap: 4px;
}

.nb-card-center {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

/* 5. Fakten-Leiste */
.nb-strip {
  background-color: var(--nb-yellow);
  border-bottom: var(--nb-border);
  padding: 18px 0;
}

.nb-strip-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.nb-strip-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.85rem;
}

/* 6. Sektionen & Karten-Raster */
.nb-section {
  padding: 80px 0;
  border-bottom: var(--nb-border);
}

.nb-section-alt {
  background-color: #f4f1e6;
}

.nb-section-head {
  margin-bottom: 40px;
}

.nb-h2 {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(1.8rem, 3.5vw, 2.6rem);
  line-height: 1.1;
  margin: 14px 0 0;
  text-transform: uppercase;
}

.nb-h3 {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 1.45rem;
  line-height: 1.25;
  margin: 0 0 12px;
}

.nb-body {
  margin: 0 0 24px;
  font-size: 1rem;
}

.nb-grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 28px;
}

.nb-grid-2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 32px;
}

.nb-box {
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-md);
  padding: 28px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.nb-box-lg {
  box-shadow: var(--nb-shadow-lg);
  padding: 36px;
}

.nb-box .nb-body {
  margin-bottom: 0;
}

.nb-box-lg .nb-body {
  margin-bottom: 28px;
}

.nb-box-top {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
}

.nb-mono-tag {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.85rem;
  margin: 0;
}

.nb-icon-box {
  width: 52px;
  height: 52px;
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

/* 7. Footer */
.nb-footer {
  padding: 32px 0;
  background-color: var(--nb-bg);
}

.nb-footer-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.nb-footer-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 24px;
}

.nb-footer-links a {
  font-family: var(--font-heading);
  font-weight: 700;
  color: var(--nb-ink);
  text-decoration: none;
}

.nb-footer-links a:hover {
  text-decoration: underline;
  text-decoration-thickness: 2px;
}

/* Responsive Anpassungen */
@media (max-width: 920px) {
  .nb-hero-grid,
  .nb-grid-3,
  .nb-grid-2 {
    grid-template-columns: 1fr;
  }

  .nb-strip-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .nb-hero-stage {
    margin-top: 24px;
  }
}

@media (max-width: 480px) {
  .nb-header-inner {
    gap: 10px;
  }

  .nb-logo {
    gap: 8px;
    min-width: 0;
  }

  .nb-logo-text {
    font-size: clamp(0.8rem, 4.2vw, 1.05rem);
    white-space: nowrap;
  }

  .nb-logo :global(.logo) {
    height: clamp(26px, 8vw, 44px);
    width: auto;
  }

  /* der hervorgehobene Kasten um „DOPPELKOPF.“ darf auch auf kleinen Telefonen nicht über den Rand ragen */
  .nb-display {
    font-size: clamp(1.9rem, 8.6vw, 2.5rem);
  }
}

@media (max-width: 380px) {
  .nb-header-inner {
    flex-wrap: wrap;
    padding-block: 8px;
  }
}

@media (max-width: 560px) {
  .nb-nav-link {
    display: none;
  }

  .nb-strip-grid {
    grid-template-columns: 1fr;
  }
}

/* Häufige Fragen */
.nb-faq {
  display: grid;
  gap: 16px;
  max-width: 820px;
}

.nb-faq-item {
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-sm);
  background-color: var(--nb-bg);
}

.nb-faq-item summary {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  cursor: pointer;
  list-style: none;
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 1.05rem;
}

.nb-faq-item summary::-webkit-details-marker {
  display: none;
}

.nb-faq-item summary::after {
  content: "+";
  font-family: var(--font-mono);
}

.nb-faq-item[open] summary::after {
  content: "–";
}

.nb-faq-item p {
  margin: 0;
  padding: 0 18px 16px;
}

.nb-faq-more {
  margin: 24px 0 0;
}

.nb-faq-more a {
  color: var(--nb-ink);
  font-weight: 700;
}

/* Verbesserungsvorschläge */
.idea-box {
  background: var(--nb-paper);
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.idea-box .nb-h3 {
  margin: 8px 0;
}

@media (max-width: 720px) {
  .idea-box {
    flex-direction: column;
    align-items: stretch;
    text-align: left;
  }
}
</style>
