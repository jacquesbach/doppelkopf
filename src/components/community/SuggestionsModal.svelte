<script>
  import { onMount } from "svelte";
  import Dialog from "../ui/Dialog.svelte";
  import { api } from "../../lib/services.js";
  import {
    TITLE_MAX, DESC_MAX, TITLE_MIN, DESC_MIN,
    rankSuggestions, applyVote, formProblem,
  } from "../../lib/suggestions.js";

  let { onClose } = $props();

  let items = $state(null); // null = lädt
  let loadFailed = $state(false);
  let formOpen = $state(false);
  let title = $state("");
  let description = $state("");
  let website = $state(""); // Honigtopf: Menschen sehen das Feld nicht
  let answer = $state("");
  let captcha = $state(null); // { token, svg }
  let captchaFailed = $state(false);
  let sending = $state(false);
  let error = $state("");
  let thanks = $state(false);
  let voting = $state(new Set());
  let voteError = $state("");

  async function loadList() {
    try {
      items = rankSuggestions((await api.suggestions()).suggestions);
      loadFailed = false;
    } catch {
      loadFailed = true;
      items ??= [];
    }
  }

  async function loadCaptcha() {
    captchaFailed = false;
    answer = "";
    try {
      captcha = await api.captcha();
    } catch (e) {
      captcha = null;
      captchaFailed = true;
      error = e.message;
    }
  }

  function openForm() {
    formOpen = true;
    thanks = false;
    error = "";
    loadCaptcha();
  }

  async function submit(event) {
    event.preventDefault();
    error = formProblem(title, description) ?? "";
    if (error) return;
    if (!captcha || !answer.trim()) {
      error = "Bitte gib die Zeichen aus der Grafik ein.";
      return;
    }
    sending = true;
    try {
      const { suggestion } = await api.submitSuggestion({
        title, description, website,
        captchaToken: captcha.token, captchaAnswer: answer,
      });
      items = rankSuggestions([...(items ?? []), suggestion]);
      title = description = answer = "";
      captcha = null;
      formOpen = false;
      thanks = true;
    } catch (e) {
      error = e.message;
      // Ein Captcha gilt nur einmal: bei jedem Captcha-Fehler gleich ein frisches holen.
      if (String(e.code ?? "").startsWith("captcha_")) await loadCaptcha();
    } finally {
      sending = false;
    }
  }

  async function vote(item) {
    if (voting.has(item.id)) return;
    voting = new Set(voting).add(item.id);
    voteError = "";
    try {
      items = applyVote(items, item.id, await api.voteSuggestion(item.id));
    } catch (e) {
      voteError = e.message;
      if (e.status === 404) await loadList(); // inzwischen entfernt
    } finally {
      const next = new Set(voting);
      next.delete(item.id);
      voting = next;
    }
  }

  onMount(loadList);
</script>

<Dialog title="VERBESSERUNGSVORSCHLÄGE" {onClose} wide>
  <p class="intro">
    Was fehlt dir im Spiel? Schlage Neues vor und gib den Ideen anderer einen Daumen hoch –
    die beliebtesten stehen oben.
  </p>

  {#if thanks}
    <p class="ok" role="status">Danke! Dein Vorschlag ist jetzt in der Liste.</p>
  {/if}

  {#if !formOpen}
    <button type="button" class="nx-btn nx-btn-block add" onclick={openForm}>+ EIGENEN VORSCHLAG EINREICHEN</button>
  {:else}
    <form class="form" onsubmit={submit} novalidate>
      {#if error}<p class="nx-error" role="alert">{error}</p>{/if}

      <div class="nx-field">
        <label class="nx-label" for="sg-title">Titel</label>
        <input id="sg-title" class="nx-input" bind:value={title} maxlength={TITLE_MAX} autocomplete="off" />
        <span class="nx-hint count" class:low={title.trim().length > 0 && title.trim().length < TITLE_MIN}>
          {title.length}/{TITLE_MAX} (mind. {TITLE_MIN})
        </span>
      </div>

      <div class="nx-field">
        <label class="nx-label" for="sg-desc">Kurzbeschreibung</label>
        <textarea id="sg-desc" class="nx-input" rows="4" bind:value={description} maxlength={DESC_MAX}></textarea>
        <span class="nx-hint count" class:low={description.trim().length > 0 && description.trim().length < DESC_MIN}>
          {description.length}/{DESC_MAX} (mind. {DESC_MIN}) · Bitte keine Links – sie werden abgelehnt.
        </span>
      </div>

      <!-- Honigtopf gegen Bots -->
      <div class="trap" aria-hidden="true">
        <label>Website <input type="text" tabindex="-1" autocomplete="off" bind:value={website} /></label>
      </div>

      <div class="nx-field">
        <span class="nx-label" id="sg-cap-label">Sicherheitsabfrage</span>
        <div class="captcha">
          {#if captcha}
            <!-- vom Server erzeugte Vektorgrafik (nur Linien und Pfade, kein Skript) -->
            <div class="cap-img" role="img" aria-label="Grafik mit fünf verzerrten Zeichen">{@html captcha.svg}</div>
          {:else if captchaFailed}
            <span class="nx-hint">Konnte nicht geladen werden.</span>
          {:else}
            <span class="nx-hint">Lädt …</span>
          {/if}
          <button type="button" class="nx-btn nx-btn-sm" onclick={loadCaptcha} aria-label="Neue Grafik laden">NEU</button>
        </div>
        <input
          class="nx-input cap-input"
          aria-labelledby="sg-cap-label"
          bind:value={answer}
          maxlength="8"
          autocomplete="off"
          autocapitalize="characters"
          spellcheck="false"
          placeholder="Zeichen eingeben"
        />
        <span class="nx-hint">Groß-/Kleinschreibung egal. Verwechselbare Zeichen wie 0/O oder 1/I kommen nicht vor.</span>
      </div>

      <div class="nx-btn-row">
        <button type="submit" class="nx-btn nx-bg-green" disabled={sending}>
          {sending ? "SENDE …" : "VORSCHLAG ABSENDEN"}
        </button>
        <button type="button" class="nx-btn" onclick={() => (formOpen = false)}>ABBRECHEN</button>
      </div>
    </form>
  {/if}

  {#if voteError}<p class="nx-error" role="alert">{voteError}</p>{/if}

  <h3 class="nx-h3 list-title">Alle Vorschläge{items?.length ? ` (${items.length})` : ""}</h3>
  <div aria-live="polite">
    {#if items === null}
      <p class="empty">Lade Vorschläge …</p>
    {:else if loadFailed && !items.length}
      <p class="empty">Die Vorschläge sind gerade nicht erreichbar.</p>
    {:else if !items.length}
      <p class="empty">Noch keine Vorschläge – mach den Anfang!</p>
    {:else}
      <ol class="list">
        {#each items as item (item.id)}
          <li class="item">
            <button
              type="button"
              class="thumb"
              class:on={item.voted}
              aria-pressed={item.voted}
              aria-label={item.voted ? "Daumen zurücknehmen" : "Daumen hoch geben"}
              disabled={voting.has(item.id)}
              onclick={() => vote(item)}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M2 10h4v11H2zM7 10l4-8c1.5 0 2.5 1 2.5 2.5V8H20c1 0 1.8.9 1.6 1.9l-1.6 9c-.2 1.2-1.2 2.1-2.4 2.1H7z"
                      fill={item.voted ? "#000" : "#fff"} stroke="#000" stroke-width="2" stroke-linejoin="round" />
              </svg>
              <span class="n">{item.votes}</span>
            </button>
            <div class="text">
              <h4>{item.title}</h4>
              <p>{item.description}</p>
            </div>
          </li>
        {/each}
      </ol>
    {/if}
  </div>
</Dialog>

<style>
  .intro { margin: 0 0 14px; }
  .add { margin-bottom: 8px; }
  .ok { background: var(--nb-green); border: 3px solid #000; box-shadow: var(--nb-shadow-sm); padding: 8px 12px; font-weight: 700; margin: 0 0 14px; }
  .form { border: 3px solid #000; background: var(--nb-paper); padding: 16px; margin-bottom: 16px; }
  textarea { resize: vertical; min-height: 90px; }
  .count.low { color: #a00; font-weight: 600; }
  .trap { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
  .captcha { display: flex; gap: 10px; align-items: stretch; flex-wrap: wrap; }
  .cap-img { border: 3px solid #000; background: #fff; line-height: 0; min-width: 180px; }
  .cap-img :global(svg) { display: block; max-width: 100%; height: auto; }
  .cap-input { text-transform: uppercase; letter-spacing: 0.15em; font-family: var(--font-mono); max-width: 260px; }
  .list-title { margin: 18px 0 10px; }
  .empty { margin: 0; color: #444; }
  .list { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
  .item { display: flex; gap: 12px; align-items: flex-start; border: 3px solid #000; background: #fff; box-shadow: var(--nb-shadow-sm); padding: 10px 12px; }
  .thumb { flex: 0 0 auto; display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 54px; padding: 6px 8px; border: 3px solid #000; background: #fff; cursor: pointer; font: inherit; color: #000; }
  .thumb.on { background: var(--nb-yellow); box-shadow: var(--nb-shadow-sm); }
  .thumb:disabled { opacity: 0.6; cursor: progress; }
  .thumb:not(:disabled):active { transform: translate(2px, 2px); }
  .n { font-family: var(--font-mono); font-weight: 700; }
  .text { min-width: 0; }
  .text h4 { margin: 0 0 4px; font-family: var(--font-heading); font-size: 1.05rem; overflow-wrap: anywhere; }
  .text p { margin: 0; white-space: pre-line; overflow-wrap: anywhere; }
</style>
