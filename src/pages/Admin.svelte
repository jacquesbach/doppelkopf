<script>
  import { onMount } from "svelte";
  import PageShell from "../components/ui/PageShell.svelte";
  import AdminLive from "../components/admin/AdminLive.svelte";
  import AdminInsights from "../components/admin/AdminInsights.svelte";
  import AdminSystem from "../components/admin/AdminSystem.svelte";
  import AdminDesign from "../components/admin/AdminDesign.svelte";
  import AdminStats from "../components/admin/AdminStats.svelte";
  import AdminPhrases from "../components/admin/AdminPhrases.svelte";
  import AdminSuggestions from "../components/admin/AdminSuggestions.svelte";
  import AdminLab from "../components/admin/AdminLab.svelte";
  import { api } from "../lib/services.js";

  // Das Token liegt nur im Tab-Speicher (sessionStorage): Tab zu = abgemeldet.
  const KEY = "doko.admin.v1";
  const TABS = [
    ["live", "LIVE"],
    ["stats", "STATISTIK"],
    ["insights", "AUSWERTUNG"],
    ["system", "SYSTEM"],
    ["design", "DESIGN"],
    ["phrases", "SPRÜCHE"],
    ["suggestions", "VORSCHLÄGE"],
    ["lab", "TEST-TISCH"],
  ];

  let enabled = $state(null); // null = prüfe
  let token = $state(readToken());
  let password = $state("");
  let error = $state("");
  let busy = $state(false);
  let tab = $state("live");

  function readToken() {
    try {
      return window.sessionStorage.getItem(KEY) || "";
    } catch {
      return "";
    }
  }
  function writeToken(value) {
    token = value;
    try {
      if (value) window.sessionStorage.setItem(KEY, value);
      else window.sessionStorage.removeItem(KEY);
    } catch {
      /* ohne Speicher: gilt bis zum Neuladen */
    }
  }

  onMount(async () => {
    try {
      enabled = (await api.adminStatus()).enabled;
    } catch (e) {
      enabled = false;
      error = e.message;
    }
  });

  async function login(event) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      writeToken((await api.adminLogin(password)).token);
      password = "";
    } catch (e) {
      error = e.status === 401 ? "Passwort falsch." : e.message;
    } finally {
      busy = false;
    }
  }

  function authLost() {
    writeToken("");
    error = "Die Anmeldung ist abgelaufen. Bitte neu anmelden.";
  }
</script>

<svelte:head><meta name="robots" content="noindex, nofollow" /></svelte:head>

<PageShell narrow={!token}>
  <h1 class="nx-title">BETREIBER</h1>

  {#if enabled === null}
    <p>Prüfe …</p>
  {:else if enabled === false}
    <div class="nx-box">
      <p>
        Das Betreiber-Backend ist nicht eingerichtet. Setze beim Start des Servers die Umgebungsvariable
        <code>ADMIN_PASSWORD</code> (in Produktion mindestens 10 Zeichen) und starte neu.
      </p>
      {#if error}<p class="nx-error" role="alert">{error}</p>{/if}
    </div>
  {:else if !token}
    <form class="nx-box" onsubmit={login}>
      {#if error}<p class="nx-error" role="alert">{error}</p>{/if}
      <div class="nx-field">
        <label class="nx-label" for="adm-pw">Passwort</label>
        <input id="adm-pw" class="nx-input" type="password" bind:value={password} autocomplete="current-password" />
      </div>
      <button type="submit" class="nx-btn nx-btn-block nx-bg-yellow" disabled={busy || !password}>
        {busy ? "PRÜFE …" : "ANMELDEN"}
      </button>
    </form>
  {:else}
    <div class="bar">
      <div class="tabs" role="tablist" aria-label="Bereiche">
        {#each TABS as [id, label] (id)}
          <button
            type="button"
            role="tab"
            id="tab-{id}"
            aria-selected={tab === id}
            aria-controls="panel-{id}"
            class="nx-btn nx-btn-sm"
            class:on={tab === id}
            onclick={() => (tab = id)}
          >{label}</button>
        {/each}
      </div>
      <button type="button" class="nx-btn nx-btn-sm" onclick={() => writeToken("")}>ABMELDEN</button>
    </div>

    <section class="panel nx-box" role="tabpanel" id="panel-{tab}" aria-labelledby="tab-{tab}">
      {#key tab}
        {#if tab === "live"}
          <AdminLive {token} onAuthLost={authLost} />
        {:else if tab === "insights"}
          <AdminInsights {token} onAuthLost={authLost} />
        {:else if tab === "system"}
          <AdminSystem {token} onAuthLost={authLost} />
        {:else if tab === "design"}
          <AdminDesign {token} onAuthLost={authLost} />
        {:else if tab === "stats"}
          <AdminStats {token} onAuthLost={authLost} />
        {:else if tab === "phrases"}
          <AdminPhrases {token} onAuthLost={authLost} />
        {:else if tab === "lab"}
          <AdminLab {token} onAuthLost={authLost} />
        {:else}
          <AdminSuggestions {token} onAuthLost={authLost} />
        {/if}
      {/key}
    </section>
  {/if}
</PageShell>

<style>
  .bar { display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
  .tabs { display: flex; gap: 8px; flex-wrap: wrap; }
  .tabs .on { background: var(--nb-yellow); box-shadow: none; transform: translate(2px, 2px); }
  .panel { min-width: 0; }
</style>
