<script>
  import { link, navigate } from "../../lib/nav.svelte.js";
  import { presence } from "../../lib/presence.svelte.js";
  import FriendsDialog from "./FriendsDialog.svelte";

  // Einladungen von Freunden (kurze Hinweise unten) und der Dialog. Erscheint nur, wenn man den Online-Status selbst eingeschaltet hat.
  function accept(invite) {
    presence.dismissInvite(invite.id);
    navigate(`/beitreten/${invite.table}`);
  }
</script>

{#if presence.invites.length}
  <div class="stack" aria-live="polite">
    {#each presence.invites as i (i.id)}
      <div class="invite" role="status">
        <p><b>{i.from}</b> lädt dich an Tisch <span class="mono">{i.table}</span> ein{#if i.hasPassword} (mit Passwort){/if}.</p>
        <div class="row">
          <button type="button" class="nx-btn nx-btn-sm nx-bg-green" onclick={() => accept(i)}>BEITRETEN</button>
          <button type="button" class="nx-btn nx-btn-sm" onclick={() => presence.dismissInvite(i.id)}>NICHT JETZT</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

{#if presence.dialogOpen}
  <FriendsDialog onClose={() => presence.close()} />
{/if}

<style>
  .stack { position: fixed; left: 12px; right: 12px; top: 12px; z-index: 60; display: grid; gap: 10px; justify-items: center; pointer-events: none; }
  .invite { pointer-events: auto; width: min(420px, 100%); border: 3px solid #000; box-shadow: 5px 5px 0 0 #000; background: var(--nb-blue); padding: 10px 12px; color: #000; }
  .invite p { margin: 0 0 8px; font-weight: 600; }
  .mono { font-family: var(--font-mono); font-weight: 700; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
