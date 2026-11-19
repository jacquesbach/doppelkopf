<script>
  import { onMount, untrack } from "svelte";
  import { api, labSeats, sessions } from "../../lib/services.js";
  import { navigate } from "../../lib/nav.svelte.js";
  import { formatDateTime } from "../../lib/format.js";
  import {
    addCard, canAdd, clearHand, editorFromPreset, faceLabel, firstHumanSeat, fitToDeck, handSize, isRed, newEditor,
    paletteFaces, removeCard, toScenario, trumpCount, usedCount,
  } from "../../lib/lab.js";
  import RuleForm from "../ui/RuleForm.svelte";

  let { token, onAuthLost } = $props();

  let schema = $state(null);
  let presets = $state([]);
  let tables = $state([]);
  let editor = $state(newEditor());
  let presetId = $state("");
  let activeSeat = $state(0);
  let error = $state("");
  let busy = $state(false);

  const sharp = $derived(!!editor.settings.sharp_doppelkopf);
  const size = $derived(handSize(sharp));
  const palette = $derived(paletteFaces(sharp));
  const columns = $derived(sharp ? 5 : 6);
  const defaults = $derived(schema ? Object.fromEntries(schema.map((s) => [s.id, s.default])) : {});

  function fail(e) {
    if (e.status === 401) return onAuthLost();
    error = e.message;
  }

  onMount(async () => {
    try {
      schema = (await api.ruleSchema()).options;
      editor = newEditor(Object.fromEntries(schema.map((s) => [s.id, s.default])));
      const [p, t] = await Promise.all([api.adminLabPresets(token), api.adminLabTables(token)]);
      presets = p.presets;
      tables = t.tables;
    } catch (e) {
      fail(e);
    }
  });

  // Blatt ohne Neunen: bereits gewählte Neunen und überzählige Karten verschwinden.
  $effect(() => {
    if (!sharp) return;
    const hands = untrack(() => editor.hands);
    if (Object.values(hands).some((c) => c.length > 10 || c.some((x) => x.startsWith("9")))) editor.hands = fitToDeck(hands, true);
  });

  function loadPreset(preset) {
    presetId = preset.id;
    editor = editorFromPreset(preset, defaults);
    activeSeat = 0;
    error = "";
  }

  const add = (face) => (editor.hands = addCard(editor.hands, activeSeat, face, sharp));
  const remove = (index) => (editor.hands = removeCard(editor.hands, activeSeat, index));
  const clear = () => (editor.hands = clearHand(editor.hands, activeSeat));
  const clearAll = () => {
    for (const s of [0, 1, 2, 3]) editor.hands = clearHand(editor.hands, s);
  };

  function remember(res) {
    labSeats.set(res.code, res.seats);
    const me = firstHumanSeat(res.seats);
    sessions.set(res.code, { token: me.token, memberId: me.memberId });
    navigate(`/tisch/${res.code}`);
  }

  async function create(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      remember(await api.adminLabCreate(token, toScenario(editor)));
    } catch (e) {
      busy = false;
      fail(e);
    }
  }

  async function reopen(code) {
    error = "";
    try {
      remember(await api.adminLabOpen(token, code));
    } catch (e) {
      fail(e);
    }
  }

  async function drop(code) {
    error = "";
    try {
      await api.adminLabDelete(token, code);
      labSeats.remove(code);
      sessions.remove(code);
      tables = (await api.adminLabTables(token)).tables;
    } catch (e) {
      fail(e);
    }
  }

  const seatTitle = (i) => `${i + 1}`;
</script>

<p class="nx-hint lead">
  Ein Test-Tisch ist ein echter Tisch (gleicher Spielcode, gleiche Bots, gleiche Oberfläche) – nur mit Karten, Regeln und
  Spielstand, die du festlegst. Plätze ohne „Bot“ spielst du selbst und wechselst unten am Tisch zwischen ihnen.
  Test-Tische erscheinen nicht in der Statistik und nie öffentlich; nach 12 Stunden ohne Aktion räumt sie das System ab.
</p>

{#if error}<p class="nx-error" role="alert">{error}</p>{/if}

<form onsubmit={create}>
  <section class="blk">
    <h2 class="nx-h2">1 · Vorlage</h2>
    <div class="presets">
      {#each presets as p (p.id)}
        <button type="button" class="preset" class:on={presetId === p.id} onclick={() => loadPreset(p)}>
          <b>{p.title}</b>
          <span>{p.description}</span>
        </button>
      {/each}
      {#if !presets.length}<p class="nx-hint">Lade Vorlagen …</p>{/if}
    </div>
  </section>

  <section class="blk">
    <h2 class="nx-h2">2 · Plätze und Geber</h2>
    <div class="seats">
      {#each editor.seats as seat, i (i)}
        <div class="seat">
          <span class="num">{i + 1}</span>
          <input class="nx-input" maxlength="32" aria-label="Name Platz {i + 1}" bind:value={seat.name} />
          <label class="bot"><input type="checkbox" bind:checked={seat.bot} /> Bot</label>
        </div>
      {/each}
    </div>
    <div class="nx-field" style="margin-top:12px;">
      <label class="nx-label" for="lab-dealer">Geber (links davon beginnt das Spiel)</label>
      <select id="lab-dealer" class="nx-input" bind:value={editor.dealer}>
        {#each [0, 1, 2, 3] as i (i)}<option value={i}>Platz {i + 1} – {editor.seats[i].name}</option>{/each}
      </select>
    </div>
  </section>

  <section class="blk">
    <h2 class="nx-h2">3 · Karten</h2>
    <p class="nx-hint">Nicht gewählte Karten werden zufällig verteilt. Jedes Kartenbild gibt es zweimal.</p>
    <div class="tabs" role="tablist" aria-label="Platz wählen">
      {#each [0, 1, 2, 3] as i (i)}
        <button type="button" role="tab" aria-selected={activeSeat === i} class="nx-btn nx-btn-sm" class:on={activeSeat === i}
          onclick={() => (activeSeat = i)}>
          {seatTitle(i)} <small>{editor.hands[i].length}/{size}</small>
        </button>
      {/each}
    </div>

    <div class="hand">
      <div class="hand-head">
        <b>{editor.seats[activeSeat].name}</b>
        <span>{editor.hands[activeSeat].length}/{size} Karten · {trumpCount(editor.hands[activeSeat])} Trümpfe (Normalspiel)</span>
      </div>
      <div class="chips" aria-live="polite">
        {#each editor.hands[activeSeat] as face, i (i + face)}
          <button type="button" class="chip" class:red={isRed(face)} onclick={() => remove(i)} aria-label="{faceLabel(face)} entfernen">{faceLabel(face)}</button>
        {:else}
          <span class="nx-hint">Keine festen Karten – zufällig.</span>
        {/each}
      </div>
      <div class="btns">
        <button type="button" class="nx-btn nx-btn-sm" onclick={clear}>HAND LEEREN</button>
        <button type="button" class="nx-btn nx-btn-sm" onclick={clearAll}>ALLE LEEREN</button>
      </div>
    </div>

    <div class="palette" style="--cols:{columns}" role="group" aria-label="Karten hinzufügen">
      {#each palette as face (face)}
        {@const left = 2 - usedCount(editor.hands, face)}
        <button type="button" class="pal" class:red={isRed(face)} disabled={!canAdd(editor.hands, activeSeat, face, sharp)}
          onclick={() => add(face)} aria-label="{faceLabel(face)} hinzufügen, noch {left} frei">
          {faceLabel(face)}<small>×{left}</small>
        </button>
      {/each}
    </div>
  </section>

  <section class="blk">
    <h2 class="nx-h2">4 · Rundenstand und Vorspielen</h2>
    <div class="grid2">
      <div class="nx-field">
        <label class="nx-label" for="lab-played">Gespielte Normalspiele (0–24)</label>
        <input id="lab-played" class="nx-input" type="number" min="0" max="24" bind:value={editor.round.normalGamesPlayed} />
      </div>
      <div class="nx-field">
        <label class="nx-label" for="lab-bock">Offene Bockspiele</label>
        <input id="lab-bock" class="nx-input" type="number" min="0" max="99" bind:value={editor.round.bockRemaining} />
      </div>
    </div>
    <fieldset class="solo">
      <legend class="nx-label">Pflichtsolo schon gespielt</legend>
      {#each [0, 1, 2, 3] as i (i)}
        <label><input type="checkbox" bind:checked={editor.round.pflichtsoloDone[i]} /> Platz {i + 1}</label>
      {/each}
    </fieldset>
    <div class="grid2">
      <div class="nx-field">
        <label class="nx-label" for="lab-adv">Vorspielen (Bots spielen für alle Plätze)</label>
        <select id="lab-adv" class="nx-input" bind:value={editor.advance}>
          <option value="none">Nein – ab der Vorbehaltsabfrage</option>
          <option value="playing">Bis zum Spielbeginn (erste Karte)</option>
          <option value="tricks">Bis zu einer Stichzahl</option>
        </select>
      </div>
      {#if editor.advance === "tricks"}
        <div class="nx-field">
          <label class="nx-label" for="lab-tricks">Stiche vorgespielt (0–{size})</label>
          <input id="lab-tricks" class="nx-input" type="number" min="0" max={size} bind:value={editor.tricks} />
        </div>
      {/if}
    </div>
  </section>

  <section class="blk">
    <h2 class="nx-h2">5 · Regeln</h2>
    {#if schema}
      <RuleForm {schema} bind:settings={editor.settings} />
    {:else}
      <p>Lade Regeln …</p>
    {/if}
  </section>

  <div class="nx-btn-row">
    <button type="submit" class="nx-btn nx-btn-lg nx-bg-yellow" disabled={busy || !schema}>
      {busy ? "ERÖFFNE …" : "TEST-TISCH ERÖFFNEN"} &rarr;
    </button>
  </div>
</form>

<section class="blk" style="margin-top:28px;">
  <h2 class="nx-h2">Offene Test-Tische</h2>
  {#if !tables.length}
    <p class="nx-hint">Keine.</p>
  {:else}
    <ul class="open">
      {#each tables as t (t.code)}
        <li>
          <span class="mono">{t.code}</span>
          <span>{t.title || "ohne Titel"} <small>· {formatDateTime(new Date(t.createdAt).getTime() / 1000)}</small></span>
          <span class="btns">
            <button type="button" class="nx-btn nx-btn-sm" onclick={() => reopen(t.code)}>ÖFFNEN</button>
            <button type="button" class="nx-btn nx-btn-sm nx-bg-coral" onclick={() => drop(t.code)}>LÖSCHEN</button>
          </span>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  .lead { margin-top: 0; }
  .blk { margin-bottom: 26px; min-width: 0; }
  .presets { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 10px; }
  .preset { text-align: left; font: inherit; background: #fff; border: 3px solid #000; box-shadow: var(--nb-shadow-sm); padding: 10px 12px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; }
  .preset b { font-family: var(--font-heading); }
  .preset span { font-size: 0.82rem; color: #333; }
  .preset.on { background: var(--nb-yellow); box-shadow: none; transform: translate(2px, 2px); }
  .seats { display: grid; gap: 8px; }
  .seat { display: grid; grid-template-columns: 28px 1fr auto; gap: 8px; align-items: center; }
  .num { font-family: var(--font-heading); font-weight: 700; text-align: center; }
  .bot { display: flex; gap: 6px; align-items: center; font-weight: 700; }
  .tabs { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 12px; }
  .tabs .on { background: var(--nb-yellow); box-shadow: none; transform: translate(2px, 2px); }
  .hand { border: 3px solid #000; background: var(--nb-paper); padding: 10px; margin-bottom: 12px; }
  .hand-head { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; font-size: 0.9rem; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; min-height: 40px; align-items: center; margin-bottom: 8px; }
  .chip, .pal { font: inherit; font-weight: 700; background: #fff; border: 2px solid #000; padding: 6px 10px; cursor: pointer; min-width: 46px; }
  .chip.red, .pal.red { color: #c0182b; }
  .btns { display: flex; gap: 8px; flex-wrap: wrap; }
  .palette { display: grid; grid-template-columns: repeat(var(--cols), minmax(0, 1fr)); gap: 6px; }
  .pal { display: flex; flex-direction: column; align-items: center; padding: 8px 2px; box-shadow: 2px 2px 0 #000; }
  .pal small { font-weight: 400; font-size: 0.7rem; color: #444; }
  .pal:disabled { opacity: 0.35; cursor: not-allowed; box-shadow: none; }
  .grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; }
  .solo { border: 0; padding: 0; margin: 4px 0 14px; display: flex; gap: 14px; flex-wrap: wrap; }
  .solo legend { padding: 0; margin-bottom: 4px; }
  .open { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
  .open li { display: grid; grid-template-columns: auto 1fr auto; gap: 10px; align-items: center; border: 3px solid #000; padding: 8px 10px; background: #fff; }
  .mono { font-family: var(--font-mono); font-weight: 700; }
  small { color: #444; }
</style>
