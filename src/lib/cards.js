// Karten-Hilfen. Das Backend liefert Karten als {rank, suit, copy}; die Kennung ist "rank-suit-copy".
export const SUITS = {
  "♣": { key: "clubs", name: "Kreuz" },
  "♠": { key: "spades", name: "Pik" },
  "♥": { key: "hearts", name: "Herz" },
  "♦": { key: "diamonds", name: "Karo" },
};

// Anzeige: Q → D (Dame), J → B (Bube)
export const RANK_LABELS = { A: "A", 10: "10", K: "K", Q: "D", J: "B", 9: "9" };
const RANK_NAMES = { A: "Ass", 10: "Zehn", K: "König", Q: "Dame", J: "Bube", 9: "Neun" };

export function cardId(card) {
  return `${card.rank}-${card.suit}-${card.copy}`;
}

export function parseCardId(id) {
  const [rank, suit, copy] = String(id).split("-");
  if (!rank || !SUITS[suit]) return null;
  return { rank, suit, copy: Number(copy) || 0 };
}

export function rankLabel(rank) {
  return RANK_LABELS[rank] ?? String(rank);
}

export function suitKey(suit) {
  return SUITS[suit]?.key ?? "clubs";
}

export function cardName(card) {
  return `${SUITS[card.suit]?.name ?? card.suit} ${RANK_NAMES[card.rank] ?? card.rank}`;
}
