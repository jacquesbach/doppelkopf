// Grenzen und Sortierung der Verbesserungsvorschläge (spiegelt backend/app/community/suggestions.py).
export const TITLE_MIN = 4;
export const TITLE_MAX = 80;
export const DESC_MIN = 10;
export const DESC_MAX = 500;

// Beliebteste zuerst; bei Gleichstand der ältere Vorschlag vorn.
export function rankSuggestions(items) {
  return [...items].sort(
    (a, b) => b.votes - a.votes || a.createdAt - b.createdAt || a.id - b.id,
  );
}

// Ergebnis eines Daumens in die Liste übernehmen: { votes, voted } vom Server.
export function applyVote(items, id, result) {
  return rankSuggestions(items.map((s) => (s.id === id ? { ...s, votes: result.votes, voted: result.voted } : s)));
}

export function trimmedLength(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim().length;
}

export function formProblem(title, description) {
  const t = trimmedLength(title);
  const d = trimmedLength(description);
  if (t < TITLE_MIN) return `Der Titel braucht mindestens ${TITLE_MIN} Zeichen.`;
  if (d < DESC_MIN) return `Die Beschreibung braucht mindestens ${DESC_MIN} Zeichen.`;
  return null;
}
