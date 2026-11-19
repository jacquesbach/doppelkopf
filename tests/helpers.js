// Kleine Fabrik für Server-Sichten in den Tests.
export function makeView({ mySeat = 0, game = {}, table = {} } = {}) {
  return {
    version: 1,
    table: {
      seats: ["Anna", "Ben", "Cleo", "Dirk"].map((name, seat) => ({ seat, name, memberId: seat + 1, isBot: false })),
      mySeat,
      gameNumber: 3,
      finished: false,
      round: { dealer: 1, totals: [0, 0, 0, 0], bockRemaining: 0, results: [] },
      ...table,
    },
    game: {
      phase: "playing",
      dealer: 1,
      turn: 0,
      querySeat: null,
      baptismSeat: null,
      resolution: { stage: null, seat: null },
      mandatoryAnnouncementSeat: null,
      currentTrick: [],
      announcements: [],
      legalActions: [],
      hand: [],
      myParty: "re",
      kind: "normal",
      gameType: "normal",
      ...game,
    },
  };
}
