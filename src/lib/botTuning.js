// Bot-Einstellungen im Betreiber-Backend: reine Hilfsfunktionen (ohne DOM), damit sie sich testen lassen.
// Die Liste der Einstellungen (Texte, Grenzen, Standard) kommt vom Server (`GET /api/admin/bots`); hier steht keine zweite Kopie.

/** Antwort des Servers absichern: fehlende Teile werden leer, Unbrauchbares verworfen. */
export function normalizeBots(raw) {
  const data = raw && typeof raw === "object" ? raw : {};
  const list = (x, idKey) => (Array.isArray(x) ? x.filter((i) => i && typeof i === "object" && typeof i[idKey] === "string") : []);
  const plain = (x) => (x && typeof x === "object" && !Array.isArray(x) ? { ...x } : {});
  return { values: plain(data.values), defaults: plain(data.defaults), groups: list(data.groups, "id"), items: list(data.items, "key") };
}

/** Einstellungen je Gruppe in der Reihenfolge des Servers; leere Gruppen entfallen. */
export function groupedItems(schema) {
  return schema.groups
    .map((group) => ({ group, items: schema.items.filter((i) => i.group === group.id) }))
    .filter((g) => g.items.length > 0);
}

/** Ist eine Einstellung wirksam? Sie haengt ggf. von einem Hauptschalter ab ("needs": {key, value}). */
export function isActive(item, values) {
  return !item.needs || values[item.needs.key] === item.needs.value;
}

export function isDefault(key, values, defaults) {
  return values[key] === defaults[key];
}

/** Namen der Einstellungen, die vom gespeicherten Stand abweichen. */
export function changedKeys(values, saved) {
  return Object.keys(values).filter((k) => values[k] !== saved[k]);
}

/** Nur die geaenderten Werte, so wie der Server sie als Teilmenge erwartet. */
export function updatePayload(values, saved) {
  return { values: Object.fromEntries(changedKeys(values, saved).map((k) => [k, values[k]])) };
}

/** Meldung zu einem Wert (leer = in Ordnung): dieselben Grenzen wie auf dem Server, damit der Betreiber nicht erst nach dem Speichern erfaehrt, was nicht geht. */
export function problem(item, value) {
  if (item.kind !== "number") return "";
  if (typeof value !== "number" || !Number.isFinite(value)) return `„${item.label}“ muss eine Zahl sein.`;
  if (value < item.min || value > item.max) return `„${item.label}“ muss zwischen ${item.min} und ${item.max} ${item.unit} liegen.`;
  return "";
}

/** Alle Probleme des Formulars, einschliesslich der Regel „Absage-Schwelle nicht unter Re/Kontra-Schwelle“. */
export function problems(schema, values) {
  const out = [];
  for (const item of schema.items) {
    const msg = problem(item, values[item.key]);
    if (msg) out.push(msg);
  }
  if (values.announce_p1 < values.announce_p0) out.push("Die Schwelle für Absagen darf nicht unter der Schwelle für Re/Kontra liegen.");
  return out;
}

/** Kurzer Text fuer den Wert (fuer die Anzeige „Standard: …“). */
export function valueText(item, value) {
  if (item.kind === "bool") return value ? "an" : "aus";
  if (item.kind === "choice") return item.options.find((o) => o.value === value)?.label ?? String(value);
  return `${value} ${item.unit}`;
}
