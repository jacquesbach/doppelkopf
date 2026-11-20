<script>
  import { onMount } from "svelte";
  import { api, sessions } from "../lib/services.js";
  import { navigate } from "../lib/nav.svelte.js";
  import PageShell from "../components/ui/PageShell.svelte";
  import PublicTables from "../components/ui/PublicTables.svelte";

  let { code: initialCode = "" } = $props();

  let code = $state(initialCode);
  let name = $state(sessions.lastName());
  let password = $state("");
  let seatCode = $state("");
  let role = $state("player");
  let room = $state(null); // Raum-Vorschau (zeigt, ob ein Passwort nötig ist)
  let error = $state("");
  let busy = $state(false);

  onMount(() => {
    // Wer schon am Tisch sitzt, geht direkt dorthin.
    if (initialCode && sessions.get(initialCode)) navigate(`/tisch/${initialCode}`, { replace: true });
    else if (initialCode) lookup();
  });

  async function lookup() {
    room = null;
    const value = code.trim().toUpperCase();
    if (value.length < 3) return;
    try {
      room = (await api.getRoom(value)).room;
      error = "";
    } catch (e) {
      error = e.status === 404 ? "Diesen Tisch gibt es nicht (mehr)." : e.message;
    }
  }

  const claimable = $derived(
    room && room.status !== "waiting" ? room.players.filter((p) => p.role === "player" && !p.isBot) : [],
  );

  async function reclaim(playerName) {
    error = "";
    busy = true;
    try {
      const value = code.trim().toUpperCase();
      const res = await api.rejoin(value, { name: playerName, password, seatCode });
      sessions.rememberName(playerName);
      sessions.set(value, { token: res.token, memberId: res.memberId });
      navigate(`/tisch/${value}`);
    } catch (e) {
      error = e.message;
      busy = false;
    }
  }

  async function submit(event) {
    event.preventDefault();
    error = "";
    const value = code.trim().toUpperCase();
    if (!value) return (error = "Bitte gib den Tisch-Code ein.");
    if (!name.trim()) return (error = "Bitte gib deinen Spielernamen ein.");
    busy = true;
    try {
      const res = await api.joinRoom(value, { name: name.trim(), role, password });
      sessions.rememberName(name.trim());
      sessions.set(value, { token: res.token, memberId: res.memberId });
      navigate(`/tisch/${value}`);
    } catch (e) {
      error = e.message;
      busy = false;
    }
  }
</script>

<PageShell narrow>
  <span class="nx-badge nx-bg-blue">EINLADUNG</span>
  <h1 class="nx-title">Tisch beitreten</h1>

  <form class="nx-box" onsubmit={submit} novalidate>
    {#if error}<p class="nx-error" role="alert">{error}</p>{/if}

    <div class="nx-field">
      <label class="nx-label" for="j-code">Tisch-Code</label>
      <input
        id="j-code"
        class="nx-input"
        style="font-family: var(--font-mono); text-transform: uppercase;"
        maxlength="12"
        autocomplete="off"
        bind:value={code}
        onblur={lookup}
      />
    </div>
    <div class="nx-field">
      <label class="nx-label" for="j-name">Spielername</label>
      <input id="j-name" class="nx-input" maxlength="32" autocomplete="nickname" bind:value={name} />
    </div>
    {#if room?.hasPassword}
      <div class="nx-field">
        <label class="nx-label" for="j-pass">Passwort</label>
        <input id="j-pass" class="nx-input" type="password" autocomplete="off" bind:value={password} />
      </div>
    {/if}
    <fieldset style="border:0;padding:0;margin:0 0 18px;">
      <legend class="nx-label" style="padding:0;margin-bottom:6px;">Ich möchte</legend>
      <div class="nx-btn-row">
        <label class="nx-btn nx-btn-sm" style="background:{role === 'player' ? 'var(--nb-yellow)' : 'var(--nb-bg)'}">
          <input class="nx-sr" type="radio" name="role" value="player" bind:group={role} /> MITSPIELEN
        </label>
        <label class="nx-btn nx-btn-sm" style="background:{role === 'spectator' ? 'var(--nb-yellow)' : 'var(--nb-bg)'}">
          <input class="nx-sr" type="radio" name="role" value="spectator" bind:group={role} /> ZUSCHAUEN
        </label>
      </div>
    </fieldset>

    <button type="submit" class="nx-btn nx-btn-lg" disabled={busy}>BEITRETEN &rarr;</button>
  </form>

  <h2 class="nx-h2" style="margin-top:32px;">Diese Tische suchen Mitspieler</h2>
  <PublicTables compact />

  {#if claimable.length}
    <div class="nx-box nx-bg-lavender">
      <h2 class="nx-h2">Platz zurückholen</h2>
      <p class="nx-hint" style="color:#000;">
        Die Runde läuft bereits. Gehörte dir ein Platz (z. B. auf einem anderen Gerät), holst du ihn mit deinem
        <strong>Platz-Code</strong> zurück. Du findest ihn am Tisch im Menü unter „PLATZ-CODE“. Hast du ihn verloren, kann der
        Host ihn dir nennen. Das Passwort des Tisches oben gilt auch hier.
      </p>
      <div class="nx-field">
        <label class="nx-label" for="j-seat">Platz-Code</label>
        <input id="j-seat" class="nx-input" style="font-family: var(--font-mono); text-transform: uppercase;" maxlength="12" autocomplete="off" placeholder="ABCD-EFGH" bind:value={seatCode} />
      </div>
      <div class="nx-btn-row">
        {#each claimable as p (p.id)}
          <button type="button" class="nx-btn nx-btn-sm nx-bg-white" disabled={busy || p.connected || !seatCode.trim()} onclick={() => reclaim(p.name)}>
            Ich bin {p.name}{p.connected ? " (verbunden)" : ""}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</PageShell>
