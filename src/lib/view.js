// Reine Ableitungen aus der Server-Sicht (view). Der Server ist die Wahrheit: `legalActions` entscheidet,
// was die Oberfläche anbietet; hier wird nichts nachgerechnet.
import { cardId } from "./cards.js";
import { announceLabel, gameTypeLabel, kindLabel, partyLabel, RULE_TAGS, scoreItemLabel, bockTriggerLabel } from "./labels.js";

const PLACEMENTS = ["bottom", "left", "top", "right"];

export function relSeat(seat, mySeat) {
  return (((seat - (mySeat ?? 0)) % 4) + 4) % 4;
}

export function placementOf(seat, mySeat) {
  return PLACEMENTS[relSeat(seat, mySeat)];
}

export function seatName(view, seat) {
  return view?.table?.seats?.[seat]?.name ?? `Platz ${seat + 1}`;
}

export function legalAction(view, type) {
  return view?.game?.legalActions?.find((a) => a.type === type) ?? null;
}

/** Welcher modale Dialog ist für MICH gerade nötig? */
export function activeDialog(view) {
  for (const type of ["declare", "resolve", "baptize"]) {
    const action = legalAction(view, type);
    if (action) return { type, action };
  }
  return null;
}

/** Wessen Handlung wird gerade erwartet (Sitz) – null, wenn niemand (Spielende). */
export function actingSeat(view) {
  const g = view?.game;
  if (!g) return null;
  switch (g.phase) {
    case "reservation_query": return g.querySeat;
    case "reservation_resolution": return g.resolution?.seat ?? null;
    case "baptism": return g.baptismSeat;
    case "playing": return g.mandatoryAnnouncementSeat ?? g.turn;
    default: return null;
  }
}

export function isMyTurn(view) {
  const me = view?.table?.mySeat;
  return me != null && actingSeat(view) === me;
}

export function playableIds(view) {
  return new Set(legalAction(view, "play_card")?.cards ?? []);
}

/**
 * Was liegt auf dem Tisch? Der laufende Stich – oder, solange noch keine neue Karte liegt, der soeben beendete
 * Stich (mit Gewinner), damit man ihn in Ruhe ansehen kann.
 */
export function shownTrick(view) {
  const g = view?.game;
  if (!g) return { plays: [], complete: false, winnerSeat: null };
  if (g.currentTrick?.length) return { plays: g.currentTrick, complete: false, winnerSeat: null };
  if (g.lastTrick && (g.phase === "playing" || g.phase === "finished"))
    return { plays: g.lastTrick.plays, complete: true, winnerSeat: g.lastTrick.winnerSeat };
  return { plays: [], complete: false, winnerSeat: null };
}

/** Spiel gegen Bots: der Server wartet nach dem Stich auf „Nächster Stich“. */
export function isHolding(view) {
  return !!view?.table?.holding;
}

/** Läuft ein Countdown, nach dem ein Bot für einen inaktiven Spieler übernimmt? → {seat, remaining} oder null. */
export function takeoverWarning(view) {
  return view?.table?.takeoverWarning ?? null;
}

/** Hat der Countdown MICH im Visier (Dialog „Weiterspielen“)? */
export function isMyTakeoverWarning(view) {
  const w = takeoverWarning(view);
  return !!w && w.seat === view?.table?.mySeat;
}

/** Verbleibende Sekunden: Der Server meldet `remaining` zum Zeitpunkt `receivedAt` (ms); die Uhr läuft lokal weiter. */
export function countdownLeft(remaining, receivedAt, now) {
  return Math.max(0, remaining - (now - receivedAt) / 1000);
}

export function myAutoplay(view) {
  const me = view?.table?.mySeat;
  return me != null && !!view.table.seats[me]?.autoplay;
}

/** Ansage-Schaltflächen: [{level, label}] */
export function announceOptions(view) {
  const action = legalAction(view, "announce");
  if (!action) return [];
  const party = view.game.myParty;
  return action.levels.map((level) => ({ level, label: announceLabel(level, party) }));
}

/** Karten des laufenden Stichs nach Sitz. */
export function trickBySeat(view) {
  const bySeat = {};
  for (const play of view?.game?.currentTrick ?? []) bySeat[play.seat] = play.card;
  return bySeat;
}

/** Höchste Ansage je Sitz, z. B. {2: "Re", 3: "keine 90"}. */
export function announcementsBySeat(view) {
  const result = {};
  for (const entry of view?.game?.announcements ?? []) {
    const label = announceLabel(entry.level, entry.party);
    const prev = result[entry.seat];
    if (!prev || entry.level >= prev.level) result[entry.seat] = { level: entry.level, label, party: entry.party };
  }
  return Object.fromEntries(Object.entries(result).map(([seat, v]) => [seat, v.label]));
}

/** Kleine Marken am Sitz: Geber, Partei (nur wenn öffentlich/bekannt), Solo, Hochzeit, Schweinchen. */
export function seatBadges(view, seat) {
  const g = view?.game;
  const badges = [];
  if (!g) return badges;
  if (g.dealer === seat) badges.push("Geber");
  if (view.table.seats[seat]?.autoplay) badges.push("Bot übernimmt");
  const me = view.table.mySeat;
  if (g.phase === "finished" && g.parties) badges.push(partyLabel(g.parties[seat]));
  else if (seat === me && g.myParty) badges.push(partyLabel(g.myParty));
  if (g.phase === "playing" || g.phase === "finished") {
    if (g.soloSeat === seat) badges.push("Solo");
    if (g.weddingSeat === seat && g.kind === "wedding") badges.push("Hochzeit");
    if (g.weddingPartner === seat) badges.push("Partner");
  }
  if (g.schweinchenSeat === seat) badges.push("Schweinchen");
  return badges;
}

export function gameHeadline(view) {
  const g = view?.game;
  if (!g) return "";
  const nr = `Spiel ${view.table.gameNumber}`;
  if (g.phase === "playing" || g.phase === "finished") {
    const what = g.gameType && g.gameType !== "normal" ? gameTypeLabel(g.gameType) : kindLabel(g.kind);
    return `${nr} · ${what}`;
  }
  return nr;
}

export function statusText(view) {
  const g = view?.game;
  if (!g) return "";
  const seat = actingSeat(view);
  const me = view.table.mySeat;
  const who = seat == null ? "" : seat === me ? "Du bist" : `${seatName(view, seat)} ist`;
  const whoVerb = seat === me ? "Du" : seatName(view, seat);
  switch (g.phase) {
    case "reservation_query":
      return `${whoVerb} ${seat === me ? "musst" : "muss"} sich entscheiden: gesund oder Vorbehalt?`;
    case "reservation_resolution":
      return `${whoVerb} ${seat === me ? "entscheidest" : "entscheidet"} über das ${g.resolution?.stage === "pflichtsolo" ? "Pflichtsolo" : "Lustsolo"}.`;
    case "baptism":
      return `${whoVerb} ${seat === me ? "taufst" : "tauft"} den Vorbehalt.`;
    case "playing":
      if (view.table.holding) return "Stich beendet – weiter mit „Nächster Stich“.";
      if (g.mandatoryAnnouncementSeat != null)
        return `${whoVerb} ${seat === me ? "musst" : "muss"} Re oder Kontra ansagen.`;
      return `${who} am Zug.`;
    case "finished":
      return "Spiel beendet.";
    default:
      return "";
  }
}

/** Zwischenstand der Runde, absteigend; gleiche Punkte = gleicher Platz. */
export function roundRanking(view) {
  const totals = view?.table?.round?.totals ?? [];
  const rows = totals.map((points, seat) => ({ seat, name: seatName(view, seat), points }));
  rows.sort((a, b) => b.points - a.points || a.seat - b.seat);
  let rank = 0;
  return rows.map((row, i) => {
    if (i === 0 || row.points !== rows[i - 1].points) rank = i + 1;
    return { ...row, rank };
  });
}

/** Aufbereitetes Spielergebnis (nur wenn das Spiel beendet ist). */
/** Namen der Gewinner/Verlierer eines Spiels aus den Re-Sitzen (`seats` = Sitze der Re-Partei). */
export function partyNames(view, reSeats, winner) {
  if (!Array.isArray(reSeats) || !reSeats.length) return { re: [], kontra: [], winners: [] };
  const re = reSeats.map((s) => seatName(view, s));
  const kontra = [0, 1, 2, 3].filter((s) => !reSeats.includes(s)).map((s) => seatName(view, s));
  return { re, kontra, winners: winner === "re" ? re : winner === "kontra" ? kontra : [] };
}

export function resultSummary(view) {
  const g = view?.game;
  const score = g?.score;
  if (g?.phase !== "finished" || !score) return null;
  const items = (party) =>
    (score.items?.[party] ?? []).map((i) => ({ label: scoreItemLabel(i.code), points: i.points }));
  return {
    winner: score.winner,
    winnerLabel: score.winner ? partyLabel(score.winner) : "Keiner (unentschieden)",
    names: partyNames(view, g.reSeats, score.winner),
    points: score.points,
    net: score.net,
    multiplier: score.multiplier ?? 1,
    soloScoring: !!score.soloScoring,
    items: { re: items("re"), kontra: items("kontra") },
    seatDeltas: (score.seatDeltas ?? []).map((delta, seat) => ({ seat, name: seatName(view, seat), delta })),
    bockTriggers: (g.bockTriggers ?? []).map(bockTriggerLabel),
  };
}

/** Etiketten der Hausregeln für die Lobby. Standard-Regeln, die ausgeschaltet sind, werden als „Ohne …“ gezeigt. */
export function activeRuleLabels(settings) {
  if (!settings) return [];
  const tags = [settings.sharp_doppelkopf ? "Ohne Neuner" : "Mit Neuner"];
  for (const [key, [on, off]] of Object.entries(RULE_TAGS)) {
    if (settings[key]) tags.push(on);
    else if (off) tags.push(off);
  }
  return tags;
}

export { cardId };
