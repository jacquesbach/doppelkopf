// Zustand eines Tisches: Raum (Lobby), Spielsicht, Chat und Verbindung. Die Oberfläche ruft nur Methoden auf.
import { ApiError } from "./api.js";
import { chatToast, describeEvent, justFinished, newEvents, redealToast } from "./events.js";
import { createRoomSocket } from "./socket.js";
import { REVEAL_MS, declarationsJustClosed } from "./view.js";

// Antwortet der Server (auch mit einem Fehler wie 404/409), besteht die Verbindung; Netzwerkfehler und 502–504 nicht.
const RESULT_DELAY_MS = 4500; // so lange bleibt der letzte Stich sichtbar, bevor das Ergebnis aufgeht

const reachable = (e) => e instanceof ApiError && e.status > 0 && e.status < 502;

export class TableStore {
  room = $state(null);
  view = $state(null);
  viewAt = $state(0); // Empfangszeit (ms) der aktuellen Sicht: Basis für lokal weiterlaufende Countdowns
  chat = $state([]);
  // connecting | online | offline. „online“ gilt, solange Socket ODER regelmäßige HTTP-Abrufe funktionieren:
  // Fällt nur der Push-Kanal aus (z. B. Proxy), läuft der Tisch dank Nachladen weiter und ist nicht „offline“.
  connection = $state("connecting");
  #socketStatus = "connecting";
  #httpOk = true;
  status = $state("loading"); // loading | ready | needs_join | not_found | error
  error = $state("");
  busy = $state(false);
  session = $state(null);
  toasts = $state([]); // kurze Hinweise auf Ansagen/Spielereignisse/Chat
  unread = $state(0); // ungelesene Chatnachrichten (solange der Chat geschlossen ist)
  chatOpen = false;
  // Nummer des Spiels, dessen Ergebnis noch zurückgehalten wird, damit man den letzten Stich in Ruhe ansehen kann.
  resultDelayGame = $state(null);
  // Nummer des Spiels, dessen Vorbehalts-Antworten nach der Abfrage noch kurz sichtbar bleiben.
  revealGame = $state(null);
  // Nachricht des Betreibers: { message, closed } – bei closed ist der Tisch beendet.
  notice = $state(null);

  #deps;
  #socket = null;
  #timers = [];
  code;

  constructor(code, deps) {
    this.code = code;
    this.#deps = deps;
  }

  get token() {
    return this.session?.token ?? null;
  }
  get me() {
    return this.room?.players.find((p) => p.isMe) ?? null;
  }
  get isHost() {
    return !!this.me?.isHost;
  }

  async init() {
    const { api, sessions } = this.#deps;
    this.session = sessions.get(this.code);
    if (!this.session) {
      this.status = "needs_join";
      return;
    }
    try {
      const { room } = await api.getRoom(this.code, this.token);
      if (!room.players.some((p) => p.isMe)) {
        sessions.remove(this.code); // Token gehört nicht (mehr) zu diesem Raum
        this.session = null;
        this.status = "needs_join";
        return;
      }
      this.room = room;
      if (room.status !== "waiting") {
        await this.refreshGame();
        // Wer zurückkommt, übernimmt den Platz wieder vom Bot (Seite offen = anwesend).
        if (this.view?.table.mySeat != null && this.view.table.seats[this.view.table.mySeat]?.autoplay) await this.resume();
      }
      this.status = "ready";
      this.#loadChat();
      this.#connect();
      this.#timers.push(setInterval(() => this.#heartbeat(), 5000)); // „verbunden“-Anzeige aktuell halten
      this.#timers.push(setInterval(() => this.#pollGame(), 3000)); // Sicherheitsnetz, falls Push-Nachrichten ausbleiben
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) this.status = "not_found";
      else {
        this.status = "error";
        this.error = e.message;
      }
    }
  }

  destroy() {
    this.#socket?.close();
    this.#socket = null;
    this.#timers.forEach((t) => (clearInterval(t), clearTimeout(t)));
    this.#timers = [];
  }

  #connect() {
    const { ioFactory, origin } = this.#deps.realtime;
    this.#socket = createRoomSocket({
      ioFactory,
      origin,
      code: this.code,
      token: this.token,
      handlers: {
        onStatus: (s) => {
          this.#socketStatus = s;
          this.#syncConnection();
        },
        onRoom: (room) => this.#applyRoom(room),
        onGame: (view) => this.#applyView(view),
        onChat: (m) => this.#addChat(m, true),
        onError: (e) => this.#fail(e?.error ?? e?.message ?? "Verbindungsfehler"),
        onNotice: (n) => this.#receiveNotice(n),
      },
    });
  }

  #syncConnection() {
    this.connection =
      this.#socketStatus === "online" || this.#httpOk ? "online" : this.#socketStatus === "connecting" ? "connecting" : "offline";
  }

  #applyRoom(room) {
    // Das Server-Ereignis kennt „isMe“ nicht (es geht an alle): aus der bisherigen Sicht übernehmen.
    const myId = this.session?.memberId ?? this.me?.id;
    this.room = { ...room, players: room.players.map((p) => ({ ...p, isMe: p.id === myId })) };
  }

  #applyView(view) {
    if (this.view && view.version < this.view.version) return;
    this.#announce(newEvents(this.view, view), view);
    const redeal = redealToast(this.view, view);
    if (redeal) this.#pushToast(redeal);
    if (justFinished(this.view, view)) this.#holdResult(view.table.gameNumber);
    if (declarationsJustClosed(this.view, view)) this.#holdDeclarations(view.table.gameNumber);
    this.#setView(view);
  }

  /** Nach der letzten Antwort der Vorbehaltsabfrage bleiben alle Antworten noch einen Moment sichtbar. */
  #holdDeclarations(gameNumber) {
    this.revealGame = gameNumber;
    this.#timers.push(setTimeout(() => {
      if (this.revealGame === gameNumber) this.revealGame = null;
    }, REVEAL_MS));
  }

  #receiveNotice(notice) {
    const message = typeof notice?.message === "string" ? notice.message : "";
    if (!message) return;
    this.notice = { message, closed: !!notice.closed };
    if (notice.closed) this.#deps.sessions.remove(this.code); // der Tisch ist weg: Platz vergessen
  }

  dismissNotice() {
    this.notice = null;
  }

  #setView(view) {
    this.view = view;
    this.viewAt = Date.now();
  }

  /** Ergebnisfenster kurz zurückhalten: Der letzte Stich bleibt sichtbar, bis der Hinweis abläuft oder man ihn überspringt. */
  #holdResult(gameNumber) {
    this.resultDelayGame = gameNumber;
    this.#timers.push(setTimeout(() => this.showResultNow(gameNumber), RESULT_DELAY_MS));
  }

  showResultNow(gameNumber = this.resultDelayGame) {
    if (this.resultDelayGame === gameNumber) this.resultDelayGame = null;
  }

  #announce(events, view) {
    for (const e of events) {
      const info = describeEvent(view, e);
      if (!info) continue;
      this.#pushToast({ key: `${view.table.gameNumber}.${view.table.redeals ?? 0}-${e.id}`, ...info });
    }
  }

  #pushToast(toast) {
    if (this.toasts.some((t) => t.key === toast.key)) return;
    this.toasts = [...this.toasts, toast].slice(-3);
    this.#timers.push(setTimeout(() => this.dismissToast(toast.key), toast.ms ?? 4500));
  }

  dismissToast(key) {
    this.toasts = this.toasts.filter((t) => t.key !== key);
  }

  #addChat(message, live = false) {
    if (this.chat.some((m) => m.id === message.id)) return;
    this.chat = [...this.chat, message].slice(-100);
    // Nur live eingehende Nachrichten anderer melden; beim Nachladen des Verlaufs und für eigene Nachrichten nicht.
    const mine = message.memberId === (this.session?.memberId ?? this.me?.id);
    if (!live || mine || this.chatOpen) return;
    this.unread += 1;
    this.#pushToast(chatToast(message));
  }

  /** Der Chat-Dialog wird geöffnet/geschlossen: offen = alles gelesen, keine Hinweise. */
  setChatOpen(open) {
    this.chatOpen = open;
    if (open) {
      this.unread = 0;
      if (this.toasts.some((t) => t.kind === "chat")) this.toasts = this.toasts.filter((t) => t.kind !== "chat");
    }
  }

  async #loadChat() {
    try {
      this.chat = (await this.#deps.api.chatHistory(this.code, this.token)).messages;
    } catch {
      /* Chat ist optional */
    }
  }

  /**
   * Holt den Spielstand regelmäßig nach. Bots spielen im Hintergrund des Servers; kommt ihr Push nicht an
   * (Proxy ohne WebSocket, kurzer Verbindungsabbruch), bliebe der Tisch sonst scheinbar stehen.
   * Der Abruf stößt serverseitig außerdem die Bot-Schleife erneut an.
   */
  async #pollGame() {
    if (this.status !== "ready" || this.busy || this.room?.status !== "playing") return;
    try {
      this.#applyView(await this.#deps.api.getGame(this.code, this.token));
      this.#httpOk = true;
    } catch (e) {
      this.#httpOk = reachable(e);
    }
    this.#syncConnection();
  }

  async #heartbeat() {
    try {
      const { room } = await this.#deps.api.getRoom(this.code, this.token);
      this.room = room;
      this.#httpOk = true;
    } catch (e) {
      this.#httpOk = reachable(e);
    }
    this.#syncConnection();
  }

  #fail(message) {
    this.error = message;
    setTimeout(() => {
      if (this.error === message) this.error = "";
    }, 6000);
  }

  clearError() {
    this.error = "";
  }

  async refreshGame() {
    try {
      this.#setView(await this.#deps.api.getGame(this.code, this.token));
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 404)) this.#fail(e.message);
    }
  }

  /** Führt eine Server-Aktion mit Fehlerbehandlung aus. */
  async #run(fn) {
    if (this.busy) return null;
    this.busy = true;
    try {
      return await fn();
    } catch (e) {
      if (e instanceof ApiError && e.isVersionConflict) await this.refreshGame();
      else this.#fail(e.message);
      return null;
    } finally {
      this.busy = false;
    }
  }

  // --- Lobby ---
  async setReady(ready) {
    const res = await this.#run(() => this.#deps.api.setReady(this.code, this.token, ready));
    if (res) this.room = res.room;
  }
  async setPublic(isPublic) {
    const res = await this.#run(() => this.#deps.api.setVisibility(this.code, this.token, isPublic));
    if (res) this.room = res.room;
  }
  async addBots() {
    const res = await this.#run(() => this.#deps.api.addBot(this.code, this.token));
    if (res) this.room = res.room;
  }
  async saveSettings(settings) {
    const res = await this.#run(() => this.#deps.api.saveSettings(this.code, this.token, settings));
    if (res && this.room) this.room = { ...this.room, settings: res.settings, profileId: res.profileId };
    return !!res;
  }
  async start() {
    const res = await this.#run(() => this.#deps.api.start(this.code, this.token));
    if (res) {
      this.#setView(res.view);
      const { room } = await this.#deps.api.getRoom(this.code, this.token);
      this.room = room;
    }
  }
  async leave() {
    const res = await this.#run(() => this.#deps.api.leave(this.code, this.token));
    if (res) this.#deps.sessions.remove(this.code);
    return !!res;
  }
  async sendChat(text) {
    const res = await this.#run(() => this.#deps.api.chatPost(this.code, this.token, text));
    if (res) this.#addChat(res.message);
    return !!res;
  }

  // --- Spiel ---
  async act(action) {
    const res = await this.#run(() => this.#deps.api.action(this.code, this.token, action, this.view?.version));
    if (res?.view) this.#applyView(res.view);
  }
  /** „Nächster Stich“ (Spiel gegen Bots). */
  async continueTrick() {
    const res = await this.#run(() => this.#deps.api.continueGame(this.code, this.token));
    if (res?.view) this.#applyView(res.view);
  }
  /** Tisch verlassen, während die Runde läuft: ein Bot spielt weiter, die Sitzung bleibt für den Wiedereintritt. */
  async leaveGame() {
    return !!(await this.#run(() => this.#deps.api.away(this.code, this.token)));
  }
  async resume() {
    const res = await this.#run(() => this.#deps.api.back(this.code, this.token));
    if (res?.view) this.#applyView(res.view);
  }
  /** „Weiterspielen“ im Countdown der Bot-Übernahme; `remember`: true = nie ersetzen, false = wieder zulassen. */
  async stay(remember) {
    const res = await this.#run(() => this.#deps.api.stay(this.code, this.token, remember));
    if (res?.view) this.#applyView(res.view);
    return !!res;
  }
  /** Host: nach wie vielen Sekunden Inaktivität ein Bot übernimmt (0 = nie). */
  async setTakeover(seconds) {
    const res = await this.#run(() => this.#deps.api.setTakeover(this.code, this.token, seconds));
    if (res && this.room) this.room = { ...this.room, botTakeover: res.seconds };
    return !!res;
  }
  playCard(cardId) {
    return this.act({ type: "play_card", cardId });
  }
  async nextGame() {
    const res = await this.#run(() => this.#deps.api.next(this.code, this.token));
    if (res?.view) this.#applyView(res.view);
  }
  async loadHistory() {
    const res = await this.#run(() => this.#deps.api.history(this.code, this.token));
    return res?.games ?? [];
  }
}
