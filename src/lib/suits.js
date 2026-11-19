// Formen der vier Kartenfarben (24×24-Raster). `ink: "black" | "red"` bestimmt die Kartenfarbe.
export const SUIT_SHAPES = {
  "♣": {
    ink: "black",
    parts: [
      { circle: [12, 7, 4.6] },
      { circle: [6.6, 14.2, 4.6] },
      { circle: [17.4, 14.2, 4.6] },
      { path: "M12 11L9.6 22H14.4Z" },
    ],
  },
  "♠": {
    ink: "black",
    parts: [
      {
        path: "M12 1.5L20.6 10.4C22.9 12.8 22.9 16.6 20.6 19C18.4 21.2 15 21.2 12.7 19.2C13 21 13.6 22 14.6 22.8H9.4C10.4 22 11 21 11.3 19.2C9 21.2 5.6 21.2 3.4 19C1.1 16.6 1.1 12.8 3.4 10.4L12 1.5Z",
      },
    ],
  },
  "♥": {
    ink: "red",
    parts: [
      {
        path: "M12 22.5L3.5 13.2C1.2 10.8 1.2 7 3.5 4.6C5.8 2.2 9.5 2.2 11.8 4.6L12 4.8L12.2 4.6C14.5 2.2 18.2 2.2 20.5 4.6C22.8 7 22.8 10.8 20.5 13.2L12 22.5Z",
      },
    ],
  },
  "♦": {
    ink: "red",
    parts: [{ path: "M12 1L20.5 12L12 23L3.5 12Z" }],
  },
};

export const INK = { black: "#16161d", red: "#d62828" };
