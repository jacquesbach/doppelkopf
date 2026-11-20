<script>
  import { presence } from "../lib/presence.svelte.js";
  import Logo from "../components/ui/Logo.svelte";
  import { tick } from "svelte";
  import { link, navigate } from "../lib/nav.svelte.js";
  import { inviteLink } from "../lib/router.js";
  import { activeRuleLabels } from "../lib/view.js";
  import RuleDialog from "../components/ui/RuleDialog.svelte";
  import TakeoverSettings from "../components/ui/TakeoverSettings.svelte";
  import QuickPhrases from "../components/ui/QuickPhrases.svelte";

  let { store } = $props();

  const room = $derived(store.room);
  const players = $derived(room.players.filter((p) => p.role === "player"));
  const spectators = $derived(room.players.filter((p) => p.role === "spectator"));
  const slots = $derived(Array.from({ length: 4 }, (_, i) => players[i] ?? null));
  const readyCount = $derived(players.filter((p) => p.ready).length);
  const allReady = $derived(players.length === 4 && readyCount === 4);
  const missing = $derived(4 - players.length);
  const tags = $derived(activeRuleLabels(room.settings));
  const statusText = $derived(
    store.connection === "offline"
      ? "OFFLINE – VERBINDE NEU …"
      : players.length < 4
        ? "WARTE AUF SPIELER"
        : allReady
          ? "STARTKLAR"
          : "WARTE AUF BEREITSCHAFT",
  );

  let draft = $state("");
  let copied = $state(false);
  let rulesDialog = $state(null); // null | "edit" | "view"
  let messagesEl = $state(null);

  function subline(p) {
    if (p.isHost) return "Gastgeber";
    if (p.isBot) return "Bot · Lückenfüller";
    if (p.isMe) return "Das bist du";
    return p.connected ? "Am Tisch" : "Nicht verbunden";
  }

  async function invite() {
    const url = inviteLink(window.location.origin, room.code);
    try {
      await navigator.clipboard.writeText(url);
      copied = true;
      setTimeout(() => (copied = false), 2500);
    } catch {
      window.prompt("Einladungslink kopieren:", url);
    }
  }

  async function send(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    if (await store.sendChat(text)) draft = "";
  }

  async function leave(event) {
    event?.preventDefault();
    if (await store.leave()) navigate("/");
  }

  // Neue Nachrichten: ans Ende scrollen
  $effect(() => {
    store.chat.length;
    tick().then(() => {
      if (messagesEl) messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  });
</script>

<div class="nb-page">
  <!-- Header -->
  <header class="nb-header">
    <div class="nb-container nb-header-inner">
      <a href="/" use:link class="nb-logo" aria-label="Doppelkopf App Startseite">
        <Logo size={40} />
        <span class="nb-logo-text">DOPPELKOPF.CC</span>
      </a>

      <div class="nb-header-meta">
        <span class="nb-badge nb-bg-yellow">TISCH #{room.code}</span>
        <span class="nb-badge nb-bg-white" aria-live="polite">STATUS: {statusText}</span>
      </div>
    </div>
  </header>

  <!-- Main Lobby Content -->
  <main class="nb-lobby-main">
    <div class="nb-container">
      <!-- Sektions-Titel -->
      <div class="nb-section-head">
        <span class="nb-badge nb-bg-lavender">MULTIPLAYER RAUM</span>
        <h1 class="nb-display">STAMMTISCH <span class="nb-highlight">{room.code}</span></h1>
      </div>

      <!-- Dashboard Grid: Links Spieler & Hausregeln, Rechts Chat & Aktionen -->
      <div class="nb-lobby-grid">
        <!-- Linke Spalte: Spieler-Slots (4er-Tisch) -->
        <div class="nb-lobby-column">
          <div class="nb-box nb-bg-white nb-box-full">
            <div class="nb-box-top">
              <h2 class="nb-h3">SPIELER AM TISCH</h2>
              <span class="nb-mono-tag">{readyCount} / 4 BEREIT</span>
            </div>

            <!-- Spieler Slots Grid -->
            <div class="nb-player-grid">
              {#each slots as p, i (p ? p.id : `empty-${i}`)}
                {#if p}
                  <div class="nb-player-card {p.isHost ? 'nb-bg-yellow' : 'nb-bg-white'}">
                    <div class="nb-player-avatar">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2.5" aria-hidden="true">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                      </svg>
                    </div>
                    <div class="nb-player-info">
                      <span class="nb-player-name">{p.name}{p.isHost ? " (Host)" : ""}</span>
                      <span class="nb-mono-sub">{subline(p)}</span>
                    </div>
                    <span class="nb-status-badge {p.ready ? 'nb-bg-green' : 'nb-bg-white'}">
                      {p.ready ? "BEREIT" : "WARTET"}
                    </span>
                  </div>
                {:else}
                  <!-- Leerer Slot (Wartend) -->
                  <div class="nb-player-card nb-player-empty">
                    <div class="nb-player-avatar nb-avatar-dashed">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#666" stroke-width="2.5" aria-hidden="true">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                      </svg>
                    </div>
                    <div class="nb-player-info">
                      <span class="nb-player-name nb-text-muted">Warte auf Mitspieler...</span>
                      <span class="nb-mono-sub">Link teilen zum Einladen</span>
                    </div>
                    <div class="nb-invite-actions">
                      <button type="button" class="nb-btn nb-btn-sm nb-bg-blue" onclick={invite}>
                        {copied ? "KOPIERT ✓" : "EINLADEN"}
                      </button>
                      {#if presence.available}
                        <button type="button" class="nb-btn nb-btn-sm nb-bg-white" onclick={() => presence.open()}>FREUNDE</button>
                      {/if}
                    </div>
                  </div>
                {/if}
              {/each}
            </div>

            {#if spectators.length}
              <p class="nb-mono-sub nb-spectators">
                Zuschauer: {spectators.map((s) => s.name).join(", ")}
              </p>
            {/if}
          </div>

          <!-- Hausregeln-Kompaktbox -->
          <div class="nb-box nb-bg-lavender nb-box-full" style="margin-top: 24px;">
            <h3 class="nb-h3">AKTIVE HAUSREGELN</h3>
            <div class="nb-rules-tags">
              {#each tags as tag (tag)}
                <span class="nb-badge nb-bg-white">{tag}</span>
              {/each}
            </div>
            <p class="nb-mono-sub" style="margin-top:12px;">
              SICHTBARKEIT: {room.isPublic ? "ÖFFENTLICH – steht in der Tischliste" : "PRIVAT – nur per Link"}
            </p>
            <div style="margin-top:12px;"><TakeoverSettings {store} /></div>
            {#if store.isHost}
              <div class="nb-box-actions">
                <button type="button" class="nb-btn nb-btn-sm nb-bg-white" onclick={() => (rulesDialog = "edit")}>
                  REGELN ÄNDERN
                </button>
                <button type="button" class="nb-btn nb-btn-sm nb-bg-white" disabled={store.busy} onclick={() => store.setPublic(!room.isPublic)}>
                  {room.isPublic ? "PRIVAT STELLEN" : "ÖFFENTLICH MACHEN"}
                </button>
              </div>
            {/if}
          </div>
        </div>

        <!-- Rechte Spalte: Chat & Steuerungs-Panel -->
        <div class="nb-lobby-column">
          <!-- Chat-Box -->
          <div class="nb-box nb-bg-white nb-box-full nb-chat-box">
            <div class="nb-box-top">
              <h3 class="nb-h3">TISCH-CHAT</h3>
              <span class="nb-mono-tag">{store.connection === "online" ? "LIVE" : "OFFLINE"}</span>
            </div>

            <div class="nb-chat-messages" bind:this={messagesEl} aria-live="polite">
              {#each store.chat as m (m.id)}
                <div class="nb-chat-msg">
                  <span class="nb-chat-author">{m.name}:</span>
                  <span class="nb-chat-text">{m.text}</span>
                </div>
              {:else}
                <span class="nb-chat-empty">Noch keine Nachrichten.</span>
              {/each}
            </div>

            <form class="nb-chat-form" onsubmit={send}>
              <label class="nx-sr" for="lobby-chat">Nachricht an den Tisch</label>
              <input
                id="lobby-chat"
                class="nb-chat-input"
                type="text"
                maxlength="200"
                autocomplete="off"
                placeholder="Nachricht an den Tisch senden..."
                bind:value={draft}
              />
              <button type="submit" class="nb-btn nb-btn-sm nb-bg-yellow" disabled={!draft.trim() || store.busy}>
                SENDEN
              </button>
            </form>
            <QuickPhrases busy={store.busy} onsend={(text) => store.sendChat(text)} />
          </div>

          <!-- Aktionen / Start-Panel -->
          <div class="nb-box nb-bg-coral nb-box-full" style="margin-top: 24px;">
            <h3 class="nb-h3" style="color: #000;">BEREIT ZUM START?</h3>
            <p class="nb-body" style="font-size: 0.95rem; margin-bottom: 20px;">
              {#if missing > 0}
                {missing === 1 ? "Es fehlt noch 1 Spieler." : `Es fehlen noch ${missing} Spieler.`}
                {store.isHost
                  ? "Teile den Link oder schalte Bots als Lückenfüller dazu."
                  : "Sobald der Tisch voll ist, startet der Host die erste Runde."}
              {:else if !allReady}
                Der Tisch ist voll. Sobald alle Spieler bereit sind, kann der Host die erste Runde starten.
              {:else}
                Alle sind bereit – {store.isHost ? "du kannst die erste Runde starten." : "der Host startet gleich die erste Runde."}
              {/if}
            </p>
            <div class="nb-cta-stack">
              {#if store.isHost}
                <button
                  type="button"
                  class="nb-btn nb-btn-lg nb-bg-yellow"
                  style="width: 100%; text-align: center;"
                  disabled={!allReady || store.busy}
                  onclick={() => store.start()}
                >
                  SPIEL STARTEN &rarr;
                </button>
                {#if missing > 0}
                  <button
                    type="button"
                    class="nb-btn nb-btn-md nb-bg-white"
                    style="width: 100%; text-align: center;"
                    disabled={store.busy}
                    onclick={() => store.addBots()}
                  >
                    + BOT ALS LÜCKENFÜLLER
                  </button>
                {/if}
              {:else if store.me?.role === "player"}
                <button
                  type="button"
                  class="nb-btn nb-btn-lg {store.me.ready ? 'nb-bg-white' : 'nb-bg-yellow'}"
                  style="width: 100%; text-align: center;"
                  disabled={store.busy}
                  onclick={() => store.setReady(!store.me.ready)}
                >
                  {store.me.ready ? "NOCH NICHT BEREIT" : "ICH BIN BEREIT"}
                </button>
              {/if}
              <button
                type="button"
                class="nb-btn nb-btn-md nb-bg-white"
                style="width: 100%; text-align: center;"
                disabled={store.busy}
                onclick={() => leave()}
              >
                AUSTRETEN
              </button>
              {#if store.isHost}
                <p class="nb-mono-sub" style="margin:0;">Als Host übergibst du den Tisch an den nächsten Spieler.</p>
              {/if}
            </div>
          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- Footer -->
  <footer class="nb-footer">
    <div class="nb-container nb-footer-inner">
      <p class="nb-mono-tag">DOKO.LOBBY &mdash; RAUM-ID: #{room.code}</p>
      <div class="nb-footer-links">
        <a href="/" onclick={leave}>Tisch verlassen</a>
        <button type="button" class="nb-link-button" onclick={() => (rulesDialog = "view")}>Regelwerk</button>
      </div>
    </div>
  </footer>
</div>

{#if rulesDialog}
  <RuleDialog
    settings={room.settings}
    editable={rulesDialog === "edit"}
    onSave={(settings) => store.saveSettings(settings)}
    onClose={() => (rulesDialog = null)}
  />
{/if}

<style>
/* Schriften: lokal gebündelt über @fontsource (siehe src/main.js) */

/* Design Tokens */
.nb-invite-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

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
  border-radius: 0;
}

/* Farb-Hilfsklassen */
.nb-bg-white { background-color: var(--nb-bg); }
.nb-bg-yellow { background-color: var(--nb-yellow); }
.nb-bg-coral { background-color: var(--nb-coral); }
.nb-bg-blue { background-color: var(--nb-blue); }
.nb-bg-green { background-color: var(--nb-green); }
.nb-bg-lavender { background-color: var(--nb-lavender); }

.nb-container {
  max-width: 1160px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Header */
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

.nb-logo-text {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.4rem;
  letter-spacing: -0.03em;
}

.nb-header-meta {
  display: flex;
  gap: 12px;
}

/* Lobby Main Layout */
.nb-lobby-main {
  padding: 60px 0 80px;
}

.nb-section-head {
  margin-bottom: 36px;
}

.nb-display {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: clamp(2rem, 4vw, 3.2rem);
  line-height: 1.05;
  margin: 12px 0 0;
  text-transform: uppercase;
}

.nb-highlight {
  display: inline-block;
  background-color: var(--nb-yellow);
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-sm);
  padding: 0 10px;
}

.nb-lobby-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 32px;
  align-items: start;
}

.nb-lobby-column {
  display: flex;
  flex-direction: column;
}

/* Box-System */
.nb-box {
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-md);
  padding: 28px;
  display: flex;
  flex-direction: column;
}

.nb-box-full {
  width: 100%;
}

.nb-box-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
}

.nb-h3 {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 1.3rem;
  margin: 0;
  text-transform: uppercase;
}

.nb-mono-tag {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.8rem;
  margin: 0;
}

/* Spieler-Slots Grid */
.nb-player-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.nb-player-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-sm);
  padding: 14px 18px;
  gap: 16px;
}

.nb-player-empty {
  background-color: rgba(0, 0, 0, 0.03);
  border: 2px dashed var(--nb-ink);
  box-shadow: none;
}

.nb-player-avatar {
  width: 42px;
  height: 42px;
  border: var(--nb-border);
  background-color: var(--nb-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nb-avatar-dashed {
  border: 2px dashed #666;
  background-color: transparent;
}

.nb-player-info {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nb-player-name {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 1.05rem;
}

.nb-mono-sub {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #444;
}

.nb-text-muted {
  color: #666;
}

.nb-status-badge {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 0.72rem;
  padding: 4px 8px;
  border: 2px solid var(--nb-ink);
}

/* Regeln & Tags */
.nb-rules-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 4px;
}

/* Chat Box */
.nb-chat-box {
  min-height: 280px;
  display: flex;
  flex-direction: column;
}

.nb-chat-messages {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background-color: #faf7ee;
  border: 2px solid var(--nb-ink);
  padding: 14px;
  margin-bottom: 16px;
  max-height: 180px;
  overflow-y: auto;
}

.nb-chat-msg {
  font-size: 0.9rem;
}

.nb-chat-author {
  font-family: var(--font-heading);
  font-weight: 700;
  margin-right: 6px;
}

.nb-chat-input-row {
  display: flex;
  gap: 10px;
}

.nb-fake-input {
  flex-grow: 1;
  border: 2px solid var(--nb-ink);
  background-color: var(--nb-bg);
  padding: 8px 12px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #666;
  display: flex;
  align-items: center;
}

/* CTA Stack */
.nb-cta-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Buttons & Badges */
.nb-btn {
  display: inline-block;
  font-family: var(--font-heading);
  font-weight: 700;
  text-transform: uppercase;
  text-decoration: none;
  color: var(--nb-ink);
  border: var(--nb-border);
  box-shadow: var(--nb-shadow-sm);
  transition: transform 0.1s ease, box-shadow 0.1s ease;
  cursor: pointer;
  text-align: center;
}

.nb-btn:hover {
  transform: translate(-2px, -2px);
  box-shadow: 5px 5px 0 0 var(--nb-ink);
}

.nb-btn:active {
  transform: translate(2px, 2px);
  box-shadow: 1px 1px 0 0 var(--nb-ink);
}

.nb-btn-sm {
  padding: 6px 12px;
  font-size: 0.78rem;
}

.nb-btn-md {
  padding: 12px 18px;
  font-size: 0.95rem;
  box-shadow: var(--nb-shadow-md);
}

.nb-btn-lg {
  padding: 16px 24px;
  font-size: 1.05rem;
  box-shadow: var(--nb-shadow-md);
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

/* Footer */
.nb-footer {
  padding: 32px 0;
  background-color: var(--nb-bg);
  border-top: var(--nb-border);
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
  gap: 24px;
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

/* Responsives Layout */
@media (max-width: 920px) {
  .nb-lobby-grid {
    grid-template-columns: 1fr;
  }
}
/* --- Ergänzungen für echte Daten (Look wie die Vorlage) --- */
.nb-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
  box-shadow: var(--nb-shadow-sm);
}

.nb-chat-input {
  flex-grow: 1;
  min-width: 0;
  border: 2px solid var(--nb-ink);
  background-color: var(--nb-bg);
  padding: 8px 12px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--nb-ink);
}

.nb-chat-input::placeholder {
  color: #666;
}

.nb-chat-empty {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #666;
}

.nb-chat-form {
  display: flex;
  gap: 10px;
}

.nb-spectators {
  margin: 16px 0 0;
}

.nb-box-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.nb-link-button {
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  font-family: var(--font-heading);
  font-weight: 700;
  color: var(--nb-ink);
  cursor: pointer;
}

.nb-link-button:hover {
  text-decoration: underline;
  text-decoration-thickness: 2px;
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
    font-size: clamp(0.8rem, 4.2vw, 1.4rem);
    white-space: nowrap;
  }

  .nb-logo :global(.logo) {
    height: clamp(26px, 8vw, 40px);
    width: auto;
  }
}

@media (max-width: 380px) {
  .nb-header-inner {
    flex-wrap: wrap;
    padding-block: 8px;
  }
}

@media (max-width: 560px) {
  .nb-header-meta {
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
  }
}
</style>
