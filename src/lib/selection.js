// Kartenauswahl am Handy: Der erste Tipp wählt eine Karte aus (sie ragt aus dem Fächer),
// der zweite Tipp auf dieselbe Karte spielt sie aus. Mit der Maus genügt ein Klick.
// Reine Funktionen, damit das Verhalten ohne Browser getestet werden kann.

/** Touch-Gerät ohne Hover (Handy, Tablet)? */
export function isTouchPrimary(win = globalThis) {
  try {
    return !!win.matchMedia?.("(hover: none) and (pointer: coarse)")?.matches;
  } catch {
    return false;
  }
}

/**
 * Ergebnis eines Tipps auf Karte `id`.
 * @returns {{ selected: string|null, play: string|null }} neue Auswahl und die zu spielende Karte (oder null)
 */
export function tapCard(selected, id, twoStep) {
  if (!twoStep) return { selected: null, play: id };
  if (selected === id) return { selected: null, play: id };
  return { selected: id, play: null };
}

/** Auswahl nur behalten, solange die Karte noch spielbar ist (Zug vorbei, Karte weg, …). */
export function keepSelection(selected, playable) {
  return selected && playable?.has(selected) ? selected : null;
}

// Armut: genau `count` Karten markieren (abgeben bzw. zurückgeben). Eine weitere Karte verdrängt die älteste Markierung,
// damit man am Handy ohne Umweg umentscheiden kann.

/** Markierung einer Karte umschalten; bei mehr als `count` Karten fällt die älteste heraus. */
export function togglePick(picked, id, count) {
  if (picked.includes(id)) return picked.filter((x) => x !== id);
  const next = [...picked, id];
  return next.length > count ? next.slice(next.length - count) : next;
}

/** Nur Markierungen behalten, die noch zur Auswahl stehen (Hand hat sich geändert). */
export function prunePick(picked, allowed) {
  return allowed ? picked.filter((id) => allowed.has(id)) : [];
}

/** Sind genau `count` Karten markiert? */
export function pickReady(picked, count) {
  return picked.length === count;
}
