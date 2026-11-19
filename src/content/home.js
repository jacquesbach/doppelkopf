// Inhalt der Startseite, soweit er auch als statisches HTML (Suchmaschinen, Besucher ohne JavaScript) ausgeliefert wird.
// Die FAQ erscheint in Landing.svelte und wird beim Build von scripts/seo-build.mjs in dieselbe Seite geschrieben.

export const HOME_H1 = "Doppelkopf online spielen";
export const HOME_LEAD =
  "DOPPELKOPF.CC ist Doppelkopf im Browser: nach den DDV-Turnierregeln, mit zuschaltbaren Hausregeln, privaten Tischen per Einladungslink und Computer-Mitspielern. " +
  "Ohne Konto, ohne Werbung, ohne Tracking.";

export const HOME_FEATURES = [
  "DDV-Turnierregeln, mit oder ohne Neunen",
  "Hausregeln pro Tisch: Schweinchen, Armut, Bockrunden, zweite Dulle und mehr",
  "Privater Stammtisch per Link oder Sofort-Partie gegen Bots",
  "Stich-Protokoll und komplette Abrechnung nach jedem Spiel",
];

export const FAQ_TITLE = "Häufige Fragen";
export const FAQ = [
  {
    q: "Ist DOPPELKOPF.CC kostenlos?",
    a: "Ja. Das Spielen ist kostenlos und werbefrei. Es gibt weder Bezahlfunktionen noch Tracking.",
  },
  {
    q: "Brauche ich ein Konto?",
    a: "Nein. Du gibst nur einen Spielnamen ein, eröffnest einen Tisch und schickst den Einladungslink an deine Mitspieler.",
  },
  {
    q: "Kann ich auch allein Doppelkopf spielen?",
    a: "Ja. Freie Plätze übernehmen Bots, die sich an die Regeln halten. Du kannst eine Partie gegen den Computer sofort starten.",
  },
  {
    q: "Welche Regeln gelten?",
    a: "Standard sind die DDV-Turnierspielregeln. Vor der ersten Runde stellt jeder Tisch ein, ob mit oder ohne Neunen gespielt wird und welche Hausregeln gelten.",
  },
  {
    q: "Was passiert, wenn jemand die Verbindung verliert?",
    a: "Wer am Zug ist und nicht reagiert, wird nach einer einstellbaren Wartezeit durch einen Bot ersetzt. Kommt die Person zurück, übernimmt sie ihren Platz wieder.",
  },
  {
    q: "Läuft das Spiel auf dem Smartphone?",
    a: "Ja. Die Seite ist für Smartphone, Tablet und Computer gestaltet und braucht nur einen aktuellen Browser.",
  },
];
