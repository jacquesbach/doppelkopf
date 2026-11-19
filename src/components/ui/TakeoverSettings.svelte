<script>
  import { TAKEOVER_OPTIONS, takeoverLabel } from "../../lib/labels.js";

  // Bot-Übernahme bei Inaktivität. Der Host stellt die Zeit für den ganzen Tisch ein (auch während der Runde);
  // jeder Spieler kann für sich ablehnen („nie durch einen Bot ersetzen“). Gegen Bots allein übernimmt nie ein Bot.
  let { store, mine = false } = $props();

  const seconds = $derived(store.room?.botTakeover ?? 180);
  const seat = $derived(store.view?.table.mySeat ?? null);
  const never = $derived(seat != null && !!store.view?.table.seats[seat]?.noTakeover);
  const id = `takeover-${Math.random().toString(36).slice(2, 7)}`;
</script>

<div class="wrap">
  {#if store.isHost}
    <label for={id} class="lbl">Bot übernimmt bei Inaktivität nach</label>
    <select {id} class="nx-input" value={seconds} disabled={store.busy} onchange={(e) => store.setTakeover(Number(e.currentTarget.value))}>
      {#each TAKEOVER_OPTIONS as [value, label] (value)}
        <option {value}>{label}</option>
      {/each}
    </select>
  {:else}
    <p class="lbl">Bot übernimmt bei Inaktivität: <strong>{seconds === 0 ? "nie" : `nach ${takeoverLabel(seconds)}`}</strong> (Einstellung des Hosts)</p>
  {/if}
  <p class="nx-hint">
    Wer am Zug ist und nicht reagiert, bekommt vorher einen 30-Sekunden-Countdown. Spielt ein Mensch allein gegen Bots,
    übernimmt nie ein Bot – der Tisch wartet. Tische ohne Aktivität werden nach 12 Stunden geschlossen.
  </p>
  {#if mine && seat != null}
    <label class="check">
      <input type="checkbox" checked={never} disabled={store.busy} onchange={(e) => store.stay(e.currentTarget.checked)} />
      <span>Für mich: bei Inaktivität nie durch einen Bot ersetzen</span>
    </label>
  {/if}
</div>

<style>
  .wrap {
    display: grid;
    gap: 8px;
  }
  .lbl {
    margin: 0;
    font-weight: 700;
  }
  .check {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    font-weight: 600;
    cursor: pointer;
  }
  .check input {
    width: 20px;
    height: 20px;
    accent-color: #000;
    flex-shrink: 0;
  }
</style>
