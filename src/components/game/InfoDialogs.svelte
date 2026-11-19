<script>
  import { onMount, tick } from "svelte";
  import { navigate } from "../../lib/nav.svelte.js";
  import { gameTypeLabel, kindLabel, partyLabel } from "../../lib/labels.js";
  import { partyNames, roundRanking, seatName } from "../../lib/view.js";
  import Dialog from "../ui/Dialog.svelte";
  import PlayingCard from "../cards/PlayingCard.svelte";
  import TakeoverSettings from "../ui/TakeoverSettings.svelte";
  import QuickPhrases from "../ui/QuickPhrases.svelte";

  // Sammlung kleiner Dialoge: Stand, letzter Stich, Protokoll, Chat. `kind` wählt den Dialog.
  let { kind, store, onClose } = $props();

  const view = $derived(store.view);
  const round = $derived(view.table.round);
  const ranking = $derived(roundRanking(view));
  const last = $derived(view.game.lastTrick);

  let games = $state(null);
  let draft = $state("");
  let listEl = $state(null);
  let inputEl = $state(null);

  onMount(async () => {
    if (kind === "history") games = await store.loadHistory();
    if (kind === "chat") inputEl?.focus(); // „Antworten“: gleich losschreiben können
  });

  $effect(() => {
    if (kind !== "chat") return;
    store.chat.length;
    tick().then(() => listEl && (listEl.scrollTop = listEl.scrollHeight));
  });

  async function send(event) {
    event.preventDefault();
    const text = draft.trim();
    if (text && (await store.sendChat(text))) draft = "";
  }

  const playing = $derived(
    view.table.mySeat != null && !view.table.finished && store.room?.status === "playing",
  );

  async function leave() {
    if (!playing || (await store.leaveGame())) navigate("/");
  }

  /** „Re: Anna & Ben“ – ältere Protokolleinträge ohne Sitzangabe zeigen nur die Partei. */
  function winnerText(g) {
    if (!g.winner) return "–";
    const { winners } = partyNames(view, g.reSeats, g.winner);
    return winners.length ? `${partyLabel(g.winner)}: ${winners.join(" & ")}` : partyLabel(g.winner);
  }

  const gameName = (g) => (g.gameType && g.gameType !== "normal" ? gameTypeLabel(g.gameType) : kindLabel(g.kind));
</script>

{#if kind === "stand"}
  <Dialog title="Stand der Runde" {onClose}>
    <p class="nx-mono">
      {round.normalGamesPlayed} / {round.normalGamesTotal} NORMALSPIELE
      {#if round.bockRemaining > 0} · BOCK: NOCH {round.bockRemaining}{/if}
    </p>
    <table class="nx-table">
      <thead><tr><th>#</th><th>Spieler</th><th class="num">Punkte</th></tr></thead>
      <tbody>
        {#each ranking as r (r.seat)}
          <tr><td>{r.rank}</td><td>{r.name}</td><td class="num">{r.points}</td></tr>
        {/each}
      </tbody>
    </table>
    <h3 class="nx-h3" style="margin-top:18px;">Bot-Übernahme</h3>
    <TakeoverSettings {store} mine />
  </Dialog>
{:else if kind === "last"}
  <Dialog title="Letzter Stich" {onClose}>
    {#if last}
      <div class="trick">
        {#each last.plays as p (p.seat)}
          <figure>
            <PlayingCard card={p.card} />
            <figcaption class:win={p.seat === last.winnerSeat}>
              {seatName(view, p.seat)}{p.seat === last.winnerSeat ? " ✓" : ""}
            </figcaption>
          </figure>
        {/each}
      </div>
      <p class="nx-hint">
        Stich {last.number} ging an {seatName(view, last.winnerSeat)} ({last.points} Augen).
      </p>
    {:else}
      <p>Es wurde noch kein Stich gespielt.</p>
    {/if}
  </Dialog>
{:else if kind === "tricks"}
  <Dialog title="Alle Stiche" {onClose} wide>
    {#if !view.game.tricks?.length}
      <p>Die Stiche werden nach dem Spielende aufgedeckt.</p>
    {:else}
      <ol class="tricks">
        {#each view.game.tricks as t (t.number)}
          <li class="trow">
            <div class="thead">
              <strong>Stich {t.number}</strong>
              <span class="nx-mono">{seatName(view, t.winnerSeat)} · {t.points} Augen</span>
            </div>
            <div class="trick small">
              {#each t.plays as p (p.seat)}
                <figure class:won={p.seat === t.winnerSeat}>
                  <PlayingCard card={p.card} />
                  <figcaption class:win={p.seat === t.winnerSeat}>{seatName(view, p.seat)}{p.seat === t.winnerSeat ? " ✓" : ""}</figcaption>
                </figure>
              {/each}
            </div>
          </li>
        {/each}
      </ol>
    {/if}
  </Dialog>
{:else if kind === "history"}
  <Dialog title="Spielprotokoll" {onClose} wide>
    {#if games === null}
      <p>Lade …</p>
    {:else if games.length === 0}
      <p>Noch kein Spiel abgeschlossen.</p>
    {:else}
      <div style="overflow-x:auto;">
        <table class="nx-table">
          <thead>
            <tr>
              <th>#</th><th>Spiel</th><th>Sieger</th>
              {#each view.table.seats as s (s.seat)}<th class="num">{s.name}</th>{/each}
            </tr>
          </thead>
          <tbody>
            {#each games as g (g.gameNumber)}
              <tr>
                <td>{g.gameNumber}</td>
                <td>{gameName(g)}{g.multiplier > 1 ? ` ×${g.multiplier}` : ""}</td>
                <td>{winnerText(g)}</td>
                {#each g.seatDeltas as d, i (i)}<td class="num">{d > 0 ? "+" : ""}{d}</td>{/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </Dialog>
{:else if kind === "leave"}
  <Dialog title="Tisch verlassen?" {onClose}>
    {#if playing}
      <p>
        Ein <strong>Bot spielt für dich weiter</strong>, damit die anderen nicht warten müssen. Dein Platz bleibt dir
        erhalten: Über den Link zum Tisch kommst du jederzeit zurück und übernimmst wieder.
      </p>
      <p class="nx-hint">
        Punkte, die der Bot für dich holt oder verliert, werden dir wie gewohnt zugerechnet. Wer die Runde nicht
        beenden möchte, kann sie einfach bis zum Ende vom Bot spielen lassen.
      </p>
    {:else}
      <p>Du verlässt den Tisch. Über den Einladungslink kannst du jederzeit wieder zuschauen.</p>
    {/if}
    <div class="nx-btn-row" style="margin-top:16px;">
      <button type="button" class="nx-btn nx-bg-coral" disabled={store.busy} onclick={leave}>
        {playing ? "BOT ÜBERNEHMEN LASSEN & GEHEN" : "ZUR STARTSEITE"}
      </button>
      <button type="button" class="nx-btn nx-bg-white" onclick={onClose}>BLEIBEN</button>
    </div>
  </Dialog>
{:else if kind === "chat"}
  <Dialog title="Tisch-Chat" {onClose}>
    <div class="msgs" bind:this={listEl} aria-live="polite">
      {#each store.chat as m (m.id)}
        <div><strong>{m.name}:</strong> {m.text}</div>
      {:else}
        <span class="nx-hint">Noch keine Nachrichten.</span>
      {/each}
    </div>
    <form class="send" onsubmit={send}>
      <label class="nx-sr" for="game-chat">Nachricht</label>
      <input id="game-chat" class="nx-input" maxlength="200" autocomplete="off" placeholder="Nachricht …" bind:value={draft} bind:this={inputEl} />
      <button type="submit" class="nx-btn nx-btn-sm" disabled={!draft.trim() || store.busy}>SENDEN</button>
    </form>
    <QuickPhrases busy={store.busy} onsend={(text) => store.sendChat(text)} />
  </Dialog>
{/if}

<style>
  .trick {
    --card-w: 72px;
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    justify-content: center;
    margin-bottom: 12px;
  }
  .tricks {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  }
  .trow {
    border: 2px solid #000;
    padding: 8px 10px;
    background: #fffdf5;
  }
  .thead {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 8px;
    font-size: 0.9rem;
  }
  .trick.small {
    --card-w: 52px;
    gap: 8px;
    margin-bottom: 0;
    flex-wrap: nowrap;
  }
  figure.won :global(.card) {
    outline: 3px solid var(--nb-yellow);
    outline-offset: 2px;
  }
  figure {
    margin: 0;
    text-align: center;
  }
  figcaption {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    margin-top: 6px;
  }
  figcaption.win {
    font-weight: 700;
    text-decoration: underline;
    text-decoration-thickness: 2px;
  }
  .msgs {
    border: 2px solid #000;
    background: #faf7ee;
    padding: 12px;
    max-height: 280px;
    min-height: 120px;
    overflow-y: auto;
    display: grid;
    gap: 8px;
    margin-bottom: 14px;
    font-size: 0.92rem;
  }
  .send {
    display: flex;
    gap: 10px;
  }
  .send .nx-input {
    flex: 1;
    min-width: 0;
  }
</style>
