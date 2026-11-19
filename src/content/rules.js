// Inhalt der Seite /regeln. Eine Quelle für zwei Verwendungen:
//  - src/pages/Rules.svelte zeigt ihn im Browser an,
//  - scripts/seo-build.mjs schreibt ihn beim Build als statisches HTML (für Suchmaschinen und Besucher ohne JavaScript).
// Blocktypen: h2, h3, p, ul (items), ol (items). Nur reiner Text, kein HTML.
// Grundlage: DDV-Turnierspielregeln (Stand 21.02.2026), Umsetzung siehe docs/DDV_REGELMATRIX.md.

export const RULES_TITLE = "Doppelkopf-Regeln einfach erklärt";
export const RULES_LEAD =
  "Doppelkopf ist ein Stichspiel für vier Personen. Hier findest du die wichtigsten Regeln so, wie sie auf DOPPELKOPF.CC gelten: " +
  "Karten, Trümpfe, Ablauf, Ansagen und Zählung nach den DDV-Turnierregeln.";

export const RULES = [
  { type: "h2", text: "Das Spiel in Kürze" },
  {
    type: "p",
    text:
      "Gespielt wird zu viert mit 48 Karten: Ass, Zehn, König, Dame, Bube und Neun in Kreuz, Pik, Herz und Karo, jeweils doppelt. " +
      "Jede Person erhält 12 Karten. Im Normalspiel bilden die beiden Spieler mit einer Kreuz-Dame die Partei Re, die anderen beiden die Partei Kontra. " +
      "Wer wer ist, merken die Beteiligten erst im Spielverlauf. Beide Parteien kämpfen um die Augen der Karten.",
  },
  { type: "h2", text: "Kartenwerte (Augen)" },
  {
    type: "ul",
    items: ["Ass: 11 Augen", "Zehn: 10 Augen", "König: 4 Augen", "Dame: 3 Augen", "Bube: 2 Augen", "Neun: 0 Augen"],
  },
  {
    type: "p",
    text: "Alle Karten zusammen zählen 240 Augen. Re gewinnt mit mindestens 121 Augen, Kontra reichen 120.",
  },
  { type: "h2", text: "Trumpf im Normalspiel" },
  {
    type: "p",
    text: "Trumpf sind 26 der 48 Karten. Von der höchsten zur niedrigsten Karte gilt diese Reihenfolge:",
  },
  {
    type: "ol",
    items: [
      "Herz-Zehn (die „Dulle“, wenn mit Dullen gespielt wird)",
      "Die vier Damen: Kreuz, Pik, Herz, Karo (die Kreuz-Dame heißt „Alte“)",
      "Die vier Buben: Kreuz, Pik, Herz, Karo",
      "Karo-Ass, Karo-Zehn, Karo-König, Karo-Neun",
    ],
  },
  {
    type: "p",
    text: "Alle übrigen Karten sind Fehlfarben (Kreuz, Pik, Herz). Dort gilt die Reihenfolge Ass, Zehn, König, Neun.",
  },
  { type: "h2", text: "Spielablauf" },
  {
    type: "ul",
    items: [
      "Die Person links vom Geber spielt zum ersten Stich aus.",
      "Es herrscht Bedienpflicht: Trumpf wird mit Trumpf bedient, eine Fehlfarbe mit derselben Fehlfarbe.",
      "Wer nicht bedienen kann, spielt eine beliebige Karte, auch einen Trumpf.",
      "Die höchste Karte gewinnt den Stich. Liegen zwei gleiche Karten, gewinnt die zuerst gespielte.",
      "Wer den Stich gewinnt, spielt zum nächsten aus. Nach 12 Stichen ist das Spiel zu Ende.",
    ],
  },
  { type: "h2", text: "Vorbehalte, Solo und Hochzeit" },
  {
    type: "p",
    text:
      "Vor dem ersten Stich fragt der Tisch reihum, ob jemand einen Vorbehalt anmeldet. Mögliche Sonderspiele sind das Farbsolo (Kreuz, Pik, Herz oder Karo), " +
      "das Damensolo, das Bubensolo und der Fleischlose (ohne Trumpf). Wer beide Kreuz-Damen hält, kann eine Hochzeit ansagen: " +
      "Der Partner ist, wer als Erstes einen Stich gewinnt, ohne selbst die Hochzeit angesagt zu haben (spätestens im dritten Stich, sonst wird daraus ein Solo). Im Turnier gehört außerdem zu jeder Runde ein Pflichtsolo je Person.",
  },
  { type: "h2", text: "Ansagen" },
  {
    type: "p",
    text:
      "Mit „Re“ oder „Kontra“ sagt eine Partei an, dass sie gewinnen will. Die Ansage ist nur möglich, solange du noch mindestens 11 Handkarten hast, also bevor du deine zweite Karte spielst. " +
      "Danach können Absagen folgen: „keine 90“, „keine 60“, „keine 30“ und „schwarz“. Sie sind mit mindestens 10, 9, 8 und 7 Handkarten erlaubt " +
      "und erhöhen das Ziel der ansagenden Partei (zum Beispiel 151 Augen bei „keine 90“).",
  },
  { type: "h2", text: "Zählung und Sonderpunkte" },
  {
    type: "ul",
    items: [
      "Ein gewonnenes Spiel bringt 1 Punkt.",
      "Je 1 Zusatzpunkt für unter 90, unter 60, unter 30 Augen und für „schwarz“.",
      "Je 2 Punkte für die Ansage Re oder Kontra, je 1 Punkt für jede Absage.",
      "Sonderpunkte im Normalspiel: Kontra gewinnt gegen die Alten, ein Doppelkopf (Stich mit mindestens 40 Augen), ein gefangener Fuchs (gegnerisches Karo-Ass) und Karlchen (letzter Stich mit dem Kreuz-Buben).",
      "Im Solo zählt das Ergebnis für die Solistin oder den Solisten dreifach, Sonderpunkte gibt es dort nicht.",
    ],
  },
  { type: "h2", text: "Hausregeln auf DOPPELKOPF.CC" },
  {
    type: "p",
    text:
      "Jeder Tisch stellt vor der ersten Runde ein, welche Regeln gelten. Zur Auswahl stehen unter anderem: Spiel mit oder ohne Dullen, " +
      "scharfer Doppelkopf (ohne Neunen, 40 Karten), Schweinchen, Armut, Pflichtansagen, Bockrunden (bei Herzstich, Nullspiel oder 120 Augen), " +
      "„zweite Dulle sticht die erste“, Karlchen, Fuchsjagd und weitere. Die Standardeinstellung folgt den DDV-Turnierregeln.",
  },
  { type: "h3", text: "Armut (Hausregel)" },
  {
    type: "p",
    text:
      "Mit der Hausregel „Armut“ darf, wer höchstens drei Trümpfe hat, als Vorbehalt eine Armut anmelden. Er legt drei Karten verdeckt ab – immer drei, " +
      "auch bei weniger Trümpfen, damit die anderen im Unklaren bleiben. Reihum, im Uhrzeigersinn, wird gefragt, wer die Armut übernimmt. " +
      "Wer zusagt, nimmt die drei Karten in sein Blatt und gibt danach drei beliebige Karten an den Armen zurück. Gespielt wird ein Normalspiel, " +
      "in dem der Arme und der Käufer automatisch zusammen die Partei Re bilden, gegen die anderen beiden (Kontra); die Kreuz-Damen spielen dafür keine Rolle. " +
      "Übernimmt niemand die Armut, wird das Blatt eingepackt und vom selben Geber neu gegeben. " +
      "Die Armut gehört nicht zu den DDV-Turnierregeln.",
  },
  { type: "h2", text: "Hinweis" },
  {
    type: "p",
    text:
      "Diese Seite fasst die Regeln zusammen und erhebt keinen Anspruch auf Vollständigkeit. Maßgeblich sind die Turnierspielregeln des Deutschen Doppelkopf-Verbands (DDV), Stand 21.02.2026. " +
      "DOPPELKOPF.CC ist ein unabhängiges Projekt und steht in keiner Verbindung zum DDV.",
  },
];
