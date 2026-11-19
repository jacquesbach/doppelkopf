// Deutsche Beschriftungen für Spielarten, Parteien, Ansagen und Wertungsposten.
export const SOLO_ORDER = [
  "solo_clubs", "solo_spades", "solo_hearts", "solo_diamonds",
  "solo_queens", "solo_jacks", "solo_aces",
];

export const SOLO_LABELS = {
  solo_clubs: "Kreuz-Solo",
  solo_spades: "Pik-Solo",
  solo_hearts: "Herz-Solo",
  solo_diamonds: "Karo-Solo",
  solo_queens: "Damen-Solo",
  solo_jacks: "Buben-Solo",
  solo_aces: "Fleischloser",
};

export const SOLO_SUIT = {
  solo_clubs: "♣", solo_spades: "♠", solo_hearts: "♥", solo_diamonds: "♦",
};

export const KIND_LABELS = {
  normal: "Normalspiel",
  pflichtsolo: "Pflichtsolo",
  pflichtsolo_forced: "Vorgeführtes Pflichtsolo",
  lustsolo: "Lustsolo",
  wedding: "Hochzeit",
  silent_wedding: "Stille Hochzeit",
  poverty: "Armut",
};

export function gameTypeLabel(type) {
  return type === "normal" ? "Normalspiel" : SOLO_LABELS[type] ?? String(type ?? "");
}

export function kindLabel(kind) {
  return KIND_LABELS[kind] ?? String(kind ?? "");
}

export function partyLabel(party) {
  return party === "re" ? "Re" : party === "kontra" ? "Kontra" : "";
}

const LEVEL_TEXT = ["", "keine 90", "keine 60", "keine 30", "schwarz"];

/** level 0 = Re/Kontra, 1–4 = Absagen. */
export function announceLabel(level, party) {
  if (level === 0) return partyLabel(party) || "Re/Kontra";
  return LEVEL_TEXT[level] ?? `Stufe ${level}`;
}

const ITEM_BASE = {
  win: "Gewonnen",
  under_90: "Unter 90",
  under_60: "Unter 60",
  under_30: "Unter 30",
  black: "Schwarz",
  doppelkopf: "Doppelkopf (40+ Augen)",
  fox_caught: "Fuchs gefangen",
  charlie_last_trick: "Karlchen im letzten Stich",
  charlie_caught: "Karlchen gefangen",
  beat_re: "Gegen die Alten",
};
const CODE_TEXT = { announce: "", no_90: "keine 90", no_60: "keine 60", no_30: "keine 30", black: "schwarz" };

export function scoreItemLabel(code) {
  if (ITEM_BASE[code]) return ITEM_BASE[code];
  let m = /^announced_(re|kontra)$/.exec(code);
  if (m) return `${partyLabel(m[1])} angesagt`;
  m = /^called_(re|kontra)_(no_90|no_60|no_30|black)$/.exec(code);
  if (m) return `${partyLabel(m[1])}: ${CODE_TEXT[m[2]]} angesagt`;
  m = /^beat_(no_90|no_60|no_30|black)$/.exec(code);
  if (m) return `Absage „${CODE_TEXT[m[1]]}“ geschlagen`;
  return code;
}

const BOCK_TEXT = {
  heart_trick: "Herzstich",
  zero_game: "Nullspiel",
  points_120: "120 : 120 Augen",
};

export function bockTriggerLabel(code) {
  return BOCK_TEXT[code] ?? code;
}

// Kurzbezeichnungen der Regeloptionen (Etiketten in der Lobby); Vollständige Texte liefert /rule-schema.
export const RULE_TAGS = {
  dulle: ["Mit Dullen", "Ohne Dullen"],
  karlchen: ["Karlchen extra", "Ohne Karlchen"],
  fuchsjagd: ["Fuchsjagd", "Ohne Fuchsjagd"],
  mandatory_announcements: ["Pflichtansagen"],
  solo_leads: ["Solo spielt aus"],
  karlchen_caught: ["Karlchen fangen"],
  schweinchen: ["Schweinchen"],
  poverty: ["Armut"],
  bock_heart_trick: ["Bock bei Herzstich"],
  bock_zero_game: ["Bock bei Nullspiel"],
  bock_120: ["Bock bei 120 Augen"],
  second_dulle_wins: ["Zweite Dulle sticht"],
  second_dulle_wins_except_last: ["… außer im letzten Stich"],
};

/** Auswahl des Hosts: nach wie viel Inaktivität ein Bot für einen Spieler übernimmt (Sekunden; 0 = nie). */
export const TAKEOVER_OPTIONS = [
  [0, "Nie"],
  [60, "1 Minute"],
  [120, "2 Minuten"],
  [180, "3 Minuten"],
  [300, "5 Minuten"],
  [600, "10 Minuten"],
  [1800, "30 Minuten"],
];

export function takeoverLabel(seconds) {
  return TAKEOVER_OPTIONS.find(([s]) => s === seconds)?.[1] ?? `${seconds} s`;
}
