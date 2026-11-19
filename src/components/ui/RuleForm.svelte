<script>
  // Regel-Schalter aus /rule-schema. Abhängige Optionen (`requires`) sind gesperrt, solange die Voraussetzung fehlt.
  let { schema, settings = $bindable(), disabled = false } = $props();

  const GROUPS = [
    { id: "popular", title: "Beliebte Regeln" },
    { id: "pub", title: "Kneipenregeln" },
  ];

  const blocked = (spec) => !!spec.requires && !settings[spec.requires];

  function toggle(spec, checked) {
    const next = { ...settings, [spec.id]: checked };
    let changed = true;
    while (changed) {
      changed = false; // Abhängige Optionen mit ausschalten
      for (const s of schema) {
        if (s.requires && !next[s.requires] && next[s.id]) {
          next[s.id] = false;
          changed = true;
        }
      }
    }
    settings = next;
  }
</script>

{#each GROUPS as group (group.id)}
  <fieldset class="nx-rule-group" style="border:0;padding:0;margin:0 0 22px;">
    <legend class="nx-h2" style="padding:0;">{group.title}</legend>
    {#each schema.filter((s) => s.group === group.id) as spec (spec.id)}
      {@const isBlocked = blocked(spec)}
      <label class="nx-rule" class:is-disabled={disabled || isBlocked}>
        <input
          type="checkbox"
          checked={!!settings[spec.id]}
          disabled={disabled || isBlocked}
          onchange={(event) => toggle(spec, event.currentTarget.checked)}
        />
        <span class="nx-check" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 16 16">
            <path d="M2.5 8.5L6.5 12.5L13.5 3.5" fill="none" stroke="#000" stroke-width="3" />
          </svg>
        </span>
        <span>
          <span class="nx-h3" style="display:block;">
            {spec.label}
            {#if spec.default}<span class="nx-badge nx-bg-green" style="margin-left:6px;">DDV-Standard</span>{/if}
          </span>
          <span class="nx-hint">{spec.description}</span>
          {#if isBlocked}<span class="nx-hint" style="display:block;">Setzt „{schema.find((s) => s.id === spec.requires)?.label}“ voraus.</span>{/if}
        </span>
      </label>
    {/each}
  </fieldset>
{/each}
