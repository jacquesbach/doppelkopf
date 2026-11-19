<script>
  import { onMount } from "svelte";
  import { api } from "../../lib/services.js";
  import Dialog from "./Dialog.svelte";
  import RuleForm from "./RuleForm.svelte";

  let { settings, editable = false, onSave = async () => true, onClose } = $props();

  let schema = $state(null);
  let draft = $state({ ...settings });
  let error = $state("");
  let saving = $state(false);

  onMount(async () => {
    try {
      schema = (await api.ruleSchema()).options;
    } catch (e) {
      error = e.message;
    }
  });

  async function save() {
    saving = true;
    const ok = await onSave(draft);
    saving = false;
    if (ok) onClose();
  }
</script>

<Dialog title={editable ? "Regeln ändern" : "Regelwerk"} {onClose} wide>
  {#if error}<p class="nx-error" role="alert">{error}</p>{/if}
  {#if schema}
    <p class="nx-hint" style="margin-top:0;">
      Grundlage sind die DDV-Turnierspielregeln. Abweichende Hausregeln gelten für den ganzen Tisch.
    </p>
    <RuleForm {schema} bind:settings={draft} disabled={!editable} />
    {#if editable}
      <div class="nx-btn-row">
        <button type="button" class="nx-btn" onclick={save} disabled={saving}>SPEICHERN</button>
        <button type="button" class="nx-btn nx-bg-white" onclick={onClose}>ABBRECHEN</button>
      </div>
    {/if}
  {:else if !error}
    <p>Lade Regeln …</p>
  {/if}
</Dialog>
