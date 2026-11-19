<script>
  import { onMount } from "svelte";
  import { api, sessions } from "../lib/services.js";
  import { navigate } from "../lib/nav.svelte.js";
  import PageShell from "../components/ui/PageShell.svelte";
  import RuleForm from "../components/ui/RuleForm.svelte";

  let schema = $state(null);
  let settings = $state({});
  let name = $state(sessions.lastName());
  let password = $state("");
  let isPublic = $state(false);
  let withBots = $state(new URLSearchParams(window.location.search).get("ki") === "1");
  let error = $state("");
  let busy = $state(false);

  onMount(async () => {
    try {
      schema = (await api.ruleSchema()).options;
      settings = Object.fromEntries(schema.map((s) => [s.id, s.default]));
    } catch (e) {
      error = e.message;
    }
  });

  async function submit(event) {
    event.preventDefault();
    error = "";
    if (!name.trim()) {
      error = "Bitte gib deinen Spielernamen ein.";
      return;
    }
    busy = true;
    try {
      const res = await api.createRoom({ name: name.trim(), password, settings, isPublic });
      const { code } = res.room;
      sessions.rememberName(name.trim());
      sessions.set(code, { token: res.token, memberId: res.memberId });
      if (withBots) {
        // Sofort-Partie: Bots füllen die freien Plätze, dann geht es direkt los.
        await api.addBot(code, res.token);
        await api.start(code, res.token);
      }
      navigate(`/tisch/${code}`);
    } catch (e) {
      error = e.message;
      busy = false;
    }
  }
</script>

<PageShell narrow>
  <span class="nx-badge nx-bg-lavender">NEUER TISCH</span>
  <h1 class="nx-title">Neuer Tisch</h1>

  <form onsubmit={submit} novalidate>
    {#if error}<p class="nx-error" role="alert">{error}</p>{/if}

    <div class="nx-box">
      <h2 class="nx-h2">Du</h2>
      <div class="nx-field">
        <label class="nx-label" for="c-name">Spielername</label>
        <input id="c-name" class="nx-input" maxlength="32" autocomplete="nickname" bind:value={name} required />
      </div>
      <div class="nx-field">
        <label class="nx-label" for="c-pass">Passwort (optional)</label>
        <input id="c-pass" class="nx-input" type="password" minlength="4" autocomplete="new-password" bind:value={password} />
        <span class="nx-hint">Mindestens vier Zeichen. Ohne Passwort kann jeder mit dem Link beitreten.</span>
      </div>
    </div>

    <div class="nx-box nx-bg-white">
      <h2 class="nx-h2" style="margin-bottom:4px;">Regeln</h2>
      <p class="nx-hint" style="margin-top:0;">
        Voreingestellt sind die DDV-Turnierspielregeln. Weitere Regeln lassen sich einzeln zuschalten.
      </p>
      {#if schema}
        <RuleForm {schema} bind:settings />
      {:else if !error}
        <p>Lade Regeln …</p>
      {/if}
    </div>

    <div class="nx-box nx-bg-white">
      <label class="nx-rule" style="border-top:0;padding:0;">
        <input type="checkbox" bind:checked={isPublic} />
        <span class="nx-check" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 16 16"><path d="M2.5 8.5L6.5 12.5L13.5 3.5" fill="none" stroke="#000" stroke-width="3" /></svg>
        </span>
        <span>
          <span class="nx-h3" style="display:block;">Öffentlicher Tisch</span>
          <span class="nx-hint">Der Tisch erscheint mit seinen Regeln in der Liste „Diese Tische suchen Mitspieler“, solange Plätze frei sind. Später änderbar.</span>
        </span>
      </label>
    </div>

    <div class="nx-box nx-bg-yellow">
      <label class="nx-rule" style="border-top:0;padding:0;">
        <input type="checkbox" bind:checked={withBots} />
        <span class="nx-check" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 16 16"><path d="M2.5 8.5L6.5 12.5L13.5 3.5" fill="none" stroke="#000" stroke-width="3" /></svg>
        </span>
        <span>
          <span class="nx-h3" style="display:block;">Sofort-Partie gegen KI</span>
          <span class="nx-hint" style="color:#000;">Drei Bots setzen sich an den Tisch, die erste Runde startet sofort.</span>
        </span>
      </label>
    </div>

    <div class="nx-btn-row" style="margin-top:28px;">
      <button type="submit" class="nx-btn nx-btn-lg" disabled={busy || !schema}>
        {withBots ? "PARTIE STARTEN" : "TISCH ERÖFFNEN"} &rarr;
      </button>
    </div>
  </form>
</PageShell>
