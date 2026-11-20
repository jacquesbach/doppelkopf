<script>
  import { untrack } from "svelte";
  import { link } from "../../lib/nav.svelte.js";
  import { cardId } from "../../lib/cards.js";
  import { pickReady, prunePick, togglePick } from "../../lib/selection.js";
  import {
    actingSeat,
    activeDialog,
    announcementsBySeat,
    gameHeadline,
    isHolding,
    isMyTakeoverWarning,
    legalAction,
    myAutoplay,
    playableIds,
    povertyPick,
    seatName,
    shownTrick,
    statusText,
    takeoverWarning,
  } from "../../lib/view.js";
  import Logo from "../ui/Logo.svelte";
  import PlayingCard from "../cards/PlayingCard.svelte";
  import Hand from "./Hand.svelte";
  import SeatPlate from "./SeatPlate.svelte";
  import DecisionPanel from "./DecisionPanel.svelte";
  import PovertyPanel from "./PovertyPanel.svelte";
  import PovertyGotDialog from "./PovertyGotDialog.svelte";
  import CardBack from "../cards/CardBack.svelte";
  import ActionBar from "./ActionBar.svelte";
  import ResultDialog from "./ResultDialog.svelte";
  import Toasts from "./Toasts.svelte";
  import InfoDialogs from "./InfoDialogs.svelte";
  import TakeoverDialog from "./TakeoverDialog.svelte";
  import TakeoverNote from "./TakeoverNote.svelte";

  let { store } = $props();

  const view = $derived(store.view);
  const game = $derived(view.game);
  const me = $derived(view.table.mySeat); // null = Zuschauer
  const REL = { bottom: 0, left: 1, top: 2, right: 3 };
  const seatAt = (place) => (((me ?? 0) + REL[place]) % 4);
  const PLACES = ["bottom", "left", "top", "right"]; // Umkehrung von REL: Abstand zum eigenen Sitz → Lage am Tisch
  const placeOf = (seat) => PLACES[(seat - (me ?? 0) + 4) % 4];

  const dialog = $derived(activeDialog(view));
  const shown = $derived(shownTrick(view));
  const holding = $derived(isHolding(view));
  const away = $derived(myAutoplay(view));
  const says = $derived(announcementsBySeat(view));
  const acting = $derived(actingSeat(view));
  const playable = $derived(legalAction(view, "play_card") ? playableIds(view) : null);
  const finished = $derived(game.phase === "finished");
  const warnedOther = $derived(!!takeoverWarning(view) && !isMyTakeoverWarning(view));
  const bock = $derived(view.table.round.bockRemaining ?? 0);

  // Armut: Karten markieren, die abgegeben bzw. zurückgegeben werden (nur in diesen beiden Phasen, nur für den Betroffenen).
  const pickAction = $derived(povertyPick(view));
  let picked = $state([]);
  $effect(() => {
    const allowed = pickAction ? new Set(pickAction.cards) : null;
    const kept = prunePick(untrack(() => picked), allowed);
    if (kept.length !== untrack(() => picked).length) picked = kept;
  });
  const pick = $derived(
    pickAction
      ? {
          selected: picked,
          allowed: new Set(pickAction.cards),
          received: pickAction.received ?? [],
          onToggle: (id) => (picked = togglePick(picked, id, pickAction.count)),
          hint:
            pickAction.type === "poverty_pass"
              ? `Karten zum Abgeben wählen (${picked.length}/${pickAction.count})`
              : `Karten zum Zurückgeben wählen (${picked.length}/${pickAction.count}) – die übernommenen Karten tragen „NEU“`,
        }
      : null,
  );
  const confirmPick = () => {
    if (pickAction && pickReady(picked, pickAction.count)) store.act({ type: pickAction.type, cardIds: picked });
  };
  const povertyOffering = $derived(game.phase === "poverty_offer");
  // Armut-Fenster: gewählte und übernommene Karten als Kartenbilder (aus der eigenen Hand).
  const handById = $derived(new Map(game.hand.map((c) => [cardId(c), c])));
  const pickedCards = $derived(picked.map((id) => handById.get(id)).filter(Boolean));
  const receivedCards = $derived((pickAction?.received ?? []).map((id) => handById.get(id)).filter(Boolean));
  // Der Arme sieht nach der Rückgabe, welche Karten er bekommen hat (einmal je Spiel; nur er, vom Server geliefert).
  let gotSeenGame = $state(null);
  const gotCards = $derived(game.povertyGot ?? []);
  const showGot = $derived(gotCards.length > 0 && game.phase !== "finished" && gotSeenGame !== gameNumber);

  let info = $state(null); // null | "stand" | "last" | "tricks" | "history" | "chat" | "leave"
  let menuOpen = $state(false); // nur Handy: Menü mit den selteneren Knöpfen
  const openInfo = (kind) => {
    menuOpen = false;
    info = kind;
  };
  // Ergebnis ist ausgeblendet, wenn es für DIESES Spiel weggeklickt wurde (neues Spiel → wieder sichtbar).
  // Bewusst kein $effect: Er würde bei jeder neuen Server-Sicht (auch beim Nachladen) das Ergebnis wieder öffnen.
  const gameNumber = $derived(view.table.gameNumber);
  let dismissedGame = $state(null);
  // Direkt nach dem letzten Stich wird das Ergebnis kurz zurückgehalten (store.resultDelayGame): Der Stich bleibt sichtbar.
  const resultDelayed = $derived(store.resultDelayGame === gameNumber);
  const showResult = $derived(dismissedGame !== gameNumber && !resultDelayed);
  const roundDone = $derived(view.table.finished);

  // Chat offen = gelesen: keine Hinweise mehr, Zähler zurücksetzen.
  // (untrack: setChatOpen liest und schreibt die Hinweisliste; ohne das würde der Effect sich selbst neu auslösen)
  $effect(() => {
    const open = info === "chat";
    untrack(() => store.setChatOpen(open));
  });

  const declared = $derived(
    game.phase === "reservation_query" || game.phase === "reservation_resolution"
      ? game.declarations.map((d, seat) => ({ seat, d })).filter((x) => x.d)
      : [],
  );
</script>

<div class="nx-page game">
  <header class="nx-header">
    <div class="nx-container nx-header-inner bar">
      <a href="/" use:link class="nx-logo" aria-label="Zur Startseite">
        <Logo size={34} />
        <span class="nx-logo-text hide-sm">DOPPELKOPF.CC</span>
      </a>
      <div class="head-mid">
        <span class="nx-badge nx-bg-yellow">{gameHeadline(view)}</span>
        {#if bock > 0}<span class="nx-badge nx-bg-coral">BOCK ×2 · NOCH {bock}</span>{/if}
        {#if me === null}<span class="nx-badge nx-bg-lavender">ZUSCHAUER</span>{/if}
        {#if store.connection === "offline"}<span class="nx-badge nx-bg-coral">OFFLINE</span>{/if}
      </div>
      <div class="tools" class:open={menuOpen}>
        <button type="button" class="nx-btn nx-btn-sm nx-bg-white sec" onclick={() => openInfo("stand")}>STAND</button>
        {#if finished}
          <button type="button" class="nx-btn nx-btn-sm nx-bg-white sec" onclick={() => openInfo("tricks")}>STICHE</button>
        {:else}
          <button type="button" class="nx-btn nx-btn-sm nx-bg-white sec" onclick={() => openInfo("last")} disabled={!game.lastTrick}>LETZTER STICH</button>
        {/if}
        <button type="button" class="nx-btn nx-btn-sm nx-bg-white sec" onclick={() => openInfo("history")}>PROTOKOLL</button>
        <button type="button" class="nx-btn nx-btn-sm nx-bg-blue chat" onclick={() => openInfo("chat")}>
          CHAT{#if store.unread > 0}<span class="unread" aria-label="{store.unread} ungelesen">{store.unread}</span>{/if}
        </button>
        <button type="button" class="nx-btn nx-btn-sm nx-bg-coral sec" onclick={() => openInfo("leave")}>VERLASSEN</button>
      </div>
      <button
        type="button"
        class="nx-btn nx-btn-sm nx-bg-white menu-toggle"
        aria-expanded={menuOpen}
        onclick={() => (menuOpen = !menuOpen)}
      >
        MENÜ <span aria-hidden="true">{menuOpen ? "▴" : "▾"}</span>
      </button>
    </div>
  </header>

  <main class="nx-container stage">
    {#if warnedOther}<TakeoverNote {store} />{/if}
    {#if away}
      <div class="away" role="alert">
        <span>Ein Bot spielt gerade für dich.</span>
        <button type="button" class="nx-btn nx-btn-sm" onclick={() => store.resume()}>ZURÜCK AM TISCH</button>
      </div>
    {/if}

    <div class="table">
      <div class="top">
        <SeatPlate {view} place="top" seat={seatAt("top")} acting={acting === seatAt("top")} announcement={says[seatAt("top")]} />
      </div>
      <div class="left">
        <SeatPlate {view} place="left" seat={seatAt("left")} acting={acting === seatAt("left")} announcement={says[seatAt("left")]} />
      </div>
      <div class="right">
        <SeatPlate {view} place="right" seat={seatAt("right")} acting={acting === seatAt("right")} announcement={says[seatAt("right")]} />
      </div>

      <div class="mid">
        <p class="status" role="status" aria-live="polite">{statusText(view)}</p>
        {#if dialog}
          <DecisionPanel
            {dialog}
            baptismKind={game.baptismKind}
            busy={store.busy}
            act={(a) => store.act(a)}
            poverty={!!game.ruleOptions?.poverty}
            poorName={seatName(view, game.poverty?.seat)}
          />
        {:else if pickAction}
          <PovertyPanel
            kind={pickAction.type}
            count={pickAction.count}
            cards={pickedCards}
            received={receivedCards}
            busy={store.busy}
            onconfirm={confirmPick}
            onremove={(id) => (picked = picked.filter((x) => x !== id))}
          />
        {:else}
          {#if povertyOffering}
            <div class="poverty-stack" aria-label="Verdeckte Armut-Karten">
              <span class="cards" aria-hidden="true"><CardBack /><CardBack /><CardBack /></span>
              <span class="note">Armut von {seatName(view, game.poverty?.seat)}: 3 Karten liegen verdeckt bereit.</span>
            </div>
          {/if}
          {#if declared.length}
            <ul class="declared">
              {#each declared as x (x.seat)}
                <li class="nx-badge">{seatName(view, x.seat)}: {x.d === "reservation" ? "Vorbehalt" : "gesund"}</li>
              {/each}
            </ul>
          {/if}
          <!-- Stich: Karten liegen im Kreuz und überlappen sich in der Reihenfolge, in der sie gespielt wurden -->
          <div class="trick" aria-label="Aktueller Stich">
            {#each shown.plays as p, i (p.seat)}
              <div class="slot {placeOf(p.seat)}" style="z-index:{i + 1}">
                {#key cardId(p.card)}
                  <div class="fly"><div class="rot"><PlayingCard card={p.card} /></div></div>
                {/key}
              </div>
            {/each}
          </div>
          {#if shown.complete && (game.phase === "playing" || finished)}
            <p class="note">
              {seatName(view, shown.winnerSeat)} gewinnt {finished ? "den letzten Stich" : "den Stich"} ({game.lastTrick.points} Augen).
            </p>
          {/if}
          {#if finished && resultDelayed}
            <button type="button" class="nx-btn" onclick={() => store.showResultNow()}>ERGEBNIS JETZT ANZEIGEN</button>
          {/if}
          {#if holding}
            <button type="button" class="nx-btn nx-btn-lg" disabled={store.busy} onclick={() => store.continueTrick()}>
              NÄCHSTER STICH &rarr;
            </button>
          {/if}
        {/if}
      </div>

      <div class="me">
        <SeatPlate
          {view}
          place="bottom"
          seat={seatAt("bottom")}
          acting={acting === seatAt("bottom")}
          announcement={says[seatAt("bottom")]}
          showBacks={me === null}
        />
        {#if me !== null && game.hand}
          <ActionBar {view} busy={store.busy} act={(a) => store.act(a)} />
          <Hand hand={game.hand} {playable} {pick} onplay={(id) => store.playCard(id)} />
        {/if}
        {#if finished && !showResult && !resultDelayed}
          <div class="nx-btn-row" style="justify-content:center;margin-top:12px;">
            <button type="button" class="nx-btn nx-bg-white" onclick={() => (dismissedGame = null)}>ERGEBNIS ANZEIGEN</button>
            <button type="button" class="nx-btn nx-bg-white" onclick={() => (info = "tricks")}>STICHE ANSEHEN</button>
            {#if !roundDone && me !== null}
              <button type="button" class="nx-btn" disabled={store.busy} onclick={() => store.nextGame()}>NÄCHSTES SPIEL &rarr;</button>
            {:else if roundDone && store.isHost}
              <button type="button" class="nx-btn" disabled={store.busy} onclick={() => store.start()}>NEUE RUNDE STARTEN &rarr;</button>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  </main>
</div>

{#if finished && showResult}
  <ResultDialog
    {view}
    isHost={store.isHost}
    busy={store.busy}
    onClose={() => (dismissedGame = gameNumber)}
    onTricks={() => {
      dismissedGame = gameNumber;
      info = "tricks";
    }}
    onNext={() => store.nextGame()}
    onNewRound={() => store.start()}
  />
{/if}

{#if showGot}
  <PovertyGotDialog cards={gotCards} buyerName={seatName(view, game.poverty?.buyer)} onClose={() => (gotSeenGame = gameNumber)} />
{/if}

{#if isMyTakeoverWarning(view)}
  <TakeoverDialog {store} />
{/if}

<Toasts
  toasts={store.toasts}
  ondismiss={(key) => store.dismissToast(key)}
  onaction={(t) => {
    if (t.action?.kind === "chat") info = "chat";
  }}
/>

{#if info}
  <InfoDialogs kind={info} {store} onClose={() => (info = null)} />
{/if}

<style>
  .game {
    --card-w: clamp(46px, 11vw, 84px);
    background: var(--nb-paper);
  }
  .bar {
    flex-wrap: wrap;
    padding-block: 8px;
  }
  .head-mid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }
  .tools {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .menu-toggle {
    display: none;
  }
  .unread {
    display: inline-block;
    min-width: 1.4em;
    margin-left: 6px;
    padding: 0 4px;
    background: var(--nb-coral);
    border: 2px solid #000;
    font-size: 0.78em;
    line-height: 1.3;
  }
  .stage {
    flex: 1;
    max-width: 1400px;
    padding-block: 16px 32px;
  }
  .status {
    margin: 0;
    text-align: center;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.9rem;
    min-height: 1.5em;
  }
  /* Vier Plätze an den vier Seiten: Gegner mit Kartenstapel am Rand, Stich in der Mitte, eigene Hand unten */
  .table {
    --back-w: clamp(44px, 4.4vw, 62px);
    --step: 0.34;
    --trick-w: clamp(54px, 6.6vw, 88px);
    --side: calc(var(--back-w) * 1.4 + 76px);
    display: grid;
    grid-template-columns: var(--side) minmax(0, 1fr) var(--side);
    grid-template-areas:
      "top top top"
      "left mid right"
      "me me me";
    gap: 14px 10px;
    align-items: start;
  }
  .top {
    grid-area: top;
    justify-self: center;
  }
  .left {
    grid-area: left;
    align-self: center;
    justify-self: start;
  }
  .right {
    grid-area: right;
    align-self: center;
    justify-self: end;
  }
  .mid {
    grid-area: mid;
    min-height: calc(var(--trick-w) * 3.2 + 40px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }
  .me {
    grid-area: me;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .poverty-stack {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
  }
  .poverty-stack .cards {
    --back-w: 44px;
    display: flex;
  }
  .poverty-stack .cards :global(.back + .back) {
    margin-left: -14px;
  }
  .declared {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }
  /* Stichfläche: Kreuz aus vier Karten, die sich überlappen (z-index = Spielreihenfolge); links/rechts quer gelegt */
  .trick {
    --card-w: var(--trick-w);
    position: relative;
    flex-shrink: 0;
    width: calc(var(--trick-w) * 3.05 + 8px);
    height: calc(var(--trick-w) * 3 + 8px);
  }
  .slot {
    position: absolute;
  }
  .slot.top,
  .slot.bottom {
    left: 50%;
    width: var(--trick-w);
    height: calc(var(--trick-w) * 1.4);
    margin-left: calc(var(--trick-w) / -2);
  }
  .slot.top {
    top: 0;
  }
  .slot.bottom {
    bottom: 0;
  }
  .slot.left,
  .slot.right {
    top: 50%;
    width: calc(var(--trick-w) * 1.4);
    height: var(--trick-w);
    margin-top: calc(var(--trick-w) / -2);
  }
  .slot.left {
    left: 0;
  }
  .slot.right {
    right: 0;
  }
  /* Karte fliegt aus der Richtung ihres Spielers auf den Tisch; Neubrutalism-Schatten, Kartenbild bleibt unverändert */
  .fly {
    position: relative;
    width: 100%;
    height: 100%;
    filter: drop-shadow(4px 4px 0 #000);
    animation-duration: 0.5s;
    animation-timing-function: cubic-bezier(0.2, 0.8, 0.25, 1);
    animation-fill-mode: both;
  }
  .fly :global(.card) {
    filter: none;
  }
  .rot {
    position: absolute;
    left: 50%;
    top: 50%;
    width: var(--trick-w);
    transform: translate(-50%, -50%);
  }
  .slot.left .rot {
    transform: translate(-50%, -50%) rotate(-90deg);
  }
  .slot.right .rot {
    transform: translate(-50%, -50%) rotate(90deg);
  }
  .slot.bottom .fly { animation-name: from-bottom; }
  .slot.top .fly { animation-name: from-top; }
  .slot.left .fly { animation-name: from-left; }
  .slot.right .fly { animation-name: from-right; }
  @keyframes from-bottom { from { transform: translateY(150px) scale(1.2); opacity: 0.2; } to { transform: none; opacity: 1; } }
  @keyframes from-top { from { transform: translateY(-150px) scale(0.8); opacity: 0.2; } to { transform: none; opacity: 1; } }
  @keyframes from-left { from { transform: translateX(-190px) scale(0.85); opacity: 0.2; } to { transform: none; opacity: 1; } }
  @keyframes from-right { from { transform: translateX(190px) scale(0.85); opacity: 0.2; } to { transform: none; opacity: 1; } }
  .note {
    margin: 0;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.85rem;
    text-align: center;
  }
  .away {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: center;
    justify-content: center;
    margin: 0 auto 12px;
    padding: 10px 14px;
    border: var(--nb-border);
    background: var(--nb-lavender);
    box-shadow: var(--nb-shadow-sm);
    font-weight: 600;
    width: fit-content;
    max-width: 100%;
  }
  /* ---------- Handy: Gegner-Stapel beginnen direkt am Bildschirmrand, Tisch über die ganze Breite ---------- */
  @media (max-width: 640px) {
    .hide-sm {
      display: none;
    }
    .game {
      /* Hand: 12 Karten passen mit gut der Hälfte Überlappung genau in die Breite (Fächer braucht seitlich etwas Luft) */
      --card-w: min(78px, calc((100vw - 44px) / 6.1));
      min-height: 100vh;
      min-height: 100dvh;
    }
    .bar {
      padding: 6px 10px;
      gap: 6px 8px;
      min-height: 0;
    }
    .head-mid {
      flex: 1;
      min-width: 0;
      gap: 6px;
    }
    .head-mid :global(.nx-badge) {
      font-size: 0.66rem;
      padding: 2px 6px;
      box-shadow: 2px 2px 0 0 #000;
    }
    .tools {
      display: contents;
    }
    .sec {
      display: none;
      order: 5;
      flex: 1 1 calc(50% - 8px);
    }
    .tools.open .sec {
      display: inline-block;
    }
    .menu-toggle {
      display: inline-block;
    }
    .stage {
      display: flex;
      flex-direction: column;
      padding: 0;
      overflow-x: clip;
    }
    .away {
      margin: 6px 6px 6px;
    }
    .status {
      font-size: 0.82rem;
      min-height: 1.3em;
    }
    /* Stapel sind nur etwa zur Hälfte zu sehen: Sie ragen vom Rand in den Tisch hinein */
    .table {
      --back-w: clamp(28px, 9.4vw, 40px);
      --step: 0.44;
      --keep: 0.62;
      --trick-w: min(78px, calc((100vw - 150px) / 3.05));
      --side: calc(var(--back-w) * 1.4 * var(--keep) + 40px);
      flex: 1;
      grid-template-rows: auto 1fr auto;
      gap: 6px 0;
    }
    .mid {
      min-height: 0;
      align-self: stretch;
      padding: 6px 4px;
    }
    .fly {
      filter: drop-shadow(3px 3px 0 #000);
    }
    .me {
      align-self: end;
    }
    .note {
      font-size: 0.74rem;
    }
  }
</style>
