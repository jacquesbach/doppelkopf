<script>
  import Dialog from "../ui/Dialog.svelte";
  import { formatCode, friendLabel, NAME_MAX } from "../../lib/friends.js";
  import { presence } from "../../lib/presence.svelte.js";
  import { inviteLink } from "../../lib/router.js";

  let { onClose } = $props();

  let aliasInput = $state(presence.name);
  let consent = $state(false);
  let addCode = $state("");
  let addName = $state("");
  let copied = $state(false);
  let confirmForget = $state(false);

  const onlineCount = $derived(presence.friends.filter((f) => presence.live[f.code]).length);

  function turnOn(event) {
    event.preventDefault();
    if (!consent) {
      presence.error = "Bitte bestätige zuerst, dass du sichtbar sein möchtest.";
      return;
    }
    presence.enable(aliasInput);
  }

  function addFriend(event) {
    event.preventDefault();
    if (presence.add(addCode, addName)) {
      addCode = "";
      addName = "";
    }
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(presence.code);
      copied = true;
      setTimeout(() => (copied = false), 2000);
    } catch {
      window.prompt("Dein Freundescode:", presence.code);
    }
  }

  function status(code) {
    const s = presence.sent[code];
    if (s === "pending") return "…";
    if (s === "sent") return "Einladung gesendet ✓";
    if (s === "offline") return "Ist nicht mehr online";
    return "";
  }
  const noneVisible = $derived(presence.connected && presence.friends.length > 0 && onlineCount === 0);
  const canInvite = $derived(!!presence.table && presence.connected);
</script>

<Dialog title="Wer ist online?" {onClose} wide>
  {#if presence.error}<p class="nx-error" role="alert">{presence.error}</p>{/if}

  {#if !presence.enabled}
    <p>
      Hier kannst du <strong>freiwillig</strong> zeigen, dass du online bist – nur für Leute, denen du deinen Freundescode gibst.
      Du brauchst dafür <strong>kein Konto</strong>. Solange das aus ist, weiß niemand, dass du hier bist, und du siehst auch niemanden.
    </p>
    <form onsubmit={turnOn}>
      <div class="nx-field">
        <label class="nx-label" for="fr-alias">Anzeigename für Freunde</label>
        <input id="fr-alias" class="nx-input" maxlength={NAME_MAX} bind:value={aliasInput} placeholder="z. B. Anna" autocomplete="off" />
      </div>
      <label class="check">
        <input type="checkbox" bind:checked={consent} />
        <span>
          Ich möchte für Freunde sichtbar sein, solange ich online bin. Mein Freundescode und mein Anzeigename werden dafür
          nur im Arbeitsspeicher des Servers gehalten und beim Trennen gelöscht. Ich kann das jederzeit ausschalten.
        </span>
      </label>
      <button type="submit" class="nx-btn nx-bg-yellow nx-btn-block" disabled={!aliasInput.trim() || !consent}>ONLINE-STATUS EINSCHALTEN</button>
    </form>
    {#if presence.friends.length}
      <p class="nx-hint">Deine gespeicherte Freundesliste ({presence.friends.length}) bleibt in diesem Browser und ist erst nach dem Einschalten wieder aktiv.</p>
    {/if}
  {:else}
    <div class="me nx-box">
      <p class="lab">Dein Freundescode – gib ihn nur Leuten, die dich sehen dürfen</p>
      <p class="code" aria-label="Dein Freundescode">{formatCode(presence.code)}</p>
      <div class="row">
        <button type="button" class="nx-btn nx-btn-sm" onclick={copyCode}>{copied ? "KOPIERT ✓" : "CODE KOPIEREN"}</button>
        <span class="dot {presence.connected ? 'on' : ''}" aria-hidden="true"></span>
        <span>{presence.connected ? `Online als „${presence.name}“` : "Verbinde …"}</span>
      </div>
      <p class="nx-hint">Wer deinen Code in seine Liste einträgt, sieht, ob du online bist – aber nur, wenn er selbst auch sichtbar ist. Trag umgekehrt auch den Code deiner Freunde ein.</p>
    </div>

    <h3 class="nx-h3">Meine Freunde {#if presence.friends.length}<small>({onlineCount} online)</small>{/if}</h3>
    {#if !presence.friends.length}
      <p>Noch niemand eingetragen. Trage unten den Code eines Freundes ein.</p>
    {:else}
      <ul class="friends">
        {#each presence.friends as f (f.code)}
          {@const live = presence.live[f.code]}
          <li>
            <span class="dot {live ? 'on' : ''}" aria-hidden="true"></span>
            <span class="who">
              <b>{friendLabel(f, live)}</b>
              <small>{live ? "online" : "nicht sichtbar"}{#if live && f.name && live.name && live.name !== f.name} · nennt sich „{live.name}“{/if}</small>
            </span>
            {#if status(f.code)}<small class="st">{status(f.code)}</small>{/if}
            {#if live && canInvite}
              <button type="button" class="nx-btn nx-btn-sm nx-bg-blue" onclick={() => presence.invite(f.code)}>EINLADEN</button>
            {/if}
            <button type="button" class="nx-btn nx-btn-sm" aria-label="{friendLabel(f, live)} entfernen" onclick={() => presence.remove(f.code)}>✕</button>
          </li>
        {/each}
      </ul>
      {#if noneVisible}<p class="nx-hint">Gerade ist keiner deiner Freunde sichtbar. Sie sehen dich nur, wenn sie deinen Code ebenfalls eingetragen haben.</p>{/if}
    {/if}

    <form class="add" onsubmit={addFriend}>
      <h3 class="nx-h3">Freund hinzufügen</h3>
      <div class="two">
        <div class="nx-field">
          <label class="nx-label" for="fr-code">Code des Freundes</label>
          <input id="fr-code" class="nx-input mono" bind:value={addCode} placeholder="ABCDE-FGHJK" autocomplete="off" autocapitalize="characters" spellcheck="false" />
        </div>
        <div class="nx-field">
          <label class="nx-label" for="fr-name">Name (optional)</label>
          <input id="fr-name" class="nx-input" maxlength={NAME_MAX} bind:value={addName} placeholder="nur für dich sichtbar" autocomplete="off" />
        </div>
      </div>
      <button type="submit" class="nx-btn nx-btn-sm nx-bg-yellow" disabled={!addCode.trim()}>HINZUFÜGEN</button>
    </form>

    <h3 class="nx-h3">Wieder zusammen spielen</h3>
    <p class="nx-hint">
      {#if presence.table}
        Du sitzt an Tisch <b>{presence.table.code}</b>. Freunde, die online sind, kannst du oben direkt einladen. Sie bekommen einen Hinweis mit Link
        (<span class="mono">{inviteLink(window.location.origin, presence.table.code).replace(/^https?:\/\//, "")}</span>).
      {:else}
        Lege einen Tisch an oder tritt einem bei – dann kannst du Freunde, die online sind, mit einem Klick einladen.
      {/if}
    </p>

    <div class="row end">
      <button type="button" class="nx-btn nx-btn-sm" onclick={() => presence.disable()}>ONLINE-STATUS AUSSCHALTEN</button>
      {#if confirmForget}
        <button type="button" class="nx-btn nx-btn-sm nx-bg-coral" onclick={() => { presence.forget(); confirmForget = false; aliasInput = ""; consent = false; }}>JA, ALLES LÖSCHEN</button>
        <button type="button" class="nx-btn nx-btn-sm" onclick={() => (confirmForget = false)}>ABBRECHEN</button>
      {:else}
        <button type="button" class="nx-btn nx-btn-sm" onclick={() => (confirmForget = true)}>CODE &amp; LISTE LÖSCHEN</button>
      {/if}
    </div>
    <p class="nx-hint">Ausschalten: Du bist sofort unsichtbar. Löschen: Code, Name und Liste werden aus diesem Browser entfernt (ein neuer Code entsteht beim nächsten Einschalten).</p>
  {/if}
</Dialog>

<style>
  .check { display: flex; gap: 10px; align-items: flex-start; margin: 4px 0 16px; font-size: 0.92rem; }
  .check input { width: 20px; height: 20px; margin-top: 3px; flex: none; accent-color: #000; }
  .me { padding: 14px; margin: 8px 0 0; background: var(--nb-yellow); }
  .lab { margin: 0; font-weight: 700; font-size: 0.85rem; }
  .code { font-family: var(--font-mono); font-weight: 700; font-size: clamp(1.4rem, 6vw, 2rem); letter-spacing: 0.06em; margin: 4px 0 8px; overflow-wrap: anywhere; }
  .row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .row.end { margin-top: 18px; }
  .dot { width: 12px; height: 12px; border-radius: 50%; border: 2px solid #000; background: #fff; flex: none; }
  .dot.on { background: #1fa34a; }
  h3 { margin: 20px 0 6px; }
  h3 small { font-weight: 400; }
  .friends { list-style: none; margin: 8px 0; padding: 0; display: grid; gap: 8px; }
  .friends li { display: flex; align-items: center; gap: 10px; border: 3px solid #000; background: #fff; padding: 6px 8px; flex-wrap: wrap; }
  .who { display: flex; flex-direction: column; flex: 1; min-width: 120px; line-height: 1.25; overflow-wrap: anywhere; }
  .who small, .st { color: #444; }
  .two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .mono { font-family: var(--font-mono); letter-spacing: 0.05em; text-transform: uppercase; }
  .hint .mono, p .mono { text-transform: none; }
  @media (max-width: 520px) { .two { grid-template-columns: 1fr; gap: 0; } }
</style>
