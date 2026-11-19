// Kurze Hinweise auf Ansagen und besondere Spielereignisse. Der Server liefert `game.events` (öffentliche Ereignisse
// mit fortlaufender `id`); hier wird nur entschieden, welche neu sind, und wie sie heißen.
import { announceLabel, gameTypeLabel, partyLabel } from "./labels.js";

const name = (view, seat) => view?.table?.seats?.[seat]?.name ?? `Platz ${Number(seat) + 1}`;

/**
 * Welche Ereignisse sind seit der vorigen Sicht neu? Beim ersten Laden (keine vorige Sicht) gilt alles als bekannt –
 * wer die Seite öffnet oder zurückkehrt, bekommt keine alten Hinweise nachgereicht.
 */
export function newEvents(prev, next) {
  const events = next?.game?.events;
  if (!prev || !events?.length) return [];
  const sameGame = prev.table?.gameNumber === next.table?.gameNumber;
  if (!sameGame) return events;
  const lastId = Math.max(0, ...(prev.game?.events ?? []).map((e) => e.id));
  return events.filter((e) => e.id > lastId);
}

/** Text und Farbton eines Ereignisses; `null` für Unbekanntes. tone: yellow | coral | blue | green | lavender */
export function describeEvent(view, e) {
  const who = name(view, e.seat);
  switch (e.type) {
    case "reservation":
      return { title: "Vorbehalt", text: `${who} hat einen Vorbehalt.`, tone: "lavender" };
    case "solo":
      return { title: "Solo", text: `${who} spielt ${gameTypeLabel(e.gameType)}.`, tone: "lavender" };
    case "wedding":
      return { title: "Hochzeit", text: `${who} hat eine Hochzeit.`, tone: "lavender" };
    case "wedding_clarified":
      return e.solo
        ? { title: "Hochzeit", text: "Niemand hat gestochen – die Hochzeit wird zum Solo.", tone: "lavender" }
        : { title: "Hochzeit", text: `${name(view, e.partner)} ist der Partner von ${name(view, view.game.weddingSeat)}.`, tone: "lavender" };
    case "announce": {
      const label = announceLabel(e.level, e.party);
      return {
        title: e.level === 0 ? partyLabel(e.party) : "Absage",
        text: e.level === 0 ? `${who} sagt ${label} an.` : `${who} (${partyLabel(e.party)}) sagt „${label}“ an.`,
        tone: e.party === "re" ? "coral" : "blue",
      };
    }
    case "schweinchen":
      return { title: "Schweinchen", text: `${who} hat Schweinchen!`, tone: "yellow" };
    case "doppelkopf":
      return { title: "Doppelkopf", text: `${who} sticht mit ${e.points} Augen – Doppelkopf!`, tone: "green" };
    case "fox_caught":
      return { title: "Fuchs gefangen", text: `${who} fängt den Fuchs von ${name(view, e.victim)}.`, tone: "green" };
    case "charlie_last_trick":
      return { title: "Karlchen", text: `${who} macht mit Karlchen den letzten Stich.`, tone: "green" };
    default:
      return null;
  }
}

// --- Chat-Hinweis ---
export const SNIPPET_MAX = 70;

/** Kurzfassung einer Chatnachricht für den Hinweis: Leerraum geglättet, bei Überlänge mit „…“ gekürzt. */
export function snippet(text, max = SNIPPET_MAX) {
  const t = String(text ?? "").replace(/\s+/g, " ").trim();
  return t.length > max ? `${t.slice(0, max - 1).trimEnd()}…` : t;
}

/** Hinweis auf eine neue Chatnachricht; „Antworten“ öffnet den Chat. */
export function chatToast(message) {
  return {
    key: `chat-${message.id}`,
    kind: "chat",
    title: `Chat · ${message.name}`,
    text: snippet(message.text),
    tone: "blue",
    action: { label: "Antworten", kind: "chat" },
    ms: 8000,
  };
}

/** Wurde das Spiel mit der neuen Sicht gerade beendet (nicht: beim ersten Laden eines schon beendeten Spiels)? */
export function justFinished(prev, next) {
  return (
    !!prev &&
    !!next &&
    prev.table?.gameNumber === next.table?.gameNumber &&
    prev.game?.phase !== "finished" &&
    next.game?.phase === "finished"
  );
}
