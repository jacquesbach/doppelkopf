<script>
  import { resultSummary, roundRanking, seatName } from "../../lib/view.js";
  import Dialog from "../ui/Dialog.svelte";

  // Ergebnis des Spiels. `onClose` blendet den Dialog aus, damit man die aufgedeckten Stiche ansehen kann.
  let { view, isHost, busy = false, onClose, onTricks, onNext, onNewRound } = $props();

  const result = $derived(resultSummary(view));
  const round = $derived(view.table.round);
  const ranking = $derived(roundRanking(view));
  const roundDone = $derived(view.table.finished);
  const next = $derived(round.next);
  const bockLeft = $derived(round.bockRemaining ?? 0);
</script>

{#if result}
  <Dialog title={roundDone ? "Runde beendet" : "Spielergebnis"} {onClose} wide>
    <div class="head">
      <span class="nx-badge {result.winner === 're' ? 'nx-bg-coral' : result.winner === 'kontra' ? 'nx-bg-blue' : 'nx-bg-yellow'}">
        {result.winner ? `${result.winnerLabel} gewinnt` : "Unentschieden"}
      </span>
      {#if result.names.winners.length}
        <span class="winners">{result.names.winners.join(" & ")}</span>
      {/if}
      <span class="nx-mono">
        RE {result.points.re} : {result.points.kontra} KONTRA
        {#if result.multiplier > 1} · BOCK ×{result.multiplier}{/if}
        {#if result.soloScoring} · SOLO ×3{/if}
      </span>
    </div>

    <div class="cols">
      {#each [["re", "Re"], ["kontra", "Kontra"]] as [party, label] (party)}
        <table class="nx-table" aria-label={`Wertung ${label}`}>
          <thead>
            <tr>
              <th>{label}{#if result.names[party].length}<span class="who"> · {result.names[party].join(" & ")}</span>{/if}</th>
              <th class="num">Pkt</th>
            </tr>
          </thead>
          <tbody>
            {#each result.items[party] as item, i (i)}
              <tr><td>{item.label}</td><td class="num">{item.points}</td></tr>
            {:else}
              <tr><td colspan="2">–</td></tr>
            {/each}
          </tbody>
        </table>
      {/each}
    </div>

    <h3 class="nx-h3" style="margin-top:18px;">Gutschrift pro Spieler</h3>
    <div class="deltas">
      {#each result.seatDeltas as d (d.seat)}
        <span class="nx-badge {d.delta > 0 ? 'nx-bg-green' : d.delta < 0 ? 'nx-bg-coral' : ''}">
          {d.name}: {d.delta > 0 ? "+" : ""}{d.delta}
        </span>
      {/each}
    </div>

    {#if result.bockTriggers.length}
      <p class="nx-mono" style="margin-top:14px;">
        BOCKRUNDE AUSGELÖST: {result.bockTriggers.join(", ")} – die nächsten 4 Spiele zählen doppelt.
      </p>
    {:else if bockLeft > 0}
      <p class="nx-mono" style="margin-top:14px;">BOCKRUNDE: noch {bockLeft} {bockLeft === 1 ? "Spiel" : "Spiele"} doppelt.</p>
    {/if}

    <h3 class="nx-h3" style="margin-top:18px;">Zwischenstand der Runde</h3>
    <ol class="rank">
      {#each ranking as r (r.seat)}
        <li><span class="nx-mono">{r.rank}.</span> {r.name} <strong>{r.points}</strong></li>
      {/each}
    </ol>

    {#if !roundDone && next}
      <p class="nx-hint">
        Nächster Geber: {seatName(view, next.dealer)}.
        {#if next.forcedSoloSeat != null}{seatName(view, next.forcedSoloSeat)} muss ein Pflichtsolo vorführen.{/if}
      </p>
    {/if}

    <div class="nx-btn-row" style="margin-top:20px;">
      {#if !roundDone && view.table.mySeat != null}
        <button type="button" class="nx-btn" disabled={busy} onclick={onNext}>NÄCHSTES SPIEL &rarr;</button>
      {:else if roundDone && isHost}
        <button type="button" class="nx-btn" disabled={busy} onclick={onNewRound}>NEUE RUNDE STARTEN &rarr;</button>
      {:else if roundDone}
        <span class="nx-hint">Der Host kann eine neue Runde starten.</span>
      {/if}
      <button type="button" class="nx-btn nx-bg-white" onclick={onTricks}>STICHE ANSEHEN</button>
      <button type="button" class="nx-btn nx-bg-white" onclick={onClose}>SCHLIESSEN</button>
    </div>
  </Dialog>
{/if}

<style>
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }
  .winners {
    font-weight: 700;
    font-size: 1.05rem;
  }
  .who {
    font-weight: 500;
    text-transform: none;
  }
  .cols {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    align-items: start; /* jede Tabelle behält ihre natürliche Höhe: gleiche Zeilenhöhe links und rechts */
  }
  .cols .nx-table td {
    vertical-align: middle;
  }
  .deltas {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .rank {
    margin: 0;
    padding: 0;
    list-style: none;
    display: grid;
    gap: 4px;
  }
  @media (max-width: 560px) {
    .cols {
      grid-template-columns: 1fr;
    }
  }
</style>
