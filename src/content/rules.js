// Inhalt der Seite /regeln. Eine Quelle für zwei Verwendungen:
//  - src/pages/Rules.svelte zeigt ihn im Browser an (mit gezeichneten Spielkarten und Inhaltsverzeichnis),
//  - scripts/seo-build.mjs schreibt ihn beim Build als statisches HTML (für Suchmaschinen und Besucher ohne JavaScript).
//
// Blocktypen (alles reiner Text, kein HTML):
//   h2     { id, text, short }       Abschnitt; `id` ist der Sprungmarker, `short` die Kurzfassung für das Inhaltsverzeichnis
//   h3     { text }                  Unterabschnitt
//   p      { text }                  Absatz
//   ul/ol  { items }                 Liste
//   table  { head, rows }            Tabelle (Zellen sind Text)
//   note   { title, text }           hervorgehobener Merksatz
//   cards  { title?, groups, note?, skipStatic? }
//                                    Spielkarten. `groups`: [{ label?, items: [Karte, …] }].
//                                    Eine Karte ist "10♥" oder { c: "10♥", cap: "Dulle", win: true }.
//                                    `win` markiert die Karte, die einen Stich gewinnt.
//                                    `skipStatic`: im statischen HTML weglassen (wenn der Text schon dasselbe sagt).
// Grundlage: DDV-Turnierspielregeln (Stand 21.02.2026), Umsetzung siehe docs/DDV_REGELMATRIX.md.

import { cardName } from "../lib/cards.js";

export const RULES_TITLE = "Doppelkopf-Regeln einfach erklärt";
export const RULES_LEAD =
  "Doppelkopf ist ein Stichspiel für vier Personen, das sich schnell lernen lässt und lange spannend bleibt. " +
  "Diese Seite erklärt es von Grund auf: Karten, Trümpfe, Spielablauf, Re und Kontra, Solospiele, Ansagen und Zählung. " +
  "Es gelten die DDV-Turnierregeln, so wie sie auf DOPPELKOPF.CC umgesetzt sind. Die Kartenbilder zeigen die Karten jeweils von der höchsten zur niedrigsten.";

export const RULES = [
  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "ueberblick", short: "Überblick", text: "Das Spiel in Kürze" },
  {
    type: "p",
    text:
      "Gespielt wird zu viert mit 48 Karten: Ass, Zehn, König, Dame, Bube und Neun in Kreuz, Pik, Herz und Karo, jede Karte doppelt. " +
      "Jede Person bekommt 12 Karten, es gibt also 12 Stiche. Die Karten tragen Augen (Punktwerte), insgesamt 240 Augen. " +
      "Zwei Parteien kämpfen um diese Augen: Re und Kontra.",
  },
  {
    type: "p",
    text:
      "Im Normalspiel gehört zu Re, wer eine Kreuz-Dame auf der Hand hat. Alle anderen spielen Kontra. Wer mit wem spielt, " +
      "ist zu Beginn geheim und zeigt sich erst im Lauf des Spiels. Re braucht zum Sieg mindestens 121 Augen, Kontra reichen 120.",
  },
  {
    type: "ol",
    items: [
      "Geben: Jede Person erhält 12 Karten.",
      "Vorbehalte: Wer ein Solo spielen will oder eine Besonderheit hat, meldet das an, bevor die erste Karte fällt.",
      "Spielen: In 12 Stichen legt jede Person reihum eine Karte. Der höchste Trumpf oder die höchste Karte der angespielten Farbe gewinnt.",
      "Ansagen: Wer sich seiner Sache sicher ist, sagt „Re“ oder „Kontra“ an und erhöht damit den Einsatz.",
      "Zählen: Die Augen der gewonnenen Stiche werden pro Partei addiert. Daraus ergeben sich die Spielpunkte.",
    ],
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "karten", short: "Karten und Augen", text: "Die Karten und ihre Augen" },
  {
    type: "p",
    text:
      "Das Blatt besteht aus sechs Kartenwerten in vier Farben (Kreuz ♣, Pik ♠, Herz ♥, Karo ♦). Jede der 24 Karten gibt es zweimal. " +
      "Auf den Karten stehen A (Ass), 10, K (König), D (Dame), B (Bube) und 9. Beim Zählen interessieren nur die Augen:",
  },
  {
    type: "cards",
    title: "Kartenwerte in Augen",
    skipStatic: true,
    groups: [
      {
        items: [
          { c: "A♣", cap: "Ass: 11" },
          { c: "10♠", cap: "Zehn: 10" },
          { c: "K♥", cap: "König: 4" },
          { c: "Q♦", cap: "Dame: 3" },
          { c: "J♣", cap: "Bube: 2" },
          { c: "9♠", cap: "Neun: 0" },
        ],
      },
    ],
  },
  {
    type: "table",
    head: ["Karte", "Augen", "Anzahl im Spiel", "Augen insgesamt"],
    rows: [
      ["Ass", "11", "8", "88"],
      ["Zehn", "10", "8", "80"],
      ["König", "4", "8", "32"],
      ["Dame", "3", "8", "24"],
      ["Bube", "2", "8", "16"],
      ["Neun", "0", "8", "0"],
      ["Alle Karten", "", "48", "240"],
    ],
  },
  {
    type: "note",
    title: "Merke",
    text:
      "240 Augen sind im Spiel, die Hälfte sind 120. Wer 121 Augen oder mehr holt, hat die Mehrheit. Bei genau 120 zu 120 gewinnt Kontra, denn Re muss mindestens 121 Augen holen.",
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "trumpf", short: "Trumpf", text: "Trumpf im Normalspiel" },
  {
    type: "p",
    text:
      "Das Besondere am Doppelkopf: Die Trümpfe sind nicht eine Farbe, sondern eine feste Gruppe aus Karten verschiedener Farben. " +
      "Im Normalspiel sind 26 der 48 Karten Trumpf, also mehr als die Hälfte. Jeder Trumpf sticht jede Fehlfarbe, und unter den Trümpfen gilt diese Reihenfolge, " +
      "von der höchsten zur niedrigsten Karte:",
  },
  {
    type: "cards",
    title: "Die 13 Trumpfkarten (jede doppelt vorhanden)",
    groups: [
      { label: "1. Höchster Trumpf", items: [{ c: "10♥", cap: "Dulle" }] },
      {
        label: "2. Die vier Damen",
        items: [{ c: "Q♣", cap: "Kreuz (Alte)" }, { c: "Q♠", cap: "Pik" }, { c: "Q♥", cap: "Herz" }, { c: "Q♦", cap: "Karo" }],
      },
      {
        label: "3. Die vier Buben",
        items: [{ c: "J♣", cap: "Kreuz (Karlchen)" }, { c: "J♠", cap: "Pik" }, { c: "J♥", cap: "Herz" }, { c: "J♦", cap: "Karo" }],
      },
      {
        label: "4. Die übrigen Karo-Karten",
        items: [{ c: "A♦", cap: "Ass (Fuchs)" }, { c: "10♦", cap: "Zehn" }, { c: "K♦", cap: "König" }, { c: "9♦", cap: "Neun" }],
      },
    ],
    note: "Damen und Buben sind immer stärker als die übrigen Karo-Karten. Unter den Damen und unter den Buben entscheidet die Farbe: Kreuz vor Pik vor Herz vor Karo.",
  },
  {
    type: "p",
    text:
      "Zusammengezählt ergibt das 2 Dullen, 8 Damen, 8 Buben und 8 Karo-Karten, also 26 Trumpfkarten. " +
      "Die Kreuz-Dame ist also kein Kreuz, sondern Trumpf, ebenso der Karo-König. Karo ist im Normalspiel die „Trumpffarbe“.",
  },
  {
    type: "note",
    title: "Gut zu wissen",
    text:
      "Die Dulle (Herz-Zehn) ist nur dann der höchste Trumpf, wenn „Dulle als Höchsttrumpf“ eingeschaltet ist. Das ist bei den DDV-Turnierregeln und auf DOPPELKOPF.CC der Standard. " +
      "Ohne Dulle ist die Herz-Zehn eine gewöhnliche Herz-Karte.",
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "fehlfarben", short: "Fehlfarben", text: "Fehlfarben" },
  {
    type: "p",
    text:
      "Alle Karten, die kein Trumpf sind, heißen Fehlfarben. Davon gibt es 22 Karten in den drei Farben Kreuz, Pik und Herz. " +
      "Damen, Buben und die Herz-Zehn fehlen in diesen Farben, weil sie Trumpf sind. Innerhalb einer Fehlfarbe gilt:",
  },
  {
    type: "cards",
    title: "Fehlfarben, von hoch nach niedrig",
    groups: [
      { label: "Kreuz", items: ["A♣", "10♣", "K♣", "9♣"] },
      { label: "Pik", items: ["A♠", "10♠", "K♠", "9♠"] },
      { label: "Herz (die Zehn ist die Dulle)", items: ["A♥", "K♥", "9♥"] },
    ],
    note: "Es gibt keine Fehlfarbe Karo: Alle Karo-Karten sind Trumpf.",
  },
  {
    type: "table",
    head: ["Kartengruppe", "Anzahl Karten"],
    rows: [
      ["Trumpf (Dulle, Damen, Buben, Karo)", "26"],
      ["Fehlfarbe Kreuz (Ass, Zehn, König, Neun)", "8"],
      ["Fehlfarbe Pik (Ass, Zehn, König, Neun)", "8"],
      ["Fehlfarbe Herz (Ass, König, Neun)", "6"],
      ["Zusammen", "48"],
    ],
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "namen", short: "Karten mit Namen", text: "Karten mit Namen" },
  {
    type: "p",
    text: "Einige Karten haben im Spiel feste Namen, die du am Tisch ständig hörst:",
  },
  {
    type: "cards",
    skipStatic: true,
    groups: [
      {
        items: [
          { c: "10♥", cap: "Dulle" },
          { c: "Q♣", cap: "Alte" },
          { c: "J♣", cap: "Karlchen" },
          { c: "A♦", cap: "Fuchs" },
        ],
      },
    ],
  },
  {
    type: "ul",
    items: [
      "Dulle: die Herz-Zehn, der höchste Trumpf. Ihre 10 Augen sind gut aufgehoben, weil sie fast jeden Stich gewinnt.",
      "Alte: die Kreuz-Dame, die höchste Dame. Wer sie hat, spielt im Normalspiel Re.",
      "Karlchen: der Kreuz-Bube, der höchste Bube. Gewinnt er den letzten Stich, gibt es einen Sonderpunkt.",
      "Fuchs: das Karo-Ass, ein Trumpf mit 11 Augen. Fängt die Gegenpartei deinen Fuchs, bekommt sie einen Sonderpunkt.",
      "Schweinchen: beide Karo-Asse in einer Hand. Nur mit der Hausregel „Schweinchen“ spielt das eine Rolle (siehe Hausregeln).",
    ],
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "geben", short: "Geben", text: "Geben und Aufspielen" },
  {
    type: "ul",
    items: [
      "Die Karten werden in vier Päckchen zu je drei Karten verteilt, sodass jede Person 12 Karten bekommt.",
      "Nach jedem Normalspiel wechselt der Geber im Uhrzeigersinn.",
      "Gespielt wird im Uhrzeigersinn. Die Person links vom Geber spielt zum ersten Stich aus.",
      "Auf DOPPELKOPF.CC mischt und gibt der Tisch automatisch. Auch der Geberwechsel läuft von selbst.",
    ],
  },
  {
    type: "p",
    text:
      "Bevor die erste Karte fällt, schaut jede Person ihr Blatt an. Mit einem besonders starken oder besonders schwachen Blatt kann man einen Vorbehalt anmelden (siehe „Vorbehalte und Sonderspiele“). Sagt niemand etwas, wird ein normales Spiel gespielt.",
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "stich", short: "Der Stich", text: "Der Stich: bedienen und gewinnen" },
  {
    type: "p",
    text:
      "Ein Stich besteht aus vier Karten, eine pro Person. Die erste Karte bestimmt, was „angespielt“ ist: entweder Trumpf oder eine bestimmte Fehlfarbe. Die Regeln dafür sind kurz:",
  },
  {
    type: "ul",
    items: [
      "Bedienpflicht: Wurde Trumpf angespielt, musst du einen Trumpf legen, wenn du einen hast. Wurde eine Fehlfarbe angespielt, musst du eine Karte derselben Fehlfarbe legen, wenn du eine hast.",
      "Achtung bei Fehlfarben: Kreuz-Dame, Buben und Herz-Zehn zählen nicht als Kreuz oder Herz, sondern als Trumpf. Wird ein Kreuz-Ass angespielt, kannst du mit der Kreuz-Dame nicht bedienen.",
      "Kannst du nicht bedienen, darfst du jede beliebige Karte legen. Legst du einen Trumpf auf eine Fehlfarbe, stichst du sie.",
      "Den Stich gewinnt der höchste Trumpf. Liegt kein Trumpf im Stich, gewinnt die höchste Karte der angespielten Farbe. Karten anderer Fehlfarben können nie gewinnen.",
      "Liegen zwei völlig gleiche Karten im Stich, gewinnt die zuerst gespielte.",
      "Wer den Stich gewinnt, nimmt ihn an sich und spielt zum nächsten aus. Nach 12 Stichen ist das Spiel zu Ende.",
    ],
  },
  {
    type: "cards",
    title: "Beispiel 1: Fehlfarbe angespielt, ein Trumpf sticht",
    groups: [
      {
        items: [
          { c: "K♠", cap: "Anna spielt aus" },
          { c: "A♠", cap: "Ben bedient" },
          { c: "9♦", cap: "Clara hat kein Pik und sticht", win: true },
          { c: "10♠", cap: "Dirk bedient" },
        ],
      },
    ],
    note: "Selbst die kleinste Trumpfkarte, die Karo-Neun, schlägt das Pik-Ass. Clara gewinnt den Stich mit 4 + 11 + 0 + 10 = 25 Augen.",
  },
  {
    type: "cards",
    title: "Beispiel 2: Trumpf angespielt",
    groups: [
      {
        items: [
          { c: "J♦", cap: "Anna spielt Trumpf aus" },
          { c: "Q♠", cap: "Ben bedient mit Trumpf" },
          { c: "A♦", cap: "Clara bedient mit Trumpf" },
          { c: "10♥", cap: "Dirk legt die Dulle", win: true },
        ],
      },
    ],
    note: "Die Dulle ist der höchste Trumpf. Dirk gewinnt 2 + 3 + 11 + 10 = 26 Augen und spielt als Nächster aus.",
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "parteien", short: "Re und Kontra", text: "Re und Kontra: die Parteien" },
  {
    type: "p",
    text:
      "Im Normalspiel halten genau zwei Personen je eine Kreuz-Dame (die „Alten“). Diese beiden bilden die Partei Re und spielen gemeinsam. " +
      "Die anderen beiden bilden die Partei Kontra. Niemand sagt es laut, jede Person weiß zu Beginn nur, auf welcher Seite sie selbst steht.",
  },
  {
    type: "cards",
    title: "Wer eine Kreuz-Dame hat, spielt Re",
    skipStatic: true,
    groups: [{ items: [{ c: { rank: "Q", suit: "♣", copy: 0 }, cap: "Re" }, { c: { rank: "Q", suit: "♣", copy: 1 }, cap: "Re (die Partnerin oder der Partner)" }] }],
  },
  {
    type: "p",
    text:
      "Die Zugehörigkeit wird sichtbar, sobald jemand eine Kreuz-Dame ausspielt oder „Re“ beziehungsweise „Kontra“ ansagt. " +
      "Auch wer auf einen angespielten Trumpf keinen Trumpf legt, zeigt damit, dass er keine Kreuz-Dame hat und also zu Kontra gehört. " +
      "Am Ende zählen alle Augen aus Stichen von Re-Spielern für Re, alle anderen für Kontra.",
  },
  {
    type: "note",
    title: "Gut zu wissen",
    text:
      "Gewinnt Kontra, gibt es einen Extrapunkt „gegen die Alten“. Kontra hat also ein kleines Plus, weil Re mit den Kreuz-Damen zunächst das stärkere Blatt hält.",
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "vorbehalte", short: "Vorbehalte und Solo", text: "Vorbehalte und Sonderspiele" },
  {
    type: "p",
    text:
      "Vor dem ersten Stich fragt der Tisch reihum, beginnend links vom Geber, ob jemand einen Vorbehalt anmeldet. Wer gesund ist, also ein normales Blatt hat, verneint. " +
      "Ein Vorbehalt bedeutet, dass nicht das normale Spiel gespielt wird, sondern ein Sonderspiel.",
  },
  {
    type: "ul",
    items: [
      "Melden mehrere Personen einen Vorbehalt an, entscheidet die Rangfolge: erst das Pflichtsolo, dann das Lustsolo, danach (nur mit der Hausregel) die Armut.",
      "Eine Hochzeit kommt bei mehreren Vorbehalten nicht zum Zug, ein Solo geht vor.",
      "Wer ein Pflichtsolo spielt, spielt zum ersten Stich selbst aus.",
    ],
  },

  { type: "h3", text: "Solospiele" },
  {
    type: "p",
    text:
      "Beim Solo spielt eine Person (die Solistin oder der Solist) allein als Re gegen alle drei anderen. Sie bestimmt, welches Solo gespielt wird. " +
      "Es gibt sieben Arten, die sich nur in der Frage unterscheiden, welche Karten Trumpf sind: vier Farbsoli, das Damensolo, das Bubensolo und den Fleischlosen.",
  },
  {
    type: "cards",
    title: "Farbsolo (Beispiel Kreuz-Solo)",
    groups: [
      { label: "Dulle", items: ["10♥"] },
      { label: "Damen", items: ["Q♣", "Q♠", "Q♥", "Q♦"] },
      { label: "Buben", items: ["J♣", "J♠", "J♥", "J♦"] },
      { label: "Kreuz statt Karo", items: ["A♣", "10♣", "K♣", "9♣"] },
    ],
    note:
      "Beim Farbsolo ersetzt die gewählte Farbe das Karo als Trumpffarbe. Bei Kreuz, Pik oder Karo sind es weiterhin 26 Trümpfe, im Herz-Solo 24, weil die Herz-Zehn schon als Dulle ganz oben steht. " +
      "Wird nicht Karo gewählt, ist Karo eine gewöhnliche Fehlfarbe.",
  },
  {
    type: "cards",
    title: "Damensolo: nur die vier Damen sind Trumpf",
    groups: [{ items: [{ c: "Q♣", cap: "Kreuz" }, { c: "Q♠", cap: "Pik" }, { c: "Q♥", cap: "Herz" }, { c: "Q♦", cap: "Karo" }] }],
    note: "Alle anderen Karten sind Fehlfarben. In jeder Farbe gilt dann Ass, Zehn, König, Bube, Neun. Auch die Herz-Zehn ist hier eine gewöhnliche Herz-Karte.",
  },
  {
    type: "cards",
    title: "Bubensolo: nur die vier Buben sind Trumpf",
    groups: [{ items: [{ c: "J♣", cap: "Kreuz" }, { c: "J♠", cap: "Pik" }, { c: "J♥", cap: "Herz" }, { c: "J♦", cap: "Karo" }] }],
    note: "In jeder Fehlfarbe gilt: Ass, Zehn, König, Dame, Neun.",
  },
  {
    type: "cards",
    title: "Fleischloser: ganz ohne Trumpf",
    groups: [{ label: "In jeder der vier Farben", items: ["A♠", "10♠", "K♠", "Q♠", "J♠", "9♠"] }],
    note: "Es gibt keinen Trumpf. Alle vier Farben sind gleichwertige Fehlfarben mit der Reihenfolge Ass, Zehn, König, Dame, Bube, Neun.",
  },
  {
    type: "ul",
    items: [
      "Pflichtsolo: Im Turnier muss jede Person im Lauf der Runde genau ein Solo spielen (siehe „Runde und Pflichtsolo“).",
      "Lustsolo: Ein freiwilliges Solo, erlaubt nach dem eigenen Pflichtsolo. Es zählt als Normalspiel, und die Person links vom Geber spielt aus.",
      "Gewertet wird ein Solo mit dem Dreifachen: Die Solistin oder der Solist erhält die dreifachen Spielpunkte, jede Gegnerin und jeder Gegner nur die einfachen. Sonderpunkte gibt es im Solo nicht.",
    ],
  },

  { type: "h3", text: "Hochzeit" },
  {
    type: "p",
    text:
      "Wer beide Kreuz-Damen auf der Hand hält, kann als Vorbehalt „Hochzeit“ anmelden und sucht damit eine Partnerin oder einen Partner. " +
      "Partner wird, wer als Erste oder Erster einen Stich gewinnt, den der Hochzeiter nicht selbst gemacht hat. Dieser Stich heißt Klärungsstich und fällt spätestens im dritten Stich. " +
      "Gewinnt der Hochzeiter die ersten drei Stiche allein, wird daraus ein Karo-Solo (Trümpfe wie im Normalspiel, gewertet wie ein Solo).",
  },
  {
    type: "ul",
    items: [
      "Bis zum Klärungsstich dürfen keine Ansagen gemacht werden. Danach gelten die üblichen Fristen, nur etwas später: Wird im 2. Stich geklärt, darf man eine Karte weniger auf der Hand haben, bei Klärung im 3. Stich zwei Karten weniger.",
      "Mit Partner wird die Hochzeit wie ein Normalspiel gewertet, mit allen Sonderpunkten.",
      "Wer beide Kreuz-Damen hat und „gesund“ sagt, spielt eine Stille Hochzeit: allein gegen drei, ohne Ankündigung. Gewertet wird wie ein Solo, die Fristen für Ansagen gelten wie im Normalspiel.",
    ],
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "ansagen", short: "Ansagen", text: "Ansagen und Absagen" },
  {
    type: "p",
    text:
      "Mit „Re“ beziehungsweise „Kontra“ kündigt eine Partei an, dass sie gewinnen wird. Mit Absagen („keine 90“, „keine 60“, „keine 30“, „schwarz“) legt sie noch eins drauf und verspricht, dass die Gegner nur sehr wenige Augen oder gar keinen Stich bekommen. " +
      "Wer richtig liegt, bekommt Extrapunkte, wer sich verschätzt, verliert entsprechend mehr. Ansagen sind nur in einem engen Zeitfenster möglich, und zwar abhängig davon, wie viele Karten du noch auf der Hand hast:",
  },
  {
    type: "table",
    head: ["Ansage", "Bedeutung", "Spätestens mit … Handkarten", "Ziel der ansagenden Partei"],
    rows: [
      ["Re / Kontra", "Wir gewinnen.", "11", "Re 121 Augen, Kontra 120 Augen"],
      ["keine 90", "Die Gegner bleiben unter 90 Augen.", "10", "mindestens 151 Augen"],
      ["keine 60", "Die Gegner bleiben unter 60 Augen.", "9", "mindestens 181 Augen"],
      ["keine 30", "Die Gegner bleiben unter 30 Augen.", "8", "mindestens 211 Augen"],
      ["schwarz", "Die Gegner bekommen keinen Stich.", "7", "alle Stiche"],
    ],
  },
  {
    type: "ul",
    items: [
      "Mit 11 Handkarten hast du gerade deine erste Karte gespielt. „Re“ oder „Kontra“ muss also spätestens gesagt sein, bevor du deine zweite Karte spielst.",
      "Eine Absage schließt die Ansage davor mit ein. Wer „keine 90“ sagt, hat damit auch „Re“ oder „Kontra“ gesagt, und das muss zu diesem Zeitpunkt noch erlaubt gewesen sein. Du darfst also Stufen überspringen, solange die übersprungenen noch erlaubt gewesen wären. Sie zählen dann mit.",
      "Erwiderung: Hat die Gegenpartei bereits angesagt, darfst du noch mit einer Handkarte weniger „Re“ oder „Kontra“ dagegen setzen. Nach so einer verspäteten Erwiderung sind aber keine Absagen mehr möglich.",
      "Eine Ansage gilt für die ganze Partei, auch wenn nur eine Person sie ausspricht. Sie kann nicht wiederholt oder zurückgenommen werden.",
    ],
  },
  {
    type: "p",
    text: "Was die Ansage bewirkt, merkst du am Gewinnziel:",
  },
  {
    type: "ul",
    items: [
      "Sagt nur Kontra an, braucht auch Kontra 121 Augen, und Re reichen 120. Die Ansage nimmt Kontra also den Vorteil, bei 120 zu 120 zu gewinnen.",
      "Sagt eine Partei eine Absage an, braucht sie das Ziel aus der Tabelle (zum Beispiel 151 Augen bei „keine 90“).",
      "Gegen eine Absage der Gegenpartei reicht ein geringeres Ziel: mindestens 90 Augen gegen „keine 90“, 60 gegen „keine 60“, 30 gegen „keine 30“ und ein einziger Stich gegen „schwarz“.",
    ],
  },
  {
    type: "note",
    title: "Ansagepflicht als Hausregel",
    text:
      "Mit der Hausregel „Ansagepflicht“ muss, wer den ersten Stich gewinnt, danach „Re“ oder „Kontra“ ansagen, bevor es weitergeht. Das gilt nur im Normalspiel und entfällt, wenn die Partei schon angesagt hat.",
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "wertung", short: "Gewinnen und Zählen", text: "Gewinnen und Zählen" },
  {
    type: "p",
    text:
      "Am Ende werden die Augen der gewonnenen Stiche je Partei addiert. Wer sein Ziel erreicht, gewinnt das Spiel. Die Spielpunkte setzen sich aus mehreren Posten zusammen, die alle für die Gewinnerpartei zählen:",
  },
  {
    type: "table",
    head: ["Posten", "Punkte", "Wann?"],
    rows: [
      ["Gewonnen", "1", "Die Partei hat ihr Ziel erreicht."],
      ["Unter 90", "+1", "Die Verlierer haben weniger als 90 Augen."],
      ["Unter 60", "+1", "Die Verlierer haben weniger als 60 Augen."],
      ["Unter 30", "+1", "Die Verlierer haben weniger als 30 Augen."],
      ["Schwarz", "+1", "Die Verlierer haben keinen einzigen Stich."],
      ["Re / Kontra angesagt", "+2 je Partei", "Jede Partei, die angesagt hat, bringt den Gewinnern zwei Punkte."],
      ["Absage", "+1 je Stufe", "Für jede Absage („keine 90“ bis „schwarz“), die eine Partei gemacht hat."],
      ["Absage geschlagen", "+1", "Eine Partei holt gegen die Absage der Gegner: 120 Augen gegen „keine 90“, 90 gegen „keine 60“, 60 gegen „keine 30“ oder 30 Augen gegen „schwarz“."],
    ],
  },
  {
    type: "p",
    text:
      "Die Punkte beider Parteien werden verrechnet. Am Ende bekommt jedes Mitglied der Gewinnerpartei die Differenz gutgeschrieben, jedes Mitglied der Verliererpartei bekommt sie abgezogen. " +
      "Erreicht ausnahmsweise keine Partei ihr Ziel, etwa weil beide ein hohes Ziel angesagt haben, gibt es keinen Sieger und weder Grundpunkt noch Ansagepunkte.",
  },
  { type: "h3", text: "Rechenbeispiele" },
  {
    type: "ul",
    items: [
      "Re gewinnt 130 zu 110 Augen, nichts angesagt: Re bekommt 1 Punkt (gewonnen). Jede Re-Person erhält +1, jede Kontra-Person −1.",
      "Kontra gewinnt 135 zu 105: 1 Punkt für den Sieg und 1 Sonderpunkt „gegen die Alten“, zusammen 2 Punkte.",
      "Re sagt „Re“ an und gewinnt 160 zu 80: 1 (gewonnen) + 2 (Re angesagt) + 1 (Kontra unter 90) = 4 Punkte.",
    ],
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "sonderpunkte", short: "Sonderpunkte", text: "Sonderpunkte" },
  {
    type: "p",
    text:
      "Im Normalspiel (auch in der Hochzeit mit Partner) gibt es zusätzlich Sonderpunkte. Sie gehören der Partei, die das Ereignis herbeiführt, und werden zu den Spielpunkten addiert. In Soli und in der Stillen Hochzeit gibt es sie nicht.",
  },
  {
    type: "table",
    head: ["Sonderpunkt", "Punkte", "Wann?"],
    rows: [
      ["Gegen die Alten", "1", "Kontra gewinnt das Spiel."],
      ["Doppelkopf", "1", "Ein Stich enthält mindestens 40 Augen. Der Punkt gehört der Partei, die den Stich macht, und gilt für jeden solchen Stich."],
      ["Fuchs gefangen", "1", "Ein Karo-Ass der Gegenpartei landet in deinem Stich. Gilt für jedes Karo-Ass einzeln."],
      ["Karlchen", "1", "Der letzte Stich wird mit dem Kreuz-Buben gewonnen."],
    ],
  },
  {
    type: "cards",
    title: "Beispiel: ein Doppelkopf (42 Augen)",
    groups: [
      {
        items: [
          { c: "A♠", cap: "11 Augen" },
          { c: "10♥", cap: "Dulle, 10 Augen", win: true },
          { c: "A♦", cap: "11 Augen" },
          { c: "10♦", cap: "10 Augen" },
        ],
      },
    ],
    note: "11 + 10 + 11 + 10 sind 42 Augen. Wer diesen Stich mit der Dulle gewinnt, holt einen Sonderpunkt für seine Partei. Dem Spiel hat dieser Stich seinen Namen gegeben.",
  },
  {
    type: "p",
    text:
      "Fuchsjagd und Karlchen-Punkt lassen sich in den Hausregeln abschalten, auf DOPPELKOPF.CC sind sie wie im Turnier eingeschaltet. Nicht zu den Turnierregeln gehört es, den gegnerischen Karlchen im letzten Stich abzufangen (Hausregel).",
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "runde", short: "Runde und Pflichtsolo", text: "Runde und Pflichtsolo" },
  {
    type: "p",
    text:
      "Ein Turnierabend besteht aus Runden. Eine Runde sind 24 Normalspiele, dazu spielt jede der vier Personen genau ein Pflichtsolo. Der Spielstand ist die Summe der Spielpunkte jeder Person.",
  },
  {
    type: "ul",
    items: [
      "Das Pflichtsolo zählt nicht zu den 24 Normalspielen. Nach einem freiwillig angemeldeten Pflichtsolo gibt derselbe Geber noch einmal.",
      "Wer sein Pflichtsolo noch nicht gespielt hat, wenn nur noch so viele Normalspiele übrig sind wie Pflichtsoli fehlen, wird „vorgeführt“: Die erste Person links vom Geber ohne Pflichtsolo muss es spielen, ohne gefragt zu werden.",
      "Ein Lustsolo ist erst nach dem eigenen Pflichtsolo erlaubt, zählt als Normalspiel, und der Geber wechselt danach.",
      "Am privaten Tisch gibt es kein Zeitlimit. Die Runde endet nach dem 24. Normalspiel.",
    ],
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "hausregeln", short: "Hausregeln", text: "Hausregeln auf DOPPELKOPF.CC" },
  {
    type: "p",
    text:
      "Der Tisch stellt vor der ersten Runde ein, welche Regeln gelten. Die Voreinstellung folgt den DDV-Turnierregeln: Eingeschaltet sind nur Dulle, Karlchen-Punkt und Fuchsjagd. Während einer Runde lassen sich die Regeln nicht mehr ändern.",
  },
  {
    type: "table",
    head: ["Regel", "Standard", "Wirkung"],
    rows: [
      ["Dulle als Höchsttrumpf", "an", "Die Herz-Zehn steht über allen anderen Trümpfen. Aus: gewöhnliche Herz-Karte."],
      ["Ohne Neunen (40 Karten)", "aus", "Die Neunen werden aussortiert. Jede Person bekommt 10 Karten, das Spiel dauert 10 Stiche."],
      ["Karlchen-Punkt", "an", "Sonderpunkt für den letzten Stich mit dem Kreuz-Buben."],
      ["Füchse jagen", "an", "Sonderpunkt für einen gefangenen Fuchs (Karo-Ass der Gegner)."],
      ["Ansagepflicht", "aus", "Wer den ersten Stich holt, muss „Re“ oder „Kontra“ ansagen. Nur im Normalspiel."],
      ["Solist kommt raus", "aus", "Wer ein Solo spielt, spielt auch im Lustsolo selbst aus."],
      ["Karlchen fangen", "aus", "Sonderpunkt, wenn im letzten Stich der Kreuz-Bube der Gegner in deinen Stich fällt."],
      ["Schweinchen", "aus", "Beide Karo-Asse in einer Hand dürfen zu den höchsten Trümpfen erklärt werden."],
      ["Armut", "aus", "Mit höchstens drei Trümpfen darf man Armut anmelden und drei Karten weitergeben."],
      ["Bock nach Herz-Stich", "aus", "Besteht ein Stich nur aus Herz-Fehlkarten, folgt eine Bockrunde."],
      ["Bock nach Nullspiel", "aus", "Bringt ein Spiel 0 Punkte, folgt eine Bockrunde."],
      ["Bock bei 120 zu 120", "aus", "Enden beide Parteien mit genau 120 Augen, folgt eine Bockrunde."],
      ["Zweite Dulle schlägt die erste", "aus", "Fallen beide Dullen in einen Stich, gewinnt die später gespielte."],
      ["Ausnahme im letzten Stich", "aus", "Im letzten Stich gewinnt trotzdem die zuerst gespielte Dulle."],
    ],
  },

  { type: "h3", text: "Schweinchen" },
  {
    type: "cards",
    skipStatic: true,
    groups: [
      {
        items: [
          { c: { rank: "A", suit: "♦", copy: 0 }, cap: "Schweinchen" },
          { c: { rank: "A", suit: "♦", copy: 1 }, cap: "Schweinchen" },
        ],
      },
    ],
  },
  {
    type: "p",
    text:
      "Wer beide Karo-Asse hält, darf sie vor der Wahl seiner ersten Karte zu den höchsten Trümpfen erklären, noch über der Dulle. " +
      "Die Erklärung ist öffentlich und gilt bis zum Ende des Spiels. Möglich ist das nur, wo das Karo-Ass Trumpf ist, also im Normalspiel, in der Hochzeit und im Karo-Solo. " +
      "Liegen beide Schweinchen im selben Stich, gewinnt das zuerst gespielte.",
  },

  { type: "h3", text: "Bockrunden" },
  {
    type: "p",
    text:
      "Ein Bockspiel ist ein Spiel, in dem alle Punkte doppelt zählen. Löst ein Spiel eine der eingeschalteten Bock-Regeln aus, zählen die nächsten vier Spiele doppelt. " +
      "Jede Bock-Regel kann pro Spiel nur einmal auslösen. Treffen zwei verschiedene Auslöser in einem Spiel zusammen, ergibt das acht Bockspiele hintereinander. " +
      "Jedes gespielte Spiel, auch ein Pflichtsolo, verbraucht ein Bockspiel. Ein Bockspiel kann selbst wieder eine neue Bockrunde auslösen.",
  },

  { type: "h3", text: "Zweite Dulle" },
  {
    type: "cards",
    skipStatic: true,
    groups: [
      {
        items: [
          { c: { rank: "10", suit: "♥", copy: 0 }, cap: "zuerst gespielt: gewinnt (Standard)" },
          { c: { rank: "10", suit: "♥", copy: 1 }, cap: "später gespielt: gewinnt (Hausregel)" },
        ],
      },
    ],
  },
  {
    type: "p",
    text:
      "Normalerweise gewinnt bei zwei gleichen Karten die zuerst gespielte, also auch die erste Dulle. " +
      "Mit der Hausregel „Zweite Dulle schlägt die erste“ ist es umgekehrt. Dazu lässt sich einstellen, dass im allerletzten Stich trotzdem die zuerst gespielte Dulle gewinnt.",
  },

  { type: "h3", text: "Armut" },
  {
    type: "p",
    text:
      "Mit der Hausregel „Armut“ darf, wer höchstens drei Trümpfe hat, als Vorbehalt eine Armut anmelden. Er legt drei Karten verdeckt ab, immer drei, " +
      "auch bei weniger Trümpfen, damit die anderen im Unklaren bleiben. Reihum, im Uhrzeigersinn, wird gefragt, wer die Armut übernimmt. " +
      "Wer zusagt, nimmt die drei Karten in sein Blatt und gibt danach drei beliebige Karten an den Armen zurück. Gespielt wird ein Normalspiel, " +
      "in dem der Arme und der Käufer automatisch zusammen die Partei Re bilden, gegen die anderen beiden (Kontra). Die Kreuz-Damen spielen dafür keine Rolle. " +
      "Übernimmt niemand die Armut, wird das Blatt eingepackt und vom selben Geber neu gegeben. " +
      "Die Armut gehört nicht zu den DDV-Turnierregeln.",
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "woerterbuch", short: "Kleines Wörterbuch", text: "Kleines Wörterbuch" },
  {
    type: "table",
    head: ["Begriff", "Bedeutung"],
    rows: [
      ["Augen", "Die Punktwerte der Karten (Ass 11, Zehn 10, König 4, Dame 3, Bube 2, Neun 0). Insgesamt 240."],
      ["Stich", "Vier Karten, eine pro Person. Die höchste Karte gewinnt alle vier."],
      ["Trumpf", "Karte, die jede Fehlfarbe sticht: Dulle, Damen, Buben und die Karo-Karten."],
      ["Fehlfarbe", "Jede Karte, die kein Trumpf ist (Kreuz, Pik, Herz)."],
      ["Bedienen", "Eine Karte der angespielten Farbe oder, bei Trumpf, einen Trumpf legen."],
      ["Stechen", "Mit einem Trumpf eine angespielte Fehlfarbe schlagen."],
      ["Re", "Die Partei mit der Kreuz-Dame („die Alten“)."],
      ["Kontra", "Die Partei ohne Kreuz-Dame."],
      ["Ansage / Absage", "Ankündigung eines Sieges beziehungsweise eines hohen Siegs (keine 90, 60, 30, schwarz)."],
      ["Schwarz", "Eine Partei hat keinen einzigen Stich."],
      ["Vorbehalt", "Meldung vor dem ersten Stich, dass kein normales Spiel gespielt wird."],
      ["Solo", "Eine Person spielt allein gegen drei. Gewertet mit dem Dreifachen."],
      ["Hochzeit", "Beide Kreuz-Damen in einer Hand. Der Partner wird im Spiel ermittelt."],
      ["Doppelkopf", "Ein Stich mit mindestens 40 Augen."],
      ["Bock", "Spiel, in dem alle Punkte doppelt zählen (Hausregel)."],
    ],
  },

  // ------------------------------------------------------------------------------------------------------------------
  { type: "h2", id: "hinweis", short: "Hinweis", text: "Hinweis" },
  {
    type: "p",
    text:
      "Diese Seite fasst die Regeln zusammen und erhebt keinen Anspruch auf Vollständigkeit. Maßgeblich sind die Turnierspielregeln des Deutschen Doppelkopf-Verbands (DDV), Stand 21.02.2026. " +
      "DOPPELKOPF.CC ist ein unabhängiges Projekt und steht in keiner Verbindung zum DDV.",
  },
];

// --- Hilfen für Anzeige und statisches HTML ----------------------------------------------------------------------------

/** Einträge des Inhaltsverzeichnisses: alle Abschnitte (h2) mit Sprungmarke. */
export const RULES_TOC = RULES.filter((b) => b.type === "h2").map((b) => ({ id: b.id, label: b.short ?? b.text, text: b.text }));

/** "10♥" -> { rank: "10", suit: "♥", copy: 0 }; Objekte { rank, suit, copy } werden durchgereicht. */
export function parseCardCode(code) {
  if (typeof code !== "string") return { rank: code.rank, suit: code.suit, copy: code.copy ?? 0 };
  return { rank: code.slice(0, -1), suit: code.slice(-1), copy: 0 };
}

/** Normalisiert einen Karteneintrag eines `cards`-Blocks zu { card, cap, win }. */
export function cardEntry(entry) {
  const spec = typeof entry === "string" ? { c: entry } : entry;
  return { card: parseCardCode(spec.c), cap: spec.cap ?? "", win: Boolean(spec.win) };
}

/** Lesbarer Text eines Karteneintrags (für das statische HTML), z. B. "Herz Zehn (Dulle)". */
export function cardEntryText(entry) {
  const { card, cap, win } = cardEntry(entry);
  const extra = [cap, win ? "gewinnt den Stich" : ""].filter(Boolean).join(", ");
  return extra ? `${cardName(card)} (${extra})` : cardName(card);
}
